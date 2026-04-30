"""Base classes for the exporter registry."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar, Tuple

from ..state import ItemVersion, WorkspaceItem


class ExporterError(Exception):
    pass


@dataclass
class ExportPayload:
    filename: str
    media_type: str
    body: bytes


class Exporter(ABC):
    name: ClassVar[str] = ""
    handles_kind: ClassVar[str] = ""
    handles_media: ClassVar[Tuple[str, ...]] = ("image",)
    filename_template: ClassVar[str] = "{stem}"

    @abstractmethod
    def export(self, item: WorkspaceItem, version: ItemVersion) -> ExportPayload:
        raise NotImplementedError
