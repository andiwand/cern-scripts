#!/usr/bin/env python3
"""Binned rates and prompt resolutions at the predeclared 99.5% point."""
import argparse
import json
from pathlib import Path
import numpy as np
from analyze import load, selection, best, keys

p = argparse.ArgumentParser()
p.add_argument("directory", type=Path)
p.add_argument("plan", type=Path)
p.add_argument("output", type=Path)
a = p.parse_args()
choices = json.loads(a.plan.read_text())["choices"]["0.995"]["groups"]
data = {c["variant"]: load(a.directory / c["variant"]) for c in choices.values()}
selected = {
    f: selection(data[c["variant"]], c["metric"], c["cut"]) for f, c in choices.items()
}
matched = {f: best(r) for f, r in selected.items()}
common = set.intersection(*(set(m) for m in matched.values()))
output = {"retention": 0.995, "common_truth": len(common), "groups": {}}
for family, c in choices.items():
    truth = data[c["variant"]]["P"]
    r = selected[family]
    m = matched[family]
    found = np.array([k in m for k in keys(truth)])
    fake = (~np.isfinite(r["prob"])) | (r["prob"] < 0.5)
    result = {"efficiency": {}, "fake_rate": {}, "resolution": {}}
    for field, edges, absolute in [
        ("eta", [0, 1, 2, 2.5, 3, 4], True),
        ("pt", [1, 2, 5, 10, 1000], False),
        ("hs", [-0.5, 0.5, 1.5], False),
    ]:
        v = np.abs(truth[field]) if absolute else truth[field]
        result["efficiency"][field] = {"edges": edges, "total": [], "passed": []}
        for lo, hi in zip(edges[:-1], edges[1:]):
            mask = (v >= lo) & (v < hi)
            result["efficiency"][field]["total"].append(int(mask.sum()))
            result["efficiency"][field]["passed"].append(int((mask & found).sum()))
    for field, edges, absolute in [
        ("eta", [0, 1, 2, 2.5, 3, 4], True),
        ("pt", [0, 1, 2, 5, 10, 1000], False),
    ]:
        v = np.abs(r[field]) if absolute else r[field]
        result["fake_rate"][field] = {"edges": edges, "total": [], "passed": []}
        for lo, hi in zip(edges[:-1], edges[1:]):
            mask = (v >= lo) & (v < hi) & (np.abs(r["eta"]) < 4)
            result["fake_rate"][field]["total"].append(int(mask.sum()))
            result["fake_rate"][field]["passed"].append(int((mask & fake).sum()))
    for parameter in ["d0res", "z0res", "qptres"]:
        bins = []
        edges = [1, 2, 5, 10, 1000]
        for lo, hi in zip(edges[:-1], edges[1:]):
            v = np.array(
                [
                    m[k][parameter]
                    for k, t in zip(keys(truth), truth)
                    if k in common and lo <= t["pt"] < hi
                ]
            )
            v = v[np.isfinite(v)]
            if len(v) >= 30:
                q = np.quantile(v, [0.025, 0.15865, 0.5, 0.84135, 0.975])
                bins.append(
                    dict(
                        n=len(v),
                        median=float(q[2]),
                        width68=float((q[3] - q[1]) / 2),
                        width95=float((q[4] - q[0]) / 2),
                    )
                )
            else:
                bins.append(dict(n=len(v), median=None, width68=None, width95=None))
        result["resolution"][parameter] = {"edges": edges, "bins": bins}
    output["groups"][family] = result

a.output.write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")
