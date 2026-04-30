"""Result dataclasses for the DriverFlow data-science API.

Type hints reference numpy / torch via string annotations
(``from __future__ import annotations``) so that importing this module does
not require torch or numpy. Heavy imports happen lazily inside the Pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    import numpy as np
    import torch


@dataclass
class Detections:
    """Output of ``Pipeline.detect``."""

    image_source: "np.ndarray"        # HxWx3 uint8 RGB (from groundingdino load_image)
    image_tensor: "torch.Tensor"      # CxHxW float (DINO normalized input tensor)
    boxes_cxcywh_norm: "torch.Tensor" # (N,4) DINO native: cx, cy, w, h normalized to [0, 1]
    boxes_xyxy: "np.ndarray"          # (N,4) absolute pixel coordinates
    scores: "np.ndarray"              # (N,) confidence
    phrases: List[str]                # (N,) class phrase per box
    image_width: int
    image_height: int


@dataclass
class SegResult:
    """Output of ``Pipeline.segment`` and ``Pipeline.apply_refinements``."""

    masks: "np.ndarray"          # (N,H,W) bool
    iou_scores: "np.ndarray"     # (N,) SAM 2 predicted IoU
    boxes_xyxy: "np.ndarray"     # passthrough from Detections
    phrases: List[str]           # passthrough
    image_source: "np.ndarray"   # passthrough (used by viz helpers)
