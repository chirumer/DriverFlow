"""Export Detections as YOLO bounding-box annotations.

Mirrors the legacy /api/download_yolo logic: zips ``classes.txt`` (sorted
unique phrases) and ``annotations.txt`` (one ``cls cx cy w h`` row per box,
all coordinates normalized).
"""

from __future__ import annotations

import io
import os
import zipfile

from ..state import ItemVersion, WorkspaceItem
from . import register
from .base import ExportPayload, Exporter, ExporterError


class YoloBoxesExporter(Exporter):
    name = "yolo_boxes"
    handles_kind = "detected"
    handles_media = ("image",)
    filename_template = "{stem}_yolo_boxes.zip"

    def export(self, item: WorkspaceItem, version: ItemVersion) -> ExportPayload:
        det = version.payload
        if det is None or not hasattr(det, "boxes_cxcywh_norm"):
            raise ExporterError("YOLO boxes export expected a Detections payload.")

        phrases = list(det.phrases)
        boxes = det.boxes_cxcywh_norm
        boxes_list = (
            boxes.cpu().tolist() if hasattr(boxes, "cpu") else list(boxes)
        )

        classes = sorted(set(phrases))
        class_to_id = {cls: idx for idx, cls in enumerate(classes)}

        annotation_lines = []
        for phrase, box in zip(phrases, boxes_list):
            cx, cy, w, h = box
            cid = class_to_id[phrase]
            annotation_lines.append(f"{cid} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("classes.txt", "\n".join(classes))
            zf.writestr("annotations.txt", "\n".join(annotation_lines))
        buf.seek(0)

        stem = os.path.splitext(item.name)[0]
        return ExportPayload(
            filename=f"{stem}_yolo_boxes.zip",
            media_type="application/zip",
            body=buf.getvalue(),
        )


register(YoloBoxesExporter())
