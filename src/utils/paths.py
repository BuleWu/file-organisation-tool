"""Project paths: bundled resources vs the writable per-user dir, frozen-aware."""
import os
import sys
from pathlib import Path

if getattr(sys, "frozen", False):
    RESOURCE_ROOT = Path(sys._MEIPASS)  # PyInstaller extraction dir
else:
    RESOURCE_ROOT = Path(__file__).resolve().parents[2]

WINDOW_ICON = RESOURCE_ROOT / "assets" / "icons" / "folder.ico"
DEFAULT_RULES_PATH = RESOURCE_ROOT / "configs" / "default_rules.yaml"


def _user_data_dir() -> Path:
    """A writable per-user directory for config and logs."""
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming"
        return Path(base) / "FileOrganiser"
    return Path.home() / ".file-organiser"


USER_DATA_DIR = _user_data_dir()
USER_RULES_PATH = USER_DATA_DIR / "user_rules.yaml"
LOG_FILE = USER_DATA_DIR / "file-organiser.log"
