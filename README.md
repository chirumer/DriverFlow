# DriverFlow

DriverFlow is an AI-assisted image annotation and segmentation workspace for
Google Colab. It combines Grounding DINO detection, SAM 2 segmentation, click
refinement, versioned previews, and YOLO/raw-media export in a browser UI.

## Quick Start

```python
!pip install driverflow

from driverflow import DriverFlow

DriverFlow().start()              # Colab proxy URL
# DriverFlow().start(tunnel=True) # public Cloudflare quick-tunnel URL
```

`DriverFlow` starts the current workspace UI. The older single-image,
detect-only UI is still available as `DriverFlowOld` for backwards
compatibility.

```python
from driverflow import DriverFlowOld

DriverFlowOld().start()
```

## Workspace UI

The web UI lets you build a small in-memory workspace of images and videos:

- Import images, videos, or zip files by dragging onto the page, clicking the
  import button, or clicking the empty preview area.
- Import from the mocked DriverFlow Cloud tree. Cloud is not implemented yet;
  selected image files become 500x500 white PNGs and selected video files
  become plain 2-second MP4s.
- Use the left sidebar to browse raw, processed, and exported items with
  image/video filters.
- Click or drag one item into the preview area to make it the working item.
- Use the right tools panel to run image tools. Videos can be organized,
  previewed, and raw-exported, but no video tools are currently available.
- Scroll to the Data Workspace to view every version of the working item:
  raw media, detected boxes, segmented masks, and refined masks with clicks.
- Click or drag any Data Workspace card into the preview area to make that
  version authoritative for the next tool run or export.

Replacing a dirty working item warns before switching away from unexported
derived work.

## Models And Tools

Models are loaded on demand from the right-side model panel:

- `Detect` requires Grounding DINO and a raw image version.
- `Segment` requires SAM 2 and a detected image version with boxes.
- `Refine` requires SAM 2 and a segmented or refined image version with masks.

Trying to interact with a tool whose model is not loaded expands/highlights the
required model. Heavy model dependencies and weights are installed lazily when
models are loaded.

## Export

The export button exports exactly the version currently shown in the preview:

- Raw image/video versions export the original media bytes.
- Detected image versions export YOLO bounding-box annotations.
- Segmented or refined image versions export YOLO segmentation annotations.

YOLO exports are ZIP files containing `classes.txt` and `annotations.txt`.

## Library API

You can also use the pipeline directly from Python:

```python
from driverflow import Pipeline, viz

pipe = Pipeline().setup(dino=True, sam=True)
det = pipe.detect("image.jpg", prompt="car . person . traffic light")
seg = pipe.segment(det)
viz.show_masks(seg)
```

## Web API Shape

The workspace UI is backed by a local FastAPI server. The main endpoint groups
are:

- `POST /api/import/upload`
- `GET /api/import/cloud_tree`
- `POST /api/import/cloud_select`
- `GET /api/items`
- `GET /api/preview/{item_id}`
- `GET /api/preview/thumb/{item_id}`
- `GET /api/models/status`
- `POST /api/models/load_dino`
- `POST /api/models/load_sam`
- `GET /api/tools/registry`
- `POST /api/tools/{name}`
- `GET /api/export/{item_id}`

The old `/api/detect` and `/api/download_yolo` endpoints belong to the legacy
`DriverFlowOld` UI.

## License

MIT - see [LICENSE](LICENSE).
