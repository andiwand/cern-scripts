"""Byte-identical event replay and native/reference checks; raw or archived output."""

import argparse
import gzip
import hashlib
import json
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--work", type=Path, required=True)
a = p.parse_args()


def hashes(path):
    manifest = path / "csv-sha256.json"
    if manifest.exists() and not list(path.glob("event*.csv*")):
        return json.loads(manifest.read_text())
    result = {}
    for f in sorted(path.glob("event*.csv*")):
        with gzip.open(f, "rb") if f.suffix == ".gz" else f.open("rb") as stream:
            result[f.name.removesuffix(".gz")] = hashlib.file_digest(
                stream, "sha256"
            ).hexdigest()
    return result


checks = {}
for name in ["current", "legacy-fixed"]:
    reference = hashes(a.work / name)
    assert len(reference) == 6
    for i in [1, 2, 3, 4]:
        checks[f"{name} repeat {i}"] = (
            hashes(a.work / f"{name}-repeat-{i}") == reference
        )
checks["standard 1 vs 4 workers"] = (
    hashes(a.work / "standard-1") == hashes(a.work / "standard-4")
    and len(hashes(a.work / "standard-1")) == 6
)
reference = (
    Path.home() / "cern/scripts/acts/fatras-realism/fatras-soft-secondaries/results/2026-10-15/geant4"
)
checks["fresh G4 vs archived reference"] = (
    hashes(a.work / "geant4-refreshed") == hashes(reference)
    and len(hashes(reference)) == 6
)
assert all(checks.values()), checks
(a.work / "checks.json").write_text(json.dumps(checks, indent=2))
print(checks)
