"""Item listing + preview routes."""

from __future__ import annotations

import os
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Response

from ..render import render_detected, render_raw_image, render_segmented, render_thumb
from ..state import WORKSPACE


router = APIRouter()


def _preview_bytes_for_version(item, version) -> tuple[bytes, str]:
    """Return (payload_bytes, content_type) for a preview request."""
    media_type = item.media_type
    kind = version.kind

    if kind == "raw":
        if media_type == "video":
            payload = version.payload
            if isinstance(payload, (bytes, bytearray)):
                return bytes(payload), "video/mp4"
            if isinstance(payload, str) and os.path.exists(payload):
                with open(payload, "rb") as f:
                    return f.read(), "video/mp4"
            raise HTTPException(status_code=500, detail="Unreadable video payload.")

        # image raw
        payload = version.payload
        if isinstance(payload, (bytes, bytearray)):
            return render_raw_image(bytes(payload)), "image/jpeg"
        if isinstance(payload, str) and os.path.exists(payload):
            with open(payload, "rb") as f:
                return render_raw_image(f.read()), "image/jpeg"
        raise HTTPException(status_code=500, detail="Unreadable image payload.")

    if kind == "detected":
        return render_detected(version.payload), "image/jpeg"

    if kind == "segmented":
        return render_segmented(version.payload), "image/jpeg"

    if kind == "refined":
        extra = version.extra or {}
        return (
            render_segmented(
                version.payload,
                points=extra.get("points"),
                labels=extra.get("labels"),
            ),
            "image/jpeg",
        )

    raise HTTPException(status_code=500, detail=f"Unknown version kind: {kind}")


@router.get("/items")
async def list_items(
    source: Optional[List[str]] = Query(default=None),
    media_type: Optional[List[str]] = Query(default=None),
) -> dict:
    sources = source or ["raw", "processed", "exported"]
    media_types = media_type or ["image", "video"]
    seen: set = set()
    out: List[dict] = []
    for src in sources:
        for media in media_types:
            for item in WORKSPACE.list(source=src, media_type=media):  # type: ignore[arg-type]
                if item.id in seen:
                    continue
                seen.add(item.id)
                out.append(item.to_summary_dict())
    # Stable order: insertion order from the dict
    return {"items": out}


@router.get("/preview/{item_id}")
async def get_preview(item_id: str, version: Optional[str] = None) -> Response:
    item = WORKSPACE.get(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found.")
    target = item.get_version(version) if version else item.latest()
    if target is None:
        raise HTTPException(status_code=404, detail="Version not found.")
    body, content_type = _preview_bytes_for_version(item, target)
    return Response(content=body, media_type=content_type)


@router.get("/preview/thumb/{item_id}")
async def get_thumb(item_id: str) -> Response:
    item = WORKSPACE.get(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found.")
    raw = item.versions[0]
    payload = raw.payload

    if item.media_type == "video":
        # Trivial fallback — render a small black frame as the thumb.
        import cv2
        import numpy as np

        frame = np.zeros((90, 120, 3), dtype=np.uint8)
        cv2.putText(frame, "video", (12, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                    (220, 220, 220), 1, cv2.LINE_AA)
        ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        return Response(content=bytes(buf) if ok else b"", media_type="image/jpeg")

    if isinstance(payload, (bytes, bytearray)):
        return Response(content=render_thumb(bytes(payload)), media_type="image/jpeg")
    if isinstance(payload, str) and os.path.exists(payload):
        with open(payload, "rb") as f:
            return Response(content=render_thumb(f.read()), media_type="image/jpeg")
    raise HTTPException(status_code=500, detail="Unreadable thumb payload.")
