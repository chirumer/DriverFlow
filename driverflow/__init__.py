"""DriverFlow — image annotation and segmentation tooling for Colab.

Two ways to use this package:

  * UI mode (FastAPI workspace with versioned data, all Pipeline tools)::

        from driverflow import DriverFlow
        DriverFlow().start()

  * Legacy single-page detect-only UI (kept for back-compat)::

        from driverflow import DriverFlowOld
        DriverFlowOld().start()

  * Library mode (call DINO + SAM 2 directly from a notebook)::

        from driverflow import Pipeline, viz
        pipe = Pipeline().setup(dino=True, sam=True)
        det  = pipe.detect("image.jpg", prompt="car . person")
        seg  = pipe.segment(det)
        viz.show_masks(seg)

The top-level import is intentionally cheap: torch, groundingdino, and
sam2 are imported lazily inside ``Pipeline._load_*`` and ``viz.*``.
"""

from . import viz
from ._driverflow import DriverFlowOld
from ._driverflow_new import DriverFlow
from .pipeline import Pipeline
from .refine import ClickSession
from .setup import (
    download_dino_weights,
    ensure_dino,
    ensure_sam2,
    setup_groundingdino,
    setup_sam2,
)
from .types import Detections, SegResult

__all__ = [
    "DriverFlow",
    "DriverFlowOld",
    "Pipeline",
    "Detections",
    "SegResult",
    "ClickSession",
    "viz",
    "setup_groundingdino",
    "download_dino_weights",
    "setup_sam2",
    "ensure_dino",
    "ensure_sam2",
]
