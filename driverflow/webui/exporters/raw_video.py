"""Export a raw video item — original bytes, original filename."""

from __future__ import annotations

import os

from ..state import ItemVersion, WorkspaceItem
from . import register
from .base import ExportPayload, Exporter, ExporterError


class RawVideoExporter(Exporter):
    name = "raw_video"
    handles_kind = "raw"
    handles_media = ("video",)
    filename_template = "{stem}{ext}"

    def export(self, item: WorkspaceItem, version: ItemVersion) -> ExportPayload:
        payload = version.payload
        if isinstance(payload, (bytes, bytearray)):
            data = bytes(payload)
        elif isinstance(payload, str) and os.path.exists(payload):
            with open(payload, "rb") as f:
                data = f.read()
        else:
            raise ExporterError("Raw video payload is not exportable.")
        return ExportPayload(
            filename=item.name,
            media_type="video/mp4",
            body=data,
        )


register(RawVideoExporter())
