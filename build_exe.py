"""PyInstaller build automation script for YouTube Keyword Finder.

Packages the application as a standalone Windows desktop distribution:
- Includes Streamlit static assets and runtime dependencies
- Preserves local SQLite database location outside package bundle
- Configures onedir distribution for instant startup without temp directory unpacking
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

def build():
    print("=== STARTING PYINSTALLER BUILD ===")
    dist_dir = PROJECT_ROOT / "dist"
    build_dir = PROJECT_ROOT / "build"
    spec_file = PROJECT_ROOT / "YouTubeKeywordFinder.spec"

    # Locate pyinstaller in venv
    pyinstaller_exe = PROJECT_ROOT / ".venv" / "Scripts" / "pyinstaller.exe"
    if not pyinstaller_exe.exists():
        pyinstaller_exe = Path("pyinstaller")

    cmd = [
        str(pyinstaller_exe),
        "--noconfirm",
        "--onedir",
        "--name", "YouTubeKeywordFinder",
        "--add-data", f"{PROJECT_ROOT / 'src'};src",
        "--add-data", f"{PROJECT_ROOT / 'app.py'};.",
        "--collect-all", "streamlit",
        "--collect-all", "openpyxl",
        "--collect-all", "altair",
        "--hidden-import", "sqlite3",
        "--hidden-import", "unicodedata",
        "--hidden-import", "requests",
        "--hidden-import", "pandas",
        str(PROJECT_ROOT / "launch_desktop.py"),
    ]

    print("Running command:", " ".join(cmd[:6]), "...")
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    if result.returncode != 0:
        print("[ERROR] PyInstaller build failed with exit code:", result.returncode)
        sys.exit(result.returncode)

    output_exe = dist_dir / "YouTubeKeywordFinder" / "YouTubeKeywordFinder.exe"
    if output_exe.exists():
        print(f"=== BUILD SUCCESSFUL: {output_exe} ({output_exe.stat().st_size} bytes) ===")
    else:
        print(f"[ERROR] Output executable not found at: {output_exe}")
        sys.exit(1)

if __name__ == "__main__":
    build()
