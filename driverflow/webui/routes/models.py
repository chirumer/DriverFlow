"""Model load + status routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..pipeline_holder import PIPELINE


router = APIRouter()


@router.get("/models/status")
async def status() -> dict:
    return PIPELINE.status()


@router.post("/models/load_dino")
async def load_dino() -> dict:
    try:
        return PIPELINE.load_dino()
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Failed to load DINO: {e}")


@router.post("/models/load_sam")
async def load_sam(body: dict | None = None) -> dict:
    body = body or {}
    size = body.get("size", "large")
    try:
        return PIPELINE.load_sam(size=size)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Failed to load SAM: {e}")
