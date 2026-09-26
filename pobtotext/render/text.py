"""Comprehensive plain-text renderer (v1 default).

Produces a single readable dump of the whole build: overview, stats grouped into
offense/defense/other, passive tree summary, skill setups, equipped items with
their full mod text, config, and notes. Designed to be pasted straight into an
AI chat or read by a human.
"""

from __future__ import annotations

from ..model import Build, SkillGroup
from ._stats import grouped_stats
from .base import Renderer


class TextRenderer(Renderer):
    name = "text"

    def render(self, build: Build) -> str:
        lines: list[str] = []
        self._overview(build, lines)
        self._stats(build, lines)
        self._tree(build, lines)
        self._skills(build, lines)
        self._items(build, lines)
        self._config(build, lines)
        self._notes(build, lines)
        return "\n".join(lines).rstrip() + "\n"

    # -- sections ---------------------------------------------------------

    def _heading(self, lines: list[str], title: str) -> None:
        if lines:
            lines.append("")
        lines.append(f"== {title} ==")

    def _overview(self, build: Build, lines: list[str]) -> None:
        lines.append("== Build Overview ==")
        klass = build.class_name or "Unknown class"
        if build.ascend_name and build.ascend_name != "None":
            klass = f"{klass} ({build.ascend_name})"
        lines.append(f"Class: {klass}")
        if build.level is not None:
            lines.append(f"Level: {build.level}")
        if build.main_skill_name:
            lines.append(f"Main skill: {build.main_skill_name}")
        if build.bandit and build.bandit != "None":
            lines.append(f"Bandit: {build.bandit}")

    def _stats(self, build: Build, lines: list[str]) -> None:
        if not build.stats:
            return
        offense, defense, other = grouped_stats(build.stats)
        for title, rows in (
            ("Offense", offense),
            ("Defense", defense),
            ("Other stats", other),
        ):
            if rows:
                self._heading(lines, title)
                for label, value in rows:
                    lines.append(f"{label}: {value}")

    def _tree(self, build: Build, lines: list[str]) -> None:
        tree = build.active_tree
        if tree is None:
            return
        self._heading(lines, "Passive Tree")
        if tree.tree_version:
            lines.append(f"Tree version: {tree.tree_version.replace('_', '.')}")
        lines.append(f"Points allocated: {len(tree.node_ids)}")

        if tree.resolved:
            if tree.keystones:
                lines.append(f"Keystones: {', '.join(tree.keystones)}")
            if tree.notables:
                lines.append(f"Notables: {', '.join(tree.notables)}")
            if tree.masteries:
                lines.append("Masteries:")
                for name, stats in tree.masteries:
                    lines.append(f"  {name}: {stats}")
            remainder = [f"{tree.small_count} small passives"]
            if tree.unknown_count:
                remainder.append(f"{tree.unknown_count} unresolved")
            lines.append(f"(+ {', '.join(remainder)})")
        elif tree.mastery_effects:
            # No tree data loaded: show the raw ids rather than nothing.
            lines.append(f"Mastery effects (raw ids): {tree.mastery_effects}")

        if tree.url:
            lines.append(f"Tree URL: {tree.url}")
        if len(build.trees) > 1:
            others = [t.title for t in build.trees if not t.is_active]
            lines.append(f"({len(build.trees)} trees saved; also: {', '.join(others)})")

    def _skills(self, build: Build, lines: list[str]) -> None:
        if not build.skill_groups:
            return
        self._heading(lines, "Skills")
        for group in build.skill_groups:
            if not group.gems:
                continue
            lines.append(self._group_header(group))
            for gem in group.gems:
                lines.append("  " + self._gem_line(gem))

    def _group_header(self, group: SkillGroup) -> str:
        parts: list[str] = []
        parts.append(group.slot or group.label or "Unslotted")
        tags = []
        if group.is_main:
            tags.append("MAIN")
        if not group.enabled:
            tags.append("disabled")
        if tags:
            parts.append(f"[{', '.join(tags)}]")
        return " ".join(parts) + ":"

    def _gem_line(self, gem) -> str:
        bits = [gem.name]
        meta = []
        if gem.level is not None:
            meta.append(f"lvl {gem.level}")
        if gem.quality:
            meta.append(f"{gem.quality}% quality")
        if meta:
            bits.append(f"({', '.join(meta)})")
        if not gem.enabled:
            bits.append("[disabled]")
        return " ".join(bits)

    def _items(self, build: Build, lines: list[str]) -> None:
        item_set = build.active_item_set
        if item_set is None or not item_set.slots:
            # No slot mapping — dump any loose items so nothing is lost.
            if build.items:
                self._heading(lines, "Items")
                for item in build.items.values():
                    lines.append("")
                    lines.append(item.raw_text)
            return

        self._heading(lines, f"Items ({item_set.title})")
        for slot in item_set.slots:
            item = build.items.get(slot.item_id)
            lines.append("")
            lines.append(f"--- {slot.name} ---")
            lines.append(item.raw_text if item else "(item data missing)")

    def _config(self, build: Build, lines: list[str]) -> None:
        if not build.config:
            return
        self._heading(lines, "Configuration")
        for name in sorted(build.config):
            lines.append(f"{name}: {build.config[name]}")

    def _notes(self, build: Build, lines: list[str]) -> None:
        if not build.notes:
            return
        self._heading(lines, "Notes")
        lines.append(build.notes)
