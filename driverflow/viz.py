"""Matplotlib visualization helpers for Detections and SegResult.

Heavy imports (matplotlib, cv2, numpy) happen lazily inside functions so
that ``import driverflow`` stays cheap.
"""

from __future__ import annotations

from typing import Dict, Optional, Sequence, TYPE_CHECKING, Tuple

if TYPE_CHECKING:
    from .types import Detections, SegResult


def _draw_mask(ax, mask, rng) -> None:
    import cv2
    import numpy as np

    m = mask
    if m.ndim == 3:
        m = m.squeeze(0)
    m = m.astype(np.uint8)
    h, w = m.shape

    color = np.concatenate([rng.random(3), np.array([0.55])], axis=0)
    overlay = m.reshape(h, w, 1) * color.reshape(1, 1, -1)

    contours, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    contours = [cv2.approxPolyDP(c, epsilon=0.01, closed=True) for c in contours]
    overlay = cv2.drawContours(overlay, contours, -1, (1, 1, 1, 0.6), thickness=2)
    ax.imshow(overlay)


def show_detections(
    det: "Detections",
    *,
    figsize: Tuple[int, int] = (12, 12),
    title: Optional[str] = None,
) -> None:
    """Show the source image with DINO bounding boxes + class/score labels."""
    import matplotlib.patches as patches
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=figsize)
    ax.imshow(det.image_source)
    for box, phrase, score in zip(det.boxes_xyxy, det.phrases, det.scores):
        x1, y1, x2, y2 = box
        ax.add_patch(patches.Rectangle(
            (x1, y1), x2 - x1, y2 - y1,
            linewidth=2, edgecolor="lime", facecolor="none",
        ))
        ax.text(
            x1, max(0, y1 - 6), f"{phrase} {float(score):.2f}",
            color="black", fontsize=11, weight="bold",
            bbox=dict(facecolor="lime", alpha=0.8, edgecolor="none", pad=2),
        )
    if title:
        ax.set_title(title, fontsize=16)
    ax.axis("off")
    plt.show()


def show_masks(
    seg: "SegResult",
    *,
    points: Optional[Sequence[Sequence[float]]] = None,
    labels: Optional[Sequence[int]] = None,
    singular_map: Optional[Dict[str, str]] = None,
    figsize: Tuple[int, int] = (16, 16),
    title: Optional[str] = None,
    show_boxes: bool = False,
) -> None:
    """Show the source image with translucent masks + per-box class label.

    If ``points`` and ``labels`` are passed, positive points are drawn as
    green stars and negative points as red stars (useful for showing the
    refinement clicks alongside the refined masks).
    """
    import matplotlib.patches as patches
    import matplotlib.pyplot as plt
    import numpy as np

    fig, ax = plt.subplots(figsize=figsize)
    ax.imshow(seg.image_source)

    rng = np.random.default_rng(0)
    for idx, mask in enumerate(seg.masks):
        _draw_mask(ax, mask, rng)

        x1, y1, x2, y2 = seg.boxes_xyxy[idx]
        cx = (x1 + x2) / 2.0
        cy = (y1 + y2) / 2.0

        raw_label = seg.phrases[idx] if idx < len(seg.phrases) else f"Box {idx}"
        label = (singular_map or {}).get(raw_label, raw_label)
        ax.text(
            cx, cy, label.title(),
            color="white", fontsize=14, weight="bold",
            ha="center", va="center",
            bbox=dict(facecolor="black", alpha=0.55, edgecolor="none", boxstyle="round,pad=0.5"),
        )

        if show_boxes:
            ax.add_patch(patches.Rectangle(
                (x1, y1), x2 - x1, y2 - y1,
                linewidth=2, edgecolor="red", facecolor="none",
            ))

    if points is not None and labels is not None and len(points) > 0:
        pts = np.asarray(points, dtype=float)
        lbs = np.asarray(labels, dtype=int)
        pos = pts[lbs == 1]
        neg = pts[lbs == 0]
        if len(pos) > 0:
            ax.scatter(pos[:, 0], pos[:, 1], color="lime", marker="*", s=300, edgecolor="white", linewidth=1.5)
        if len(neg) > 0:
            ax.scatter(neg[:, 0], neg[:, 1], color="red", marker="*", s=300, edgecolor="white", linewidth=1.5)

    if title:
        ax.set_title(title, fontsize=18)
    ax.axis("off")
    plt.show()
