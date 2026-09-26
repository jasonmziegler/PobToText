"""High-level pipeline: reference -> export code -> XML -> Build -> rendered text.

This is the reusable entry point for any front end (CLI now, web/library later).
Passive-tree name resolution is optional: pass a loaded ``TreeData`` and the build
is enriched before rendering; omit it and trees render as counts + URL.
"""

from __future__ import annotations

from .decode import decode_export_code
from .inputs import get_source
from .model import Build
from .parse import parse_xml
from .render import DEFAULT_FORMAT, get_renderer
from .treedata import TreeData


def code_to_build(reference: str, source: str = "auto") -> Build:
    """Resolve a reference to an export code, then decode and parse it."""
    code = get_source(source).resolve(reference)
    xml = decode_export_code(code)
    return parse_xml(xml)


def convert(
    reference: str,
    source: str = "auto",
    fmt: str = DEFAULT_FORMAT,
    tree_data: TreeData | None = None,
) -> str:
    """Convert an input reference straight to rendered output text.

    If ``tree_data`` is provided, passive-tree ids are resolved to keystone/
    notable/mastery names before rendering.
    """
    build = code_to_build(reference, source=source)
    if tree_data is not None:
        tree_data.enrich_build(build)
    return get_renderer(fmt).render(build)
