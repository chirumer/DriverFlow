"""Boot the FastAPI app in-process on a daemon thread.

The new workspace UI keeps the Pipeline (with loaded weights) in the same
Python process as the FastAPI app, so we run uvicorn on a thread instead
of spawning a subprocess like the legacy launcher did.
"""

from __future__ import annotations

import threading
import time
import urllib.request
from typing import Optional

from . import cloudflared as _cf
from .server import build_app


_server_thread: Optional[threading.Thread] = None
_server_lock = threading.Lock()


def _start_uvicorn(port: int) -> None:
    import uvicorn

    app = build_app()
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
    server = uvicorn.Server(config)
    server.run()


def _wait_for_server(port: int, timeout: float = 600.0) -> None:
    deadline = time.time() + timeout
    last_err: Optional[Exception] = None
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"http://localhost:{port}/", timeout=2)
            return
        except Exception as e:  # noqa: BLE001 — broad on purpose, we just retry
            last_err = e
            time.sleep(0.5)
    raise RuntimeError(
        f"Webui backend failed to start within {timeout:.0f} seconds. Last error: {last_err}"
    )


def start_server(port: int) -> None:
    """Start uvicorn on a daemon thread (idempotent)."""
    global _server_thread
    with _server_lock:
        if _server_thread is not None and _server_thread.is_alive():
            return
        t = threading.Thread(target=_start_uvicorn, args=(port,), daemon=True)
        t.start()
        _server_thread = t
    _wait_for_server(port)


def get_colab_url(port: int) -> str:
    """Resolve the Colab proxy URL for ``port``. Raises if not running in Colab."""
    from google.colab.output import eval_js  # type: ignore[import-not-found]

    return eval_js(f"google.colab.kernel.proxyPort({port})")


def get_tunnel_url(port: int) -> str:
    return _cf.start_tunnel(port)
