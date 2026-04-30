import os
import sys
import threading
import io
import base64
import zipfile
import tempfile
import json
from pathlib import Path

HOME = "/content"

os.chdir(f"{HOME}/GroundingDINO")
from groundingdino.util.inference import load_model, load_image, predict
os.chdir(HOME)

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
import cv2
import numpy as np
from PIL import Image

CONFIG_PATH = f"{HOME}/GroundingDINO/groundingdino/config/GroundingDINO_SwinT_OGC.py"
WEIGHTS_PATH = f"{HOME}/weights/groundingdino_swint_ogc.pth"

model = load_model(CONFIG_PATH, WEIGHTS_PATH)
model_lock = threading.Lock()

app = FastAPI()

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def _annotate_image(image_source, boxes, logits, phrases):
    frame = image_source[:, :, ::-1].copy()
    height, width = frame.shape[:2]
    boxes_list = boxes.cpu().tolist() if hasattr(boxes, "cpu") else boxes.tolist()
    logits_list = logits.cpu().tolist() if hasattr(logits, "cpu") else logits.tolist()

    for box, logit, phrase in zip(boxes_list, logits_list, phrases):
        cx, cy, box_w, box_h = box
        x1 = int((cx - box_w / 2) * width)
        y1 = int((cy - box_h / 2) * height)
        x2 = int((cx + box_w / 2) * width)
        y2 = int((cy + box_h / 2) * height)

        x1 = max(0, min(width - 1, x1))
        y1 = max(0, min(height - 1, y1))
        x2 = max(0, min(width - 1, x2))
        y2 = max(0, min(height - 1, y2))

        label = f"{phrase} {logit:.2f}"
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

        (label_w, label_h), baseline = cv2.getTextSize(
            label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1
        )
        label_y1 = max(0, y1 - label_h - baseline - 6)
        label_y2 = label_y1 + label_h + baseline + 6
        label_x2 = min(width - 1, x1 + label_w + 8)

        cv2.rectangle(frame, (x1, label_y1), (label_x2, label_y2), (0, 255, 0), -1)
        cv2.putText(
            frame,
            label,
            (x1 + 4, label_y2 - baseline - 3),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 0, 0),
            1,
            cv2.LINE_AA,
        )

    return frame


@app.get("/")
async def root():
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/api/detect")
async def detect(
    image: UploadFile = File(...),
    text_prompt: str = Form(...),
    box_threshold: float = Form(0.35),
    text_threshold: float = Form(0.25),
):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            tmp_path = tmp.name
            tmp.write(await image.read())

        try:
            image_source, image_tensor = load_image(tmp_path)

            with model_lock:
                boxes, logits, phrases = predict(
                    model=model,
                    image=image_tensor,
                    caption=text_prompt,
                    box_threshold=box_threshold,
                    text_threshold=text_threshold,
                )

            boxes_list = boxes.cpu().tolist() if hasattr(boxes, "cpu") else boxes.tolist()
            logits_list = logits.cpu().tolist() if hasattr(logits, "cpu") else logits.tolist()

            detections = []
            class_counts = {}

            for box, logit, phrase in zip(boxes_list, logits_list, phrases):
                detections.append(
                    {"phrase": phrase, "confidence": logit, "box_cxcywh": box}
                )

                if phrase not in class_counts:
                    class_counts[phrase] = {"count": 0, "sum_confidence": 0.0}
                class_counts[phrase]["count"] += 1
                class_counts[phrase]["sum_confidence"] += logit

            class_counts_list = [
                {
                    "class": cls,
                    "count": counts["count"],
                    "avg_confidence": counts["sum_confidence"] / counts["count"],
                }
                for cls, counts in sorted(class_counts.items())
            ]

            annotated_frame = _annotate_image(image_source, boxes, logits, phrases)

            _, buffer = cv2.imencode(".jpg", annotated_frame)
            img_b64 = base64.b64encode(buffer).decode("utf-8")

            H, W = image_source.shape[:2]

            return JSONResponse(
                {
                    "detections": detections,
                    "class_counts": class_counts_list,
                    "annotated_image_b64": img_b64,
                    "image_width": W,
                    "image_height": H,
                }
            )

        finally:
            os.unlink(tmp_path)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/download_yolo")
async def download_yolo(body: dict):
    try:
        detections = body.get("detections", [])
        image_width = body.get("image_width", 0)
        image_height = body.get("image_height", 0)

        phrases = [d["phrase"] for d in detections]
        classes = sorted(set(phrases))
        class_to_id = {cls: idx for idx, cls in enumerate(classes)}

        classes_txt = "\n".join(classes)

        annotations_lines = []
        for detection in detections:
            phrase = detection["phrase"]
            box = detection["box_cxcywh"]
            class_id = class_to_id[phrase]
            cx, cy, w, h = box
            annotations_lines.append(
                f"{class_id} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}"
            )

        annotations_txt = "\n".join(annotations_lines)

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("classes.txt", classes_txt)
            zf.writestr("annotations.txt", annotations_txt)

        zip_buffer.seek(0)

        return StreamingResponse(
            iter([zip_buffer.getvalue()]),
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=driverflow_annotations.zip"},
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
