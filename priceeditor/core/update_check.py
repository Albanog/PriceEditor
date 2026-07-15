from __future__ import annotations

import json
import urllib.error
import urllib.request

from .. import __version__

REPO = "Albanog/PriceEditor"
API_URL = f"https://api.github.com/repos/{REPO}/releases/latest"
TIMEOUT_SECONDS = 4


def _parse_version(tag: str) -> tuple[int, ...]:
    cleaned = tag.lstrip("vV")
    parts = []
    for part in cleaned.split("."):
        digits = "".join(ch for ch in part if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


def check_for_update() -> tuple[str, str] | None:
    """Return (latest_version, html_url) if a newer release exists, else None."""
    try:
        request = urllib.request.Request(
            API_URL, headers={"Accept": "application/vnd.github+json"}
        )
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            data = json.load(response)
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        return None

    latest_tag = data.get("tag_name")
    html_url = data.get("html_url")
    if not latest_tag or not html_url:
        return None

    if _parse_version(latest_tag) > _parse_version(__version__):
        return latest_tag, html_url
    return None
