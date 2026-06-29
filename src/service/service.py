"""Service lifecycle: ties the folder watcher to the organizer via the rules."""
import logging
from collections.abc import Callable
from pathlib import Path

from src.config.rules import RulesConfig
from src.core.organizer import organise_file, simulate
from src.core.stats import Stats
from src.core.watcher import FolderWatcher

logger = logging.getLogger(__name__)


class OrganiserService:
    """Owns the watcher lifecycle and applies the rules to incoming files."""

    def __init__(self, rules: RulesConfig | None = None) -> None:
        self.rules = rules or RulesConfig()
        self._watcher: FolderWatcher | None = None
        self.stats = Stats()
        # set by the GUI; given (source, target), returns rename|skip|overwrite|defer.
        self.conflict_resolver: Callable[[Path, Path], str] | None = None

    @property
    def is_running(self) -> bool:
        return self._watcher is not None and self._watcher.is_running

    def _handle_file(self, path: Path) -> None:
        organise_file(path, self.rules, self.rules.watch.output, self.conflict_resolver, self.stats)

    def organise_with_decision(self, source: Path, decision: str) -> None:
        """Organise one file, forcing a pre-chosen conflict decision."""
        organise_file(source, self.rules, self.rules.watch.output, lambda s, t: decision, self.stats)

    def simulate(self) -> dict:
        """Preview what organising the watched folder would do (no disk changes)."""
        return simulate(self.rules)

    def organise_existing(self) -> int:
        """Sort files already present in the watched folder. Returns how many moved."""
        watch = self.rules.watch
        if not watch.directory or not watch.output:
            logger.warning("watched and output folders must both be set")
            return 0
        root = Path(watch.directory)
        if not root.is_dir():
            logger.warning("watched folder does not exist: %s", root)
            return 0
        Path(watch.output).mkdir(parents=True, exist_ok=True)
        paths = root.rglob("*") if watch.recursive else root.glob("*")
        existing = [p for p in paths if p.is_file()]  # snapshot before moving anything
        moved = sum(
            organise_file(p, self.rules, watch.output, self.conflict_resolver, self.stats) is not None
            for p in existing
        )
        logger.info("organised %d existing file(s) in %s", moved, root)
        return moved

    def start(self) -> None:
        """Begin watching the configured folder and organising new files."""
        if self.is_running:
            return
        watch = self.rules.watch
        if not watch.directory or not watch.output:
            logger.warning("watched and output folders must both be set")
            return
        root = Path(watch.directory)
        if not root.is_dir():
            logger.warning("watched folder does not exist: %s", root)
            return
        Path(watch.output).mkdir(parents=True, exist_ok=True)
        self._watcher = FolderWatcher(root, self._handle_file, recursive=watch.recursive)
        self._watcher.start()
        logger.info("watching %s -> %s (recursive=%s)", root, watch.output, watch.recursive)

    def pause(self) -> None:
        """Stop the observer; watchdog has no native pause, so resume recreates it."""
        self.stop()

    def resume(self) -> None:
        """Resume watching after a pause."""
        self.start()

    def stop(self) -> None:
        """Stop watching and tear down the watcher."""
        if self._watcher is None:
            return
        self._watcher.stop()
        self._watcher = None
        logger.info("stopped watching")
