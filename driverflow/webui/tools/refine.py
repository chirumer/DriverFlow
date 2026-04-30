"""Refine tool — bypasses Pipeline.refine() (which is Colab-only).

Constructs a :class:`ClickSession` directly from request payload, marks
``done_event`` so ``apply_refinements`` does not block, and stores the
points / labels on the resulting version's ``extra`` so the data-workspace
card can re-render the click overlay later.
"""

from __future__ import annotations

from ...refine import ClickSession
from ..state import ItemVersion
from . import register
from .base import Tool, ToolContext, ToolError


class RefineTool(Tool):
    name = "refine"
    label = "Refine"
    requires_model = "sam"
    requires_input_kind = "segmented"
    media_types = ("image",)
    params_schema = [
        # The actual click collection happens in the front-end canvas overlay.
        # The tool body still expects {points, labels} in the request payload.
        {"name": "points", "type": "points", "default": [],
         "label": "Refinement Points"},
        {"name": "labels", "type": "labels", "default": [],
         "label": "Point Labels"},
    ]

    def run(self, ctx: ToolContext, parent: ItemVersion, **params) -> ItemVersion:
        if ctx.pipeline.sam_predictor is None:
            raise ToolError("SAM 2 model is not loaded.")
        if parent.kind not in ("segmented", "refined"):
            raise ToolError("Refine requires pixel masks (run Segment first).")

        points = list(params.get("points") or [])
        labels = list(params.get("labels") or [])
        if len(points) != len(labels):
            raise ToolError("Refine: points and labels must have the same length.")
        if not points:
            raise ToolError("Refine: at least one click is required.")

        seg = parent.payload
        session = ClickSession(seg)
        session.points = [tuple(float(c) for c in p) for p in points]
        session.labels = [int(lb) for lb in labels]
        session.done_event.set()  # apply_refinements will not block

        with ctx.pipeline_lock:
            refined = ctx.pipeline.apply_refinements(seg, session)

        return ItemVersion.make(
            kind="refined",
            payload=refined,
            parent_id=parent.id,
            summary={
                "n_points": int(len(points)),
                "n_masks": int(len(refined.masks)),
            },
            extra={"points": session.points, "labels": session.labels},
        )


register(RefineTool())
