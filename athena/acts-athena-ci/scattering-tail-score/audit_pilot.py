#!/usr/bin/env python3
"""Require unchanged reconstruction and valid optional AOD scores (pilot.sh output).

usage: audit_pilot.py PILOT_DIR   compares every <variant>_on with <variant>_off; writes audit.json
"""
import json
from pathlib import Path
import sys
import numpy as np
from analyze import load

root = Path(sys.argv[1])
report = {}
for variant in sorted(p.name[:-3] for p in root.glob("*_on") if p.is_dir()):
    on, off = (load(root / (variant + "_" + state)) for state in ["on", "off"])
    assert np.array_equal(on["P"], off["P"]), variant
    assert np.array_equal(on["E"], off["E"]), variant
    for field in on["R"].dtype.names:
        if field in ["score", "dim", "weight", "logl"]:
            continue
        a, b = on["R"][field], off["R"][field]
        assert np.array_equal(a, b, equal_nan=True), (variant, field)
    r = on["R"]
    for field in ["score", "dim", "weight", "logl"]:
        assert np.isfinite(r[field]).all(), (variant, field)
    assert np.isnan(off["R"]["score"]).all()
    assert np.array_equal(r["dim"], r["ndf"])
    assert np.all(r["score"] >= 0) and np.all(r["dim"] > 0)
    assert np.all((r["weight"] >= 0) & (r["weight"] <= r["dim"]))
    if variant.startswith("core"):
        assert np.all(r["weight"] == 0)
    else:
        assert np.count_nonzero(r["weight"]) > 0
    report[variant] = dict(
        events=len(on["E"]),
        tracks=len(r),
        unchanged=True,
        dimensions_match=True,
        nonzero_tail_weights=int(np.count_nonzero(r["weight"])),
        score_per_dim_quantiles=np.quantile(
            r["score"] / r["dim"], [0, 0.5, 0.9, 0.99, 1]
        ).tolist(),
    )
(root / "audit.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
