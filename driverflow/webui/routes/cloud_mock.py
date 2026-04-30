"""Mocked DriverFlow Cloud.

Serves a fixed fake file tree. Selecting a leaf materializes it server-side
into the workspace as a 500x500 white PNG (image leaves) or a 2-second
blank MP4 (video leaves). No real cloud connection — this is a stand-in
until DriverFlow Cloud is implemented.
"""

from __future__ import annotations

import io
import os
import tempfile
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException

from ..state import WORKSPACE


router = APIRouter()


# Deterministic mock tree. Paths are virtual.
_MOCK_TREE: List[Dict[str, Any]] = [
    {
        "name": "Datasets",
        "kind": "dir",
        "path": "/Datasets",
        "children": [
            {
                "name": "street_scenes",
                "kind": "dir",
                "path": "/Datasets/street_scenes",
                "children": [
                    {"name": "scene_001.png", "kind": "image", "path": "/Datasets/street_scenes/scene_001.png"},
                    {"name": "scene_002.png", "kind": "image", "path": "/Datasets/street_scenes/scene_002.png"},
                    {"name": "scene_003.png", "kind": "image", "path": "/Datasets/street_scenes/scene_003.png"},
                ],
            },
            {
                "name": "demo_videos",
                "kind": "dir",
                "path": "/Datasets/demo_videos",
                "children": [
                    {"name": "clip_a.mp4", "kind": "video", "path": "/Datasets/demo_videos/clip_a.mp4"},
                    {"name": "clip_b.mp4", "kind": "video", "path": "/Datasets/demo_videos/clip_b.mp4"},
                ],
            },
        ],
    },
    {
        "name": "Personal",
        "kind": "dir",
        "path": "/Personal",
        "children": [
            {"name": "snapshot.png", "kind": "image", "path": "/Personal/snapshot.png"},
            {"name": "intro.mp4", "kind": "video", "path": "/Personal/intro.mp4"},
        ],
    },
]


def _flatten(tree: List[Dict[str, Any]], out: Dict[str, Dict[str, Any]]) -> None:
    for node in tree:
        if node.get("kind") in ("image", "video"):
            out[node["path"]] = node
        if node.get("children"):
            _flatten(node["children"], out)


_LEAVES: Dict[str, Dict[str, Any]] = {}
_flatten(_MOCK_TREE, _LEAVES)


def _make_white_png() -> bytes:
    from PIL import Image

    img = Image.new("RGB", (500, 500), "white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_blank_mp4(seconds: float = 2.0, fps: int = 30) -> bytes:
    """Encode a short blank MP4 (black frames) to a temp file, return its bytes."""
    import cv2
    import numpy as np

    width, height = 320, 240
    n_frames = max(1, int(round(seconds * fps)))
    frame = np.zeros((height, width, 3), dtype=np.uint8)

    tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
    tmp.close()
    try:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(tmp.name, fourcc, fps, (width, height))
        if not writer.isOpened():
            raise HTTPException(
                status_code=500, detail="Cloud mock: cv2.VideoWriter could not be opened."
            )
        for _ in range(n_frames):
            writer.write(frame)
        writer.release()
        with open(tmp.name, "rb") as f:
            return f.read()
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass


@router.get("/import/cloud_tree")
async def cloud_tree() -> dict:
    return {"tree": _MOCK_TREE}


@router.post("/import/cloud_select")
async def cloud_select(body: dict) -> dict:
    paths = body.get("paths") or []
    if not isinstance(paths, list):
        raise HTTPException(status_code=400, detail="paths must be a list")

    out: List[dict] = []
    for path in paths:
        leaf = _LEAVES.get(path)
        if leaf is None:
            raise HTTPException(status_code=404, detail=f"Unknown cloud path: {path}")
        name = leaf["name"]
        if leaf["kind"] == "image":
            data = _make_white_png()
            item = WORKSPACE.add_item(name=name, media_type="image", raw_payload=data)
        else:
            data = _make_blank_mp4()
            item = WORKSPACE.add_item(name=name, media_type="video", raw_payload=data)
        out.append(item.to_summary_dict())
    return {"items": out}
