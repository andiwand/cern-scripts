#!/usr/bin/env python3
"""Describe frozen-point gains/losses; no tuning or reconstruction changes."""
import argparse
from collections import Counter
import json
from pathlib import Path
import numpy as np
from analyze import load, selection, best, keys, values, counts

PD = [("run", "u8"), ("event", "u8"), ("id", "u8"), ("pt", "f8"), ("eta", "f8")]
RD = [
    ("run", "u8"),
    ("event", "u8"),
    ("index", "u8"),
    ("truth_id", "u8"),
    ("truth_pt", "f8"),
    ("truth_eta", "f8"),
] + [
    (n, "i4")
    for n in [
        "pixel_hits",
        "strip_hits",
        "pixel_holes",
        "strip_holes",
        "pixel_outliers",
        "strip_outliers",
        "pixel_shared",
        "strip_shared",
    ]
]


def extras(path):
    cache = path / "extras.npz"
    if cache.exists():
        with np.load(cache) as f:
            return {k: f[k] for k in f.files}
    rows = {"P": [], "R": []}
    with (path / "extras.tsv").open() as f:
        for line in f:
            c, *v = line.split()
            rows[c].append(tuple(v))
    d = {k: np.array(rows[k], dtype=dt) for k, dt in [("P", PD), ("R", RD)]}
    for k in d:
        d[k].sort(order=["run", "event", "id" if k == "P" else "index"])
    assert len(set(keys(d["P"]))) == len(d["P"])
    np.savez_compressed(cache, **d)
    return d


def describe(v):
    v = np.asarray(v)
    v = v[np.isfinite(v)]
    return (
        dict(
            n=len(v),
            quantiles=np.quantile(v, [0.1, 0.5, 0.9, 0.99]).tolist(),
            mean=float(v.mean()),
        )
        if len(v)
        else dict(n=0)
    )


def features(r, e, mask):
    features = {
        "pt": r["pt"],
        "abs_eta": np.abs(r["eta"]),
        "dimension": r["dim"],
        "T_per_dim": r["score"] / r["dim"],
        "chi2_per_dim": r["chi2"] / r["dim"],
        "excess_per_dim": (r["score"] - r["chi2"]) / r["dim"],
        "sum_weight": r["weight"],
        "weight_per_dim": r["weight"] / r["dim"],
    }
    for name in ["hits", "holes", "outliers", "shared"]:
        x, y = e["pixel_" + name], e["strip_" + name]
        features[name] = np.where((x >= 0) & (y >= 0), x + y, np.nan)
    out = {name: describe(v[mask]) for name, v in features.items()}
    for name in ["holes", "outliers", "shared"]:
        v = features[name][mask]
        v = v[np.isfinite(v)]
        if len(v):
            out[name]["fraction_positive"] = float(np.mean(v > 0))
    return out


def profile(p, ids):
    use = np.array([k in ids for k in keys(p)])
    return dict(
        n=int(use.sum()),
        pt=describe(p["pt"][use]),
        abs_eta=describe(np.abs(p["eta"][use])),
        hs_fraction=float(p["hs"][use].mean()) if use.any() else None,
    )


p = argparse.ArgumentParser()
p.add_argument("run", type=Path)
a = p.parse_args()
plan = json.loads((a.run / "training.json").read_text())["choices"]["0.995"]["groups"]
assert plan["previous"]["variant"] == plan["new"]["variant"]
d = {v: load(a.run / "validation" / v) for v in {c["variant"] for c in plan.values()}}
x = {v: extras(a.run / "validation" / v) for v in d}
for v in d:
    assert np.array_equal(
        d[v]["R"][["run", "event", "index"]], x[v]["R"][["run", "event", "index"]]
    ), v
m = {
    f: set(best(selection(d[c["variant"]], c["metric"], c["cut"])))
    for f, c in plan.items()
}
truth = next(iter(d.values()))["P"]
out = {
    "point": 0.995,
    "frozen_choices": plan,
    "truth_changes": {},
    "track_profiles": {},
    "inclusive": {v: counts(q, "none", 0) for v, q in d.items()},
}
for ref in ["core", "previous"]:
    out["truth_changes"]["new-" + ref] = {
        "gained": profile(truth, m["new"] - m[ref]),
        "lost": profile(truth, m[ref] - m["new"]),
        "common": len(m["new"] & m[ref]),
    }
for f, c in plan.items():
    r = d[c["variant"]]["R"]
    e = x[c["variant"]]["R"]
    cut = values(r, c["metric"]) <= c["cut"]
    eta = np.abs(r["eta"]) < 4
    fake = (~np.isfinite(r["prob"])) | (r["prob"] < 0.5)
    real = r["prob"] > 0.5
    out["track_profiles"][f] = {
        label: features(r, e, mask)
        for label, mask in [
            ("fakes_before", eta & fake),
            ("fakes_after", eta & fake & cut),
            ("nonfakes_after", eta & real & cut),
            ("selected_truth_after", eta & real & (r["id"] != 0) & cut),
        ]
    }
    out["track_profiles"][f]["fake_low_reco_pt_fraction"] = float(
        np.mean(r["pt"][eta & fake & cut] < 1)
    )

v = plan["new"]["variant"]
r = d[v]["R"]
e = x[v]["R"]
prev = values(r, plan["previous"]["metric"]) <= plan["previous"]["cut"]
new = values(r, plan["new"]["metric"]) <= plan["new"]["cut"]
fake = (~np.isfinite(r["prob"])) | (r["prob"] < 0.5)
eta = np.abs(r["eta"]) < 4
out["tail_cut_changes"] = {
    name: dict(
        tracks=int(mask.sum()),
        fakes=int((mask & fake).sum()),
        features=features(r, e, mask & fake),
    )
    for name, mask in [("removed", eta & prev & ~new), ("added", eta & new & ~prev)]
}

low = next(iter(x.values()))["P"]
comparable = all(np.array_equal(low, q["P"]) for q in x.values())
out["low_pt"] = {
    "comparable_truth": comparable,
    "truth_counts": {v: len(q["P"]) for v, q in x.items()},
}
if comparable:
    eligible = set(keys(low))
    found = {}
    for f, c in plan.items():
        r = d[c["variant"]]["R"]
        e = x[c["variant"]]["R"]
        mask = (values(r, c["metric"]) <= c["cut"]) & (r["prob"] > 0.5)
        found[f] = {
            (int(z["run"]), int(z["event"]), int(z["truth_id"])) for z in e[mask]
        } & eligible
    out["low_pt"]["selected"] = {
        f: dict(matched=len(s), truth=len(eligible), efficiency=len(s) / len(eligible))
        for f, s in found.items()
    }
    raw = {}
    for variant, q in d.items():
        e = x[variant]["R"]
        good = q["R"]["prob"] > 0.5
        ids = {
            (int(z["run"]), int(z["event"]), int(z["truth_id"])) for z in e[good]
        } & eligible
        raw[variant] = dict(
            matched=len(ids), truth=len(eligible), efficiency=len(ids) / len(eligible)
        )
    out["low_pt"]["inclusive"] = raw
    events = [
        tuple(map(int, (e["run"], e["event"]))) for e in next(iter(d.values()))["E"]
    ]
    nt = Counter(k[:2] for k in eligible)
    truth_counts = np.array([nt[e] for e in events], dtype=float)
    for ref in ["core", "previous"]:
        nc = Counter(k[:2] for k in found["new"])
        rc = Counter(k[:2] for k in found[ref])
        delta = np.array([nc[e] - rc[e] for e in events], dtype=float)
        change = delta.sum() / truth_counts.sum()
        influence = (delta - change * truth_counts) / truth_counts.sum()
        se = float(np.sqrt(len(events) / (len(events) - 1) * (influence**2).sum()))
        out["low_pt"]["new-" + ref] = dict(
            efficiency_change_pp=100 * change,
            efficiency_se_pp=100 * se,
            gained=len(found["new"] - found[ref]),
            lost=len(found[ref] - found["new"]),
        )
(a.run / "why.json").write_text(json.dumps(out, indent=2, allow_nan=False) + "\n")
print(json.dumps({k: out[k] for k in ["truth_changes", "low_pt"]}, indent=2))
