"""Parse Path of Building build XML into the :mod:`pobtotext.model` dataclasses.

Parsing is deliberately forgiving: PoB's schema has drifted across versions and
builds are user-generated, so unknown or missing attributes are skipped rather
than raising. The goal is a best-effort readable snapshot, not strict validation.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

from .model import (
    Build,
    Gem,
    Item,
    ItemSet,
    ItemSlot,
    SkillGroup,
    TreeSpec,
)


class ParseError(ValueError):
    """Raised when the XML is not a recognisable PoB build."""


def _to_int(value: str | None) -> int | None:
    try:
        return int(value) if value is not None and value != "" else None
    except ValueError:
        return None


def _to_float(value: str | None) -> float | None:
    try:
        return float(value) if value is not None and value != "" else None
    except ValueError:
        return None


def _to_bool(value: str | None, default: bool = True) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"true", "1", "yes"}


def parse_xml(xml: str) -> Build:
    """Parse build XML into a :class:`~pobtotext.model.Build`."""
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as exc:
        raise ParseError(f"Invalid XML: {exc}") from exc

    if root.tag != "PathOfBuilding":
        raise ParseError(
            f"Root element is <{root.tag}>, expected <PathOfBuilding>. "
            "This does not look like a PoB build."
        )

    build = Build()
    build_el = root.find("Build")
    _parse_build_header(build_el, build)
    main_socket_group = _to_int(build_el.get("mainSocketGroup")) if build_el is not None else None
    _parse_skills(root.find("Skills"), build, main_socket_group)
    _parse_trees(root.find("Tree"), build)
    _parse_items(root.find("Items"), build)
    _parse_config(root.find("Config"), build)
    _parse_notes(root, build)
    return build


def _parse_build_header(el: ET.Element | None, build: Build) -> None:
    if el is None:
        return
    build.level = _to_int(el.get("level"))
    build.class_name = el.get("className", "")
    build.ascend_name = el.get("ascendClassName", "")
    build.bandit = el.get("bandit", "")

    for stat in el.findall("PlayerStat"):
        name = stat.get("stat")
        value = _to_float(stat.get("value"))
        if name and value is not None:
            build.stats[name] = value


def _parse_skills(
    el: ET.Element | None, build: Build, main_group_index: int | None
) -> None:
    if el is None:
        return

    # A build may hold several SkillSets; the active one is referenced by id.
    # Prefer it, else fall back to the first, else read groups directly.
    active_id = el.get("activeSkillSet")
    skill_sets = el.findall("SkillSet")
    container: ET.Element = el
    if skill_sets:
        container = next(
            (s for s in skill_sets if s.get("id") == active_id),
            skill_sets[0],
        )

    for i, skill_el in enumerate(container.findall("Skill"), start=1):
        group = SkillGroup(
            slot=skill_el.get("slot", ""),
            label=skill_el.get("label", ""),
            enabled=_to_bool(skill_el.get("enabled")),
            is_main=(i == main_group_index),
        )
        for gem_el in skill_el.findall("Gem"):
            group.gems.append(_parse_gem(gem_el))
        build.skill_groups.append(group)

    if main_group_index and 1 <= main_group_index <= len(build.skill_groups):
        main_group = build.skill_groups[main_group_index - 1]
        active = [g for g in main_group.gems if not g.is_support and g.enabled]
        if active:
            build.main_skill_name = active[0].name


def _parse_gem(el: ET.Element) -> Gem:
    name = el.get("nameSpec") or el.get("skillId") or el.get("gemId") or "Unknown Gem"
    # Support gems either carry a "Support" skillId/name or are flagged by PoB.
    is_support = "support" in (el.get("skillId", "").lower()) or "support" in name.lower()
    return Gem(
        name=name,
        level=_to_int(el.get("level")),
        quality=_to_int(el.get("quality")),
        enabled=_to_bool(el.get("enabled")),
        is_support=is_support,
        count=_to_int(el.get("count")) or 1,
    )


_CLASS_BY_ID = {
    "0": "Scion",
    "1": "Marauder",
    "2": "Ranger",
    "3": "Witch",
    "4": "Duelist",
    "5": "Templar",
    "6": "Shadow",
}


def _parse_trees(el: ET.Element | None, build: Build) -> None:
    if el is None:
        return
    active_spec = el.get("activeSpec", "1")
    for i, spec_el in enumerate(el.findall("Spec"), start=1):
        url_el = spec_el.find("URL")
        node_str = spec_el.get("nodes", "")
        node_ids = [int(n) for n in node_str.split(",") if n.strip().isdigit()]
        build.trees.append(
            TreeSpec(
                title=spec_el.get("title", "") or f"Tree {i}",
                tree_version=spec_el.get("treeVersion", ""),
                class_name=_CLASS_BY_ID.get(spec_el.get("classId", ""), build.class_name),
                ascend_name=build.ascend_name,
                node_ids=node_ids,
                mastery_effects=spec_el.get("masteryEffects", ""),
                url=(url_el.text or "").strip() if url_el is not None else "",
                is_active=(str(i) == active_spec),
            )
        )


def _parse_items(el: ET.Element | None, build: Build) -> None:
    if el is None:
        return
    active_set = el.get("activeItemSet", "1")

    for item_el in el.findall("Item"):
        item_id = item_el.get("id", "")
        if not item_id:
            continue
        build.items[item_id] = Item(item_id=item_id, raw_text=(item_el.text or "").strip())

    for i, set_el in enumerate(el.findall("ItemSet"), start=1):
        set_id = set_el.get("id", str(i))
        item_set = ItemSet(
            set_id=set_id,
            title=set_el.get("title", "") or f"Item Set {set_id}",
            is_active=(set_id == active_set),
        )
        for slot_el in set_el.findall("Slot"):
            name = slot_el.get("name", "")
            item_id = slot_el.get("itemId", "")
            if name and item_id and item_id != "0":
                item_set.slots.append(ItemSlot(name=name, item_id=item_id))
        build.item_sets.append(item_set)


def _parse_config(el: ET.Element | None, build: Build) -> None:
    if el is None:
        return
    for input_el in el.findall("Input"):
        name = input_el.get("name")
        if not name:
            continue
        for attr in ("string", "number", "boolean"):
            value = input_el.get(attr)
            if value is not None:
                build.config[name] = value
                break


def _parse_notes(root: ET.Element, build: Build) -> None:
    notes_el = root.find("Notes")
    if notes_el is not None and notes_el.text:
        build.notes = notes_el.text.strip()
