"""Annotate tool — manually create Detections from drawn bounding boxes."""

from __future__ import annotations

import os
from collections import Counter

from ...types import Detections
from ..state import ItemVersion
from . import register
from .base import Tool, ToolContext, ToolError


class AnnotateTool(Tool):
    name = "annotate"
    label = "Annotate"
    requires_model = None
    requires_input_kind = "raw"
    media_types = ("image",)
    params_schema = [
        {"name": "boxes", "type": "boxes", "default": [], "label": "Bounding Boxes"},
    ]

    def run(self, ctx: ToolContext, parent: ItemVersion, **params) -> ItemVersion:
        boxes_payload = list(params.get("boxes") or [])
        if not boxes_payload:
            raise ToolError("Annotate requires at least one bounding box.")

        import cv2
        import numpy as np

        image_source = _payload_to_rgb(parent.payload)
        height, width = image_source.shape[:2]

        boxes_xyxy = []
        boxes_cxcywh = []
        phrases = []
        for raw in boxes_payload:
            try:
                x1 = float(raw["x1"])
                y1 = float(raw["y1"])
                x2 = float(raw["x2"])
                y2 = float(raw["y2"])
                label = str(raw.get("label") or "").strip()
            except (KeyError, TypeError, ValueError) as e:
                raise ToolError(f"Annotate received an invalid box: {raw!r}") from e

            if not label:
                raise ToolError("Annotate requires a class label for every box.")

            x1, x2 = sorted((max(0.0, min(float(width), x1)), max(0.0, min(float(width), x2))))
            y1, y2 = sorted((max(0.0, min(float(height), y1)), max(0.0, min(float(height), y2))))
            if x2 - x1 < 1 or y2 - y1 < 1:
                raise ToolError("Annotate boxes must be at least 1 pixel wide and tall.")

            boxes_xyxy.append([x1, y1, x2, y2])
            boxes_cxcywh.append([
                ((x1 + x2) / 2.0) / width,
                ((y1 + y2) / 2.0) / height,
                (x2 - x1) / width,
                (y2 - y1) / height,
            ])
            phrases.append(label)

        det = Detections(
            image_source=image_source,
            image_tensor=None,  # Manual annotations do not have a DINO tensor.
            boxes_cxcywh_norm=np.asarray(boxes_cxcywh, dtype=float),
            boxes_xyxy=np.asarray(boxes_xyxy, dtype=float),
            scores=np.ones((len(phrases),), dtype=float),
            phrases=phrases,
            image_width=int(width),
            image_height=int(height),
        )

        return ItemVersion.make(
            kind="detected",
            payload=det,
            parent_id=parent.id,
            summary={
                "source": "manual",
                "n_boxes": int(len(phrases)),
                "class_counts": dict(Counter(phrases)),
            },
        )


def _payload_to_rgb(payload):
    import cv2
    import numpy as np

    if isinstance(payload, (bytes, bytearray)):
        raw = bytes(payload)
    elif isinstance(payload, str) and os.path.exists(payload):
        with open(payload, "rb") as f:
            raw = f.read()
    else:
        raise ToolError("Annotate input is not a readable image payload.")

    arr = np.frombuffer(raw, dtype=np.uint8)
    bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if bgr is None:
        raise ToolError("Annotate input could not be decoded as an image.")
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)


register(AnnotateTool())
