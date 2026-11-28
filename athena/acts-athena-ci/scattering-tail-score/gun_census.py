"""Freeze earlier raw-cluster delta-like tags, independent of new reconstruction."""

import hashlib
import json
from pathlib import Path
import sys
import numpy as np

A = Path("/home/astefl/source/acts/acts-athena-ci")
sys.path.insert(0, "/home/astefl/scripts/athena/acts-athena-ci/nn-postcalibration")
from paired import load_k

R = A / "run/nn-postcalibration"
truth = {}
tagged = set()
sources = {}
for group in range(5):
    outcomes = R / f"gun-outcomes/mu10/force7/{group}.txt"
    for line in outcomes.read_text().splitlines():
        _, run, event, identity, _ = line.split()
        key = (group, int(run), int(event))
        assert key not in truth
        truth[key] = int(identity)
    path = R / f"single-force/mu10/base7/{group}/dump.txt"
    sources[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    for c in load_k(str(path)):
        if c["typ"] != 1 or not c["tok"] or not c["cells"]:
            continue
        sx, sy = np.sqrt(c["cxx"]), np.sqrt(c["cyy"])
        if (
            max(abs((c["lx"] - c["tru"][0]) / sx), abs((c["ly"] - c["tru"][1]) / sy))
            <= 5
        ):
            continue
        shift = c["lx"] - np.mean([cell[0] for cell in c["cells"]])
        px, py = np.sqrt(12) * sx, np.sqrt(12) * sy
        if any(
            abs(cell[0] + shift - c["tru"][0]) < 0.75 * px + 0.03
            and abs(cell[1] - c["tru"][1]) < 0.75 * py + 0.03
            for cell in c["cells"]
        ):
            tagged.add((group, 350000, c["ev"]))
assert len(truth) == 5000 and len(tagged) == 320 and tagged <= truth.keys()
result = dict(
    method="Existing raw residual >5 sigma plus cell-proximity primary-cluster proxy; not an exact delta-ray truth label.",
    source_sha256=sources,
    particles=[
        dict(group=g, run=r, event=e, id=i, delta_like=(g, r, e) in tagged)
        for (g, r, e), i in sorted(truth.items())
    ],
)
(A / "run/scattering-tail-score/gun/cohort.json").write_text(
    json.dumps(result, indent=2) + "\n"
)
print("Frozen 5000 physical truth identities; 320 delta-like tags", flush=True)
