"""Renderer abstraction: turn a :class:`~pobtotext.model.Build` into output text."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..model import Build


class Renderer(ABC):
    """Renders a parsed build into a string in some format."""

    #: Short name used to select this renderer (e.g. ``--format text``).
    name: str = ""

    @abstractmethod
    def render(self, build: Build) -> str:
        """Return the rendered representation of ``build``."""
