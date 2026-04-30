"""Tool execution routes.

POST /api/tools/{name} dispatches to whichever Tool is registered. The
parent version defaults to the latest version on the item but can be
overridden via ``parent_version_id`` (so the user can re-run a tool from
an older snapshot in the data workspace).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .. import tools as tool_registry
from ..pipeline_holder import PIPELINE
from ..state import WORKSPACE
from ..tools.base import ToolContext, ToolError


router = APIRouter()


@router.get("/tools/registry")
async def get_registry() -> dict:
    return {"tools": tool_registry.list_descriptors()}


@router.post("/tools/{name}")
async def run_tool(name: str, body: dict) -> dict:
    if not tool_registry.has(name):
        raise HTTPException(status_code=404, detail=f"Unknown tool: {name}")
    tool = tool_registry.get(name)

    item_id = body.get("item_id")
    if not item_id:
        raise HTTPException(status_code=400, detail="item_id is required")
    item = WORKSPACE.get(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Unknown item.")

    parent_version_id = body.get("parent_version_id")
    if parent_version_id:
        parent = item.get_version(parent_version_id)
    else:
        if tool.requires_input_kind:
            parent = item.latest(tool.requires_input_kind)
        else:
            parent = item.latest()
    if parent is None:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Tool {name!r} requires an input version of kind "
                f"{tool.requires_input_kind!r} on this item."
            ),
        )

    if tool.requires_input_kind == "raw" and parent.kind != "raw":
        # Re-running detect from a derived parent is invalid; force the raw.
        parent = item.versions[0]

    if item.media_type not in tool.media_types:
        raise HTTPException(
            status_code=409,
            detail=f"Tool {name!r} does not support media type {item.media_type!r}.",
        )

    params = {k: v for k, v in body.items() if k not in ("item_id", "parent_version_id")}

    ctx = ToolContext(holder=PIPELINE)
    try:
        version = tool.run(ctx, parent, **params)
    except ToolError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Tool {name!r} failed: {e}")

    WORKSPACE.add_version(item_id, version)
    return {"version": version.to_summary_dict(), "item": item.to_summary_dict()}
