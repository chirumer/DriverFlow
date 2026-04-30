"""Legacy DriverFlow UI launcher.

Boots the FastAPI annotation server bundled under ``backend/`` and exposes
it via the Colab proxy or a Cloudflare quick tunnel. The data-science
helpers (``Pipeline``, ``viz``, ``refine``) are an additive alternative for
notebooks that don't need the full UI.
"""

import os
import re
import subprocess
import sys
import threading
import time
import urllib.request

from . import setup as _setup


class DriverFlow:
    _CLOUDFLARED_BIN = "/usr/local/bin/cloudflared"
    _CLOUDFLARED_URL = (
        "https://github.com/cloudflare/cloudflared/releases/latest/download/"
        "cloudflared-linux-amd64"
    )
    _PORT = 8000

    def start(self, tunnel=False):
        self._setup_groundingdino()
        self._download_weights()
        self._install_backend_deps()
        self._start_backend()
        url = self._start_cloudflare_tunnel() if tunnel else self._get_colab_url()
        self._print_banner(url, tunnel)

    # ------------------------------------------------------------------

    def _setup_groundingdino(self):
        _setup.setup_groundingdino()

    def _download_weights(self):
        _setup.download_dino_weights()

    def _install_backend_deps(self):
        repo_dir = os.path.dirname(os.path.abspath(__file__))
        req_file = os.path.join(repo_dir, "backend", "requirements_colab.txt")
        print("Installing backend dependencies...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-q", "-r", req_file],
            check=True,
        )
        print("✓ Dependencies installed.")

    def _start_backend(self):
        repo_dir = os.path.dirname(os.path.abspath(__file__))
        backend_dir = os.path.join(repo_dir, "backend")
        print("Starting backend server (loading model, this may take a minute)...")
        proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", str(self._PORT)],
            cwd=backend_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )

        def _stream_stderr():
            for line in proc.stderr:
                print(line.decode("utf-8", errors="replace"), end="", flush=True)

        threading.Thread(target=_stream_stderr, daemon=True).start()

        deadline = time.time() + 600
        while time.time() < deadline:
            try:
                urllib.request.urlopen(f"http://localhost:{self._PORT}/", timeout=2)
                print("✓ Backend is up.")
                return
            except Exception:
                time.sleep(0.5)
        proc.kill()
        raise RuntimeError("Backend failed to start within 600 seconds.")

    def _start_cloudflare_tunnel(self):
        if not os.path.exists(self._CLOUDFLARED_BIN):
            print("Downloading cloudflared...")
            subprocess.run(
                ["wget", "-q", "-O", self._CLOUDFLARED_BIN, self._CLOUDFLARED_URL],
                check=True,
            )
            os.chmod(self._CLOUDFLARED_BIN, 0o755)

        print("Starting Cloudflare tunnel...")
        proc = subprocess.Popen(
            [self._CLOUDFLARED_BIN, "tunnel", "--url", f"http://localhost:{self._PORT}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

        url_found = threading.Event()
        url_result = []

        def _reader():
            for raw in proc.stdout:
                line = raw.decode("utf-8", errors="replace")
                m = re.search(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", line)
                if m:
                    url_result.append(m.group(0))
                    url_found.set()
                    return

        threading.Thread(target=_reader, daemon=True).start()

        if not url_found.wait(timeout=30):
            proc.kill()
            raise RuntimeError("Cloudflare tunnel URL not found within 30 seconds.")

        return url_result[0]

    def _get_colab_url(self):
        from google.colab.output import eval_js
        return eval_js(f"google.colab.kernel.proxyPort({self._PORT})")

    def _print_banner(self, url, tunnel):
        lines = [
            "╔══════════════════════════════════════════╗",
            "║         DriverFlow is LIVE!              ║",
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
