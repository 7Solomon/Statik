"""One-off migration of hand labels written before the OBB switch.

Two things changed under the existing annotations at once:

  1. The label format went from axis-aligned `class cx cy w h` to oriented
     `class x1 y1 x2 y2 x3 y3 x4 y4`. An axis-aligned box is a valid oriented
     box, so this direction is lossless - the four corners are just written out.

  2. STRECKENLAST joined the class list *in the middle*, after the moments, so
     every id from VOLLGELENK onward shifted up by one. Left alone, 72 hand-drawn
     VOLLGELENK boxes would silently have become STRECKENLAST.

Ids are remapped by NAME rather than by a fixed offset, so this stays correct if
the list is reordered again.

Dry run by default; pass --apply to write.

    python -m src.plugins.labeling.migrate_obb
    python -m src.plugins.labeling.migrate_obb --apply
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from src.plugins.generator.image.stanli_symbols import detectable_class_names

#: The class list as it stood when these labels were drawn.
LEGACY_CLASSES = [
    "FESTLAGER", "LOSLAGER", "FESTE_EINSPANNUNG", "GLEITLAGER",
    "EINZELLAST", "MOMENT_UHRZEIGER", "MOMENT_GEGEN_UHRZEIGER",
    "VOLLGELENK", "SCHUBGELENK", "NORMALKRAFTGELENK",
]


def remap_class(old_id: int, new_classes: List[str]) -> Optional[int]:
    if not 0 <= old_id < len(LEGACY_CLASSES):
        return None
    name = LEGACY_CLASSES[old_id]
    return new_classes.index(name) if name in new_classes else None


def convert_line(line: str, new_classes: List[str]) -> Optional[str]:
    """One label row, old or new. Returns None for a row to drop."""
    parts = line.split()
    if not parts:
        return None

    if len(parts) == 9:
        return line.strip()  # already migrated; idempotent

    if len(parts) != 5:
        return None

    old_id = int(float(parts[0]))
    new_id = remap_class(old_id, new_classes)
    if new_id is None:
        return None

    cx, cy, w, h = (float(v) for v in parts[1:])
    x0, y0, x1, y1 = cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2
    corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    coords = " ".join(f"{min(1.0, max(0.0, v)):.6f}" for c in corners for v in c)
    return f"{new_id} {coords}"


def migrate(root: Path, apply: bool) -> int:
    new_classes = detectable_class_names()
    annotations = sorted((root / "annotations").glob("*.txt"))
    if not annotations:
        print(f"no annotations under {root}")
        return 0

    files_changed = rows_converted = rows_dropped = rows_already = 0
    moves = {}

    for path in annotations:
        original = path.read_text(encoding="utf-8").splitlines()
        converted: List[str] = []
        changed = False
        for line in original:
            if not line.split():
                continue
            out = convert_line(line, new_classes)
            if out is None:
                rows_dropped += 1
                changed = True
                continue
            if len(line.split()) == 9:
                rows_already += 1
            else:
                rows_converted += 1
                changed = True
                old_name = LEGACY_CLASSES[int(float(line.split()[0]))]
                new_id = int(out.split()[0])
                moves[old_name] = (int(float(line.split()[0])), new_id)
            converted.append(out)

        if changed:
            files_changed += 1
            if apply:
                path.write_text("\n".join(converted) + "\n", encoding="utf-8")

    verb = "migrated" if apply else "would migrate"
    print(f"{verb} {files_changed} of {len(annotations)} files")
    print(f"  rows converted : {rows_converted}")
    print(f"  rows already ok: {rows_already}")
    print(f"  rows dropped   : {rows_dropped}")
    if moves:
        print("  class id moves:")
        for name, (old, new) in sorted(moves.items(), key=lambda kv: kv[1][0]):
            arrow = "->" if old != new else "=="
            print(f"    {old:>2} {arrow} {new:<2}  {name}")
    if not apply:
        print("\ndry run - nothing written. Re-run with --apply.")
    return files_changed


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, default=Path("content/labeling"),
                    help="labeling root, or one session folder")
    ap.add_argument("--apply", action="store_true", help="write the changes")
    args = ap.parse_args(argv)

    root = args.root
    sessions = ([root] if (root / "annotations").is_dir()
                else sorted(p for p in root.iterdir() if (p / "annotations").is_dir())
                if root.is_dir() else [])
    if not sessions:
        print(f"no labeling sessions under {root}", file=sys.stderr)
        return 1

    for session in sessions:
        print(f"\n== {session}")
        migrate(session, args.apply)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
