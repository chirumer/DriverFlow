"""Export a raw image item — original bytes, original filename."""

from __future__ import annotations

import os

from ..state import ItemVersion, WorkspaceItem
from . import register
from .base import ExportPayload, Exporter, ExporterError


def _media_type_for(name: str) -> str:
    ext = os.path.splitext(name)[1].lower()
    return {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
        ".gif": "image/gif",
    }.get(ext, "application/octet-stream")


class RawImageExporter(Exporter):
    name = "raw_image"
    handles_kind = "raw"
    handles_media = ("image",)
    filename_template = "{stem}{ext}"

    def export(self, item: WorkspaceItem, version: ItemVersion) -> ExportPayload:
        payload = version.payload
        if isinstance(payload, (bytes, bytearray)):
            data = bytes(payload)
        elif isinstance(payload, str) and os.path.exists(payload):
            with open(payload, "rb") as f:
                data = f.read()
        else:
            raise ExporterError("Raw image payload is not exportable.")
        return ExportPayload(
            filename=item.name,
            media_type=_media_type_for(item.name),
            body=data,
        )


register(RawImageExporter())
