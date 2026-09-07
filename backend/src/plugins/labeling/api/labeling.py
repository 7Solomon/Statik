"""HTTP surface for hand-labelling real harvested figures.

The generator produces perfect labels for free, so the only labels worth a
person's time are the ones on real pages. This blueprint is the tool for making
them: it serves an image folder one image at a time, records the boxes drawn on
each, and exports the result as a YOLO dataset the trainer already understands.

Export deliberately carries the SKIPPED images through as background images
(a present but empty .txt). They are the pages the model currently fires on -
formula blocks, function plots, norm figures - and ultralytics reads them as
"there is nothing here", which is the correction those false positives need.
"""

from __future__ import annotations

import base64
import csv
import shutil
import sys
import traceback
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from flask import Blueprint, jsonify, request

from src.plugins.labeling.icons import class_icons
from src.plugins.labeling.split import group_key, plan_split
from src.plugins.labeling.store import (
    IMAGE_SUFFIXES, LABELED, SKIPPED, LabelingSession, LegacyLabelsError, slug,
)

bp = Blueprint("labeling", __name__, url_prefix="/api/labeling")

CONTENT_ROOT = Path("./content")
DATASETS_ROOT = CONTENT_ROOT / "datasets"


def _resolve_images_dir(raw: str) -> Path:
    """Confine every request to content/, so a path cannot escape the volume."""
    base = CONTENT_ROOT.resolve()
    path = (base / raw if not Path(raw).is_absolute() else Path(raw)).resolve()
    if base != path and base not in path.parents:
        raise PermissionError(f"image folder must live under {base}")
    return path


def _session(payload: dict) -> LabelingSession:
    images_dir = _resolve_images_dir(payload.get("images_dir", ""))
    return LabelingSession.open(CONTENT_ROOT.resolve(), images_dir)


def _fail(exc: Exception, code: int = 400):
    if isinstance(exc, LegacyLabelsError):
        # Not a bug to trace out; it is an instruction for the operator.
        sys.stderr.write(f"[LABELING] {exc}\n")
        return jsonify({"error": str(exc)}), 409
    sys.stderr.write(f"[LABELING] {exc}\n{traceback.format_exc()}")
    sys.stderr.flush()
    return jsonify({"error": str(exc)}), code


def _manifest(images_dir: Path) -> Dict[str, dict]:
    """Optional harvest metadata, joined on filename.

    tmp/harvest.py writes a manifest next to the image folder recording which
    PDF and page each crop came from. Source is the strongest available signal
    for whether a crop is worth labelling, so it is surfaced for filtering
    rather than left in the CSV.
    """
    path = images_dir.parent / "manifest.csv"
    if not path.exists():
        return {}
    out: Dict[str, dict] = {}
    try:
        with open(path, encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                name = row.get("filename")
                if not name:
                    continue
                try:
                    score = float(row.get("score") or 0.0)
                except ValueError:
                    score = 0.0
                out[name] = {
                    "lecture": row.get("lecture") or "",
                    "page": row.get("page") or "",
                    "score": score,
                    "source_pdf": Path(row.get("source_pdf") or "").name,
                }
    except Exception as exc:  # a broken manifest must not block labelling
        sys.stderr.write(f"[LABELING] manifest unreadable: {exc}\n")
    return out


@bp.route("/class_icons", methods=["GET"])
def get_class_icons():
    """A small PNG per class, drawn with the generator's own symbol code."""
    return jsonify({"icons": class_icons()})


@bp.route("/sources", methods=["GET"])
def list_sources():
    """Every folder under content/ that holds images, e.g. the mounted harvest."""
    root = CONTENT_ROOT.resolve()
    sources = []
    if root.exists():
        candidates = [root / "harvest" / "images"]
        for entry in sorted(root.iterdir()):
            if entry.is_dir() and entry.name not in {"datasets", "labeling"}:
                candidates.append(entry / "images")
                candidates.append(entry)
        seen = set()
        for cand in candidates:
            if cand in seen or not cand.is_dir():
                continue
            seen.add(cand)
            count = sum(1 for p in cand.iterdir()
                        if p.suffix.lower() in IMAGE_SUFFIXES)
            if count:
                sources.append({
                    "images_dir": str(cand.relative_to(root)),
                    "label": str(cand.relative_to(root)),
                    "count": count,
                    "has_manifest": (cand.parent / "manifest.csv").exists(),
                })
    return jsonify({"sources": sources, "content_root": str(root)})


@bp.route("/session", methods=["POST"])
def open_session():
    """Full index for one image folder: status and metadata for every image."""
    try:
        payload = request.get_json() or {}
        session = _session(payload)
        data = session.overview()
        meta = _manifest(session.images_dir)
        for item in data["images"]:
            item["meta"] = meta.get(item["filename"], {})
        data["lectures"] = sorted({m["lecture"] for m in meta.values() if m["lecture"]})
        return jsonify(data)
    except Exception as exc:
        return _fail(exc)


@bp.route("/images_batch", methods=["POST"])
def images_batch():
    """Base64 data URIs for several images at once, so the UI can prefetch."""
    try:
        payload = request.get_json() or {}
        session = _session(payload)
        results: Dict[str, Optional[str]] = {}
        for filename in payload.get("filenames", [])[:32]:
            path = session.images_dir / Path(filename).name
            if not path.exists() or path.suffix.lower() not in IMAGE_SUFFIXES:
                results[filename] = None
                continue
            mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
            encoded = base64.b64encode(path.read_bytes()).decode("ascii")
            results[filename] = f"data:{mime};base64,{encoded}"
        return jsonify(results)
    except Exception as exc:
        return _fail(exc)


@bp.route("/boxes", methods=["POST"])
def get_boxes():
    try:
        payload = request.get_json() or {}
        session = _session(payload)
        filename = Path(payload["filename"]).name
        return jsonify({
            "filename": filename,
            "boxes": [b.to_dict() for b in session.read_boxes(filename)],
        })
    except Exception as exc:
        return _fail(exc)


@bp.route("/save", methods=["POST"])
def save_boxes():
    try:
        payload = request.get_json() or {}
        session = _session(payload)
        filename = Path(payload["filename"]).name
        return jsonify(session.save(filename, payload.get("boxes", [])))
    except Exception as exc:
        return _fail(exc)


@bp.route("/skip", methods=["POST"])
def skip_image():
    try:
        payload = request.get_json() or {}
        session = _session(payload)
        return jsonify(session.skip(Path(payload["filename"]).name))
    except Exception as exc:
        return _fail(exc)


@bp.route("/reset", methods=["POST"])
def reset_image():
    try:
        payload = request.get_json() or {}
        session = _session(payload)
        return jsonify(session.reset(Path(payload["filename"]).name))
    except Exception as exc:
        return _fail(exc)


@bp.route("/export", methods=["POST"])
def export_dataset():
    """Write the labelled set out as a YOLO dataset under content/datasets.

    Splits are drawn from a seeded shuffle so re-exporting the same decisions
    reproduces the same split, and the val set stays comparable run to run.
    """
    try:
        payload = request.get_json() or {}
        session = _session(payload)
        include_negatives = bool(payload.get("include_negatives", True))
        val_ratio = float(payload.get("val_ratio", 0.2))
        name = slug(payload.get("dataset_name") or f"real-{session.name}")

        overview = session.overview()
        wanted = {LABELED} | ({SKIPPED} if include_negatives else set())
        picked = [i["filename"] for i in overview["images"] if i["status"] in wanted]
        if not picked:
            return jsonify({"error": "nothing labelled yet"}), 400

        # Split by source document, not by image, and steer the rare classes
        # into val on purpose - see split.py for what the plain shuffle did.
        manifest = _manifest(session.images_dir)
        plan = plan_split(
            [(name, group_key(name, manifest.get(name)),
              [b.class_id for b in session.read_boxes(name)])
             for name in picked],
            val_ratio=val_ratio,
        )
        splits = plan["picked"]

        out_dir = DATASETS_ROOT / name
        if out_dir.exists():
            shutil.rmtree(out_dir)

        counts = {}
        for split, names in splits.items():
            img_dir = out_dir / split / "images"
            lbl_dir = out_dir / split / "labels"
            img_dir.mkdir(parents=True, exist_ok=True)
            lbl_dir.mkdir(parents=True, exist_ok=True)
            for filename in names:
                shutil.copy2(session.images_dir / filename, img_dir / filename)
                boxes = session.read_boxes(filename)
                # A skipped image gets an empty file, not no file: that is what
                # makes it a background sample rather than an unlabelled one.
                (lbl_dir / (Path(filename).stem + ".txt")).write_text(
                    "".join(b.to_line() + "\n" for b in boxes), encoding="utf-8")
            counts[split] = len(names)

        (out_dir / "dataset.yaml").write_text(yaml.safe_dump({
            "path": str(out_dir.resolve()),
            "train": "train/images",
            "val": "val/images",
            "names": session.classes,
            # Hand labels are oriented boxes, same as the generator's; the
            # trainer reads this to pick an -obb base checkpoint.
            "task": "obb",
        }, sort_keys=False), encoding="utf-8")

        negatives = sum(1 for f in picked if not session.read_boxes(f))
        return jsonify({
            "success": True,
            "dataset_path": str(out_dir),
            "counts": counts,
            "total": len(picked),
            "negatives": negatives,
            # The split is only trustworthy if the rare classes reached val, so
            # the evidence ships with the result rather than needing a re-count.
            "per_class": {session.classes[c]: v
                          for c, v in sorted(plan["per_class"].items())},
            "single_source_classes": [session.classes[c]
                                      for c in plan["single_group_classes"]],
            "n_source_documents": len(set(plan["documents"]["train"])
                                      | set(plan["documents"]["val"])),
            # Must be empty. A document on both sides is the leakage the
            # grouping exists to stop, so it is reported, not assumed away.
            "shared_documents": plan["shared_documents"],
        })
    except Exception as exc:
        return _fail(exc, 500)
