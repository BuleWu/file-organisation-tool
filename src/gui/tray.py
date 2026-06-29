"""System-tray icon (pystray) so the app can run hidden in the background."""
from collections.abc import Callable

try:
    import pystray
    from PIL import Image

    TRAY_AVAILABLE = True
except ImportError:  # pystray not installed
    TRAY_AVAILABLE = False

if TRAY_AVAILABLE and hasattr(pystray.Icon, "_on_notify"):
    # pystray ignores balloon-notification clicks; route them to the default action (Open)
    _NIN_BALLOONUSERCLICK = 0x405
    _pystray_on_notify = pystray.Icon._on_notify

    def _on_notify_with_balloon_click(self, wparam, lparam):
        if lparam == _NIN_BALLOONUSERCLICK:
            self()  # activate the default item
            return
        return _pystray_on_notify(self, wparam, lparam)

    pystray.Icon._on_notify = _on_notify_with_balloon_click


class TrayIcon:
    """A tray icon with Open (default) and Quit menu items."""

    def __init__(
        self,
        image_path: str,
        on_open: Callable[[], None],
        on_quit: Callable[[], None],
        title: str = "File organiser",
    ) -> None:
        image = Image.open(image_path)
        menu = pystray.Menu(
            pystray.MenuItem("Open", lambda icon, item: on_open(), default=True),
            pystray.MenuItem("Quit", lambda icon, item: on_quit()),
        )
        self._icon = pystray.Icon("file_organiser", image, title, menu)

    def start(self) -> None:
        """Run the tray icon on its own thread."""
        self._icon.run_detached()

    def stop(self) -> None:
        self._icon.stop()

    def notify(self, message: str, title: str | None = None) -> None:
        """Show a balloon notification (best effort)."""
        try:
            self._icon.notify(message, title)
        except (NotImplementedError, OSError, RuntimeError):
            pass
