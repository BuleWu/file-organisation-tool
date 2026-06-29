"""Entry point: launch the File Organiser GUI."""
import logging
import sys
from pathlib import Path

# make 'import src...' resolve when launched from any cwd (e.g. Windows startup)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.gui.app import App  # noqa: E402


def main() -> None:
    """Create the application window and enter the GUI event loop."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    app = App(start_hidden="--startup" in sys.argv)
    app.mainloop()


if __name__ == "__main__":
    main()
