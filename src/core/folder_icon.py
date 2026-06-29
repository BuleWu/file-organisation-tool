"""Apply a custom folder icon on Windows via ``desktop.ini`` (no-op elsewhere)."""
import ctypes
import logging
import os
import shutil
from pathlib import Path

from PIL import Image

logger = logging.getLogger(__name__)

ICON_FILENAME = "folder_icon.ico"
DESKTOP_INI = "desktop.ini"
_HIDDEN = 0x2
_SYSTEM = 0x4


def _set_attributes(path: Path, attributes: int) -> None:
    if os.name == "nt":
        ctypes.windll.kernel32.SetFileAttributesW(str(path), attributes)


def apply_folder_icon(folder: Path, icon_path: str) -> None:
    """Point ``folder``'s Explorer icon at ``icon_path`` (Windows only)."""
    if os.name != "nt" or not icon_path:
        return
    source = Path(icon_path)
    if not source.is_file():
        return
    folder = Path(folder)
    ico = folder / ICON_FILENAME
    try:
        if source.suffix.lower() == ".ico":
            shutil.copyfile(source, ico)
        else:
            Image.open(source).save(ico, format="ICO")
        ini = folder / DESKTOP_INI
        ini.write_text(
            f"[.ShellClassInfo]\nIconResource={ico},0\nIconFile={ico}\nIconIndex=0\n",
            encoding="utf-8",
        )
        _set_attributes(ini, _HIDDEN | _SYSTEM)
        _set_attributes(ico, _HIDDEN)
        _set_attributes(folder, _SYSTEM)
    except (OSError, ValueError) as exc:
        logger.warning("could not set folder icon for %s: %s", folder, exc)
