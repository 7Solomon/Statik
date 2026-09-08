#!/usr/bin/env python
"""Generate (drawing, ground truth) pairs for measuring reconstruction.

    PYTHONPATH=. python scripts/make_eval_set.py --count 20 --out content/eval/set1

Writes NNN.png and NNN.truth.json per sample, plus a manifest. The pictures are
the input an agent is given; the truths are what it should have come back with.
Nothing here calls a model -- feeding the pictures to one is a separate step, so
this can be regenerated cheaply and scored repeatedly.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.plugins.agent.evalset import image_system_to_compact
from src.plugins.generator.image.renderer import render_structure_to_image
from src.plugins.generator.image.structure_generator import RandomStructureGenerator


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--out", type=Path, default=Path("content/eval/default"))
    parser.add_argument("--seed", type=int, default=0,
                        help="fixed by default so a run is reproducible")
    parser.add_argument("--width", type=int, default=900)
    parser.add_argument("--height", type=int, default=660)
    args = parser.parse_args()

    random.seed(args.seed)
    args.out.mkdir(parents=True, exist_ok=True)

    generator = RandomStructureGenerator(width=args.width, height=args.height)
    manifest = []

    for index in range(args.count):
        system = generator.generate()
        # style stays None: AnnotationRenderer randomises its text on purpose
        # (see plugins/agent/render.py), and invented annotation would be
        # measuring the wrong thing.
        image = render_structure_to_image(system, image_size=(args.width, args.height))
        truth = image_system_to_compact(system)

        name = f"{index:03d}"
        image.save(args.out / f"{name}.png")
        (args.out / f"{name}.truth.json").write_text(
            json.dumps(truth, indent=2), encoding="utf-8")

        manifest.append({
            "id": name,
            "image": f"{name}.png",
            "truth": f"{name}.truth.json",
            "nodes": len(truth["nodes"]),
            "members": len(truth["members"]),
            "loads": len(truth["loads"]),
            "supports": sorted({n["support"] for n in truth["nodes"] if n.get("support")}),
        })

    (args.out / "manifest.json").write_text(
        json.dumps({"seed": args.seed, "samples": manifest}, indent=2), encoding="utf-8")

    print(f"{len(manifest)} samples -> {args.out}")
    print(f"  nodes   {sum(m['nodes'] for m in manifest)}")
    print(f"  members {sum(m['members'] for m in manifest)}")
    print(f"  loads   {sum(m['loads'] for m in manifest)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
