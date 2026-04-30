"""Cloudflare quick-tunnel helpers (lifted from the legacy launcher).

Used by :class:`driverflow.DriverFlow` when ``start(tunnel=True)``. Returns
the public ``trycloudflare.com`` URL once the binary prints it.
"""

from __future__ import annotations

import os
import re
import subprocess
import threading


CLOUDFLARED_BIN = "/usr/local/bin/cloudflared"
CLOUDFLARED_URL = (
    "https://github.com/cloudflare/cloudflared/releases/latest/download/"
    "cloudflared-linux-amd64"
)


def ensure_cloudflared() -> None:
    """Download the cloudflared binary if not already present."""
    if os.path.exists(CLOUDFLARED_BIN):
        return
    print("Downloading cloudflared...")
    subprocess.run(
        ["wget", "-q", "-O", CLOUDFLARED_BIN, CLOUDFLARED_URL],
        check=True,
    )
    os.chmod(CLOUDFLARED_BIN, 0o755)


def start_tunnel(port: int, *, timeout: float = 30.0) -> str:
    """Spawn ``cloudflared tunnel`` and return the public URL it prints."""
    ensure_cloudflared()
    print("Starting Cloudflare tunnel...")
    proc = subprocess.Popen(
        [CLOUDFLARED_BIN, "tunnel", "--url", f"http://localhost:{port}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    found = threading.Event()
    result: list[str] = []

    def _reader() -> None:
        for raw in proc.stdout:  # type: ignore[union-attr]
            line = raw.decode("utf-8", errors="replace")
            m = re.search(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", line)
            if m:
                result.append(m.group(0))
                found.set()
                return

    threading.Thread(target=_reader, daemon=True).start()

    if not found.wait(timeout=timeout):
        proc.kill()
        raise RuntimeError(f"Cloudflare tunnel URL not found within {timeout:.0f} seconds.")
    return result[0]
