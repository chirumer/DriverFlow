"""Export SegResult as YOLO segmentation annotations.

YOLO seg format: one row per mask, ``class_id x1 y1 x2 y2 ... xN yN`` with
all coordinates normalized to [0, 1]. Polygons come from
``cv2.findContours`` + ``cv2.approxPolyDP`` on each mask.
"""

from __future__ import annotations

import io
import os
import zipfile
from typing import List, Tuple


from ..state import ItemVersion, WorkspaceItem
from . import register
from .base import ExportPayload, Exporter, ExporterError


def _polygon_from_mask(mask, *, epsilon_ratio: float = 0.005) -> List[Tuple[float, float]]:
    """Largest external contour, simplified, returned as a flat list of (x, y) pairs."""
    import cv2
    import numpy as np

    m = mask
    if m.ndim == 3:
        m = m.squeeze(0)
    m_uint = (m.astype(np.uint8) * 255)
    contours, _ = cv2.findContours(m_uint, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return []
    largest = max(contours, key=cv2.contourArea)
    if cv2.contourArea(largest) <= 0:
        return []
    perimeter = cv2.arcLength(largest, True)
    epsilon = max(1.0, epsilon_ratio * perimeter)
    simplified = cv2.approxPolyDP(largest, epsilon, True)
    pts = simplified.reshape(-1, 2)
    return [(float(x), float(y)) for x, y in pts]


class YoloSegmentsExporter(Exporter):
    name = "yolo_segments"
    handles_kind = "segmented"
    handles_media = ("image",)
    filename_template = "{stem}_yolo_segments.zip"

    def export(self, item: WorkspaceItem, version: ItemVersion) -> ExportPayload:
        seg = version.payload
        if seg is None or not hasattr(seg, "masks") or not hasattr(seg, "image_source"):
            raise ExporterError("YOLO segments export expected a SegResult payload.")

        H, W = seg.image_source.shape[:2]
        phrases = list(seg.phrases)
        masks = list(seg.masks)

        classes = sorted(set(phrases))
        class_to_id = {cls: idx for idx, cls in enumerate(classes)}

        annotation_lines = []
        for phrase, mask in zip(phrases, masks):
            polygon = _polygon_from_mask(mask)
            if len(polygon) < 3:
                continue
            cid = class_to_id[phrase]
            coords = []
            for x, y in polygon:
                coords.append(f"{x / W:.6f}")
                coords.append(f"{y / H:.6f}")
            annotation_lines.append(f"{cid} " + " ".join(coords))

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("classes.txt", "\n".join(classes))
            zf.writestr("annotations.txt", "\n".join(annotation_lines))
        buf.seek(0)

        stem = os.path.splitext(item.name)[0]
        return ExportPayload(
            filename=f"{stem}_yolo_segments.zip",
            media_type="application/zip",
            body=buf.getvalue(),
        )


# Both segmented and refined versions export to the same YOLO seg format.
register(YoloSegmentsExporter())


class YoloSegmentsRefinedExporter(YoloSegmentsExporter):
    name = "yolo_segments_refined"
    handles_kind = "refined"


register(YoloSegmentsRefinedExporter())
