"""Entry point: launch the File Organiser GUI."""
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

# make 'import src...' resolve when launched from any cwd (e.g. Windows startup)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.gui.app import App  # noqa: E402
from src.utils.paths import LOG_FILE, USER_DATA_DIR  # noqa: E402
from src.utils.single_instance import SingleInstance  # noqa: E402


def _log_uncaught(exc_type, exc, tb) -> None:
    logging.getLogger("src").critical("uncaught exception", exc_info=(exc_type, exc, tb))


def main() -> None:
    """Create the application window and enter the GUI event loop."""
    USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
    handlers: list[logging.Handler] = [
        RotatingFileHandler(LOG_FILE, maxBytes=512_000, backupCount=2, encoding="utf-8")
    ]
    if not getattr(sys, "frozen", False):
        handlers.append(logging.StreamHandler())  # console only when run from source
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        handlers=handlers,
    )
    sys.excepthook = _log_uncaught

    instance = SingleInstance()
    if not instance.acquire():
        logging.getLogger("src").info("another instance is already running; exiting")
        return

    app = App(start_hidden="--startup" in sys.argv)
    instance.on_activate = app.request_show
    app.mainloop()
    instance.release()


if __name__ == "__main__":
    main()
