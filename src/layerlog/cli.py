"""Command-line interface and local JSON storage for LayerLog."""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


def default_database_path() -> Path:
    """Return an OS-appropriate per-user data file path."""
    if os.name == "nt":
        root = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return root / "LayerLog" / "prints.json"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "LayerLog" / "prints.json"
    root = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return root / "layerlog" / "prints.json"


def load_entries(path: Path) -> list[dict[str, Any]]:
    """Load entries, returning an empty list when the database does not exist."""
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"could not read database {path}: {exc}") from exc
    if not isinstance(data, list) or any(not isinstance(item, dict) for item in data):
        raise ValueError(f"database {path} has an invalid format")
    return data


def save_entries(path: Path, entries: list[dict[str, Any]]) -> None:
    """Write entries atomically to reduce the chance of a partial database."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = path.with_suffix(path.suffix + ".tmp")
        temporary_path.write_text(
            json.dumps(entries, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        temporary_path.replace(path)
    except OSError as exc:
        raise ValueError(f"could not save database {path}: {exc}") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="layerlog",
        description="Keep a simple local log of your 3D prints.",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=None,
        metavar="PATH",
        help="database JSON file (default: your user data directory)",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    add_parser = commands.add_parser("add", help="record a completed print")
    add_parser.add_argument("--name", required=True, help="print name")
    add_parser.add_argument("--printer", required=True, help="printer used")
    add_parser.add_argument("--material", default="PLA", help="filament material (default: PLA)")
    add_parser.add_argument("--grams", type=float, default=0, help="filament used in grams")
    add_parser.add_argument("--minutes", type=int, default=0, help="print duration in minutes")
    add_parser.add_argument("--notes", default="", help="optional note")
    add_parser.set_defaults(handler=add_print)

    list_parser = commands.add_parser("list", help="show recorded prints")
    list_parser.add_argument("--limit", type=int, default=20, help="maximum entries to show (default: 20)")
    list_parser.set_defaults(handler=list_prints)

    stats_parser = commands.add_parser("stats", help="show print totals and breakdowns")
    stats_parser.set_defaults(handler=show_stats)
    return parser


def add_print(args: argparse.Namespace, database: Path) -> int:
    name = args.name.strip()
    printer = args.printer.strip()
    material = args.material.strip()
    if not name or not printer or not material:
        raise ValueError("name, printer, and material must not be blank")
    if args.grams < 0:
        raise ValueError("grams cannot be negative")
    if args.minutes < 0:
        raise ValueError("minutes cannot be negative")

    entries = load_entries(database)
    entry = {
        "id": uuid.uuid4().hex[:8],
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "name": name,
        "printer": printer,
        "material": material,
        "grams": round(args.grams, 2),
        "minutes": args.minutes,
        "notes": args.notes.strip(),
    }
    entries.append(entry)
    save_entries(database, entries)
    print(f"Saved {entry['name']} [{entry['id']}]")
    return 0


def list_prints(args: argparse.Namespace, database: Path) -> int:
    if args.limit < 1:
        raise ValueError("limit must be at least 1")
    entries = sorted(
        load_entries(database),
        key=lambda item: item.get("created_at", ""),
        reverse=True,
    )
    if not entries:
        print("No print jobs recorded yet. Add one with: layerlog add --name Benchy --printer MyPrinter")
        return 0

    print(f"{'DATE':20}  {'PRINT':24}  {'PRINTER':20}  {'MATERIAL':10}  {'GRAMS':>8}  {'MIN':>5}")
    print("-" * 99)
    for entry in entries[: args.limit]:
        created = str(entry.get("created_at", ""))[:19].replace("T", " ")
        print(
            f"{created:20}  {str(entry.get('name', ''))[:24]:24}  "
            f"{str(entry.get('printer', ''))[:20]:20}  "
            f"{str(entry.get('material', ''))[:10]:10}  "
            f"{float(entry.get('grams', 0)):8.2f}  "
            f"{int(entry.get('minutes', 0)):5d}"
        )
        notes = str(entry.get("notes", "")).strip()
        if notes:
            print(f"  Note: {notes}")
    if len(entries) > args.limit:
        print(f"Showing {args.limit} of {len(entries)} entries.")
    return 0


def show_stats(_args: argparse.Namespace, database: Path) -> int:
    entries = load_entries(database)
    if not entries:
        print("No print jobs recorded yet.")
        return 0

    total_grams = sum(float(entry.get("grams", 0)) for entry in entries)
    total_minutes = sum(int(entry.get("minutes", 0)) for entry in entries)
    by_material: dict[str, dict[str, float | int]] = defaultdict(lambda: {"prints": 0, "grams": 0.0})
    by_printer: dict[str, int] = defaultdict(int)
    for entry in entries:
        material = str(entry.get("material", "Unknown"))
        printer = str(entry.get("printer", "Unknown"))
        by_material[material]["prints"] += 1
        by_material[material]["grams"] += float(entry.get("grams", 0))
        by_printer[printer] += 1

    hours, minutes = divmod(total_minutes, 60)
    print(f"Prints recorded: {len(entries)}")
    print(f"Filament used:   {total_grams:.2f} g")
    print(f"Print time:      {hours}h {minutes}m")
    print("\nBy material:")
    for material, values in sorted(by_material.items()):
        print(f"  {material}: {values['prints']} prints, {float(values['grams']):.2f} g")
    print("\nBy printer:")
    for printer, count in sorted(by_printer.items()):
        print(f"  {printer}: {count} prints")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    database = (args.db or default_database_path()).expanduser()
    try:
        return args.handler(args, database)
    except ValueError as exc:
        print(f"layerlog: error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
