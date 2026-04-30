"""In-memory workspace state.

All UI items live in a process-wide :class:`Workspace` singleton. Each
``WorkspaceItem`` owns an ordered list of ``ItemVersion`` snapshots; the
first is always the raw upload, subsequent ones are produced by tools.

The store is intentionally simple — a dict keyed by item id, guarded by an
``RLock``. Sidebar sections (raw / processed / exported) are derived as
filters over the same dict via ``Workspace.list``.
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional


VersionKind = Literal["raw", "detected", "segmented", "refined"]
MediaType = Literal["image", "video"]
SourceFilter = Literal["raw", "processed", "exported"]


def _new_id() -> str:
    return uuid.uuid4().hex


@dataclass
class ItemVersion:
    """One snapshot in an item's edit history."""

    id: str
    parent_id: Optional[str]
    kind: VersionKind
    payload: Any
    summary: Dict[str, Any] = field(default_factory=dict)
    extra: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    @classmethod
    def make(
        cls,
        *,
        kind: VersionKind,
        payload: Any,
        parent_id: Optional[str] = None,
        summary: Optional[Dict[str, Any]] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> "ItemVersion":
        return cls(
            id=_new_id(),
            parent_id=parent_id,
            kind=kind,
            payload=payload,
            summary=dict(summary or {}),
            extra=dict(extra or {}),
        )

    def to_summary_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "parent_id": self.parent_id,
            "kind": self.kind,
            "summary": self.summary,
            "created_at": self.created_at,
        }


@dataclass
class WorkspaceItem:
    """Single piece of media + every version produced from it."""

    id: str
    name: str
    media_type: MediaType
    versions: List[ItemVersion] = field(default_factory=list)
    exported: bool = False

    def has_kind(self, kind: VersionKind) -> bool:
        return any(v.kind == kind for v in self.versions)

    def latest(self, kind: Optional[VersionKind] = None) -> Optional[ItemVersion]:
        if kind is None:
            return self.versions[-1] if self.versions else None
        for v in reversed(self.versions):
            if v.kind == kind:
                return v
        return None

    def get_version(self, version_id: str) -> Optional[ItemVersion]:
        for v in self.versions:
            if v.id == version_id:
                return v
        return None

    def is_processed(self) -> bool:
        return any(v.kind != "raw" for v in self.versions)

    def to_summary_dict(self) -> Dict[str, Any]:
        sources: List[str] = ["raw"]
        if self.is_processed():
            sources.append("processed")
        if self.exported:
            sources.append("exported")
        return {
            "id": self.id,
            "name": self.name,
            "media_type": self.media_type,
            "sources": sources,
            "version_kinds": [v.kind for v in self.versions],
            "versions": [v.to_summary_dict() for v in self.versions],
            "thumb_url": f"/api/preview/thumb/{self.id}",
        }


class Workspace:
    """Process-wide store. All public methods are thread-safe."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._items: Dict[str, WorkspaceItem] = {}

    def add_item(self, *, name: str, media_type: MediaType, raw_payload: Any) -> WorkspaceItem:
        with self._lock:
            item_id = _new_id()
            raw = ItemVersion.make(kind="raw", payload=raw_payload)
            item = WorkspaceItem(id=item_id, name=name, media_type=media_type, versions=[raw])
            self._items[item_id] = item
            return item

    def get(self, item_id: str) -> Optional[WorkspaceItem]:
        with self._lock:
            return self._items.get(item_id)

    def require(self, item_id: str) -> WorkspaceItem:
        item = self.get(item_id)
        if item is None:
            raise KeyError(f"Unknown item id: {item_id}")
        return item

    def list(
        self,
        *,
        source: Optional[SourceFilter] = None,
        media_type: Optional[MediaType] = None,
    ) -> List[WorkspaceItem]:
        with self._lock:
            items = list(self._items.values())
        if media_type is not None:
            items = [i for i in items if i.media_type == media_type]
        if source == "processed":
            items = [i for i in items if i.is_processed()]
        elif source == "exported":
            items = [i for i in items if i.exported]
        # source == "raw" includes everything (every item starts with a raw version).
        return items

    def add_version(self, item_id: str, version: ItemVersion) -> WorkspaceItem:
        with self._lock:
            item = self.require(item_id)
            item.versions.append(version)
            return item

    def mark_exported(self, item_id: str) -> None:
        with self._lock:
            item = self.require(item_id)
            item.exported = True


# Process-wide singleton. Routers import this directly.
WORKSPACE = Workspace()
