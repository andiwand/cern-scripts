import argparse

p = argparse.ArgumentParser()
p.add_argument("--work", type=__import__("pathlib").Path, required=True)
a = p.parse_args()
from pathlib import Path
import csv, math, json, gzip, hashlib
from collections import defaultdict

w = a.work
bins = [0.1, 0.2, 1.022, 5, 20, 100, 1000]


def sigma(e):
    x = e / 0.51099895
    if x < 0.001:
        return 4 / 3 * (1 - 2 * x + x * x * (5.2 - 13.3 * x))
    l = math.log1p(2 * x)
    d = 1 + 2 * x
    return (1 + x) / x**2 * (2 * (1 + x) / d - l / x) + l / (2 * x) - (1 + 3 * x) / d**2


c = defaultdict(lambda: defaultdict(float))
for row in csv.reader((w / "compton-columns.csv").open()):
    e, d, mm, accepted, recoil, after = map(float, row[5:])
    b = str(next((i for i, x in enumerate(bins) if e < x), len(bins)))
    v = c[b]
    v["columns"] += 1
    v["expected_first"] += -math.expm1(-d)
    v["observed_first"] += accepted
    v["depth_sum"] += d
    v["depth_max"] = max(v["depth_max"], d)
    if accepted:
        rem = (
            0.5 + d / 12
            if d < 0.001
            else 1 - 1 / d + (1 / math.expm1(d) if d < 700 else 0)
        )
        v["remaining_depth_at_exit_energy"] += d * rem * sigma(after) / sigma(e)
        v["second_scatter_probability_upper"] += -math.expm1(
            -d * rem * sigma(after) / sigma(e)
        )
        v["recoil_above_40keV"] += recoil >= 0.04
out = {
    "edges_MeV": bins,
    "event": 0,
    "bins": dict(c),
    "totals": {
        key: sum(v.get(key, 0) for v in c.values())
        for key in [
            "columns",
            "expected_first",
            "observed_first",
            "remaining_depth_at_exit_energy",
            "second_scatter_probability_upper",
            "recoil_above_40keV",
        ]
    },
}
(w / "columns.json").write_text(json.dumps(out, indent=2))
print(json.dumps(out, indent=2))
old = (
    Path.home()
    / "cern/scripts/acts/fatras-realism/fatras-radiative-secondaries/results/2026-10-16/current"
)
for f in (w / "trace-current").glob("event*.csv"):
    assert (
        hashlib.sha256(f.read_bytes()).digest()
        == hashlib.sha256(
            gzip.decompress((old / (f.name + ".gz")).read_bytes())
        ).digest()
    ), f
print("Instrumented native run reproduces both reference event CSVs exactly")
