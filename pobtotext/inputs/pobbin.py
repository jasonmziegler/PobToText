"""pobb.in URL input source.

pobb.in hosts PoB builds behind short URLs like ``https://pobb.in/abc123``. Each
build's raw export code is served at ``https://pobb.in/<id>/raw``, so this source
extracts the id and fetches that endpoint.

Uses only the standard library (``urllib``) to stay dependency-free. The actual
HTTP call lives in :meth:`_fetch` so tests can stub it without hitting the network.
"""

from __future__ import annotations

import re
import urllib.error
import urllib.request

from .base import InputError, InputSource

# Matches the build id in any pobb.in URL, ignoring an optional /raw or trailing
# slash. pobb.in ids use URL-safe base64 characters (letters, digits, - and _).
_POBBIN_RE = re.compile(r"pobb\.in/([A-Za-z0-9_-]+)", re.IGNORECASE)

_RAW_URL = "https://pobb.in/{id}/raw"
_USER_AGENT = "PobToText/0.1 (+https://github.com/; standard-library urllib)"
_TIMEOUT_SECONDS = 15


class PobbinInput(InputSource):
    """Fetches a PoB export code from a pobb.in share URL."""

    name = "pobbin"

    def resolve(self, reference: str) -> str:
        match = _POBBIN_RE.search(reference.strip())
        if not match:
            raise InputError(
                "Not a recognisable pobb.in URL (expected something like "
                "https://pobb.in/abc123)."
            )
        build_id = match.group(1)
        url = _RAW_URL.format(id=build_id)
        code = self._fetch(url).strip()
        if not code:
            raise InputError(f"pobb.in returned an empty response for '{build_id}'.")
        return code

    @classmethod
    def matches(cls, reference: str) -> bool:
        return bool(_POBBIN_RE.search(reference.strip()))

    def _fetch(self, url: str) -> str:
        """Fetch ``url`` and return the body text. Overridable for testing."""
        request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS) as response:
                return response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise InputError(f"pobb.in build not found (404): {url}") from exc
            raise InputError(f"pobb.in request failed (HTTP {exc.code}): {url}") from exc
        except urllib.error.URLError as exc:
            raise InputError(f"Could not reach pobb.in: {exc.reason}") from exc
        except TimeoutError as exc:
            raise InputError("pobb.in request timed out.") from exc
