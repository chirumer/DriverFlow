"""New ``DriverFlow`` launcher — boots the workspace UI under ``webui/``.

Replaces the legacy single-page detect-only launcher (now ``DriverFlowOld``
in :mod:`driverflow._driverflow`). Same public ``.start(tunnel=False)``
shape so existing notebooks just need to keep using the ``DriverFlow``
import.
"""

from __future__ import annotations

import subprocess
import sys

from .webui import launcher as _launcher


class DriverFlow:
    """Boot the DriverFlow workspace UI.

    Typical use::

        from driverflow import DriverFlow
        DriverFlow().start()              # Colab proxy URL
        DriverFlow().start(tunnel=True)   # public Cloudflare quick-tunnel URL
    """

    _PORT = 8000

    def start(self, tunnel: bool = False) -> str:
        self._install_runtime_deps()
        _launcher.start_server(self._PORT)
        url = (
            _launcher.get_tunnel_url(self._PORT)
            if tunnel
            else _launcher.get_colab_url(self._PORT)
        )
        self._print_banner(url, tunnel)
        return url

    # ------------------------------------------------------------------

    def _install_runtime_deps(self) -> None:
        """Install the small set of pip deps the FastAPI server needs.

        Heavy weights (DINO, SAM 2) are installed lazily on demand when the
        user clicks Load DINO / Load SAM in the UI.
        """
        deps = [
            "fastapi==0.111.0",
            "uvicorn[standard]==0.29.0",
            "python-multipart==0.0.9",
            "opencv-python-headless",
            "pillow",
        ]
        print("Installing webui runtime dependencies...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-q", *deps],
            check=True,
        )

    def _print_banner(self, url: str, tunnel: bool) -> None:
        lines = [
            "╔══════════════════════════════════════════╗",
            "║      DriverFlow Workspace is LIVE!       ║",
            "║                                          ║",
            "║  Open this URL in your browser:          ║",
            f"║  {url:<40}║",
            "║                                          ║",
        ]
        if not tunnel:
            lines += [
                "║  Note: Colab proxy may expire on         ║",
                "║  inactivity. Use tunnel=True for a       ║",
                "║  persistent public URL.                  ║",
                "║                                          ║",
            ]
        lines.append("╚══════════════════════════════════════════╝")
        print("\n" + "\n".join(lines) + "\n")
