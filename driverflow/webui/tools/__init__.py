"""Pluggable tool registry.

Each tool is a subclass of :class:`Tool` (see :mod:`.base`). Modules that
define a tool also call :func:`register` at import time. The FastAPI
``server.build_app`` triggers those imports so the registry is populated
before any request lands.
"""

from __future__ import annotations

from typing import Dict, List

from .base import Tool, ToolContext, ToolError


_REGISTRY: Dict[str, Tool] = {}


def register(tool: Tool) -> Tool:
    """Add ``tool`` to the registry. Re-registration overwrites silently so
    that hot-reloads in development don't crash."""
    _REGISTRY[tool.name] = tool
    return tool


def get(name: str) -> Tool:
    if name not in _REGISTRY:
        raise ToolError(f"Unknown tool: {name}")
    return _REGISTRY[name]


def has(name: str) -> bool:
    return name in _REGISTRY


def list_descriptors() -> List[dict]:
    return [t.descriptor() for t in _REGISTRY.values()]


__all__ = [
    "Tool",
    "ToolContext",
    "ToolError",
    "register",
    "get",
    "has",
    "list_descriptors",
]
