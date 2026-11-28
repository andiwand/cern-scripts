#!/usr/bin/env python3
"""Independent vectorized counter check at the predeclared validation point."""
from pathlib import Path
import json
import sys
import numpy as np
from analyze import load, values

p = Path(sys.argv[1])
choices = json.loads((p / "training.json").read_text())["choices"]["0.995"]["groups"]
data = {v: load(p / "validation" / v) for v in {c["variant"] for c in choices.values()}}
result = {}
for family, c in choices.items():
    d = data[c["variant"]]
    r = d["R"]
    passed = values(r, c["metric"]) <= c["cut"]
    eta = np.abs(r["eta"]) < 4
    matched = r[passed & (r["prob"] > 0.5) & (r["id"] != 0)][["run", "event", "id"]]
    nmatched = len(np.unique(matched))
    ntracks = int(np.count_nonzero(passed & eta))
    nfakes = int(
        np.count_nonzero(passed & eta & ((r["prob"] < 0.5) | ~np.isfinite(r["prob"])))
    )
    result[family] = dict(
        events=len(d["E"]),
        matched=nmatched,
        truth=len(d["P"]),
        tracks=ntracks,
        fakes=nfakes,
        efficiency=nmatched / len(d["P"]),
        fake_rate=nfakes / ntracks,
    )
if (p / "validation.json").exists():
    evaluated = json.loads((p / "validation.json").read_text())["points"]["0.995"][
        "groups"
    ]
    for family, independent in result.items():
        for key, value in independent.items():
            assert evaluated[family]["validation"][key] == value, (family, key)
(p / "main-point-check.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
