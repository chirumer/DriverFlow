"""FastAPI app factory.

Wires the static mount, every route module, and registers the built-in
tools and exporters. Importing this module is cheap; heavy imports (torch,
GroundingDINO, SAM 2) only happen when a request actually needs them.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


def _register_builtins() -> None:
    """Import-and-register every built-in tool + exporter."""
    # Side-effect imports that call register() at module scope.
    from .tools import detect as _detect_tool  # noqa: F401
    from .tools import segment as _segment_tool  # noqa: F401
    from .tools import refine as _refine_tool  # noqa: F401

    from .exporters import raw_image as _raw_image_exp  # noqa: F401
    from .exporters import raw_video as _raw_video_exp  # noqa: F401
    from .exporters import yolo_boxes as _yolo_boxes_exp  # noqa: F401
    from .exporters import yolo_segments as _yolo_seg_exp  # noqa: F401


def build_app() -> FastAPI:
    """Construct a FastAPI app with all routers wired in."""
    _register_builtins()

    app = FastAPI(title="DriverFlow Workspace")

    static_dir = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/")
    async def root():
        return FileResponse(static_dir / "index.html")

    # Routers are defined inline-imported so the module import graph stays
    # lazy and so circular imports cannot accidentally form between routes
    # and the tool / exporter registries.
    from .routes import import_ as r_import
    from .routes import items as r_items
    from .routes import models as r_models
    from .routes import tools as r_tools
    from .routes import export as r_export
    from .routes import cloud_mock as r_cloud

    app.include_router(r_import.router, prefix="/api")
    app.include_router(r_cloud.router, prefix="/api")
    app.include_router(r_items.router, prefix="/api")
    app.include_router(r_models.router, prefix="/api")
    app.include_router(r_tools.router, prefix="/api")
    app.include_router(r_export.router, prefix="/api")

    return app
