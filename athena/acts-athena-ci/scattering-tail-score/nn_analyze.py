#!/usr/bin/env python3
"""Reuse frozen-study definitions; match NN targets to the raw training reference."""
import argparse
import json
from pathlib import Path
import sys
import numpy as np
import analyze as original
from analyze import load, check_same, selection, threshold


def counts(data, metric, cut):
    r = selection(data, metric, cut)
    matches = r[(r["prob"] > 0.5) & (r["id"] != 0)]
    unique = np.unique(matches[["run", "event", "id"]])
    accepted = r[np.abs(r["eta"]) < 4]
    fake = (~np.isfinite(accepted["prob"])) | (accepted["prob"] < 0.5)
    return dict(
        events=len(data["E"]),
        truth=len(data["P"]),
        matched=len(unique),
        tracks=len(accepted),
        fakes=int(fake.sum()),
        efficiency=len(unique) / len(data["P"]),
        fake_rate=int(fake.sum()) / len(accepted),
        duplicates=len(matches) - len(unique),
    )


def tune():
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=["tune"])
    p.add_argument("directory", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--reference-plan", type=Path, required=True)
    a = p.parse_args()
    raw = json.loads(a.reference_plan.read_text())
    data = {
        d.name: load(d)
        for d in sorted(a.directory.iterdir())
        if (d / "rows.tsv").exists()
    }
    check_same(data)
    events = [
        list(map(int, (e["run"], e["event"]))) for e in next(iter(data.values()))["E"]
    ]
    assert events == raw["events"]
    report = dict(
        reference="original raw tail5",
        reference_matches=raw["reference_matches"],
        events=events,
        inclusive={n: counts(d, "none", 0) for n, d in data.items()},
        choices={},
    )
    for retention, point in raw["choices"].items():
        target = point["target"]
        groups = {}
        for family in ["core", "previous", "new"]:
            candidates = []
            for name, d in data.items():
                if name.startswith("core") != (family == "core"):
                    continue
                for metric in (
                    ["score/dim"] if family == "new" else ["chi2", "chi2/dim"]
                ):
                    cut = threshold(d, metric, target)
                    if cut is not None:
                        candidates.append(
                            dict(
                                variant=name,
                                metric=metric,
                                cut=cut,
                                training=counts(d, metric, cut),
                            )
                        )
            if candidates:
                groups[family] = min(
                    candidates,
                    key=lambda c: (
                        c["training"]["fakes"],
                        c["training"]["matched"] - target,
                        c["training"]["tracks"],
                    ),
                )
        report["choices"][retention] = dict(target=target, groups=groups)
    a.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps(report, indent=2))


def reuse_last_evaluation_choice():
    """Avoid repeated sorting of the same immutable selection; keep only one."""
    select_impl, best_impl = original.selection, original.best
    selected_key = selected = ranked_input = ranked = None

    def select(data, metric, cut):
        nonlocal selected_key, selected
        key = (id(data), metric, cut)
        if key != selected_key:
            selected = select_impl(data, metric, cut)
            selected_key = key
        return selected

    def best(rows):
        nonlocal ranked_input, ranked
        if rows is not ranked_input:
            ranked = best_impl(rows)
            ranked_input = rows
        return ranked

    original.selection, original.best = select, best


if __name__ == "__main__":
    if sys.argv[1] == "tune":
        tune()
    else:
        original.counts = counts
        reuse_last_evaluation_choice()
        original.main()
