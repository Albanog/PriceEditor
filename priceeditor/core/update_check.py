from __future__ import annotations

import json
import os
import ssl
import traceback
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

from .. import __version__

REPO = "Albanog/PriceEditor"
API_URL = f"https://api.github.com/repos/{REPO}/releases/latest"
TIMEOUT_SECONDS = 10


def _log_path() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home())
    return Path(base) / "PriceEditor" / "update_check.log"


def _log(message: str) -> None:
    """Append to the update-check log; never raise."""
    try:
        path = _log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] v{__version__} {message}\n")
    except OSError:
        pass


def _ssl_context() -> ssl.SSLContext:
    # Use the Windows certificate store so antivirus/proxy HTTPS inspection
    # certificates trusted by the OS are also trusted here.
    try:
        import truststore

        return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    except Exception:
        return ssl.create_default_context()


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
            API_URL,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": f"PriceEditor/{__version__}",
            },
        )
        with urllib.request.urlopen(
            request, timeout=TIMEOUT_SECONDS, context=_ssl_context()
        ) as response:
            data = json.load(response)
    except urllib.error.HTTPError as e:
        _log(f"HTTP {e.code} {e.reason}")
        return None
    except Exception:
        _log("request failed:\n" + traceback.format_exc())
        return None

    latest_tag = data.get("tag_name")
    html_url = data.get("html_url")
    if not latest_tag or not html_url:
        _log(f"unexpected response: {str(data)[:300]}")
        return None

    newer = _parse_version(latest_tag) > _parse_version(__version__)
    _log(f"ok, latest={latest_tag}, newer={newer}")
    return (latest_tag, html_url) if newer else None
