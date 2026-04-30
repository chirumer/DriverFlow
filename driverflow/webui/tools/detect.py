"""Detect tool — wraps ``Pipeline.detect``."""

from __future__ import annotations

import os
import tempfile
from collections import Counter

from ..state import ItemVersion
from . import register
from .base import Tool, ToolContext, ToolError


class DetectTool(Tool):
    name = "detect"
    label = "Detect"
    requires_model = "dino"
    requires_input_kind = "raw"
    media_types = ("image",)
    params_schema = [
        {"name": "prompt", "type": "string", "default": "",
         "placeholder": "e.g. car . person . traffic light",
         "label": "Text Prompt", "required": True},
        {"name": "box_threshold", "type": "number", "default": 0.35,
         "min": 0.1, "max": 0.9, "step": 0.01, "label": "Box Threshold"},
        {"name": "text_threshold", "type": "number", "default": 0.25,
         "min": 0.1, "max": 0.9, "step": 0.01, "label": "Text Threshold"},
    ]

    def run(self, ctx: ToolContext, parent: ItemVersion, **params) -> ItemVersion:
        if ctx.pipeline.dino_model is None:
            raise ToolError("DINO model is not loaded.")
        prompt = (params.get("prompt") or "").strip()
        if not prompt:
            raise ToolError("Detect requires a non-empty text prompt.")

        box_threshold = float(params.get("box_threshold", 0.35))
        text_threshold = float(params.get("text_threshold", 0.25))

        raw_payload = parent.payload
        with _payload_as_image_path(raw_payload) as image_path, ctx.pipeline_lock:
            det = ctx.pipeline.detect(
                image_path,
                prompt=prompt,
                box_threshold=box_threshold,
                text_threshold=text_threshold,
            )

        counts = Counter(det.phrases)
        return ItemVersion.make(
            kind="detected",
            payload=det,
            parent_id=parent.id,
            summary={
                "prompt": prompt,
                "box_threshold": box_threshold,
                "text_threshold": text_threshold,
                "n_boxes": int(len(det.phrases)),
                "class_counts": dict(counts),
            },
        )


class _payload_as_image_path:
    """Context manager: write raw bytes to a temp JPEG and yield its path."""

    def __init__(self, payload):
        self.payload = payload
        self._tmp = None

    def __enter__(self) -> str:
        if isinstance(self.payload, (bytes, bytearray)):
            self._tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
            self._tmp.write(bytes(self.payload))
            self._tmp.close()
            return self._tmp.name
        if isinstance(self.payload, str) and os.path.exists(self.payload):
            return self.payload
        raise ToolError("Detect input is not a readable image payload.")

    def __exit__(self, *exc):
        if self._tmp is not None:
            try:
                os.unlink(self._tmp.name)
            except OSError:
                pass


register(DetectTool())
