"""watchdog integration: forward file events to a callback."""
import logging
from collections.abc import Callable
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

logger = logging.getLogger(__name__)


class _DispatchHandler(FileSystemEventHandler):
    """Logs directory activity and forwards new files to ``on_file``."""

    def __init__(self, on_file: Callable[[Path], None]) -> None:
        self._on_file = on_file

    def on_created(self, event: FileSystemEvent) -> None:
        kind = "folder" if event.is_directory else "file"
        logger.info("%s added: %s", kind, Path(event.src_path).name)
        if not event.is_directory:
            self._on_file(Path(event.src_path))

    def on_deleted(self, event: FileSystemEvent) -> None:
        kind = "folder" if event.is_directory else "file"
        logger.info("%s removed: %s", kind, Path(event.src_path).name)

    def on_moved(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            logger.info(
                "folder moved: %s → %s", Path(event.src_path).name, Path(event.dest_path).name
            )
        else:
            self._on_file(Path(event.dest_path))


class FolderWatcher:
    """Watches a folder tree and forwards its file events to ``on_file``."""

    def __init__(
        self, path: Path, on_file: Callable[[Path], None], recursive: bool = True
    ) -> None:
        self.path = Path(path)
        self.recursive = recursive
        self._on_file = on_file
        self._observer: Observer | None = None

    @property
    def is_running(self) -> bool:
        return self._observer is not None and self._observer.is_alive()

    def start(self) -> None:
        """Begin watching the folder."""
        if self.is_running:
            return
        self._observer = Observer()
        self._observer.schedule(
            _DispatchHandler(self._on_file), str(self.path), recursive=self.recursive
        )
        self._observer.start()

    def stop(self) -> None:
        """Stop watching and release the observer thread."""
        if self._observer is None:
            return
        self._observer.stop()
        self._observer.join()
        self._observer = None
