"""Server-side preview rendering.

Wraps the existing helpers (``_annotate_image`` and ``_composite_jpeg_b64``)
without re-implementing annotation logic. Each renderer emits JPEG bytes
suitable for sending straight back from a route handler.
"""

from __future__ import annotations

import base64
from typing import List, Optional, Sequence, Tuple


def _encode_jpeg(bgr) -> bytes:
    import cv2

    ok, buf = cv2.imencode(".jpg", bgr, [cv2.IMWRITE_JPEG_QUALITY, 90])
    if not ok:
        raise RuntimeError("Failed to encode preview as JPEG.")
    return bytes(buf)


def render_raw_image(image_bytes: bytes) -> bytes:
    """Pass-through for raw image previews. Always re-encodes as JPEG so the
    browser sees a stable content-type even for unusual source formats."""
    import cv2
    import numpy as np

    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if bgr is None:
        # Already JPEG/PNG bytes that opencv could not decode (rare). Send as-is.
        return image_bytes
    return _encode_jpeg(bgr)


def render_detected(det) -> bytes:
    """Render a Detections card: original image + DINO boxes + class labels."""
    import cv2
    import numpy as np

    image_source = det.image_source  # HxWx3 RGB uint8
    bgr = cv2.cvtColor(image_source, cv2.COLOR_RGB2BGR).copy()
    H, W = bgr.shape[:2]

    boxes = np.asarray(det.boxes_xyxy, dtype=int)
    scores = list(det.scores) if hasattr(det.scores, "__iter__") else []
    phrases = list(det.phrases)

    for i, box in enumerate(boxes):
        x1, y1, x2, y2 = [int(v) for v in box[:4]]
        x1 = max(0, min(W - 1, x1))
        y1 = max(0, min(H - 1, y1))
        x2 = max(0, min(W - 1, x2))
        y2 = max(0, min(H - 1, y2))

        score = float(scores[i]) if i < len(scores) else 0.0
        phrase = phrases[i] if i < len(phrases) else f"box {i}"
        label = f"{phrase} {score:.2f}"
        cv2.rectangle(bgr, (x1, y1), (x2, y2), (0, 255, 0), 2)

        (lw, lh), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        ly1 = max(0, y1 - lh - baseline - 6)
        ly2 = ly1 + lh + baseline + 6
        lx2 = min(W - 1, x1 + lw + 8)
        cv2.rectangle(bgr, (x1, ly1), (lx2, ly2), (0, 255, 0), -1)
        cv2.putText(
            bgr, label, (x1 + 4, ly2 - baseline - 3),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA,
        )

    return _encode_jpeg(bgr)


def render_segmented(
    seg,
    *,
    points: Optional[Sequence[Sequence[float]]] = None,
    labels: Optional[Sequence[int]] = None,
) -> bytes:
    """Render a SegResult preview: masks + box outlines, optionally with click overlay.

    Reuses :func:`driverflow.refine._composite_jpeg_b64` for the heavy lifting
    and only adds the click dots on top when refine points are present.
    """
    import cv2
    import numpy as np

    from ..refine import _composite_jpeg_b64

    composite_b64 = _composite_jpeg_b64(seg)
    raw = base64.b64decode(composite_b64)

    if not points:
        return raw

    arr = np.frombuffer(raw, dtype=np.uint8)
    bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if bgr is None:
        return raw

    pts = list(points)
    lbs = list(labels or [1] * len(pts))
    for (x, y), lb in zip(pts, lbs):
        x = int(round(x))
        y = int(round(y))
        color = (80, 220, 40) if int(lb) == 1 else (60, 60, 240)
        cv2.circle(bgr, (x, y), 8, color, -1, cv2.LINE_AA)
        cv2.circle(bgr, (x, y), 8, (255, 255, 255), 2, cv2.LINE_AA)

    return _encode_jpeg(bgr)


def render_thumb(image_bytes: bytes, *, size: int = 240) -> bytes:
    """Small JPEG thumbnail used for sidebar entries."""
    import cv2
    import numpy as np

    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if bgr is None:
        return image_bytes
    h, w = bgr.shape[:2]
    if max(h, w) > size:
        scale = size / float(max(h, w))
        bgr = cv2.resize(bgr, (max(1, int(w * scale)), max(1, int(h * scale))))
    return _encode_jpeg(bgr)
