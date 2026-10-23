"""Verify reference, prototype, repeated-event and worker reproducibility."""

import argparse, gzip, hashlib, json
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--work", type=Path, required=True)
a = p.parse_args()


def hashes(root):
    files = list(root.glob("event*.csv*"))
    if not files:
        return json.loads((root / "csv-sha256.json").read_text())
    result = {}
    for f in files:
        with gzip.open(f, "rb") if f.suffix == ".gz" else f.open("rb") as stream:
            h = hashlib.sha256()
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                h.update(chunk)
        result[f.name.removesuffix(".gz")] = h.hexdigest()
    return result


w = a.work
s = Path.home() / "cern/scripts/acts"
checks = {}
for name in ["control", "current"]:
    ref = hashes(w / (name + "-0"))
    assert len(ref) == 6
    for i in [1, 2]:
        checks[name + " repeat " + str(i)] = hashes(w / f"{name}-{i}") == ref
checks["control matches accepted radiation reference"] = hashes(
    w / "control-0"
) == hashes(s / "fatras-radiative-secondaries/results/2026-10-16/current")
checks["production matches diagnostic column prototype"] = hashes(
    w / "current-0"
) == hashes(w / "birth-column-inclusive")
checks["standard one versus four workers"] = (
    hashes(w / "standard-1") == hashes(w / "standard-4")
    and len(hashes(w / "standard-1")) == 6
)
checks["fresh default G4 matches reference"] = hashes(w / "geant4-refreshed") == hashes(
    s / "fatras-soft-secondaries/results/2026-10-15/geant4"
)
if (w / "optimized-0").exists():
    for i in range(3):
        checks["optimized " + str(i) + " matches resolved reference"] = hashes(
            w / f"optimized-{i}"
        ) == hashes(w / "current-0")
    checks["optimized standard matches resolved reference"] = hashes(
        w / "optimized-standard-1"
    ) == hashes(w / "standard-1")
if (w / "guarded-0").exists():
    for i in range(3):
        checks[f"guarded {i} matches optimized reference"] = hashes(
            w / f"guarded-{i}"
        ) == hashes(w / "optimized-0")
    ref = hashes(w / "guarded-standard-1")
    checks["guarded standard matches resolved reference"] = (
        ref == hashes(w / "standard-1") and len(ref) == 6
    )
    for suffix in ["", "-repeat1", "-repeat2"]:
        checks["guarded standard four workers" + suffix] = (
            hashes(w / ("guarded-standard-4" + suffix)) == ref
        )
# The pre-guard optimized-standard-4 process aborted with G4 PART122 (Na25).
# Its failure log is retained; it is not a successful replay check.
assert all(checks.values()), checks
(w / "checks.json").write_text(json.dumps(checks, indent=2))
print(checks)
