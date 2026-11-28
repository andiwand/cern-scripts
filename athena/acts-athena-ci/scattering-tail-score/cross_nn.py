"""Paired raw/NN comparison at the same frozen training match target."""

import json
from pathlib import Path
import sys
import numpy as np
from analyze import load, check_same, selection, best, event_counts
from nn_analyze import counts

root = Path(sys.argv[1])
nn_directory = root / (sys.argv[2] if len(sys.argv) > 2 else "nn-native")
retention = sys.argv[3] if len(sys.argv) > 3 else "0.995"
choices = {}
data = {}
for prefix, directory in [("raw", root), ("nn", nn_directory)]:
    plan = json.loads((directory / "training.json").read_text())
    if prefix == "raw":
        target = plan["choices"][retention]["target"]
    assert plan["choices"][retention]["target"] == target
    for family, c in plan["choices"][retention]["groups"].items():
        label = prefix + "-" + family
        choices[label] = c
        path = directory / "validation" / c["variant"]
        if path not in data:
            data[path] = load(path)
        choices[label] = dict(c, path=path)
check_same(data)
reference_events = next(iter(data.values()))["E"][["run", "event", "particles"]]
assert all(
    np.array_equal(d["E"][["run", "event", "particles"]], reference_events)
    for d in data.values()
)
matched = {}
events = {}
result = {}
score_profiles = {}
for label, c in choices.items():
    d = data[c["path"]]
    r = selection(d, c["metric"], c["cut"])
    matched[label] = best(r)
    events[label] = event_counts(d, c["metric"], c["cut"])
    result[label] = counts(d, c["metric"], c["cut"])
    totals = np.sum(list(events[label].values()), axis=0)
    assert tuple(totals) == tuple(
        result[label][k] for k in ["matched", "fakes", "tracks"]
    ), label
    score_profiles[label] = {}
    for population, mask in [
        ("selected_truth_tracks", (r["prob"] > 0.5) & (r["id"] != 0)),
        (
            "fake_tracks",
            (np.abs(r["eta"]) < 4) & ((r["prob"] < 0.5) | ~np.isfinite(r["prob"])),
        ),
    ]:
        rows = r[mask]
        score_profiles[label][population] = dict(
            tracks=len(rows),
            mean_tail_weight=float(rows["weight"].mean()),
            median_tail_weight=float(np.median(rows["weight"])),
            mean_score_minus_chi2_per_dimension=float(
                np.mean((rows["score"] - rows["chi2"]) / rows["dim"])
            ),
        )
common = set.intersection(*(set(m) for m in matched.values()))
profiles = {}
for label, m in matched.items():
    profiles[label] = {}
    for field in ["d0res", "z0res", "qptres", "weight"]:
        v = np.array([m[k][field] for k in common])
        v = v[np.isfinite(v)]
        q = np.quantile(v, [0.025, 0.15865, 0.5, 0.84135, 0.975])
        profiles[label][field] = dict(
            n=len(v),
            mean=float(v.mean()),
            median=float(q[2]),
            width68=float((q[3] - q[1]) / 2),
            width95=float((q[4] - q[0]) / 2),
        )
first = next(iter(data.values()))
order = [tuple(map(int, (e["run"], e["event"]))) for e in first["E"]]
truth = first["E"]["particles"].astype(float)
N = len(order)
paired = {}
for a, b in [
    ("raw-core", "nn-core"),
    ("raw-core", "nn-new"),
    ("raw-new", "nn-new"),
    ("nn-core", "nn-new"),
]:
    ref = np.array([events[a][e] for e in order], float)
    new = np.array([events[b][e] for e in order], float)
    delta = (new[:, 0].sum() - ref[:, 0].sum()) / truth.sum()
    ei = (new[:, 0] - ref[:, 0] - delta * truth) / truth.sum()
    rf = ref[:, 1].sum() / ref[:, 2].sum()
    nf = new[:, 1].sum() / new[:, 2].sum()
    fi = (new[:, 1] - nf * new[:, 2]) / new[:, 2].sum() - (
        ref[:, 1] - rf * ref[:, 2]
    ) / ref[:, 2].sum()
    paired[b + " minus " + a] = dict(
        efficiency_change_pp=100 * delta,
        efficiency_se_pp=100 * float(np.sqrt(N / (N - 1) * sum(ei**2))),
        fake_rate_change_pp=100 * (nf - rf),
        fake_rate_se_pp=100 * float(np.sqrt(N / (N - 1) * sum(fi**2))),
        gained=len(set(matched[b]) - set(matched[a])),
        lost=len(set(matched[a]) - set(matched[b])),
    )
out = dict(
    retention=retention,
    target=target,
    events=N,
    counts=result,
    paired=paired,
    common_truth=len(common),
    common_profiles=profiles,
    score_profiles=score_profiles,
)
(
    nn_directory
    / (
        "cross-calibration"
        + ("" if retention == "0.995" else "-" + retention)
        + ".json"
    )
).write_text(json.dumps(out, indent=2) + "\n")
print(json.dumps(out, indent=2))
