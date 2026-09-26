"""Shared stat catalogue and grouping used by every renderer.

Keeping this in one place means new PoB stats or relabelling benefit all output
formats at once, and renderers only differ in layout, not in what they show.
"""

from __future__ import annotations

_OFFENSE = "offense"
_DEFENSE = "defense"

# PoB PlayerStat name -> (friendly label, group). Anything not listed is still
# emitted under "Other" using its raw name, so new PoB stats never vanish.
_STAT_CATALOG: dict[str, tuple[str, str]] = {
    # Offense
    "AverageDamage": ("Average hit", _OFFENSE),
    "AverageHit": ("Average hit", _OFFENSE),
    "CombinedDPS": ("Combined DPS", _OFFENSE),
    "TotalDPS": ("Skill DPS", _OFFENSE),
    "FullDPS": ("Full DPS", _OFFENSE),
    "WithPoisonDPS": ("DPS (with poison)", _OFFENSE),
    "TotalDot": ("Damage over time", _OFFENSE),
    "Speed": ("Attacks/casts per sec", _OFFENSE),
    "CritChance": ("Crit chance", _OFFENSE),
    "CritMultiplier": ("Crit multiplier", _OFFENSE),
    "HitChance": ("Hit chance", _OFFENSE),
    # Defense
    "Life": ("Life", _DEFENSE),
    "LifeUnreserved": ("Life unreserved", _DEFENSE),
    "LifeRegen": ("Life regen/sec", _DEFENSE),
    "EnergyShield": ("Energy shield", _DEFENSE),
    "EnergyShieldRegen": ("ES regen/sec", _DEFENSE),
    "Mana": ("Mana", _DEFENSE),
    "ManaUnreserved": ("Mana unreserved", _DEFENSE),
    "Ward": ("Ward", _DEFENSE),
    "TotalEHP": ("Effective HP", _DEFENSE),
    "Armour": ("Armour", _DEFENSE),
    "Evasion": ("Evasion", _DEFENSE),
    "BlockChance": ("Block chance", _DEFENSE),
    "SpellBlockChance": ("Spell block", _DEFENSE),
    "SpellSuppressionChance": ("Spell suppression", _DEFENSE),
    "FireResist": ("Fire resist", _DEFENSE),
    "ColdResist": ("Cold resist", _DEFENSE),
    "LightningResist": ("Lightning resist", _DEFENSE),
    "ChaosResist": ("Chaos resist", _DEFENSE),
    "MeleeAvoidChance": ("Melee avoidance", _DEFENSE),
}

# Preferred display order within each group; unlisted-but-known stats follow.
_OFFENSE_ORDER = [
    "FullDPS", "CombinedDPS", "TotalDPS", "WithPoisonDPS", "TotalDot",
    "AverageDamage", "AverageHit", "Speed", "CritChance", "CritMultiplier", "HitChance",
]
_DEFENSE_ORDER = [
    "Life", "LifeUnreserved", "LifeRegen", "EnergyShield", "EnergyShieldRegen",
    "Ward", "Mana", "ManaUnreserved", "TotalEHP", "Armour", "Evasion",
    "BlockChance", "SpellBlockChance", "SpellSuppressionChance",
    "FireResist", "ColdResist", "LightningResist", "ChaosResist", "MeleeAvoidChance",
]


def fmt_number(value: float) -> str:
    """Format a stat value with thousands separators and sensible precision."""
    if value == int(value):
        return f"{int(value):,}"
    if abs(value) >= 100:
        return f"{value:,.0f}"
    if abs(value) >= 10:
        return f"{value:,.1f}"
    return f"{value:,.2f}"


def _group_rows(remaining: dict[str, float], order: list[str], group_key: str):
    rows: list[tuple[str, str]] = []
    for stat in order:
        if stat in remaining:
            label = _STAT_CATALOG[stat][0]
            rows.append((label, fmt_number(remaining.pop(stat))))
    for stat, (label, grp) in _STAT_CATALOG.items():
        if grp == group_key and stat in remaining:
            rows.append((label, fmt_number(remaining.pop(stat))))
    return rows


def grouped_stats(stats: dict[str, float]):
    """Split stats into (offense, defense, other) lists of (label, value) pairs.

    ``other`` holds stats absent from the catalogue, keyed by their raw PoB name
    and sorted alphabetically, so nothing is dropped.
    """
    remaining = dict(stats)
    offense = _group_rows(remaining, _OFFENSE_ORDER, _OFFENSE)
    defense = _group_rows(remaining, _DEFENSE_ORDER, _DEFENSE)
    other = [(name, fmt_number(remaining[name])) for name in sorted(remaining)]
    return offense, defense, other
