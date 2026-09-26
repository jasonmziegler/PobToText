"""End-to-end tests for the PobToText pipeline.

Run with: python -m pytest   (or) python tests/test_pipeline.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pobtotext.core import code_to_build, convert  # noqa: E402
from pobtotext.decode import decode_export_code, encode_export_code  # noqa: E402
from pobtotext.parse import parse_xml  # noqa: E402

_SAMPLE_XML = os.path.join(os.path.dirname(__file__), "sample_build.xml")


def _sample_code() -> str:
    with open(_SAMPLE_XML, "r", encoding="utf-8") as fh:
        return encode_export_code(fh.read())


def test_decode_roundtrip():
    xml = "<PathOfBuilding><Build level=\"1\"/></PathOfBuilding>"
    assert decode_export_code(encode_export_code(xml)) == xml


def test_decode_tolerates_whitespace_and_padding():
    xml = "<PathOfBuilding><Build level=\"1\"/></PathOfBuilding>"
    code = encode_export_code(xml)
    noisy = code.rstrip("=") + "\n  " + "  "  # strip padding, add whitespace
    # Re-inject a newline in the middle to simulate wrapped clipboard text.
    mid = len(noisy) // 2
    noisy = noisy[:mid] + "\n" + noisy[mid:]
    assert decode_export_code(noisy) == xml


def test_parse_header():
    with open(_SAMPLE_XML, encoding="utf-8") as fh:
        build = parse_xml(fh.read())
    assert build.class_name == "Witch"
    assert build.ascend_name == "Necromancer"
    assert build.level == 94
    assert build.main_skill_name == "Raise Spectre"
    assert build.stats["FullDPS"] == 4521233


def test_parse_skills_and_main_flag():
    build = code_to_build(_sample_code())
    # mainSocketGroup=1 -> first group is main.
    assert build.skill_groups[0].is_main is True
    assert build.skill_groups[0].slot == "Body Armour"
    names = [g.name for g in build.skill_groups[0].gems]
    assert names[0] == "Raise Spectre"
    # Support detection.
    assert build.skill_groups[0].gems[1].is_support is True
    # Disabled group preserved.
    assert build.skill_groups[2].enabled is False


def test_parse_tree_and_items():
    build = code_to_build(_sample_code())
    tree = build.active_tree
    assert tree.title == "Endgame"
    assert len(tree.node_ids) == 5
    assert len(build.trees) == 2
    active_set = build.active_item_set
    # Gloves slot points at itemId 0 -> filtered out.
    assert [s.name for s in active_set.slots] == ["Body Armour", "Boots"]


def test_render_text_contains_key_sections():
    out = convert(_sample_code())
    for marker in (
        "== Build Overview ==",
        "Class: Witch (Necromancer)",
        "Main skill: Raise Spectre",
        "== Offense ==",
        "== Defense ==",
        "== Passive Tree ==",
        "== Skills ==",
        "Body Armour [MAIN]:",
        "Minion Damage Support",
        "== Items (Main) ==",
        "Corpse Cage",
        "== Configuration ==",
        "== Notes ==",
    ):
        assert marker in out, f"missing: {marker}\n---\n{out}"
    # Number formatting with thousands separators.
    assert "4,521,233" in out


def test_render_markdown_structure():
    out = convert(_sample_code(), fmt="markdown")
    for marker in (
        "# Raise Spectre",              # H1 uses main skill name
        "- **Class:** Witch (Necromancer)",
        "## Offense",
        "| Stat | Value |",             # stats table
        "| Full DPS | 4,521,233 |",
        "## Passive Tree",
        "## Skills",
        "**Body Armour** _MAIN_",
        "  - Minion Damage Support",
        "## Items — Main",
        "### Body Armour",
        "```",                          # item text fenced
        "Corpse Cage",
        "## Configuration",
        "| Setting | Value |",
        "## Notes",
        "> Spectres:",                  # notes as blockquote
    ):
        assert marker in out, f"missing: {marker}\n---\n{out}"


def test_render_json_is_valid_and_structured():
    import json

    out = convert(_sample_code(), fmt="json")
    data = json.loads(out)  # must be valid JSON
    assert data["schemaVersion"] == 1
    build = data["build"]
    assert build["class_name"] == "Witch"
    assert build["main_skill_name"] == "Raise Spectre"
    # Raw numeric value preserved (not a formatted string).
    assert build["stats"]["FullDPS"] == 4521233
    assert isinstance(build["stats"]["FullDPS"], (int, float))
    # Nested structures serialise fully.
    assert build["skill_groups"][0]["gems"][0]["name"] == "Raise Spectre"
    assert build["items"]["1"]["raw_text"].startswith("Rarity: RARE")
    assert data["activeTreeTitle"] == "Endgame"
    assert data["activeItemSetTitle"] == "Main"


def test_pobbin_matches_urls():
    from pobtotext.inputs import get_source
    from pobtotext.inputs.pobbin import PobbinInput

    assert PobbinInput.matches("https://pobb.in/abc123")
    assert PobbinInput.matches("  http://www.pobb.in/XyZ9/raw  ")
    assert not PobbinInput.matches("eNqtVM== just a code")
    # Regression: real pobb.in ids contain URL-safe base64 chars (- and _).
    from pobtotext.inputs.pobbin import _POBBIN_RE

    assert _POBBIN_RE.search("https://pobb.in/UOov3Kd-zDHd").group(1) == "UOov3Kd-zDHd"
    # auto-detection routes a pobb.in URL to the pobbin source, not raw_code.
    assert get_source("auto")  # smoke
    from pobtotext.inputs import _SOURCES  # order: pobbin before raw_code

    assert _SOURCES[0] is PobbinInput


def test_pobbin_resolve_builds_raw_url_and_strips():
    from pobtotext.inputs.base import InputError
    from pobtotext.inputs.pobbin import PobbinInput

    captured = {}

    class StubbedPobbin(PobbinInput):
        def _fetch(self, url):
            captured["url"] = url
            return "  eNqtVMxxxCODExxx==  \n"

    assert StubbedPobbin().resolve("https://pobb.in/abc123/raw") == "eNqtVMxxxCODExxx=="
    assert captured["url"] == "https://pobb.in/abc123/raw"

    # A non-URL reference is rejected before any fetch.
    try:
        StubbedPobbin().resolve("not a url")
        assert False, "expected InputError"
    except InputError:
        pass


def test_pobbin_end_to_end_with_stubbed_fetch():
    from unittest import mock

    from pobtotext.core import convert
    from pobtotext.inputs.pobbin import PobbinInput

    code = _sample_code()
    with mock.patch.object(PobbinInput, "_fetch", return_value=code):
        out = convert("https://pobb.in/testid")  # source defaults to auto
    assert "Class: Witch (Necromancer)" in out


# -- passive tree data -------------------------------------------------------

def _sample_tree_data():
    """Synthetic TreeData covering the ids used in sample_build.xml."""
    from pobtotext.treedata import TreeData

    slim = {
        "nodes": {
            "123": {"n": "Test Keystone", "k": 1},
            "456": {"n": "Test Notable", "no": 1},
            "789": {"n": "Some Mastery", "m": 1},
            "1011": {"n": "Small A"},
            "1213": {"n": "Small B"},
            "12345": {"n": "Life Mastery", "m": 1},
        },
        "effects": {"54321": "+50 to maximum Life"},
    }
    return TreeData.from_slim(slim)


def test_treedata_enrich_classifies_nodes():
    build = code_to_build(_sample_code())
    _sample_tree_data().enrich_build(build)
    tree = build.active_tree
    assert tree.resolved is True
    assert tree.keystones == ["Test Keystone"]
    assert tree.notables == ["Test Notable"]
    assert tree.masteries == [("Life Mastery", "+50 to maximum Life")]
    assert tree.small_count == 2          # 1011, 1213 (789 is a mastery node)
    assert tree.unknown_count == 0


def test_treedata_extract_and_distil_from_html():
    from pobtotext.treedata import TreeData

    html = (
        "junk before ... function (PassiveSkillTree) {\n"
        '  var passiveSkillTreeData = {"nodes": {'
        '"1": {"name": "Acrobatics", "isKeystone": true, "stats": ["x"]}, '
        '"2": {"name": "Life Mastery", "isMastery": true, '
        '"masteryEffects": [{"effect": 77, "stats": ["+50 to maximum Life"]}]}'
        "}};\n more junk }"
    )
    slim = TreeData._distil(TreeData._extract_json(html))
    assert slim["nodes"]["1"] == {"n": "Acrobatics", "k": 1}
    assert slim["nodes"]["2"]["m"] == 1
    assert slim["effects"]["77"] == "+50 to maximum Life"


def test_treedata_load_from_cache_without_network(tmp_path=None):
    import json
    import tempfile
    from pathlib import Path

    from pobtotext.treedata import TreeData, cache_file

    d = Path(tempfile.mkdtemp())
    slim = {"nodes": {"5": {"n": "Chaos Inoculation", "k": 1}}, "effects": {}}
    cache_file(d).write_text(json.dumps(slim), encoding="utf-8")
    td = TreeData.load(cache_dir=d)  # must NOT hit the network
    assert td.node_name(5) == "Chaos Inoculation"


def test_render_text_shows_resolved_tree():
    from pobtotext.core import convert

    build = code_to_build(_sample_code())
    _sample_tree_data().enrich_build(build)
    from pobtotext.render import get_renderer

    out = get_renderer("text").render(build)
    assert "Keystones: Test Keystone" in out
    assert "Notables: Test Notable" in out
    assert "Life Mastery: +50 to maximum Life" in out
    assert "small passives" in out


def test_unresolved_tree_shows_raw_mastery_ids():
    # No tree_data passed -> raw ids, resolved flag stays false.
    out = convert(_sample_code())
    assert "Mastery effects (raw ids): {12345,54321}" in out
    assert "Keystones:" not in out


def test_cli_infers_markdown_from_output_extension(tmp_path=None):
    import os
    import tempfile

    from pobtotext.cli import main

    code = _sample_code()
    d = tempfile.mkdtemp()
    out_path = os.path.join(d, "build.md")
    rc = main([code, "--output", out_path])
    assert rc == 0
    content = open(out_path, encoding="utf-8").read()
    assert content.startswith("# ")          # markdown, not the text "== " header
    assert "| Stat | Value |" in content


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failures = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except AssertionError as exc:
            failures += 1
            print(f"FAIL {fn.__name__}: {exc}")
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"ERROR {fn.__name__}: {type(exc).__name__}: {exc}")
    print(f"\n{len(fns) - failures}/{len(fns)} passed")
    sys.exit(1 if failures else 0)
