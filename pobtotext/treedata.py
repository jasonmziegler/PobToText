"""Passive-tree data: resolve node/effect ids into human names and stat text.

PoB stores allocated passives as numeric node ids and mastery choices as
``{nodeId, effectId}`` pairs. Those are meaningless without the passive-tree data
for the game version. GGG serves that data as JSON embedded in the passive tree
page; this module fetches it once, distils it to a slim id->name/effect lookup,
caches it under ``~/.pobtotext/``, and enriches :class:`~pobtotext.model.TreeSpec`.

Network policy lives with the caller (the CLI): this module fetches only when
asked and surfaces failures as :class:`TreeDataError` so callers can degrade
gracefully to the count-only view.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

from .model import Build, TreeSpec

_TREE_URL = "https://www.pathofexile.com/passive-skill-tree"
_MARKER = "var passiveSkillTreeData = "
_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
_TIMEOUT_SECONDS = 30
_CACHE_FILENAME = "treedata.json"

# {nodeId,effectId} pairs in TreeSpec.mastery_effects (first = node, second = effect).
_MASTERY_PAIR_RE = re.compile(r"\{(\d+),(\d+)\}")


class TreeDataError(RuntimeError):
    """Raised when passive-tree data cannot be obtained or parsed."""


def default_cache_dir() -> Path:
    """Directory used to cache the distilled tree data."""
    override = os.environ.get("POBTOTEXT_CACHE_DIR")
    return Path(override) if override else Path.home() / ".pobtotext"


def cache_file(cache_dir: Path | None = None) -> Path:
    return (cache_dir or default_cache_dir()) / _CACHE_FILENAME


def is_cached(cache_dir: Path | None = None) -> bool:
    return cache_file(cache_dir).exists()


class TreeData:
    """Slim passive-tree lookup: node id -> name/flags, effect id -> stat text."""

    def __init__(self, nodes: dict[str, dict], effects: dict[str, str]):
        # nodes: {"<id>": {"n": name, "k"?:1 keystone, "no"?:1 notable, "m"?:1 mastery}}
        self._nodes = nodes
        self._effects = effects

    # -- lookups ----------------------------------------------------------

    def node_name(self, node_id: int) -> str | None:
        node = self._nodes.get(str(node_id))
        return node.get("n") if node else None

    def effect_stats(self, effect_id: int) -> str | None:
        return self._effects.get(str(effect_id))

    def enrich_tree(self, tree: TreeSpec) -> None:
        """Populate ``tree.resolved_*`` fields from this data."""
        keystones: list[str] = []
        notables: list[str] = []
        small = 0
        unknown = 0
        for node_id in tree.node_ids:
            node = self._nodes.get(str(node_id))
            if node is None:
                unknown += 1
            elif node.get("k"):
                keystones.append(node.get("n", f"Node {node_id}"))
            elif node.get("no"):
                notables.append(node.get("n", f"Node {node_id}"))
            elif node.get("m"):
                pass  # mastery node itself; the chosen effect is listed below
            else:
                small += 1

        masteries: list[tuple[str, str]] = []
        for node_str, effect_str in _MASTERY_PAIR_RE.findall(tree.mastery_effects):
            name = self.node_name(int(node_str)) or f"Node {node_str}"
            stats = self.effect_stats(int(effect_str)) or f"effect {effect_str}"
            masteries.append((name, stats))

        tree.keystones = sorted(keystones)
        tree.notables = sorted(notables)
        tree.masteries = masteries
        tree.small_count = small
        tree.unknown_count = unknown
        tree.resolved = True

    def enrich_build(self, build: Build) -> None:
        """Enrich every tree spec in the build."""
        for tree in build.trees:
            self.enrich_tree(tree)

    # -- loading ----------------------------------------------------------

    @classmethod
    def load(cls, cache_dir: Path | None = None, refresh: bool = False) -> "TreeData":
        """Load tree data from cache, fetching from GGG on a miss (or ``refresh``)."""
        path = cache_file(cache_dir)
        if path.exists() and not refresh:
            try:
                slim = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                raise TreeDataError(f"Cached tree data is unreadable: {exc}") from exc
        else:
            slim = cls._fetch_slim()
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(slim), encoding="utf-8")
            except OSError:
                pass  # caching is best-effort; still usable this run
        return cls(slim.get("nodes", {}), slim.get("effects", {}))

    @classmethod
    def from_slim(cls, slim: dict) -> "TreeData":
        return cls(slim.get("nodes", {}), slim.get("effects", {}))

    # -- fetch/extract (overridable for tests) ----------------------------

    @staticmethod
    def _fetch_slim() -> dict:
        html = TreeData._fetch_html()
        raw = TreeData._extract_json(html)
        return TreeData._distil(raw)

    @staticmethod
    def _fetch_html() -> str:
        request = urllib.request.Request(_TREE_URL, headers={"User-Agent": _USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS) as response:
                return response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            raise TreeDataError(
                f"Could not download tree data (HTTP {exc.code}). "
                "GGG may be rate-limiting; try again shortly."
            ) from exc
        except urllib.error.URLError as exc:
            raise TreeDataError(f"Could not reach pathofexile.com: {exc.reason}") from exc
        except TimeoutError as exc:
            raise TreeDataError("Downloading tree data timed out.") from exc

    @staticmethod
    def _extract_json(html: str) -> dict:
        """Extract the ``passiveSkillTreeData`` object literal from the page HTML."""
        start = html.find(_MARKER)
        if start == -1:
            raise TreeDataError("Tree data marker not found on the page (layout changed?).")
        start += len(_MARKER)
        # Brace-match to find the end of the JSON object, respecting string escapes.
        depth = 0
        in_string = False
        escaped = False
        for i in range(start, len(html)):
            c = html[i]
            if in_string:
                if escaped:
                    escaped = False
                elif c == "\\":
                    escaped = True
                elif c == '"':
                    in_string = False
            else:
                if c == '"':
                    in_string = True
                elif c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        try:
                            return json.loads(html[start : i + 1])
                        except ValueError as exc:
                            raise TreeDataError(f"Tree data JSON did not parse: {exc}") from exc
        raise TreeDataError("Tree data object was not properly terminated.")

    @staticmethod
    def _distil(raw: dict) -> dict:
        """Reduce GGG's large tree JSON to the slim lookup we cache."""
        nodes_out: dict[str, dict] = {}
        effects_out: dict[str, str] = {}
        for node_id, node in raw.get("nodes", {}).items():
            if not isinstance(node, dict):
                continue
            entry: dict = {"n": node.get("name", "")}
            if node.get("isKeystone"):
                entry["k"] = 1
            if node.get("isNotable"):
                entry["no"] = 1
            if node.get("isMastery"):
                entry["m"] = 1
            nodes_out[node_id] = entry
            for effect in node.get("masteryEffects", []) or []:
                eff_id = effect.get("effect")
                if eff_id is not None:
                    effects_out[str(eff_id)] = "; ".join(effect.get("stats", []))
        return {"nodes": nodes_out, "effects": effects_out}
