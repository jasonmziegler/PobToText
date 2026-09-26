"""Command-line interface for PobToText.

Usage examples::

    # From an argument
    python -m pobtotext "eNqt...=="

    # From stdin (handy for piping)
    pbpaste | python -m pobtotext -

    # From a file containing the code
    python -m pobtotext --file build.txt
"""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .core import convert
from .decode import DecodeError
from .inputs import InputError, available_sources
from .parse import ParseError
from .render import DEFAULT_FORMAT, available_formats
from .treedata import TreeData, TreeDataError, is_cached


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pobtotext",
        description="Convert a Path of Building build into readable text for humans and AI.",
    )
    parser.add_argument(
        "code",
        nargs="?",
        help="PoB export code (or '-' to read from stdin). Omit if using --file.",
    )
    parser.add_argument(
        "--file",
        "-f",
        metavar="PATH",
        help="Read the export code from a file instead of an argument.",
    )
    parser.add_argument(
        "--source",
        "-s",
        default="auto",
        choices=available_sources(),
        help="Input source. 'auto' detects it (default). More sources coming.",
    )
    parser.add_argument(
        "--format",
        default=None,
        choices=available_formats(),
        help=f"Output format. Defaults to {DEFAULT_FORMAT}; inferred from --output "
        "extension (.md -> markdown, .json -> json).",
    )
    parser.add_argument(
        "--output",
        "-o",
        metavar="PATH",
        help="Write output to a file instead of stdout.",
    )
    parser.add_argument(
        "--no-resolve-tree",
        action="store_true",
        help="Skip passive-tree name resolution (no download; show point counts only).",
    )
    parser.add_argument(
        "--refresh-tree-data",
        action="store_true",
        help="Re-download the passive-tree data even if a cached copy exists.",
    )
    parser.add_argument("--version", action="version", version=f"pobtotext {__version__}")
    return parser


def _read_reference(args: argparse.Namespace) -> str:
    if args.file:
        with open(args.file, "r", encoding="utf-8") as fh:
            return fh.read()
    if args.code == "-" or (args.code is None and not sys.stdin.isatty()):
        return sys.stdin.read()
    if args.code:
        return args.code
    raise InputError("No input given. Provide a code, use --file, or pipe via stdin.")


_EXT_FORMATS = {
    ".md": "markdown",
    ".markdown": "markdown",
    ".json": "json",
}


def _resolve_format(args: argparse.Namespace) -> str:
    if args.format is not None:
        return args.format
    if args.output:
        lower = args.output.lower()
        for ext, fmt in _EXT_FORMATS.items():
            if lower.endswith(ext):
                return fmt
    return DEFAULT_FORMAT


def _load_tree_data(args: argparse.Namespace) -> TreeData | None:
    """Load tree data unless disabled; degrade gracefully on failure."""
    if args.no_resolve_tree:
        return None
    if args.refresh_tree_data or not is_cached():
        print(
            "Downloading passive tree data from pathofexile.com (one-time, cached)...",
            file=sys.stderr,
        )
    try:
        return TreeData.load(refresh=args.refresh_tree_data)
    except TreeDataError as exc:
        print(
            f"warning: passive-tree names unavailable ({exc}); showing point counts only. "
            "Use --no-resolve-tree to silence.",
            file=sys.stderr,
        )
        return None


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        reference = _read_reference(args)
        tree_data = _load_tree_data(args)
        output = convert(
            reference,
            source=args.source,
            fmt=_resolve_format(args),
            tree_data=tree_data,
        )
    except (InputError, DecodeError, ParseError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except FileNotFoundError as exc:
        print(f"error: file not found: {exc.filename}", file=sys.stderr)
        return 1

    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(output)
    else:
        sys.stdout.write(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
