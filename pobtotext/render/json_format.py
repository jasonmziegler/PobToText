"""JSON renderer (``--format json``) for programmatic consumers.

Unlike the text/markdown renderers, this emits the structured :class:`Build`
model verbatim — raw numeric stat values, every gem/item/tree field — so callers
can parse and query it. The shape mirrors :mod:`pobtotext.model` one-to-one, plus
a ``schemaVersion`` for forward compatibility.
"""

from __future__ import annotations

import dataclasses
import json

from ..model import Build
from .base import Renderer

# Bump when the emitted JSON shape changes in a breaking way.
SCHEMA_VERSION = 1


class JsonRenderer(Renderer):
    name = "json"

    def render(self, build: Build) -> str:
        payload = {
            "schemaVersion": SCHEMA_VERSION,
            "build": dataclasses.asdict(build),
            # Convenience pointers so consumers need not re-derive "which is active".
            "activeTreeTitle": build.active_tree.title if build.active_tree else None,
            "activeItemSetTitle": (
                build.active_item_set.title if build.active_item_set else None
            ),
        }
        return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
