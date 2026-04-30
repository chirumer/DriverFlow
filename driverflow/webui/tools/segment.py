"""Segment tool — wraps ``Pipeline.segment``. Requires bounding boxes."""

from __future__ import annotations

from ..state import ItemVersion
from . import register
from .base import Tool, ToolContext, ToolError


class SegmentTool(Tool):
    name = "segment"
    label = "Segment"
    requires_model = "sam"
    requires_input_kind = "detected"
    media_types = ("image",)
    params_schema = []

    def run(self, ctx: ToolContext, parent: ItemVersion, **params) -> ItemVersion:
        if ctx.pipeline.sam_predictor is None:
            raise ToolError("SAM 2 model is not loaded.")
        if parent.kind != "detected":
            raise ToolError("Segment requires bounding boxes (run Detect first).")

        det = parent.payload
        with ctx.pipeline_lock:
            seg = ctx.pipeline.segment(det)

        return ItemVersion.make(
            kind="segmented",
            payload=seg,
            parent_id=parent.id,
            summary={"n_masks": int(len(seg.masks))},
        )


register(SegmentTool())
