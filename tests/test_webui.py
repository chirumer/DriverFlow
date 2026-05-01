import io
import zipfile

from fastapi.testclient import TestClient
from PIL import Image

from driverflow.webui import tools as tool_registry
from driverflow.webui.server import build_app
from driverflow.webui.state import ItemVersion, WORKSPACE
from driverflow.webui.tools.base import Tool


def png_bytes(color="red", size=(16, 12)):
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


def clear_workspace():
    with WORKSPACE._lock:
        WORKSPACE._items.clear()


def client():
    clear_workspace()
    return TestClient(build_app())


class ParentEchoTool(Tool):
    name = "parent_echo"
    label = "Parent Echo"
    requires_input_kind = "detected"
    media_types = ("image",)
    params_schema = []

    def run(self, ctx, parent, **params):
        return ItemVersion.make(
            kind="segmented",
            payload={"parent_kind": parent.kind},
            parent_id=parent.id,
            summary={"parent_id": parent.id},
        )


tool_registry.register(ParentEchoTool())


def test_upload_image_zip_and_unsupported_files():
    c = client()

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        zf.writestr("one.png", png_bytes("blue"))
        zf.writestr("nested/two.jpg", png_bytes("green"))
        zf.writestr("notes.txt", b"ignore me")

    resp = c.post(
        "/api/import/upload",
        files=[
            ("files", ("single.png", png_bytes(), "image/png")),
            ("files", ("bundle.zip", zip_buf.getvalue(), "application/zip")),
            ("files", ("skip.txt", b"ignored", "text/plain")),
        ],
    )

    assert resp.status_code == 200
    assert [item["name"] for item in resp.json()["items"]] == [
        "single.png",
        "one.png",
        "two.jpg",
    ]


def test_cloud_mock_imports_white_png_and_blank_video():
    c = client()

    resp = c.post(
        "/api/import/cloud_select",
        json={
            "paths": [
                "/Datasets/street_scenes/scene_001.png",
                "/Datasets/demo_videos/clip_a.mp4",
            ]
        },
    )

    assert resp.status_code == 200
    items = resp.json()["items"]
    assert [item["media_type"] for item in items] == ["image", "video"]

    image = c.get(f"/api/preview/{items[0]['id']}")
    video = c.get(f"/api/preview/{items[1]['id']}")
    assert image.status_code == 200
    assert image.headers["content-type"].startswith("image/jpeg")
    assert video.status_code == 200
    assert video.headers["content-type"].startswith("video/mp4")


def test_raw_preview_thumb_and_export():
    c = client()
    upload = c.post(
        "/api/import/upload",
        files=[("files", ("red.png", png_bytes(), "image/png"))],
    )
    item = upload.json()["items"][0]

    thumb = c.get(f"/api/preview/thumb/{item['id']}")
    preview = c.get(f"/api/preview/{item['id']}?version={item['versions'][0]['id']}")
    exported = c.get(f"/api/export/{item['id']}?version={item['versions'][0]['id']}")

    assert thumb.status_code == 200
    assert thumb.headers["content-type"].startswith("image/jpeg")
    assert preview.status_code == 200
    assert preview.headers["content-type"].startswith("image/jpeg")
    assert exported.status_code == 200
    assert exported.headers["content-type"].startswith("image/png")
    assert 'filename="red.png"' in exported.headers["content-disposition"]


def test_export_marks_only_requested_version_exported():
    c = client()
    item = WORKSPACE.add_item(name="multi.png", media_type="image", raw_payload=png_bytes("red"))
    second_raw = ItemVersion.make(
        kind="raw",
        payload=png_bytes("blue"),
        parent_id=item.versions[0].id,
    )
    WORKSPACE.add_version(item.id, second_raw)

    resp = c.get(f"/api/export/{item.id}?version={second_raw.id}")
    assert resp.status_code == 200

    summary = c.get("/api/items").json()["items"][0]
    versions = {version["id"]: version for version in summary["versions"]}
    assert versions[item.versions[0].id]["exported"] is False
    assert versions[second_raw.id]["exported"] is True
    assert "exported" in summary["sources"]


def test_tool_honors_parent_version_id_and_rejects_wrong_kind():
    c = client()
    item = WORKSPACE.add_item(name="tool.png", media_type="image", raw_payload=png_bytes())
    detected_a = ItemVersion.make(kind="detected", payload={"n": 1}, parent_id=item.versions[0].id)
    detected_b = ItemVersion.make(kind="detected", payload={"n": 2}, parent_id=item.versions[0].id)
    WORKSPACE.add_version(item.id, detected_a)
    WORKSPACE.add_version(item.id, detected_b)

    resp = c.post(
        "/api/tools/parent_echo",
        json={"item_id": item.id, "parent_version_id": detected_a.id},
    )
    assert resp.status_code == 200
    assert resp.json()["version"]["parent_id"] == detected_a.id

    wrong = c.post(
        "/api/tools/parent_echo",
        json={"item_id": item.id, "parent_version_id": item.versions[0].id},
    )
    assert wrong.status_code == 409


def test_tool_rejects_wrong_media_type():
    c = client()
    item = WORKSPACE.add_item(name="clip.mp4", media_type="video", raw_payload=b"video")

    resp = c.post("/api/tools/parent_echo", json={"item_id": item.id})

    assert resp.status_code == 409
