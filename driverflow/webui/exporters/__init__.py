"""Pluggable exporter registry.

Exporters are looked up by ``(version.kind, item.media_type)``. The export
endpoint dispatches on the latest (or requested) version's kind so the
user can export the same item as raw bytes, YOLO bboxes, or YOLO segments
depending on what's currently in the preview area.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from .base import ExportPayload, Exporter, ExporterError


_REGISTRY: Dict[Tuple[str, str], Exporter] = {}


def register(exporter: Exporter) -> Exporter:
    for media in exporter.handles_media:
        _REGISTRY[(exporter.handles_kind, media)] = exporter
    return exporter


def dispatch(*, kind: str, media_type: str) -> Exporter:
    key = (kind, media_type)
    if key not in _REGISTRY:
        raise ExporterError(
            f"No exporter for kind={kind!r} media_type={media_type!r}."
        )
    return _REGISTRY[key]


def list_descriptors() -> List[dict]:
    return [
        {
            "name": exp.name,
            "kind": kind,
            "media_type": media,
            "filename_template": exp.filename_template,
        }
        for (kind, media), exp in _REGISTRY.items()
    ]


__all__ = [
    "Exporter",
    "ExporterError",
    "ExportPayload",
    "register",
    "dispatch",
    "list_descriptors",
]
