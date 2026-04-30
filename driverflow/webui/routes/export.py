"""Export routes — dispatch by (version.kind, item.media_type)."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Response

from .. import exporters as exporter_registry
from ..exporters.base import ExporterError
from ..state import WORKSPACE


router = APIRouter()


@router.get("/export/registry")
async def get_registry() -> dict:
    return {"exporters": exporter_registry.list_descriptors()}


@router.get("/export/{item_id}")
async def export_item(item_id: str, version: Optional[str] = None) -> Response:
    item = WORKSPACE.get(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found.")
    target = item.get_version(version) if version else item.latest()
    if target is None:
        raise HTTPException(status_code=404, detail="Version not found.")
    try:
        exporter = exporter_registry.dispatch(kind=target.kind, media_type=item.media_type)
    except ExporterError as e:
        raise HTTPException(status_code=409, detail=str(e))

    try:
        payload = exporter.export(item, target)
    except ExporterError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Export failed: {e}")

    WORKSPACE.mark_exported(item_id)

    return Response(
        content=payload.body,
        media_type=payload.media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{payload.filename}"',
        },
    )
