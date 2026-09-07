"""Grouped, class-stratified train/val split for the hand-labelled real set.

A plain per-image shuffle fails this set in two ways, both measured on it.

**Leakage.** The crops are pages of a few dozen PDFs, and pages of one PDF share
a figure style, a line weight and often the same worked example. Splitting by
image put 8 of 14 val source documents into train as well - among them the Werkle
textbook, which alone contributes a sixth of the labelled pages. A val number
drawn from that is closer to a training number.

**Rare classes miss val entirely.** Five of the eleven classes have 3-8 boxes in
the whole set. The uniform shuffle left MOMENT_UHRZEIGER and NORMALKRAFTGELENK
with zero val instances, so their AP read 0.0 whatever the model actually did.

Three things follow, and the second two were both learned by getting them wrong:

1. Documents are assigned whole, so no PDF spans the split.

2. Except when one document is too big to place. Werkle is 183 of 357 crops -
   51% - and a group that size cannot go anywhere without wrecking a 20% val
   split; the first run of this module duly put all 183 in val, making val
   larger than train. An oversized document is therefore cut into *contiguous
   page blocks*, which keeps the real leakage risk - near-identical figures on
   neighbouring pages - inside one block, and only exposes it at the few seams.

3. Rare classes are seeded into val explicitly, before anything else is placed.
   A proportional objective cannot do this: GLEITLAGER has 4 boxes in 2
   documents, so its val quota is 0.8 of a box and *any* assignment to val reads
   as an overshoot. Both documents went to train and val saw zero. Presence in
   val is a precondition for measuring a class at all, not something to trade
   off against proportion, so it is decided first.

None of this manufactures what the corpus lacks. A class whose every instance
sits in one document can only land on one side, and the caller is told which
classes those are rather than left to read it off a zero.
"""

from __future__ import annotations

import math
import random
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

TRAIN = "train"
VAL = "val"
SPLITS = (TRAIN, VAL)

#: Class balance is the reason this module exists, so it outweighs hitting the
#: image ratio exactly. Both terms are "how full is this split", same 0..1 scale.
_IMAGE_WEIGHT = 0.5

#: A quota of zero would make every fill ratio infinite; floor it instead.
_EPS = 1e-9

#: Documents at or below this many crops are never cut into page blocks. The
#: imbalance a group this small can cause is smaller than the seam it costs.
_MIN_GROUP_CAP = 8

_PAGE_RE = re.compile(r"_p(\d+)$")


def group_key(filename: str, meta: Optional[dict] = None) -> str:
    """Which document a crop came from - the unit that must not be split.

    The manifest's source PDF is the truth. Without it, fall back to the name
    tmp/harvest.py gives a crop, `<index>_<lecture>_<document>_p<page>.png`:
    dropping the index and the page leaves the document.
    """
    if meta:
        pdf = (meta.get("source_pdf") or "").strip()
        if pdf:
            return pdf
    stem = Path(filename).stem
    _, _, body = stem.partition("_")
    return (body or stem).rsplit("_p", 1)[0] or stem


def page_of(filename: str) -> int:
    """Page number from the crop name, for ordering within a document."""
    match = _PAGE_RE.search(Path(filename).stem)
    return int(match.group(1)) if match else 0


@dataclass
class _Group:
    key: str
    files: List[str] = field(default_factory=list)
    counts: Counter = field(default_factory=Counter)

    @property
    def n_boxes(self) -> int:
        return sum(self.counts.values())

    @property
    def positive(self) -> bool:
        return self.n_boxes > 0


def _subdivide(
    groups: Dict[str, _Group],
    classes_of: Dict[str, Sequence[int]],
    n_images: int,
    max_share: float,
) -> Dict[str, _Group]:
    """Cut any document too large to place into contiguous page blocks."""
    cap = max(int(n_images * max_share), _MIN_GROUP_CAP)
    out: Dict[str, _Group] = {}
    for key, group in groups.items():
        if len(group.files) <= cap:
            out[key] = group
            continue
        # By page, so a block is a stretch of the document rather than a
        # scatter of it - neighbouring pages are what actually look alike.
        ordered = sorted(group.files, key=lambda f: (page_of(f), f))
        n_blocks = math.ceil(len(ordered) / cap)
        size = math.ceil(len(ordered) / n_blocks)
        for start in range(0, len(ordered), size):
            block = ordered[start:start + size]
            sub = _Group(f"{key}#p{page_of(block[0]):04d}-{page_of(block[-1]):04d}")
            sub.files = list(block)
            for name in block:
                sub.counts.update(classes_of[name])
            out[sub.key] = sub
    return out


def plan_split(
    items: Sequence[Tuple[str, str, Sequence[int]]],
    val_ratio: float = 0.2,
    seed: int = 1337,
    max_group_share: Optional[float] = None,
) -> dict:
    """Assign every file to train or val, keeping documents intact.

    `items` is one `(filename, group_key, class_ids)` per image; `class_ids` is
    empty for a background image. Returns the split lists plus the per-class
    matrix the caller should show the operator, because "did the rare classes
    reach val" is the only question this function exists to answer.
    """
    val_ratio = min(1.0, max(0.0, float(val_ratio)))
    # No document may exceed the val quota, or it cannot be placed in val at
    # all; the 0.1 floor keeps a tiny val_ratio from shredding every document.
    if max_group_share is None:
        max_group_share = max(val_ratio, 0.1)

    groups: Dict[str, _Group] = {}
    classes_of: Dict[str, Sequence[int]] = {}
    for filename, key, class_ids in items:
        group = groups.setdefault(key, _Group(key))
        group.files.append(filename)
        group.counts.update(class_ids)
        classes_of[filename] = list(class_ids)

    n_images = len(classes_of)
    if len(groups) > 1:
        groups = _subdivide(groups, classes_of, n_images, max_group_share)

    totals: Counter = Counter()
    n_groups_with: Counter = Counter()
    for group in groups.values():
        totals.update(group.counts)
        for class_id in group.counts:
            n_groups_with[class_id] += 1

    picked: Dict[str, List[str]] = {TRAIN: [], VAL: []}
    picked_groups: Dict[str, List[str]] = {TRAIN: [], VAL: []}
    have: Dict[str, Counter] = {TRAIN: Counter(), VAL: Counter()}
    assigned: Dict[str, str] = {}

    def place(group: _Group, split: str) -> None:
        picked[split].extend(sorted(group.files))
        picked_groups[split].append(group.key)
        have[split].update(group.counts)
        assigned[group.key] = split

    # A quota of zero is floored to _EPS below, and an empty split then looks
    # maximally attractive the moment the other one starts filling. There is
    # nothing to balance in that case anyway, so decide it here.
    if val_ratio in (0.0, 1.0):
        target = VAL if val_ratio == 1.0 else TRAIN
        for group in sorted(groups.values(), key=lambda g: g.key):
            place(group, target)
        return _result(picked, picked_groups, have, groups, totals, n_groups_with)

    # Sort by key before shuffling: dict order follows the caller's item order,
    # and a shuffle seeded off that would make the split depend on it.
    ordered = sorted(groups.values(), key=lambda g: g.key)
    random.Random(seed).shuffle(ordered)

    positives = [g for g in ordered if g.positive]
    negatives = [g for g in ordered if not g.positive]

    # Presence first - see point 3 in the module docstring. Rarest class first,
    # so the class with the least room to manoeuvre picks before the others
    # have spent the groups it needed.
    for class_id in sorted(totals, key=lambda c: (totals[c], c)):
        if n_groups_with[class_id] < 2 or have[VAL][class_id]:
            continue
        free = [g for g in positives
                if g.key not in assigned and g.counts.get(class_id)]
        # Fewer than two left would mean seeding val by emptying train.
        if len(free) < 2:
            continue
        # The lightest contributor, so presence costs val as little quota as
        # possible and the proportional pass below still has room to work.
        place(min(free, key=lambda g: (g.counts[class_id], len(g.files), g.key)),
              VAL)

    image_quota = {VAL: max(n_images * val_ratio, _EPS),
                   TRAIN: max(n_images * (1.0 - val_ratio), _EPS)}
    # Floor the quota at one box for any class that could be on both sides, so
    # "val has none of this" always reads as underfull rather than on-target.
    class_quota = {
        VAL: {c: max(n * val_ratio, 1.0 if n_groups_with[c] > 1 else _EPS)
              for c, n in totals.items()},
        TRAIN: {c: max(n * (1.0 - val_ratio), 1.0 if n_groups_with[c] > 1 else _EPS)
                for c, n in totals.items()},
    }

    def cost(split: str, group: _Group) -> float:
        # Fill *after* adding the group, not before: a group of 60 crops looks
        # free on an empty split otherwise, and lands there whole.
        images = (len(picked[split]) + len(group.files)) / image_quota[split]
        if not group.counts:
            return images
        # Weight by rarity so a group's scarcest class decides where it goes;
        # the mean keeps groups of different breadth comparable.
        weights = sum(1.0 / totals[c] for c in group.counts)
        classes = sum(
            ((have[split][c] + n) / class_quota[split][c]) / totals[c]
            for c, n in group.counts.items()
        ) / weights
        return classes + _IMAGE_WEIGHT * images

    # Rarest class first, heaviest group first within that: the big groups are
    # the ones that overshoot a quota, so place them while there is still room
    # to compensate.
    positives.sort(key=lambda g: (min(totals[c] for c in g.counts), -g.n_boxes))
    negatives.sort(key=lambda g: -len(g.files))

    for group in positives + negatives:
        if group.key in assigned:
            continue
        # An exact tie goes to val: it is the smaller side, so it is the one
        # that runs out of room.
        place(group, min(SPLITS, key=lambda s: (cost(s, group), s != VAL)))

    return _result(picked, picked_groups, have, groups, totals, n_groups_with)


def _document_of(group_key_: str) -> str:
    """The document a (possibly subdivided) group came from."""
    return group_key_.split("#p", 1)[0]


def _result(picked, picked_groups, have, groups, totals, n_groups_with) -> dict:
    # Compare documents, not group keys: two page blocks of one PDF have
    # different keys, so a seam that did straddle the split would report clean.
    docs = {s: {_document_of(k) for k in picked_groups[s]} for s in SPLITS}
    return {
        "picked": {s: picked[s] for s in SPLITS},
        "groups": {s: sorted(picked_groups[s]) for s in SPLITS},
        "documents": {s: sorted(docs[s]) for s in SPLITS},
        "shared_documents": sorted(docs[TRAIN] & docs[VAL]),
        "per_class": {c: {s: have[s].get(c, 0) for s in SPLITS} for c in totals},
        "totals": dict(totals),
        # Classes in fewer than two documents cannot reach both sides however
        # the groups are dealt. Surfaced so a 0 in the val column reads as "the
        # corpus has no second source" rather than as a bug in this function.
        "single_group_classes": sorted(c for c in totals if n_groups_with[c] < 2),
        "n_groups": len(groups),
    }
