"""Import routes — drag/drop uploads, including zip unpacking."""

from __future__ import annotations

import io
import os
import zipfile
from typing import List

from fastapi import APIRouter, File, HTTPException, UploadFile

from ..state import WORKSPACE


router = APIRouter()


_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}
_VIDEO_EXTS = {".mp4", ".mov", ".webm", ".mkv", ".avi"}


def _media_type_for(name: str) -> str | None:
    ext = os.path.splitext(name)[1].lower()
    if ext in _IMAGE_EXTS:
        return "image"
    if ext in _VIDEO_EXTS:
        return "video"
    return None


def _add_one(name: str, data: bytes) -> dict | None:
    media = _media_type_for(name)
    if media is None:
        return None
    item = WORKSPACE.add_item(
        name=os.path.basename(name),
        media_type=media,  # type: ignore[arg-type]
        raw_payload=data,
    )
    return item.to_summary_dict()


@router.post("/import/upload")
async def upload(files: List[UploadFile] = File(...)) -> dict:
    """Accept one or more uploads. Zips are unpacked; only image/video members kept."""
    out: List[dict] = []
    for upload in files:
        try:
            payload = await upload.read()
        except Exception as e:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=f"Could not read {upload.filename}: {e}")

        ext = os.path.splitext(upload.filename or "")[1].lower()
        if ext == ".zip":
            try:
                with zipfile.ZipFile(io.BytesIO(payload)) as zf:
                    for member in zf.infolist():
                        if member.is_dir():
                            continue
                        member_name = os.path.basename(member.filename)
                        if not member_name:
                            continue
                        media = _media_type_for(member_name)
                        if media is None:
                            continue
                        with zf.open(member) as f:
                            data = f.read()
                        added = _add_one(member_name, data)
                        if added:
                            out.append(added)
            except zipfile.BadZipFile:
                raise HTTPException(
                    status_code=400, detail=f"{upload.filename}: not a valid zip archive."
                )
            continue

        added = _add_one(upload.filename or "upload", payload)
        if added is not None:
            out.append(added)

    return {"items": out}
