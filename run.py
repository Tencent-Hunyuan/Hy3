"""
Launcher for the Hy3 RAG application.

- Frees port 8766 if another process is holding it (Windows-safe).
- Starts the FastAPI backend via uvicorn.
- Opens the default browser to the app URL.

Usage:
    .venv/Scripts/python.exe run.py
"""
import os
import sys
import time
import socket
import subprocess
import threading
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PORT = int(os.getenv("PORT", "8766"))
HOST = os.getenv("HOST", "0.0.0.0")


def _port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def _free_port_windows(port: int):
    """Kill the process listening on `port` (Windows only)."""
    if not sys.platform.startswith("win"):
        return
    try:
        out = subprocess.run(
            ["netstat", "-ano"], capture_output=True, text=True
        ).stdout
        for line in out.splitlines():
            if f":{port}" in line and "LISTENING" in line:
                pid = line.split()[-1]
                subprocess.run(["taskkill", "/PID", pid, "/F"],
                               capture_output=True)
                time.sleep(1)
    except Exception:
        pass


def _open_browser(url: str):
    try:
        import webbrowser
        webbrowser.open(url)
    except Exception:
        pass


def main():
    if _port_in_use(PORT):
        print(f"[run] Port {PORT} is busy, trying to release it...")
        _free_port_windows(PORT)
        time.sleep(1)

    env = os.environ.copy()
    python = sys.executable
    url = f"http://localhost:{PORT}"
    print(f"[run] Starting Hy3 RAG on {url}")

    # Modules under backend/ use flat imports (import config, from embedder
    # import ...), so uvicorn must run with backend/ as the working dir.
    backend_dir = BASE_DIR / "backend"
    proc = subprocess.Popen(
        [python, "-m", "uvicorn", "main:app",
         "--host", HOST, "--port", str(PORT)],
        cwd=backend_dir, env=env,
    )

    threading.Timer(2.5, lambda: _open_browser(url)).start()

    try:
        proc.wait()
    except KeyboardInterrupt:
        print("\n[run] Stopping...")
        proc.terminate()


if __name__ == "__main__":
    main()
