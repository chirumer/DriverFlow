"""Install and download helpers for GroundingDINO and SAM 2.

All functions are idempotent: calling them when the dependency / weights are
already present is a no-op (with a printed status line). They are designed
for Colab (`/content/...` paths) but will work anywhere those paths are
writable.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys


GDINO_DIR = "/content/GroundingDINO"
GDINO_URL = "https://github.com/IDEA-Research/GroundingDINO.git"
GDINO_CFG = f"{GDINO_DIR}/groundingdino/config/GroundingDINO_SwinT_OGC.py"

WEIGHTS_DIR = "/content/weights"
DINO_WEIGHTS = f"{WEIGHTS_DIR}/groundingdino_swint_ogc.pth"
DINO_WEIGHTS_URL = (
    "https://github.com/IDEA-Research/GroundingDINO/releases/download/"
    "v0.1.0-alpha/groundingdino_swint_ogc.pth"
)

SAM2_CKPT_DIR = "/content/checkpoints"
SAM2_WEIGHTS = f"{SAM2_CKPT_DIR}/sam2.1_hiera_large.pt"
SAM2_WEIGHTS_URL = (
    "https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_large.pt"
)
SAM2_CFG = "configs/sam2.1/sam2.1_hiera_l.yaml"
SAM2_PIP_SPEC = "git+https://github.com/facebookresearch/sam2.git"


def _say(verbose: bool, msg: str) -> None:
    if verbose:
        print(msg)


def setup_groundingdino(verbose: bool = True) -> None:
    """Clone GroundingDINO, patch its CUDA op for newer PyTorch, and pip install -e."""
    if not os.path.exists(GDINO_DIR):
        _say(verbose, "Cloning GroundingDINO...")
        subprocess.run(
            ["git", "clone", GDINO_URL, GDINO_DIR],
            check=True, capture_output=True,
        )
    else:
        _say(verbose, "GroundingDINO directory already present.")

    cuda_file = os.path.join(
        GDINO_DIR,
        "groundingdino/models/GroundingDINO/csrc/MsDeformAttn/ms_deform_attn_cuda.cu",
    )
    if os.path.exists(cuda_file):
        text = open(cuda_file).read()
        text = text.replace("value.type()", "value.scalar_type()")
        text = text.replace("value.scalar_type().is_cuda()", "value.is_cuda()")
        open(cuda_file, "w").write(text)

    if importlib.util.find_spec("groundingdino") is None:
        _say(verbose, "Installing GroundingDINO (this may take a few minutes)...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-q", "-e", "."],
            cwd=GDINO_DIR, check=True,
        )
    else:
        _say(verbose, "GroundingDINO already installed.")

    # GroundingDINO + newer transformers crash with
    # "BertModel has no attribute 'get_head_mask'". Pin to the version the
    # reference notebook uses. Always re-run pip — cheap if already pinned,
    # and fixes pre-existing environments where transformers is too new.
    _say(verbose, "Pinning transformers==4.38.2 and installing supervision...")
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q",
         "supervision", "transformers==4.38.2"],
        check=True,
    )

    _say(verbose, "GroundingDINO ready.")


def download_dino_weights(verbose: bool = True) -> str:
    """Download the GroundingDINO SwinT-OGC checkpoint. Returns the local path."""
    os.makedirs(WEIGHTS_DIR, exist_ok=True)
    if not os.path.exists(DINO_WEIGHTS):
        _say(verbose, "Downloading GroundingDINO weights (this may take a few minutes)...")
        subprocess.run(
            ["wget", "-q", "-O", DINO_WEIGHTS, DINO_WEIGHTS_URL],
            check=True,
        )
        _say(verbose, "GroundingDINO weights downloaded.")
    else:
        _say(verbose, "GroundingDINO weights already present.")
    return DINO_WEIGHTS


def setup_sam2(size: str = "large", verbose: bool = True) -> str:
    """Pip-install SAM 2 from source and download the checkpoint. Returns the weights path.

    Only ``size="large"`` is currently implemented. Other sizes raise
    NotImplementedError.
    """
    if size != "large":
        raise NotImplementedError(
            f"SAM 2 size {size!r} not supported yet; only 'large' is implemented."
        )

    if importlib.util.find_spec("sam2") is None:
        _say(verbose, "Installing SAM 2 (this may take a few minutes)...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-q", SAM2_PIP_SPEC],
            check=True,
        )
    else:
        _say(verbose, "SAM 2 already installed.")

    os.makedirs(SAM2_CKPT_DIR, exist_ok=True)
    if not os.path.exists(SAM2_WEIGHTS):
        _say(verbose, "Downloading SAM 2 weights (~900MB)...")
        subprocess.run(
            ["wget", "-q", "-O", SAM2_WEIGHTS, SAM2_WEIGHTS_URL],
            check=True,
        )
        _say(verbose, "SAM 2 weights downloaded.")
    else:
        _say(verbose, "SAM 2 weights already present.")

    return SAM2_WEIGHTS


def ensure_dino(verbose: bool = True) -> None:
    setup_groundingdino(verbose=verbose)
    download_dino_weights(verbose=verbose)


def ensure_sam2(size: str = "large", verbose: bool = True) -> None:
    setup_sam2(size=size, verbose=verbose)
