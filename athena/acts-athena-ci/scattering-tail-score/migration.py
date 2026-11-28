"""Check both directions across 1 GeV using existing full truth-link exports."""

from pathlib import Path
import json
import sys
import numpy as np
from analyze import load, values

root = Path(sys.argv[1])
plan = json.loads((root / "training.json").read_text())["choices"]["0.995"]["groups"]
pt = json.loads((root / "pt-working-points.json").read_text())["points"]
why = json.loads((root / "why.json").read_text())
output = {}
for family, c in plan.items():
    path = root / "validation" / c["variant"]
    d = load(path)
    with np.load(path / "extras.npz") as f:
        low = f["P"]
        extra = f["R"]
    r = d["R"]
    assert np.array_equal(
        r[["run", "event", "index"]], extra[["run", "event", "index"]]
    )
    ids = np.empty(len(r), dtype=[("run", "u8"), ("event", "u8"), ("id", "u8")])
    for key in ["run", "event"]:
        ids[key] = extra[key]
    ids["id"] = extra["truth_id"]
    mask = (r["prob"] > 0.5) & (values(r, c["metric"]) <= c["cut"]) & (r["pt"] >= 1)
    up = len(
        np.intersect1d(
            np.unique(ids[mask]), low[["run", "event", "id"]], assume_unique=True
        )
    )
    high_all = pt["truth>1,reco>=0"]["counts"][family]["matched"]
    high_above = pt["truth>1,reco>=1"]["counts"][family]["matched"]
    output[family] = dict(
        truth_0p5_to_1_matched=why["low_pt"]["selected"][family]["matched"],
        truth_0p5_to_1_reco_ge_1=up,
        truth_gt_1_matched=high_all,
        truth_gt_1_reco_ge_1=high_above,
        truth_gt_1_reco_lt_1=high_all - high_above,
    )
(root / "migration.json").write_text(json.dumps(output, indent=2) + "\n")
print(json.dumps(output, indent=2))
