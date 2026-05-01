"""Base classes for the pluggable tool registry."""

from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, ClassVar, Dict, List, Optional, Tuple

from ..pipeline_holder import PipelineHolder
from ..state import ItemVersion, VersionKind


class ToolError(Exception):
    """Raised when a tool refuses to run (bad input kind, missing model, ...)."""


@dataclass
class ToolContext:
    """Per-call context passed to ``Tool.run``."""

    holder: PipelineHolder

    @property
    def pipeline(self):
        return self.holder.pipeline

    @property
    def pipeline_lock(self) -> threading.Lock:
        return self.holder.lock


class Tool(ABC):
    """Subclass + populate the class-level fields, then call ``register(MyTool())``.

    Subclasses encode all gating in declarative class fields so the
    front-end can render disabled-state from the registry alone, with no
    duplicated logic.
    """

    name: ClassVar[str] = ""
    label: ClassVar[str] = ""
    requires_model: ClassVar[Optional[str]] = None  # "dino" | "sam" | None
    requires_input_kind: ClassVar[Optional[VersionKind]] = None
    input_kinds: ClassVar[Optional[Tuple[VersionKind, ...]]] = None
    media_types: ClassVar[Tuple[str, ...]] = ("image",)
    params_schema: ClassVar[List[Dict[str, Any]]] = []

    @abstractmethod
    def run(self, ctx: ToolContext, parent: ItemVersion, **params) -> ItemVersion:
        """Run the tool. Returns the new ItemVersion to append to the item."""
        raise NotImplementedError

    def descriptor(self) -> Dict[str, Any]:
        accepted_kinds = self.input_kinds
        if accepted_kinds is None and self.requires_input_kind is not None:
            accepted_kinds = (self.requires_input_kind,)
        return {
            "name": self.name,
            "label": self.label or self.name.title(),
            "requires_model": self.requires_model,
            "requires_input_kind": self.requires_input_kind,
            "input_kinds": list(accepted_kinds or []),
            "media_types": list(self.media_types),
            "params": list(self.params_schema),
        }
