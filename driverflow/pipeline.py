"""Stateful Pipeline that owns the loaded GroundingDINO + SAM 2 models.

The class is intentionally the only entry point for running the
data-science workflow from a Colab notebook (no module-level facade with
hidden globals). All heavy imports are lazy and live inside ``_load_*`` so
``import driverflow`` stays cheap.
"""

from __future__ import annotations

import os
import threading
import tempfile
from pathlib import Path
from typing import Optional, TYPE_CHECKING, Union

from . import setup as _setup
from .types import Detections, SegResult

if TYPE_CHECKING:
    import numpy as np

ImageInput = Union[str, "Path", "np.ndarray"]


class Pipeline:
    """Holds a loaded GroundingDINO model and SAM 2 predictor.

    Typical use::

        pipe = Pipeline().setup(dino=True, sam=True)
        det  = pipe.detect("image.jpg", prompt="car . person")
        seg  = pipe.segment(det)
        sess = pipe.refine(seg)
        seg2 = pipe.apply_refinements(seg, sess)
    """

    def __init__(self, device: Optional[str] = None):
        self.device = device  # resolved on first SAM load if None
        self.dino_model = None
        self.sam_predictor = None
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ setup

    def setup(
        self,
        dino: bool = True,
        sam: bool = True,
        sam_size: str = "large",
        verbose: bool = True,
    ) -> "Pipeline":
        """Install + load the requested models. Idempotent."""
        with self._lock:
            if dino:
                _setup.ensure_dino(verbose=verbose)
                self._load_dino()
            if sam:
                _setup.ensure_sam2(size=sam_size, verbose=verbose)
                self._load_sam()
        return self

    def _load_dino(self) -> None:
        if self.dino_model is not None:
            return
        # GroundingDINO's load_model expects to be imported from inside the
        # cloned repo (the package uses relative path tricks for its config).
        prev_cwd = os.getcwd()
        try:
            os.chdir(_setup.GDINO_DIR)
            from groundingdino.util.inference import load_model  # type: ignore[import-not-found]
        finally:
            os.chdir(prev_cwd)
        self.dino_model = load_model(_setup.GDINO_CFG, _setup.DINO_WEIGHTS)

    def _load_sam(self) -> None:
        if self.sam_predictor is not None:
            return
        import torch

        if self.device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"

        if self.device == "cuda" and torch.cuda.is_available():
            # TF32 is global and harmless for both DINO and SAM 2.
            # Do NOT enable bfloat16 autocast globally — GroundingDINO's
            # ms_deform_attn CUDA kernel doesn't support BFloat16. Autocast
            # is scoped per-call inside segment / apply_refinements instead.
            if torch.cuda.get_device_properties(0).major >= 8:
                torch.backends.cuda.matmul.allow_tf32 = True
                torch.backends.cudnn.allow_tf32 = True

        from sam2.build_sam import build_sam2  # type: ignore[import-not-found]
        from sam2.sam2_image_predictor import SAM2ImagePredictor  # type: ignore[import-not-found]

        sam_model = build_sam2(_setup.SAM2_CFG, _setup.SAM2_WEIGHTS, device=self.device)
        self.sam_predictor = SAM2ImagePredictor(sam_model)

    def _sam_autocast(self):
        """Context manager: bfloat16 autocast on CUDA, no-op on CPU."""
        import contextlib
        import torch

        if self.device == "cuda" and torch.cuda.is_available():
            return torch.autocast("cuda", dtype=torch.bfloat16)
        return contextlib.nullcontext()

    # ------------------------------------------------------------------ detect

    def detect(
        self,
        image: ImageInput,
        prompt: str,
        box_threshold: float = 0.35,
        text_threshold: float = 0.25,
    ) -> Detections:
        """Run GroundingDINO open-vocabulary detection on ``image``."""
        if self.dino_model is None:
            raise RuntimeError("DINO model not loaded. Call .setup(dino=True) first.")

        import numpy as np
        import torch

        with self._lock:
            prev_cwd = os.getcwd()
            try:
                os.chdir(_setup.GDINO_DIR)
                from groundingdino.util.inference import load_image, predict  # type: ignore[import-not-found]
                
                with _as_local_path(image) as image_path:
                    image_source, image_tensor = load_image(image_path)
                    boxes, logits, phrases = predict(
                        model=self.dino_model,
                        image=image_tensor,
                        caption=prompt,
                        box_threshold=box_threshold,
                        text_threshold=text_threshold,
                    )
            finally:
                os.chdir(prev_cwd)

            H, W = image_source.shape[:2]
            boxes_xyxy = _cxcywh_norm_to_xyxy_abs(boxes, W, H)
            scores = logits.detach().cpu().numpy() if hasattr(logits, "detach") else np.asarray(logits)

            return Detections(
                image_source=image_source,
                image_tensor=image_tensor,
                boxes_cxcywh_norm=boxes,
                boxes_xyxy=boxes_xyxy,
                scores=scores,
                phrases=list(phrases),
                image_width=int(W),
                image_height=int(H),
            )

    # ------------------------------------------------------------------ segment

    def segment(self, det: Detections) -> SegResult:
        """Convert each DINO box into a SAM 2 pixel mask."""
        if self.sam_predictor is None:
            raise RuntimeError("SAM 2 model not loaded. Call .setup(sam=True) first.")

        import numpy as np

        with self._lock:
            with self._sam_autocast():
                self.sam_predictor.set_image(det.image_source)
                masks, iou_scores, _ = self.sam_predictor.predict(
                    point_coords=None,
                    point_labels=None,
                    box=det.boxes_xyxy,
                    multimask_output=False,
                )
            masks = np.asarray(masks)
            if masks.ndim == 4:  # (N, 1, H, W) -> (N, H, W)
                masks = masks.squeeze(1)
            masks = masks.astype(bool)

            return SegResult(
                masks=masks,
                iou_scores=np.asarray(iou_scores),
                boxes_xyxy=det.boxes_xyxy,
                phrases=list(det.phrases),
                image_source=det.image_source,
            )

    # ------------------------------------------------------------------ refine

    def refine(self, seg: SegResult):
        """Display the click-refinement canvas in the current Colab cell."""
        from . import refine as _refine
        return _refine.collect_clicks(seg)

    def apply_refinements(self, seg: SegResult, session) -> SegResult:
        """Block until the user submits, then re-run SAM per box with the clicks.

        Each click is assigned to the nearest box (Euclidean distance to box
        center). Boxes with no assigned clicks keep their original mask.
        """
        if self.sam_predictor is None:
            raise RuntimeError("SAM 2 model not loaded. Call .setup(sam=True) first.")

        import numpy as np

        session.done_event.wait()

        boxes = seg.boxes_xyxy
        if len(session.points) == 0 or len(boxes) == 0:
            return seg

        centers = np.stack([
            np.array([(b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0]) for b in boxes
        ])
        pts = np.asarray(session.points, dtype=float)
        lbs = np.asarray(session.labels, dtype=int)

        # nearest-box assignment
        assignments = {i: ([], []) for i in range(len(boxes))}
        for pt, lb in zip(pts, lbs):
            distances = np.linalg.norm(centers - pt, axis=1)
            idx = int(np.argmin(distances))
            assignments[idx][0].append(pt.tolist())
            assignments[idx][1].append(int(lb))

        refined = list(seg.masks)
        refined_iou = list(seg.iou_scores) if hasattr(seg.iou_scores, "__iter__") else [None] * len(boxes)

        with self._lock:
            with self._sam_autocast():
                self.sam_predictor.set_image(seg.image_source)

                for i in range(len(boxes)):
                    pts_i, lbs_i = assignments[i]
                    if not pts_i:
                        continue
                    new_mask, new_iou, _ = self.sam_predictor.predict(
                        point_coords=np.asarray(pts_i, dtype=float),
                        point_labels=np.asarray(lbs_i, dtype=int),
                        box=np.asarray(boxes[i])[None, :],
                        multimask_output=False,
                    )
                    m = np.asarray(new_mask)
                    if m.ndim == 3:
                        m = m.squeeze(0)
                    refined[i] = m.astype(bool)
                    iou_arr = np.asarray(new_iou).reshape(-1)
                    refined_iou[i] = float(iou_arr[0]) if iou_arr.size else None

                    print(f"Box {i}: refined with {len(pts_i)} point(s).")

        return SegResult(
            masks=np.stack(refined, axis=0),
            iou_scores=np.asarray(refined_iou, dtype=object),
            boxes_xyxy=seg.boxes_xyxy,
            phrases=list(seg.phrases),
            image_source=seg.image_source,
        )


# ---------------------------------------------------------------------- helpers


class _as_local_path:
    """Context manager that yields a local image path.

    If passed a str/Path, just yields it. If passed an ndarray, writes it to
    a temporary JPEG (deleted on exit).
    """

    def __init__(self, image: ImageInput):
        self.image = image
        self._tmp = None

    def __enter__(self) -> str:
        if isinstance(self.image, (str, Path)):
            return str(self.image)
        import cv2
        import numpy as np

        arr = np.asarray(self.image)
        if arr.ndim == 3 and arr.shape[2] == 3:
            bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
        else:
            bgr = arr
        self._tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
        self._tmp.close()
        cv2.imwrite(self._tmp.name, bgr)
        return self._tmp.name

    def __exit__(self, *exc) -> None:
        if self._tmp is not None:
            try:
                os.unlink(self._tmp.name)
            except OSError:
                pass


def _cxcywh_norm_to_xyxy_abs(boxes, W: int, H: int):
    """Convert DINO normalized cxcywh -> absolute xyxy as a numpy array."""
    import numpy as np
    import torch

    if isinstance(boxes, torch.Tensor):
        b = boxes.detach().cpu().clone()
        b = b * torch.tensor([W, H, W, H], dtype=b.dtype)
        xyxy = torch.empty_like(b)
        xyxy[:, 0] = b[:, 0] - b[:, 2] / 2
        xyxy[:, 1] = b[:, 1] - b[:, 3] / 2
        xyxy[:, 2] = b[:, 0] + b[:, 2] / 2
        xyxy[:, 3] = b[:, 1] + b[:, 3] / 2
        return xyxy.numpy()

    arr = np.asarray(boxes, dtype=float).copy()
    arr = arr * np.array([W, H, W, H], dtype=float)
    out = np.empty_like(arr)
    out[:, 0] = arr[:, 0] - arr[:, 2] / 2
    out[:, 1] = arr[:, 1] - arr[:, 3] / 2
    out[:, 2] = arr[:, 0] + arr[:, 2] / 2
    out[:, 3] = arr[:, 1] + arr[:, 3] / 2
    return out
