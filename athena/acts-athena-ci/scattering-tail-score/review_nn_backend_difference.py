"""Resolve the one observed 200-event core7 backend difference explicitly."""

import json
from pathlib import Path
import sys
import numpy as np
from analyze import load
from nn_analyze import counts

root = Path(sys.argv[1])
a = load(root / "nn/training/core7")
b = load(root / "nn-native/training/core7")
assert np.array_equal(a["P"], b["P"])
ca, cb = counts(a, "none", 0), counts(b, "none", 0)
for field in ["events", "truth", "matched", "fakes", "duplicates"]:
    assert ca[field] == cb[field], (field, ca, cb)
assert ca["tracks"] == cb["tracks"] + 1
r = a["R"].copy()
s = b["R"]
removed = (r["run"] == 350200) & (r["event"] == 51) & (r["index"] == 1187)
assert removed.sum() == 1
record = r[removed][0]
assert record["id"] == 0 and record["prob"] > 0.5
r = r[~removed]
shift = (r["run"] == 350200) & (r["event"] == 51) & (r["index"] > 1187)
r["index"][shift] -= 1
for name in ["run", "event", "index", "id", "prob", "dim", "ndf"]:
    assert np.array_equal(r[name], s[name], equal_nan=True), name
assert len(r) == len(s)
columns = {}
for name in r.dtype.names:
    if name in ["run", "event", "index", "id"]:
        continue
    x, y = r[name], s[name]
    assert np.array_equal(np.isfinite(x), np.isfinite(y)), name
    finite = np.isfinite(x)
    delta = np.abs(x[finite] - y[finite])
    columns[name] = dict(
        max_absolute=float(delta.max(initial=0)),
        p99_absolute=float(np.quantile(delta, 0.99)),
    )
    if name == "pt":
        columns[name]["max_relative"] = float((delta / np.abs(x[finite])).max())
# Verify all full truth links and hit summaries, accounting only for that track.
rows = []
for backend in ["nn", "nn-native"]:
    d = {}
    for line in (root / backend / "training/core7/backend-extras.tsv").open():
        v = line.split()
        if v[0] == "R" and backend == "nn" and v[1:3] == ["350200", "51"]:
            if int(v[3]) == 1187:
                continue
            if int(v[3]) > 1187:
                v[3] = str(int(v[3]) - 1)
        key = tuple(v[:4])
        assert key not in d
        d[key] = v[4:]
    rows.append(d)
assert rows[0] == rows[1]
out = dict(
    checks="After explicitly removing one unlinked high-probability track and accounting for its index shift, all exported associations/probabilities, dimensions, full truth links and eight hit summaries agree. Efficiency/fake counts unchanged; not bit-identical.",
    onnx=ca,
    native=cb,
    removed_track={
        k: int(record[k]) if k in ["run", "event", "index", "id"] else float(record[k])
        for k in ["run", "event", "index", "id", "prob", "pt", "eta", "chi2", "dim"]
    },
    columns=columns,
)
(root / "nn-native/backend-review-core7.json").write_text(
    json.dumps(out, indent=2) + "\n"
)
print(json.dumps(out, indent=2))
