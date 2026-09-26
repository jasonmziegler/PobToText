"""Typed representation of a parsed Path of Building build.

These dataclasses are the boundary between parsing (XML-specific) and rendering
(format-specific). Renderers should depend only on this module, never on the XML.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Gem:
    """A single gem within a skill group (active or support)."""

    name: str
    level: int | None = None
    quality: int | None = None
    enabled: bool = True
    is_support: bool = False
    count: int = 1


@dataclass
class SkillGroup:
    """A socket group: the gems linked together in one item."""

    slot: str = ""
    label: str = ""
    enabled: bool = True
    is_main: bool = False
    gems: list[Gem] = field(default_factory=list)


@dataclass
class TreeSpec:
    """One passive-tree specification (a build can hold several).

    The ``resolved_*`` fields are populated only when tree data is available
    (see :mod:`pobtotext.treedata`); otherwise the renderer falls back to the
    raw node count and URL.
    """

    title: str = ""
    tree_version: str = ""
    class_name: str = ""
    ascend_name: str = ""
    node_ids: list[int] = field(default_factory=list)
    mastery_effects: str = ""
    url: str = ""
    is_active: bool = False

    # Filled in by tree-data resolution.
    resolved: bool = False
    keystones: list[str] = field(default_factory=list)
    notables: list[str] = field(default_factory=list)
    masteries: list[tuple[str, str]] = field(default_factory=list)  # (node name, effect text)
    small_count: int = 0
    unknown_count: int = 0


@dataclass
class Item:
    """A single item. ``raw_text`` is the game-style text block PoB stores verbatim."""

    item_id: str
    raw_text: str = ""


@dataclass
class ItemSlot:
    """A named equipment slot pointing at an item id."""

    name: str
    item_id: str


@dataclass
class ItemSet:
    """A named collection of equipped slots."""

    set_id: str = ""
    title: str = ""
    is_active: bool = False
    slots: list[ItemSlot] = field(default_factory=list)


@dataclass
class Build:
    """The whole parsed build."""

    level: int | None = None
    class_name: str = ""
    ascend_name: str = ""
    bandit: str = ""
    main_skill_name: str = ""
    stats: dict[str, float] = field(default_factory=dict)
    skill_groups: list[SkillGroup] = field(default_factory=list)
    trees: list[TreeSpec] = field(default_factory=list)
    items: dict[str, Item] = field(default_factory=dict)
    item_sets: list[ItemSet] = field(default_factory=list)
    config: dict[str, str] = field(default_factory=dict)
    notes: str = ""

    @property
    def active_tree(self) -> TreeSpec | None:
        for tree in self.trees:
            if tree.is_active:
                return tree
        return self.trees[0] if self.trees else None

    @property
    def active_item_set(self) -> ItemSet | None:
        for item_set in self.item_sets:
            if item_set.is_active:
                return item_set
        return self.item_sets[0] if self.item_sets else None
