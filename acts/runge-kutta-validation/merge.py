"""Merge the original runs with the corrected reruns.

    python3 merge.py RUN_DIR OUT_DIR

RUN_DIR/data holds the first pass, RUN_DIR/fix the reruns:
  - sympy jacobian rows (hom, jac) from fix/, because the first pass read the
    scaled q/p column of the sympy stepper
  - helix rows (inh, map, jac, prof, time) from fix/, which runs the
    helix stepper with the local rejection fix (helix-rejection-fix.diff)
  - all forward-backward rows from fix/fb-all.jsonl, because the first pass
    gave the actor a signed step and moved forward on the backward leg
The failure counts of the unpatched helix stepper go to helix-orig.json.
"""

import json
import sys
from collections import Counter
from pathlib import Path

run = Path(sys.argv[1])
out = Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)

REPLACE = {
    "sympy": {"hom", "jac"},
    "helix": {"inh", "map", "fb", "jac", "prof", "time"},
}
# Reference rows that the reruns repeat
REF_STUDIES = {"homfd", "jacfd", "inhref", "mapref"}


def rows(path):
    with path.open() as f:
        for line in f:
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


orig_helix = Counter()
merged = []
for path in sorted((run / "data").glob("*.jsonl")):
    for r in rows(path):
        st = r.get("stepper")
        if r["study"] == "fb":
            # The first pass moved forward on the backward leg
            if st == "helix":
                orig_helix[("fb", r.get("ok", True))] += 1
            continue
        if st in REPLACE and r["study"] in REPLACE[st]:
            if st == "helix":
                orig_helix[(r["study"], r.get("ok", True))] += 1
            continue
        merged.append(r)

for path in sorted((run / "fix").glob("*.jsonl")):
    for r in rows(path):
        if r["study"] == "fb":
            if path.name in ("fb.jsonl", "fb-all.jsonl"):
                merged.append(r)
            continue
        if r["study"] in REF_STUDIES and not r["study"].startswith("mapcap"):
            continue
        st = r.get("stepper")
        if r["study"] in ("mapcap", "mapcapref", "timecov"):
            merged.append(r)
        elif st in REPLACE and r["study"] in REPLACE[st]:
            merged.append(r)

with (out / "all.jsonl").open("w") as f:
    for r in merged:
        f.write(json.dumps(r) + "\n")

fails = {}
for (study, ok), n in orig_helix.items():
    fails.setdefault(study, {"ok": 0, "failed": 0})["ok" if ok else "failed"] += n
(out / "helix-orig.json").write_text(json.dumps(fails, indent=1))
print(len(merged), "rows;", "unpatched helix:", fails)
