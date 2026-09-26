"""Decode Path of Building export codes into XML.

A PoB export code is URL-safe base64 (``-``/``_`` instead of ``+``/``/``) whose
decoded bytes are zlib-compressed XML. This module handles the transport layer
only; parsing the XML lives in :mod:`pobtotext.parse`.
"""

from __future__ import annotations

import base64
import zlib


class DecodeError(ValueError):
    """Raised when an export code cannot be decoded into XML."""


def decode_export_code(code: str) -> str:
    """Decode a PoB export code into its XML string.

    Args:
        code: The export code, as copied from PoB's Import/Export tab. Surrounding
            whitespace and newlines are tolerated.

    Returns:
        The build XML as a ``str``.

    Raises:
        DecodeError: If the code is not valid base64 or not valid zlib data.
    """
    cleaned = "".join(code.split())
    if not cleaned:
        raise DecodeError("Export code is empty.")

    # PoB uses the URL-safe base64 alphabet. Pad to a multiple of 4 so the
    # standard library decoder accepts it even when the code was stored unpadded.
    padded = cleaned + "=" * (-len(cleaned) % 4)
    try:
        compressed = base64.urlsafe_b64decode(padded)
    except (ValueError, Exception) as exc:  # binascii.Error subclasses ValueError
        raise DecodeError(f"Not valid base64: {exc}") from exc

    try:
        raw = zlib.decompress(compressed)
    except zlib.error as exc:
        raise DecodeError(f"Not valid zlib-compressed data: {exc}") from exc

    return raw.decode("utf-8", errors="replace")


def encode_export_code(xml: str) -> str:
    """Encode build XML back into a PoB export code.

    The inverse of :func:`decode_export_code`. Useful for tests and round-tripping.
    """
    compressed = zlib.compress(xml.encode("utf-8"), level=9)
    return base64.urlsafe_b64encode(compressed).decode("ascii")
