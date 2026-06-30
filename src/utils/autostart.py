"""Run-on-startup via the per-user HKCU registry Run key (no-op off Windows)."""
import os
import sys
from pathlib import Path

from src.utils.paths import RESOURCE_ROOT

_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_VALUE_NAME = "FileOrganiser"


def is_supported() -> bool:
    return os.name == "nt"


def _command() -> str:
    """The launch command; --startup makes the app start hidden in the tray."""
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" --startup'
    python = Path(sys.executable)
    launcher = python.with_name("pythonw.exe")
    if not launcher.exists():
        launcher = python
    main_py = RESOURCE_ROOT / "src" / "main.py"
    return f'"{launcher}" "{main_py}" --startup'


def is_enabled() -> bool:
    if not is_supported():
        return False
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY) as key:
            winreg.QueryValueEx(key, _VALUE_NAME)
            return True
    except OSError:  # key or value missing
        return False


def enable() -> None:
    if not is_supported():
        return
    import winreg

    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, _VALUE_NAME, 0, winreg.REG_SZ, _command())


def disable() -> None:
    if not is_supported():
        return
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, _VALUE_NAME)
    except OSError:  # already absent
        pass
