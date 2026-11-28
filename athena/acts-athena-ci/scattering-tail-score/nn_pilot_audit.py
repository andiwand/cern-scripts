"""Check exported scores and unchanged truth before the all-charge NN scan."""

import json
from pathlib import Path
import sys
import numpy as np
from analyze import load, check_same
from nn_analyze import counts

p = Path(sys.argv[1])
data = {v: load(p / "nn-pilot" / v) for v in ["core7", "tail5"]}
check_same(data)
out = {}
for v, d in data.items():
    assert (p / "nn-pilot" / v / "exit-code").read_text().strip() == "0"
    assert len(d["E"]) == 5
    out[v] = counts(d, "none", 0)
r = data["core7"]["R"]
assert np.allclose(r["score"], r["chi2"], rtol=1e-5, atol=1e-4)
out["gaussian_score_max_difference"] = float(abs(r["score"] - r["chi2"]).max())
(p / "nn-pilot/audit.json").write_text(json.dumps(out, indent=2) + "\n")
print(json.dumps(out, indent=2), flush=True)
