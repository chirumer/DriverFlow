# DriverFlow — Intelligent Image Annotation Tool

A polished, cloud-ready annotation tool powered by **GroundingDINO** for zero-shot object detection. Deploy to Google Colab in minutes.

## Features

✨ **Zero-shot Detection** — Detect any objects using natural language prompts  
🎯 **Interactive UI** — Upload images, adjust model parameters, preview results in real-time  
📊 **Structured Output** — Generate YOLO format annotations automatically  
☁️ **Colab Native** — Runs entirely in Google Colab with ngrok or Colab proxy tunneling  
🎨 **Polished Design** — Dark theme UI with real-time feedback and smooth interactions  

## Prerequisites

1. **Google Colab** access
2. **GitHub Personal Access Token (PAT)** with `repo` scope
   - Create one at https://github.com/settings/tokens
   - Permissions needed: `repo` (full control)
3. **(Optional) ngrok auth token** for persistent public URL
   - Free tier at https://dashboard.ngrok.com/get-started/your-authtoken
   - Without ngrok, you can use Colab's built-in proxy (may auto-logout after inactivity)

## Quick Start

1. Open [`colab_launcher.ipynb`](colab_launcher.ipynb) in Google Colab
2. Fill in your GitHub credentials in the first cell:
   ```python
   GITHUB_TOKEN = "your_github_pat_here"
   GITHUB_USERNAME = "your_github_username"
   NGROK_TOKEN = "your_ngrok_token_here"  # optional
   ```
3. Click **Runtime → Run all**
4. Wait for the setup to complete (2–3 minutes)
5. Click the printed URL to open the DriverFlow UI

## Usage

1. **Upload Image** — Drag and drop or click to browse
2. **Enter Text Prompt** — Describe objects to detect (e.g., `car . person . traffic light`)
3. **Adjust Thresholds** (optional)
   - **Box Threshold** (0.1–0.9, default 0.35) — higher = more confident detections only
   - **Text Threshold** (0.1–0.9, default 0.25) — higher = stricter text-alignment matching
4. **Click Detect** — Model runs and returns:
   - Annotated image with bounding boxes and class labels
   - Summary table with detection counts and average confidence scores
5. **Download** — Export results as YOLO format (ZIP file with `annotations.txt` + `classes.txt`)

## YOLO Format

The tool exports bounding box annotations in YOLO format:

**`annotations.txt`** (one detection per line):
```
<class_id> <cx> <cy> <w> <h>
```
- `class_id` — integer index (0-based, sorted alphabetically by class name)
- `cx, cy, w, h` — normalized coordinates (0–1 range)
  - `cx`, `cy` — box center (relative to image width/height)
  - `w`, `h` — box width and height (relative to image width/height)

**`classes.txt`** (one class name per line, alphabetically sorted):
```
car
person
traffic light
```

## Architecture

```
DriverFlow/
├── colab_launcher.ipynb       # Colab entry point
├── backend/
│   ├── app.py                 # FastAPI server + GroundingDINO integration
│   ├── requirements.txt       # Python dependencies
│   └── static/
│       ├── index.html         # UI markup
│       ├── style.css          # Dark theme styling
│       └── app.js             # Browser logic & API calls
└── README.md
```

### Backend Stack
- **FastAPI** — web framework
- **GroundingDINO** — zero-shot object detection model
- **OpenCV** — image processing
- **uvicorn** — ASGI server
- **pyngrok** — ngrok integration for Colab tunneling

### Frontend Stack
- **Vanilla HTML5/CSS3/JS** — no build step, no dependencies
- **Drag-and-drop file upload** with live image preview
- **Real-time slider feedback** for model parameters
- **Base64 image embedding** for inline results
- **ZIP download** via Blob API

## API Reference

### `POST /api/detect`

Runs GroundingDINO inference on an uploaded image.

**Request** (multipart/form-data):
| Field | Type | Default | Description |
|---|---|---|---|
| `image` | File | — | Image file (JPEG, PNG, etc.) |
| `text_prompt` | str | — | Detection prompt (e.g., "car . person") |
| `box_threshold` | float | 0.35 | Objectness score cutoff |
| `text_threshold` | float | 0.25 | Text-alignment score cutoff |

**Response** (200 application/json):
```json
{
  "detections": [
    {
      "phrase": "car",
      "confidence": 0.87,
      "box_cxcywh": [0.51, 0.48, 0.12, 0.18]
    }
  ],
  "class_counts": [
    {"class": "car", "count": 3, "avg_confidence": 0.75},
    {"class": "person", "count": 1, "avg_confidence": 0.92}
  ],
  "annotated_image_b64": "<base64 JPEG string>",
  "image_width": 1280,
  "image_height": 720
}
```

### `POST /api/download_yolo`

Generates a ZIP file with YOLO format annotations.

**Request** (application/json):
```json
{
  "detections": [ ... ],
  "image_width": 1280,
  "image_height": 720
}
```

**Response** (200 application/zip):
- `classes.txt` — alphabetically sorted class names
- `annotations.txt` — normalized CXCYWH format

## Security Notes

⚠️ **Do NOT commit `colab_launcher.ipynb` with credentials filled in to a public repository.**

- The notebook stores your GitHub PAT as a plain Python string
- If you push the notebook with credentials, immediately revoke the token at https://github.com/settings/tokens
- Best practice: Use GitHub's PAT scoping to limit what the token can do

## Troubleshooting

### "Module not found" errors during Colab setup
- Some GPU/CPU compatibility issues can arise. Re-run the installer cell. CUDA patches are applied idempotently.

### ngrok connection fails
- Free tier allows one simultaneous tunnel. If you have an old tunnel active, run `ngrok.kill()` first.
- Ngrok token scope: ensure it's from a free account with no connections limit.

### Colab proxy times out
- Colab's built-in proxy may close after 30 minutes of inactivity. Use an ngrok token for persistent access.

### Slow detection on CPU
- GroundingDINO's SwinT variant is the fastest available checkpoint. Colab's GPU is usually allocated automatically; ensure you're not on a CPU-only runtime.

### Missing annotations or low confidence
- Adjust thresholds downward (e.g., 0.25 → 0.15) to be more permissive
- Refine text prompts: instead of "object," try specific descriptions like "red car" or "traffic sign"

## Model Details

**Model:** GroundingDINO SwinT-OGC (Swin Transformer Tiny, Object Grounding with Captions)
- Checkpoint: `groundingdino_swint_ogc.pth`
- Size: ~400 MB
- Architecture: Vision Transformer + BERT-based text encoder + cross-modal reasoning
- License: Apache 2.0 (IDEA-Research/GroundingDINO)

## License

This project is provided as-is. GroundingDINO is licensed under Apache 2.0. See [https://github.com/IDEA-Research/GroundingDINO](https://github.com/IDEA-Research/GroundingDINO) for details.

## Contributing

To modify or extend DriverFlow:
1. Clone this repo locally
2. Edit files in `backend/`
3. Commit and push changes
4. Re-run `colab_launcher.ipynb` to test in Colab (it pulls the latest main branch)

## Support

For issues or feedback:
- Check the Troubleshooting section above
- Report bugs at https://github.com/chirumer/DriverFlow/issues
