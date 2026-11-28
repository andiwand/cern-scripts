"""Compare exported associations/counts; quantify native floating-point differences."""

import json
from pathlib import Path
import sys
import numpy as np
from analyze import load
from nn_analyze import counts

p, q, out = map(Path, sys.argv[1:])
a, b = load(p), load(q)
assert np.array_equal(a["P"], b["P"])
assert np.array_equal(a["E"], b["E"])
assert counts(a, "none", 0) == counts(b, "none", 0)
result = dict(events=len(a["E"]), counts=counts(a, "none", 0), columns={})
for name in a["R"].dtype.names:
    x, y = a["R"][name], b["R"][name]
    if name in ["run", "event", "index", "id", "prob", "dim", "ndf"]:
        assert np.array_equal(x, y, equal_nan=True), name
    else:
        assert np.array_equal(np.isfinite(x), np.isfinite(y)), name
        finite = np.isfinite(x)
        diff = np.abs(x[finite] - y[finite])
        result["columns"][name] = dict(
            max_absolute=float(diff.max(initial=0)),
            p99_absolute=float(np.quantile(diff, 0.99)),
        )
result["checks"] = (
    "Same truth, per-event track counts, track indices, selected-truth links/probabilities, measured dimensions; floating differences recorded, not required bit-identical."
)
out.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
