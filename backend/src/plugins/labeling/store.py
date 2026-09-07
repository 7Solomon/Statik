"""On-disk store for hand-drawn labels on real (harvested) images.

Labels are YOLO OBB - `class x1 y1 x2 y2 x3 y3 x4 y4`, four corners normalised
to the image. Axis-aligned boxes would be the easier UI, but they cannot be
upgraded to oriented ones afterwards without redoing the work by hand, and the
generator already writes oriented boxes.

The images themselves are read-only input - they come from tmp/harvest.py and
live outside this tree. Everything this module writes goes into

    content/labeling/<session>/
        source.json          which image folder this session labels
        state.json           per-image decision: labeled / skipped
        annotations/*.txt    YOLO boxes, one file per labelled image

Three states, not two. "No boxes yet" and "looked at it, it is not a structural
system" are different facts and only the second one is useful later: an image
explicitly marked SKIPPED is a hard negative, and YOLO reads a *present but
empty* .txt as exactly that. Collapsing the two would throw that away, and the
false positives on real pages are the reason the set is being built at all.

Class ids come from the generator's own list so a hand label and a generated
label always mean the same thing; see stanli_symbols.detectable_class_names.
"""

from __future__ import annotations

import json
import re
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from src.plugins.generator.image.stanli_symbols import detectable_class_names

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}

UNLABELED = "unlabeled"
LABELED = "labeled"
SKIPPED = "skipped"

#: Serialised writes. The payloads are tiny but a double-click must not be able
#: to interleave a read-modify-write of state.json with another one.
_lock = threading.RLock()


class LegacyLabelsError(RuntimeError):
    """Annotations were written before the oriented-box switch."""


def slug(text: str, limit: int = 48) -> str:
    out = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()
    return out[:limit] or "session"


def _polygon_area(corners: List[Tuple[float, float]]) -> float:
    total = 0.0
    for i in range(len(corners)):
        x0, y0 = corners[i]
        x1, y1 = corners[(i + 1) % len(corners)]
        total += x0 * y1 - x1 * y0
    return abs(total) / 2.0


@dataclass(frozen=True)
class Box:
    """One YOLO OBB: class id plus four corners normalised to [0, 1].

    Oriented, not axis-aligned, to match what the generator writes - see
    stanli_symbols._obb_from_ops. A hand label and a generated label have to be
    the same shape or they cannot go into one dataset.
    """

    class_id: int
    corners: Tuple[Tuple[float, float], ...]

    #: Smaller than this (as a share of the image) is a mis-click, not a label.
    MIN_AREA = 1e-6

    @classmethod
    def parse(cls, raw: dict, n_classes: int) -> "Box":
        class_id = int(raw["class_id"])
        if not 0 <= class_id < n_classes:
            raise ValueError(f"class_id {class_id} out of range")

        pts = raw.get("corners")
        if not pts or len(pts) != 4:
            raise ValueError("an oriented box needs exactly 4 corners")

        corners = tuple(
            (min(1.0, max(0.0, float(p[0]))), min(1.0, max(0.0, float(p[1]))))
            for p in pts
        )
        if _polygon_area(list(corners)) < cls.MIN_AREA:
            raise ValueError("box has (near) zero area")
        return cls(class_id, corners)

    def to_line(self) -> str:
        coords = " ".join(f"{v:.6f}" for xy in self.corners for v in xy)
        return f"{self.class_id} {coords}"

    def to_dict(self) -> dict:
        return {"class_id": self.class_id,
                "corners": [list(c) for c in self.corners]}


class LabelingSession:
    """One image folder plus the decisions made about it so far."""

    def __init__(self, root: Path, images_dir: Path, name: str):
        self.root = root
        self.images_dir = images_dir
        self.name = name
        self.annotations_dir = root / "annotations"
        self.annotations_dir.mkdir(parents=True, exist_ok=True)
        self.classes: List[str] = list(detectable_class_names())

        source = root / "source.json"
        if not source.exists():
            source.write_text(json.dumps(
                {"images_dir": str(images_dir), "classes": self.classes},
                indent=2), encoding="utf-8")

    # --- session discovery ------------------------------------------------

    @classmethod
    def open(cls, content_root: Path, images_dir: Path) -> "LabelingSession":
        images_dir = images_dir.resolve()
        if not images_dir.is_dir():
            raise FileNotFoundError(f"no such image folder: {images_dir}")
        name = slug(images_dir.parent.name + "-" + images_dir.name)
        return cls(content_root / "labeling" / name, images_dir, name)

    # --- state ------------------------------------------------------------

    @property
    def _state_path(self) -> Path:
        return self.root / "state.json"

    def _read_state(self) -> Dict[str, dict]:
        if not self._state_path.exists():
            return {}
        try:
            return json.loads(self._state_path.read_text(encoding="utf-8"))
        except Exception:
            # A corrupt state file must not lose the .txt files, which are the
            # real work; statuses are rebuilt from them below.
            return {}

    def _write_state(self, state: Dict[str, dict]) -> None:
        tmp = self._state_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
        tmp.replace(self._state_path)

    def image_names(self) -> List[str]:
        return sorted(p.name for p in self.images_dir.iterdir()
                      if p.suffix.lower() in IMAGE_SUFFIXES)

    def _annotation_path(self, filename: str) -> Path:
        return self.annotations_dir / (Path(filename).stem + ".txt")

    def read_boxes(self, filename: str) -> List[Box]:
        path = self._annotation_path(filename)
        if not path.exists():
            return []
        boxes: List[Box] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            parts = line.split()
            if len(parts) != 9:
                continue
            try:
                values = [float(v) for v in parts[1:]]
                corners = tuple((values[2 * i], values[2 * i + 1]) for i in range(4))
                boxes.append(Box(int(float(parts[0])), corners))
            except (TypeError, ValueError):
                continue
        return boxes

    def status_of(self, filename: str, state: Dict[str, dict]) -> str:
        entry = state.get(filename)
        if entry and entry.get("status") in (LABELED, SKIPPED):
            return entry["status"]
        # Fall back to the annotation file, so labels survive a lost state.json.
        return LABELED if self._annotation_path(filename).exists() else UNLABELED

    def legacy_annotations(self) -> List[str]:
        """Annotation files still in the pre-OBB `class cx cy w h` format."""
        stale = []
        for path in sorted(self.annotations_dir.glob("*.txt")):
            for line in path.read_text(encoding="utf-8").splitlines():
                parts = line.split()
                if parts and len(parts) != 9:
                    stale.append(path.name)
                    break
        return stale

    def assert_migrated(self) -> None:
        """Refuse to serve a session whose labels predate the OBB switch.

        Failing loudly matters here: read_boxes() skips rows it cannot parse, so
        an un-migrated session would open looking merely empty, and the first
        save would overwrite real hand-drawn boxes with nothing.
        """
        stale = self.legacy_annotations()
        if stale:
            raise LegacyLabelsError(
                f"{len(stale)} annotation file(s) are still in the old "
                f"axis-aligned format and their class ids predate STRECKENLAST. "
                f"Run:  python -m src.plugins.labeling.migrate_obb "
                f"--root content/labeling --apply"
            )

    def overview(self) -> dict:
        self.assert_migrated()
        with _lock:
            state = self._read_state()
            names = self.image_names()
            items = []
            counts = {UNLABELED: 0, LABELED: 0, SKIPPED: 0}
            for name in names:
                status = self.status_of(name, state)
                counts[status] += 1
                n_boxes = len(self.read_boxes(name)) if status == LABELED else 0
                items.append({"filename": name, "status": status, "n_boxes": n_boxes})
        return {
            "session": self.name,
            "images_dir": str(self.images_dir),
            "classes": self.classes,
            "images": items,
            "counts": counts,
            "total": len(items),
        }

    # --- mutations --------------------------------------------------------

    def save(self, filename: str, raw_boxes: List[dict]) -> dict:
        """Write boxes for one image. An empty list marks it SKIPPED.

        Saving zero boxes and pressing Skip mean the same thing - the image
        holds no labelable symbol - so they are deliberately one code path.
        """
        boxes = [Box.parse(b, len(self.classes)) for b in raw_boxes]
        with _lock:
            path = self._annotation_path(filename)
            if boxes:
                path.write_text("\n".join(b.to_line() for b in boxes) + "\n",
                                encoding="utf-8")
                status = LABELED
            else:
                path.unlink(missing_ok=True)
                status = SKIPPED
            state = self._read_state()
            state[filename] = {"status": status, "updated": time.time()}
            self._write_state(state)
        return {"filename": filename, "status": status, "n_boxes": len(boxes)}

    def skip(self, filename: str) -> dict:
        return self.save(filename, [])

    def reset(self, filename: str) -> dict:
        """Back to unlabeled - undoes a mis-click on Skip."""
        with _lock:
            self._annotation_path(filename).unlink(missing_ok=True)
            state = self._read_state()
            state.pop(filename, None)
            self._write_state(state)
        return {"filename": filename, "status": UNLABELED, "n_boxes": 0}
