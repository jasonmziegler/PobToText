# PobToText

Convert a **Path of Building** build into clean, readable text — for feeding to an
AI for build planning, or just for reading a build at a glance.

PoB shares builds as an **export code**: URL-safe base64 wrapping zlib-compressed
XML. PobToText decodes that and renders a comprehensive text summary: overview,
offense/defense stats, passive tree, skill setups, equipped items with full mods,
config, and notes.

## Quick start

No dependencies — standard library only. Python 3.10+.

```bash
# From a code as an argument
python -m pobtotext "eNqt....=="

# From a pobb.in share URL (fetched automatically)
python -m pobtotext "https://pobb.in/UOov3Kd-zDHd"

# Piped from the clipboard (macOS pbpaste / Windows Get-Clipboard)
Get-Clipboard | python -m pobtotext -

# From a file, to a Markdown file (format inferred from the .md extension)
python -m pobtotext --file build.txt --output build.md
```

In PoB: **Import/Export build → Generate → Share → copy the code**, then pass it in.

Install as a command (`pobtotext ...`):

```bash
pip install -e .
```

## Usage

```
pobtotext [code] [--file PATH] [--source auto] [--format text] [--output PATH]
```

| Option | Meaning |
| --- | --- |
| `code` | The export code, or `-` to read stdin. |
| `--file`, `-f` | Read the code from a file. |
| `--source`, `-s` | Input source: `auto` (default), `code` (raw export code), or `pobbin` (pobb.in URL). `auto` picks based on the input. |
| `--format` | `text` (default), `markdown`, or `json`. Inferred from `--output` extension (`.md` → markdown, `.json` → json). |
| `--output`, `-o` | Write to a file instead of stdout. |
| `--no-resolve-tree` | Skip passive-tree name resolution (no download; show point counts only). |
| `--refresh-tree-data` | Re-download the passive-tree data even if cached. |

### Passive tree resolution

PoB stores the tree as numeric node ids and mastery choices as `{nodeId, effectId}`
pairs — meaningless on their own. PobToText resolves them to **keystones, notables,
and mastery effect text** by downloading GGG's official passive-tree data once and
caching it under `~/.pobtotext/` (override with `POBTOTEXT_CACHE_DIR`). So instead of:

```
Mastery effects: {10495,64875},{857,29586}, ...
```

you get:

```
Masteries:
  Mana Mastery: 12% increased Mana Reservation Efficiency of Skills
  Energy Shield Mastery: 30% of Chaos Damage taken does not bypass Energy Shield
```

The data is the **current league's** tree, so a very old build may show a few
`unresolved` nodes. Resolution is on by default; the first run downloads ~7 MB,
every run after uses the cache. If the download fails (offline / rate-limited),
output degrades gracefully to point counts with a warning. Use `--no-resolve-tree`
to skip it entirely.

### Formats

- **`text`** — plain text with `== Section ==` headers. Compact; ideal for pasting into a chat.
- **`markdown`** — GitHub-flavoured Markdown: heading sections, stat/config **tables**, and item mods in fenced code blocks. Ideal for saving as an `.md` file or rendering in a doc.
- **`json`** — the structured `Build` model with **raw numeric** stat values and every gem/item/tree field. For programmatic use. Carries a `schemaVersion`; shape mirrors `pobtotext/model.py`, plus `activeTreeTitle`/`activeItemSetTitle` pointers.

## As a library

```python
from pobtotext.core import convert, code_to_build

text = convert(export_code)          # straight to rendered text
build = code_to_build(export_code)   # the parsed Build dataclass, for custom use
print(build.stats["FullDPS"], build.main_skill_name)
```

## Architecture

A four-stage pipeline; each stage is swappable in isolation:

```
input source  ->  decode           ->  parse            ->  render
(reference to     (base64 + zlib       (XML -> Build        (Build -> text)
 export code)      -> XML)              dataclasses)
```

| Stage | Module | Extension point |
| --- | --- | --- |
| Input | `pobtotext/inputs/` | Subclass `InputSource`, register in `inputs/__init__.py`. |
| Decode | `pobtotext/decode.py` | Transport only; rarely changes. |
| Model | `pobtotext/model.py` | Typed boundary; renderers depend only on this. |
| Parse | `pobtotext/parse.py` | Forgiving XML → `Build`. |
| Render | `pobtotext/render/` | Subclass `Renderer`, register in `render/__init__.py`. |

## Roadmap

v1 deliberately ships the easiest working slice. The seams are already in place
for these next steps:

- **More input sources** — `pastebin.com` URL and local XML/build file
  (`pobb.in` already ships). Each is a new `InputSource` whose `matches()` lets
  `auto` route to it.
- **A compact `summary` format** — key stats + main links only (text/markdown/json
  already ship). Each format is a new `Renderer`; the `Build` model already carries
  everything needed.
- **Tree data pinned by version** — resolution currently uses the current league's
  tree; bundling/downloading per-version data would make old builds resolve exactly.
- **Gem grouping polish** — clearer active-vs-support separation and per-skill DPS
  when PoB stores it.

## Development

```bash
python tests/test_pipeline.py     # no deps
# or, with pytest installed:
python -m pytest
```

Tests round-trip a sample build (`tests/sample_build.xml`) through the whole
pipeline, so decode, parse, and render are all covered without needing a live code.
