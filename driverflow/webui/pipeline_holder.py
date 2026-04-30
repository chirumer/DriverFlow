"""Singleton holder around :class:`driverflow.Pipeline`.

The web UI must share one Pipeline (with one set of GPU-loaded weights)
across every request, so the FastAPI process keeps a process-wide instance
plus a single threading lock for serialized GPU access.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Dict

from ..pipeline import Pipeline


class PipelineHolder:
    """Single Pipeline + a global lock for tool / model-load endpoints."""

    def __init__(self) -> None:
        self.pipeline = Pipeline()
        self.lock = threading.Lock()

    # ---- model loaders -------------------------------------------------

    def load_dino(self) -> Dict[str, Any]:
        with self.lock:
            t0 = time.time()
            self.pipeline.setup(dino=True, sam=False)
            return {
                "loaded": True,
                "device": self.pipeline.device,
                "took_seconds": round(time.time() - t0, 2),
            }

    def load_sam(self, size: str = "large") -> Dict[str, Any]:
        with self.lock:
            t0 = time.time()
            self.pipeline.setup(dino=False, sam=True, sam_size=size)
            return {
                "loaded": True,
                "device": self.pipeline.device,
                "took_seconds": round(time.time() - t0, 2),
            }

    def status(self) -> Dict[str, Any]:
        return {
            "dino": self.pipeline.dino_model is not None,
            "sam": self.pipeline.sam_predictor is not None,
            "device": self.pipeline.device,
        }


# Process-wide singleton. Routers and tools import this directly.
PIPELINE = PipelineHolder()
