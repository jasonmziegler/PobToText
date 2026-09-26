"""Input-source abstraction.

An input source turns some user-supplied reference (a raw code, a URL, a file
path) into a PoB export code string. Keeping this behind a small interface lets
v1 ship raw-code-only while pobb.in / pastebin / file sources drop in later
without touching the decode/parse/render pipeline.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class InputError(ValueError):
    """Raised when an input source cannot produce an export code."""


class InputSource(ABC):
    """Resolves a user reference into a PoB export code string."""

    #: Short name used to select this source (e.g. on the CLI).
    name: str = ""

    @abstractmethod
    def resolve(self, reference: str) -> str:
        """Return the raw PoB export code for ``reference``."""

    @classmethod
    def matches(cls, reference: str) -> bool:
        """Whether this source can plausibly handle ``reference`` (for auto-detect)."""
        return False
