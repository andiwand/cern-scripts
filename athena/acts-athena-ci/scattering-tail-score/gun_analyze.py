"""Compare fixed delta-like cohorts and tight-gate recoveries in existing muon RDOs."""

import json
from pathlib import Path
import sys
import numpy as np
from analyze import load, best, keys
from nn_analyze import counts

root = Path(sys.argv[1])
cohort = json.loads((root / "cohort.json").read_text())
particles = cohort["particles"]
truth = {(p["group"], p["run"], p["event"], p["id"]) for p in particles}
tagged = {
    k
    for k, p in zip(
        [(p["group"], p["run"], p["event"], p["id"]) for p in particles], particles
    )
    if p["delta_like"]
}
assert len(truth) == 5000 and len(tagged) == 320
found = {}
totals = {}
track = {}
for variant in [
    "raw-core4",
    "raw-core7",
    "raw-tail4",
    "nn-core4",
    "nn-core7",
    "nn-tail4",
]:
    seen = set()
    matched = {}
    total = dict(tracks=0, fakes=0)
    for group in range(5):
        directory = root / variant / str(group)
        assert (directory / "exit-code").read_text().strip() == "0"
        d = load(directory)
        assert len(d["E"]) == 1000
        seen.update((group, *key) for key in keys(d["P"]))
        matched.update({(group, *k): v for k, v in best(d["R"]).items()})
        c = counts(d, "none", 0)
        for field in total:
            total[field] += c[field]
    assert seen == truth, variant
    found[variant] = set(matched)
    track[variant] = matched
    totals[variant] = total


def compare(a, b, cohort):
    gained = len((found[b] - found[a]) & cohort)
    lost = len((found[a] - found[b]) & cohort)
    n = len(cohort)
    return dict(
        gained=gained,
        lost=lost,
        efficiency_change_pp=100 * (gained - lost) / n,
        efficiency_se_pp=100
        * np.sqrt((gained + lost - (gained - lost) ** 2 / n) / (n * (n - 1))),
    )


out = dict(
    method=cohort["method"],
    events=5000,
    final_quality_cut="none; isolate measurement gate/calibration",
    totals=totals,
    cohorts={},
)
for label, subset in [
    ("all", truth),
    ("delta_like", tagged),
    ("not_tagged", truth - tagged),
]:
    out["cohorts"][label] = dict(
        truth=len(subset),
        matched={v: len(f & subset) for v, f in found.items()},
        paired={},
    )
    for a, b in [
        ("raw-core7", "raw-core4"),
        ("nn-core7", "nn-core4"),
        ("raw-core4", "nn-core4"),
        ("raw-core7", "nn-core7"),
        ("raw-core4", "raw-tail4"),
        ("nn-core4", "nn-tail4"),
    ]:
        out["cohorts"][label]["paired"][b + " minus " + a] = compare(a, b, subset)
    lost = (found["raw-core7"] - found["raw-core4"]) & subset
    out["cohorts"][label]["raw_tight_gate_losses"] = dict(
        n=len(lost),
        recovered_by_nn_core4=len(lost & found["nn-core4"]),
        recovered_by_nn_tail4=len(lost & found["nn-tail4"]),
    )
(root / "results.json").write_text(json.dumps(out, indent=2) + "\n")
print(json.dumps(out, indent=2))
