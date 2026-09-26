"""Renderer registry.

New output formats (markdown, json, summary, ...) register here and become
available via ``--format``. v1 ships ``text`` only.
"""

from __future__ import annotations

from .base import Renderer
from .json_format import JsonRenderer
from .markdown import MarkdownRenderer
from .text import TextRenderer

_RENDERERS: dict[str, type[Renderer]] = {
    TextRenderer.name: TextRenderer,
    MarkdownRenderer.name: MarkdownRenderer,
    JsonRenderer.name: JsonRenderer,
}

DEFAULT_FORMAT = TextRenderer.name


def available_formats() -> list[str]:
    return list(_RENDERERS.keys())


def get_renderer(name: str) -> Renderer:
    try:
        return _RENDERERS[name]()
    except KeyError:
        raise ValueError(
            f"Unknown format '{name}'. Available: {', '.join(available_formats())}."
        ) from None


__all__ = ["Renderer", "available_formats", "get_renderer", "DEFAULT_FORMAT"]
