from __future__ import annotations

from pathlib import Path
import sys


def project_root() -> Path:
    # In PyInstaller onefile mode, __file__ points to a temp folder.
    # Use executable directory so history persists across scheduled runs.
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent

    return Path(__file__).resolve().parents[2]


def dotenv_file() -> Path:
    return project_root() / ".env"
