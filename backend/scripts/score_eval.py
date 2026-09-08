#!/usr/bin/env python
"""Score reconstructions against the truths made by make_eval_set.py.

    PYTHONPATH=. python scripts/score_eval.py content/eval/set1

Reads NNN.pred.json next to each NNN.truth.json. A missing prediction is
counted as a failure rather than skipped -- an agent that gives up on the hard
drawings should not thereby score well on the easy ones.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.plugins.agent.compare import aggregate, compare_systems, identifiability

EMPTY = {"nodes": [], "members": [], "loads": []}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--report", type=Path, help="write the full result as JSON")
    parser.add_argument("--quiet", action="store_true", help="summary only")
    args = parser.parse_args()

    truths = sorted(args.directory.glob("*.truth.json"))
    if not truths:
        print(f"no *.truth.json in {args.directory}", file=sys.stderr)
        return 1

    results, per_sample, missing = [], [], []
    for truth_path in truths:
        name = truth_path.name.removesuffix(".truth.json")
        pred_path = truth_path.with_name(f"{name}.pred.json")

        if pred_path.exists():
            prediction = json.loads(pred_path.read_text(encoding="utf-8"))
            # Accept either the bare system or an object wrapping one.
            prediction = prediction.get("system", prediction)
        else:
            prediction = EMPTY
            missing.append(name)

        truth = json.loads(truth_path.read_text(encoding="utf-8"))
        result = compare_systems(truth, prediction)
        result["identifiability"] = identifiability(truth)
        results.append(result)
        per_sample.append({"id": name, "missing_prediction": name in missing, **result})

        if not args.quiet:
            flag = "OK " if result["fully_correct"] else ("~  " if result["topology_exact"] else "X  ")
            print(f"{flag}{name}  nodes {result['nodes']['f1']:.2f}  "
                  f"members {result['members']['f1']:.2f}  "
                  f"supports {_fmt(result['supports']['accuracy'])}  "
                  f"releases {_fmt(result['releases']['accuracy'])}  "
                  f"loads {result['loads']['f1']:.2f}")
            hidden = result["identifiability"]["unobservable"]
            if hidden:
                print(f"      ! {len(hidden)} node(s) not visible in the drawing: "
                      f"{', '.join(hidden)}")
            for note in result["notes"][:4]:
                print(f"      - {note}")

    summary = aggregate(results)
    summary["missing_predictions"] = len(missing)

    # The ceiling: a system whose picture hides a node cannot be reconstructed
    # exactly by anyone, so the score above has to be read against this.
    ceilings = [r["identifiability"] for r in results]
    summary["hidden_nodes_total"] = sum(len(c["unobservable"]) for c in ceilings)
    summary["samples_fully_recoverable"] = sum(1 for c in ceilings if c["fully_recoverable"])
    summary["ceiling_fully_correct_rate"] = round(
        summary["samples_fully_recoverable"] / len(ceilings), 4)

    print("\n" + "=" * 60)
    for key, value in summary.items():
        print(f"  {key:24} {value}")

    if args.report:
        args.report.write_text(
            json.dumps({"summary": summary, "samples": per_sample}, indent=2),
            encoding="utf-8")
        print(f"\nfull report -> {args.report}")
    return 0


def _fmt(value) -> str:
    return " -- " if value is None else f"{value:.2f}"


if __name__ == "__main__":
    raise SystemExit(main())
