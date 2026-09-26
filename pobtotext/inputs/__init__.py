"""Input-source registry.

New sources (pobb.in, pastebin, local file, ...) register here. ``auto`` picks
the first source whose ``matches()`` accepts the reference, so the CLI can accept
"whatever the user pasted" without a mode flag.
"""

from __future__ import annotations

from .base import InputError, InputSource
from .pobbin import PobbinInput
from .raw_code import RawCodeInput

# Order matters for auto-detection: most specific first. URL-based sources come
# before RawCodeInput, whose match is the broad "looks like base64" fallback.
_SOURCES: list[type[InputSource]] = [
    PobbinInput,
    RawCodeInput,
]

_BY_NAME: dict[str, type[InputSource]] = {s.name: s for s in _SOURCES}


def available_sources() -> list[str]:
    """Names of registered input sources, plus ``auto``."""
    return ["auto", *_BY_NAME.keys()]


def get_source(name: str) -> InputSource:
    """Return an input-source instance by name (``auto`` for auto-detection)."""
    if name == "auto":
        return AutoInput()
    try:
        return _BY_NAME[name]()
    except KeyError:
        raise InputError(
            f"Unknown input source '{name}'. Available: {', '.join(available_sources())}."
        ) from None


class AutoInput(InputSource):
    """Delegates to the first registered source that claims the reference."""

    name = "auto"

    def resolve(self, reference: str) -> str:
        for source_cls in _SOURCES:
            if source_cls.matches(reference):
                return source_cls().resolve(reference)
        raise InputError(
            "Could not determine how to read this input. "
            f"Tried: {', '.join(s.name for s in _SOURCES)}."
        )


__all__ = [
    "InputError",
    "InputSource",
    "available_sources",
    "get_source",
]
