"""Check GitHub for a newer release than the running version."""
import json
import urllib.error
import urllib.request

from src.version import VERSION

_LATEST_RELEASE_API = "https://api.github.com/repos/BuleWu/file-organisation-tool/releases/latest"


def _parse(version: str) -> tuple[int, ...]:
    parts = []
    for chunk in version.split("."):
        digits = "".join(c for c in chunk if c.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


def check_for_update(timeout: float = 5.0) -> tuple[str, str, str] | None:
    """Return (current, latest, release_url) if a newer release exists, else None."""
    request = urllib.request.Request(
        _LATEST_RELEASE_API,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "FileOrganiser"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.load(response)
    except (urllib.error.URLError, OSError, ValueError):
        return None
    latest = str(data.get("tag_name", "")).lstrip("v")
    url = str(data.get("html_url", ""))
    if latest and _parse(latest) > _parse(VERSION):
        return VERSION, latest, url
    return None
