"""Standalone Desktop Bootstrap Entrypoint for YouTube Keyword Finder.

Used when bundling with PyInstaller or running as a desktop app.
Directs Streamlit to launch the bundled app.py, automatically opens the
default browser to http://localhost:8501, and cleanly shuts down on exit.
"""

import os
import sys
import threading
import time
import webbrowser
from pathlib import Path

# Set UTF-8 encoding for Windows console
if sys.platform.startswith("win"):
    os.environ["PYTHONIOENCODING"] = "utf-8"

# Locate runtime bundle directory
if getattr(sys, "frozen", False):
    bundle_dir = Path(sys._MEIPASS)
else:
    bundle_dir = Path(__file__).resolve().parent

if str(bundle_dir) not in sys.path:
    sys.path.insert(0, str(bundle_dir))

import streamlit.web.cli as stcli


def auto_open_browser(url: str = "http://localhost:8501", delay_seconds: float = 2.0) -> None:
    """Open default system browser once Streamlit HTTP server is listening."""
    time.sleep(delay_seconds)
    try:
        webbrowser.open(url)
    except Exception:
        pass


def main() -> None:
    """Launch the embedded Streamlit application."""
    app_path = bundle_dir / "app.py"
    if not app_path.exists():
        print(f"[ERROR] Target application script not found at: {app_path}", file=sys.stderr)
        sys.exit(1)

    user_args = sys.argv[1:]
    port = os.environ.get("STREAMLIT_SERVER_PORT", "8501")
    for arg in user_args:
        if "--server.port=" in arg:
            port = arg.split("=", 1)[1]

    # Spawn browser opener in background thread
    threading.Thread(target=auto_open_browser, args=(f"http://localhost:{port}",), daemon=True).start()

    # Pass command-line arguments to Streamlit runtime
    sys.argv = [
        "streamlit",
        "run",
        str(app_path),
        f"--server.port={port}",
        "--server.headless=true",
        "--global.developmentMode=false",
    ] + [a for a in user_args if not a.startswith("--server.port")]
    sys.exit(stcli.main())


if __name__ == "__main__":
    main()
