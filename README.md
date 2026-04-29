# DriverFlow — Intelligent Image Annotation Tool

A cloud-ready annotation tool powered by **GroundingDINO** for zero-shot object detection. Runs entirely in Google Colab — no local setup required.

## Features

- **Zero-shot detection** — detect any objects using natural language prompts
- **Interactive UI** — upload images, adjust thresholds, preview results in real-time
- **YOLO export** — download annotations as a ZIP with `annotations.txt` + `classes.txt`
- **Cloudflare Tunnel** — optional persistent public URL with no account required

## Quick Start (Google Colab)

```python
!pip install driverflow

from driverflow import DriverFlow
DriverFlow().start()               # Colab proxy URL
# DriverFlow().start(tunnel=True)  # persistent public URL via Cloudflare
```

`start()` handles everything: installing GroundingDINO, downloading model weights, installing dependencies, and launching the web UI.

## Usage

1. **Upload an image** — drag and drop or click to browse
2. **Enter a text prompt** — describe objects to detect, e.g. `car . person . traffic light`
3. **Adjust thresholds** (optional)
   - **Box Threshold** (default 0.35) — higher = only more confident detections
   - **Text Threshold** (default 0.25) — higher = stricter text-alignment matching
4. **Click Detect** — returns an annotated image and a summary table
5. **Download** — export as YOLO format ZIP

## YOLO Export Format

**`annotations.txt`** — one detection per line:
```
<class_id> <cx> <cy> <w> <h>
```
All coordinates are normalized (0–1). `class_id` is 0-based, sorted alphabetically.

**`classes.txt`** — one class name per line, alphabetically sorted.

## API

The tool runs a local FastAPI server with two endpoints:

### `POST /api/detect`
Multipart form: `image` (file), `text_prompt` (str), `box_threshold` (float), `text_threshold` (float).

Returns JSON with `detections`, `class_counts`, `annotated_image_b64`, `image_width`, `image_height`.

### `POST /api/download_yolo`
JSON body: `detections`, `image_width`, `image_height`.

Returns a ZIP file with `annotations.txt` and `classes.txt`.

## Troubleshooting

**Slow first run** — GroundingDINO (~400 MB) and model weights are downloaded on first `start()`. Subsequent runs in the same Colab session are fast.

**Low confidence / missing detections** — lower the thresholds (e.g. 0.25 → 0.15) or use more specific prompts like `red car` instead of `car`.

**Colab proxy expires** — use `tunnel=True` for a persistent Cloudflare URL.

## Model

GroundingDINO SwinT-OGC — Vision Transformer + BERT text encoder, ~400 MB checkpoint. Licensed under Apache 2.0 by IDEA-Research.

## License

MIT — see [LICENSE](LICENSE).
