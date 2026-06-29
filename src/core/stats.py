"""A thread-safe tally of organise operations for the current session."""
import threading


class Stats:
    """Counts of files moved, their total size, and per-category counts."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.moved = 0
        self.total_size = 0
        self.per_category: dict[str, int] = {}

    def record(self, category: str, size: int) -> None:
        """Tally one moved file of ``size`` bytes into ``category``."""
        with self._lock:
            self.moved += 1
            self.total_size += size
            self.per_category[category] = self.per_category.get(category, 0) + 1

    def snapshot(self) -> tuple[int, int, dict[str, int]]:
        """Return a consistent (moved, total_size, per_category copy) tuple."""
        with self._lock:
            return self.moved, self.total_size, dict(self.per_category)

    def reset(self) -> None:
        with self._lock:
            self.moved = 0
            self.total_size = 0
            self.per_category = {}
