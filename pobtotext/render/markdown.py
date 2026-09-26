"""Markdown renderer (``--format markdown``).

Same content as the text renderer, laid out as GitHub-flavoured Markdown: headings
for sections, tables for stats and config, and fenced code blocks for the verbatim
item text (so PoB's line breaks and mods survive rendering intact).
"""

from __future__ import annotations

from ..model import Build, SkillGroup
from ._stats import grouped_stats
from .base import Renderer


class MarkdownRenderer(Renderer):
    name = "markdown"

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

    # -- helpers ----------------------------------------------------------

    def _section(self, lines: list[str], title: str, level: int = 2) -> None:
        if lines:
            lines.append("")
        lines.append(f"{'#' * level} {title}")
        lines.append("")

    def _table(self, lines: list[str], headers: tuple[str, str], rows: list[tuple[str, str]]) -> None:
        lines.append(f"| {headers[0]} | {headers[1]} |")
        lines.append("| --- | --- |")
        for left, right in rows:
            lines.append(f"| {left} | {right} |")

    # -- sections ---------------------------------------------------------

    def _overview(self, build: Build, lines: list[str]) -> None:
        klass = build.class_name or "Unknown class"
        if build.ascend_name and build.ascend_name != "None":
            klass = f"{klass} ({build.ascend_name})"
        title = build.main_skill_name or "Path of Building Build"
        lines.append(f"# {title}")
        lines.append("")
        lines.append(f"- **Class:** {klass}")
        if build.level is not None:
            lines.append(f"- **Level:** {build.level}")
        if build.main_skill_name:
            lines.append(f"- **Main skill:** {build.main_skill_name}")
        if build.bandit and build.bandit != "None":
            lines.append(f"- **Bandit:** {build.bandit}")

    def _stats(self, build: Build, lines: list[str]) -> None:
        if not build.stats:
            return
        offense, defense, other = grouped_stats(build.stats)
        for title, rows in (
            ("Offense", offense),
            ("Defense", defense),
            ("Other Stats", other),
        ):
            if rows:
                self._section(lines, title)
                self._table(lines, ("Stat", "Value"), rows)

    def _tree(self, build: Build, lines: list[str]) -> None:
        tree = build.active_tree
        if tree is None:
            return
        self._section(lines, "Passive Tree")
        if tree.tree_version:
            lines.append(f"- **Tree version:** {tree.tree_version.replace('_', '.')}")
        lines.append(f"- **Points allocated:** {len(tree.node_ids)}")

        if tree.resolved:
            if tree.keystones:
                lines.append(f"- **Keystones:** {', '.join(tree.keystones)}")
            if tree.notables:
                lines.append(f"- **Notables:** {', '.join(tree.notables)}")
            remainder = [f"{tree.small_count} small passives"]
            if tree.unknown_count:
                remainder.append(f"{tree.unknown_count} unresolved")
            lines.append(f"- **Small passives:** {', '.join(remainder)}")
            if tree.masteries:
                lines.append("")
                lines.append("**Masteries**")
                lines.append("")
                for name, stats in tree.masteries:
                    lines.append(f"- **{name}:** {stats}")
        elif tree.mastery_effects:
            lines.append(f"- **Mastery effects (raw ids):** {tree.mastery_effects}")

        if tree.url:
            lines.append(f"- **Tree URL:** <{tree.url}>")
        if len(build.trees) > 1:
            others = ", ".join(t.title for t in build.trees if not t.is_active)
            lines.append(f"- *{len(build.trees)} trees saved; also: {others}*")

    def _skills(self, build: Build, lines: list[str]) -> None:
        groups = [g for g in build.skill_groups if g.gems]
        if not groups:
            return
        self._section(lines, "Skills")
        for group in groups:
            lines.append(self._group_header(group))
            for gem in group.gems:
                lines.append(f"  - {self._gem_line(gem)}")
            lines.append("")
        if lines and lines[-1] == "":
            lines.pop()

    def _group_header(self, group: SkillGroup) -> str:
        name = group.slot or group.label or "Unslotted"
        tags = []
        if group.is_main:
            tags.append("MAIN")
        if not group.enabled:
            tags.append("disabled")
        suffix = f" _{', '.join(tags)}_" if tags else ""
        return f"**{name}**{suffix}"

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
            bits.append("_[disabled]_")
        return " ".join(bits)

    def _items(self, build: Build, lines: list[str]) -> None:
        item_set = build.active_item_set
        if item_set is None or not item_set.slots:
            if build.items:
                self._section(lines, "Items")
                for item in build.items.values():
                    self._item_block(lines, None, item.raw_text)
            return

        self._section(lines, f"Items — {item_set.title}")
        for slot in item_set.slots:
            item = build.items.get(slot.item_id)
            self._item_block(lines, slot.name, item.raw_text if item else "(item data missing)")

    def _item_block(self, lines: list[str], slot_name: str | None, text: str) -> None:
        if slot_name:
            lines.append(f"### {slot_name}")
            lines.append("")
        lines.append("```")
        lines.append(text)
        lines.append("```")
        lines.append("")

    def _config(self, build: Build, lines: list[str]) -> None:
        if not build.config:
            return
        self._section(lines, "Configuration")
        rows = [(name, build.config[name]) for name in sorted(build.config)]
        self._table(lines, ("Setting", "Value"), rows)

    def _notes(self, build: Build, lines: list[str]) -> None:
        if not build.notes:
            return
        self._section(lines, "Notes")
        for para in build.notes.splitlines():
            lines.append(f"> {para}" if para.strip() else ">")
