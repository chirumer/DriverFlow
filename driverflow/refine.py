"""Colab HTML/JS canvas widget for positive/negative click refinement.

Renders the input image overlaid with the current SAM 2 masks and DINO
boxes. The user clicks anywhere to add a refinement point (positive or
negative depending on a radio toggle), then hits Submit. The widget signals
``ClickSession.done_event`` so that ``Pipeline.apply_refinements`` can
proceed without polling.
"""

from __future__ import annotations

import base64
import html
import threading
import uuid
from typing import List, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from .types import SegResult


class ClickSession:
    """Mutable handle returned by ``collect_clicks``.

    Attributes are populated as the user clicks; ``done_event`` fires when
    the Submit button is pressed.
    """

    def __init__(self, seg: "SegResult"):
        self.seg = seg
        self.points: List[Tuple[float, float]] = []
        self.labels: List[int] = []  # 1 positive, 0 negative
        self.done_event = threading.Event()

    def _on_click(self, x: float, y: float, label: int) -> None:
        self.points.append((float(x), float(y)))
        self.labels.append(int(label))
        kind = "positive" if int(label) == 1 else "negative"
        print(f"Recorded {kind} click at ({x:.0f}, {y:.0f}). Total: {len(self.points)}")

    def _on_done(self) -> None:
        self.done_event.set()
        print(f"Submitted {len(self.points)} refinement point(s).")


def _composite_jpeg_b64(seg: "SegResult") -> str:
    """Build the canvas image: original + translucent masks + box outlines + 'Box i' labels."""
    import cv2
    import numpy as np

    img = cv2.cvtColor(seg.image_source.copy(), cv2.COLOR_RGB2BGR)

    rng = np.random.default_rng(0)  # deterministic colors
    for i, mask in enumerate(seg.masks):
        m = mask.astype(np.uint8)
        if m.ndim == 3:
            m = m.squeeze(0)

        color = rng.integers(64, 256, size=3, dtype=np.uint8).tolist()
        overlay = np.zeros_like(img)
        overlay[m > 0] = color

        alpha = 0.45
        area = m > 0
        img[area] = cv2.addWeighted(img, 1 - alpha, overlay, alpha, 0)[area]

        contours, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        cv2.drawContours(img, contours, -1, (0, 255, 255), 2)

    for i, box in enumerate(seg.boxes_xyxy):
        x1, y1, x2, y2 = map(int, box)
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 255), 2)
        label = f"Box {i}"
        cv2.putText(img, label, (x1, max(0, y1 - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

    ok, buffer = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 90])
    if not ok:
        raise RuntimeError("Failed to encode refinement composite as JPEG.")
    return base64.b64encode(buffer).decode("ascii")


_HTML_TEMPLATE = """
<div id="{uid}-wrap" style="font-family: sans-serif;">
  <div style="margin-bottom: 8px;">
    <label style="margin-right: 12px;">
      <input type="radio" name="{uid}-label" value="1" checked> Positive (foreground)
    </label>
    <label style="margin-right: 12px;">
      <input type="radio" name="{uid}-label" value="0"> Negative (background)
    </label>
    <button id="{uid}-done" style="padding: 4px 12px; cursor: pointer;">Submit</button>
    <button id="{uid}-undo" style="padding: 4px 12px; cursor: pointer; margin-left: 4px;">Undo</button>
  </div>
  <canvas id="{uid}-canvas" style="cursor: crosshair; max-width: 100%; border: 1px solid #333;"></canvas>
  <div id="{uid}-status" style="margin-top: 8px; font-weight: bold; color: #333;">
    Click the image to add refinement points, then press Submit.
  </div>
</div>
<script>
(function() {{
  var canvas = document.getElementById('{uid}-canvas');
  var ctx = canvas.getContext('2d');
  var status = document.getElementById('{uid}-status');
  var img = new Image();
  var clicks = [];

  function redraw() {{
    ctx.drawImage(img, 0, 0);
    for (var i = 0; i < clicks.length; i++) {{
      var c = clicks[i];
      ctx.beginPath();
      ctx.arc(c.x, c.y, 8, 0, 2 * Math.PI);
      ctx.fillStyle = c.label === 1 ? 'rgba(40, 220, 80, 0.9)' : 'rgba(240, 60, 60, 0.9)';
      ctx.fill();
      ctx.lineWidth = 2;
      ctx.strokeStyle = 'white';
      ctx.stroke();
    }}
  }}

  img.onload = function() {{
    canvas.width = img.width;
    canvas.height = img.height;
    redraw();
  }};
  img.src = "data:image/jpeg;base64,{img_b64}";

  canvas.onclick = function(e) {{
    var rect = canvas.getBoundingClientRect();
    var sx = canvas.width / rect.width;
    var sy = canvas.height / rect.height;
    var x = Math.round((e.clientX - rect.left) * sx);
    var y = Math.round((e.clientY - rect.top) * sy);
    var radios = document.getElementsByName('{uid}-label');
    var label = 1;
    for (var i = 0; i < radios.length; i++) {{ if (radios[i].checked) {{ label = parseInt(radios[i].value); }} }}

    clicks.push({{x: x, y: y, label: label}});
    redraw();
    var kind = label === 1 ? 'positive' : 'negative';
    status.innerHTML = 'Last: <b>' + kind + '</b> at (' + x + ', ' + y + '). Total: ' + clicks.length;
    google.colab.kernel.invokeFunction('{click_cb}', [x, y, label], {{}});
  }};

  document.getElementById('{uid}-undo').onclick = function() {{
    if (clicks.length === 0) {{ return; }}
    clicks.pop();
    redraw();
    status.innerHTML = 'Undid last click in display (server still has it). Total clicks shown: ' + clicks.length;
  }};

  document.getElementById('{uid}-done').onclick = function() {{
    status.innerHTML = 'Submitted. You can now run the next cell.';
    google.colab.kernel.invokeFunction('{done_cb}', [], {{}});
  }};
}})();
</script>
"""


def collect_clicks(seg: "SegResult") -> ClickSession:
    """Display the refinement canvas in the current Colab cell.

    Returns a ``ClickSession`` that is populated in place as the user clicks.
    The next cell should call ``pipeline.apply_refinements(seg, session)``,
    which blocks until the user presses Submit.
    """
    from google.colab import output  # type: ignore[import-not-found]
    from IPython.display import HTML, display

    session = ClickSession(seg)
    uid = f"df-{uuid.uuid4().hex[:8]}"
    click_cb = f"notebook.{uid}_click"
    done_cb = f"notebook.{uid}_done"

    output.register_callback(click_cb, session._on_click)
    output.register_callback(done_cb, session._on_done)

    img_b64 = _composite_jpeg_b64(seg)

    html_str = _HTML_TEMPLATE.format(
        uid=html.escape(uid),
        img_b64=img_b64,
        click_cb=html.escape(click_cb),
        done_cb=html.escape(done_cb),
    )
    display(HTML(html_str))
    return session
