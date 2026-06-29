"""Apply the rules to a file: classify it and move it into its category folder."""
import logging
import re
import shutil
import time
from collections.abc import Callable
from pathlib import Path

from src.config.rules import RulesConfig
from src.core.classifier import classify
from src.core.folder_icon import DESKTOP_INI, ICON_FILENAME, apply_folder_icon
from src.core.stats import Stats

logger = logging.getLogger(__name__)

_NUMBER_PREFIX = re.compile(r"^\d+_")
_SKIP_NAMES = {DESKTOP_INI.lower(), ICON_FILENAME.lower()}
_MOVE_ATTEMPTS = 15  # a just-copied file may stay locked until the copy finishes
_MOVE_DELAY = 0.4


def _safe_move(path: Path, destination: Path) -> Path | None:
    """Move ``path`` to ``destination``, retrying while it is still locked.

    A file copied in via Explorer is held open until the copy completes, which
    surfaces as a transient PermissionError (WinError 32); we back off and retry
    rather than give up. Other move errors fail immediately.
    """
    for _ in range(_MOVE_ATTEMPTS):
        try:
            return Path(shutil.move(str(path), str(destination)))
        except PermissionError:
            time.sleep(_MOVE_DELAY)
        except (OSError, shutil.Error) as exc:
            logger.warning("could not move %s -> %s: %s", path, destination, exc)
            return None
    logger.warning(
        "could not move %s: still locked after %.0fs", path.name, _MOVE_ATTEMPTS * _MOVE_DELAY
    )
    return None


def _unique_destination(destination: Path) -> Path:
    """Return a non-existing path, appending ' (n)' before the suffix if needed."""
    if not destination.exists():
        return destination
    stem, suffix, parent = destination.stem, destination.suffix, destination.parent
    counter = 1
    while True:
        candidate = parent / f"{stem} ({counter}){suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def _sort_key(path: Path, mode: str):
    if mode == "date":
        return path.stat().st_mtime
    return _NUMBER_PREFIX.sub("", path.name).lower()  # sort by real name, not old index


def _renumber(folder: Path, mode: str, order: str) -> None:
    """Prefix files in ``folder`` with a zero-padded index in sorted order."""
    files = [
        p for p in folder.iterdir() if p.is_file() and p.name.lower() not in _SKIP_NAMES
    ]
    files.sort(key=lambda p: _sort_key(p, mode), reverse=(order == "desc"))
    # two passes via temp names so shifting indices never collide mid-rename
    staged = []
    for index, path in enumerate(files):
        base = _NUMBER_PREFIX.sub("", path.name)
        temp = folder / f".reorg_{index}_{base}"
        path.rename(temp)
        staged.append((temp, base))
    for index, (temp, base) in enumerate(staged, start=1):
        temp.rename(folder / f"{index:03d}_{base}")


def organise_file(
    path: Path,
    rules: RulesConfig,
    output_root: Path,
    on_conflict: Callable[[Path, Path], str] | None = None,
    stats: Stats | None = None,
) -> Path | None:
    """Move ``path`` into its matching category folder under ``output_root``.

    On a destination name clash, ``on_conflict(source, target)`` decides the
    outcome: "rename" (keep both), "skip", "overwrite", or "defer" (leave the
    file in place to resolve later). Without a resolver it defaults to "rename".
    Records each successful move into ``stats`` when given. Returns the file's
    new path, or None if it matched nothing, was skipped/deferred, or could not
    be moved.
    """
    path = Path(path)
    output_root = Path(output_root)
    if not path.is_file():
        return None

    category = classify(path, rules)
    if category is None:
        return None

    dest_dir = output_root / category.folder
    # already in place; skip (also prevents move/rename event loops)
    if path.parent.resolve() == dest_dir.resolve():
        return None
    dest_dir.mkdir(parents=True, exist_ok=True)
    if category.icon:
        apply_folder_icon(dest_dir, category.icon)

    target = dest_dir / path.name
    if not target.exists():
        destination = target
    else:
        decision = on_conflict(path, target) if on_conflict else "rename"
        if decision == "defer":
            logger.info("deferred %s (conflict in %s/)", path.name, category.folder)
            return None
        if decision == "skip":
            logger.info("skipped %s (already in %s/)", path.name, category.folder)
            return None
        if decision == "overwrite":
            try:
                target.unlink()
            except OSError as exc:
                logger.warning("could not overwrite %s: %s", target, exc)
                return None
            destination = target
        else:  # "rename": keep both
            destination = _unique_destination(target)

    try:
        size = path.stat().st_size
    except OSError:
        size = 0
    moved = _safe_move(path, destination)
    if moved is None:
        return None
    logger.info("organised %s → %s/%s", path.name, category.folder, moved.name)
    if stats is not None:
        stats.record(category.folder, size)

    if rules.sort.mode != "none":
        try:
            _renumber(dest_dir, rules.sort.mode, rules.sort.order)
        except OSError as exc:
            logger.warning("could not renumber %s: %s", dest_dir, exc)
    return moved


def _claim_unique_name(name: str, taken: set[str]) -> str:
    """Pick a non-colliding name like _unique_destination, but against a set."""
    if name not in taken:
        return name
    stem, suffix = Path(name).stem, Path(name).suffix
    counter = 1
    while f"{stem} ({counter}){suffix}" in taken:
        counter += 1
    return f"{stem} ({counter}){suffix}"


def simulate(rules: RulesConfig) -> dict:
    """Compute what organising the watched folder would do, without touching disk.

    Returns ``{"folders": [(folder, [final_names])], "unmatched": [names],
    "matched": int, "sorted": bool}``. Files already in their destination folder
    are treated as organised and omitted. Name clashes assume "keep both".
    """
    watch = rules.watch
    result: dict = {
        "folders": [],
        "unmatched": [],
        "matched": 0,
        "sorted": rules.sort.mode != "none",
    }
    root = Path(watch.directory)
    output_root = Path(watch.output)
    if not watch.directory or not watch.output or not root.is_dir():
        return result

    paths = root.rglob("*") if watch.recursive else root.glob("*")
    files = [p for p in paths if p.is_file() and p.name.lower() not in _SKIP_NAMES]

    buckets: dict[str, list[str]] = {}
    claimed: dict[str, set[str]] = {}
    for path in files:
        category = classify(path, rules)
        if category is None or not category.folder:
            result["unmatched"].append(path.name)
            continue
        dest_dir = output_root / category.folder
        if path.parent.resolve() == dest_dir.resolve():
            continue  # already organised
        folder = category.folder
        if folder not in claimed:
            existing: set[str] = set()
            if dest_dir.is_dir():
                existing = {
                    c.name
                    for c in dest_dir.iterdir()
                    if c.is_file() and c.name.lower() not in _SKIP_NAMES
                }
            claimed[folder] = existing
            buckets[folder] = []
        final = _claim_unique_name(path.name, claimed[folder])
        claimed[folder].add(final)
        buckets[folder].append(final)
        result["matched"] += 1

    seen: set[str] = set()
    for category in rules.format_rules.categories:  # follow priority order
        if category.folder in buckets and category.folder not in seen:
            result["folders"].append((category.folder, buckets[category.folder]))
            seen.add(category.folder)
    for folder, names in buckets.items():
        if folder not in seen:
            result["folders"].append((folder, names))
            seen.add(folder)
    result["unmatched"].sort()
    return result
