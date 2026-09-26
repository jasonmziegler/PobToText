"""Raw export code input source — the v1 default."""

from __future__ import annotations

import re

from .base import InputError, InputSource

# PoB codes are URL-safe base64: letters, digits, '-', '_', optional '=' padding.
_CODE_RE = re.compile(r"^[A-Za-z0-9\-_=]+$")


class RawCodeInput(InputSource):
    """Treats the reference as a PoB export code pasted verbatim."""

    name = "code"

    def resolve(self, reference: str) -> str:
        cleaned = "".join(reference.split())
        if not cleaned:
            raise InputError("No export code provided.")
        if not _CODE_RE.match(cleaned):
            raise InputError(
                "Input does not look like a PoB export code "
                "(expected URL-safe base64 characters only)."
            )
        return cleaned

    @classmethod
    def matches(cls, reference: str) -> bool:
        cleaned = "".join(reference.split())
        return bool(cleaned) and bool(_CODE_RE.match(cleaned))
