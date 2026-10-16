"""Check deterministic replay, accepting raw runs or compressed archives."""

import argparse
import gzip
import hashlib
import json
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--work", type=Path, required=True)
p.add_argument(
    "--reference",
    type=Path,
    default=Path.home()
    / "cern/scripts/acts/fatras-transport-performance/results/2026-10-16/pruned-check",
)
a = p.parse_args()


def hashes(directory):
    files = sorted(directory.glob("event*.csv")) + sorted(
        directory.glob("event*.csv.gz")
    )
    if not files:
        result = json.loads((directory / "csv-hashes.json").read_text())
    else:
        result = {}
        for path in files:
            opener = gzip.open if path.suffix == ".gz" else open
            with opener(path, "rb") as stream:
                result[path.name.removesuffix(".gz")] = hashlib.file_digest(
                    stream, "sha256"
                ).hexdigest()
    assert len(result) == 6, (directory, len(result))
    return result


checks = {}
for other, reference in [
    ("repeat-control-1", "disabled-check"),
    ("repeat-control-2", "disabled-check"),
    ("repeat-compton-1", "compton-100"),
    ("repeat-compton-2", "compton-100"),
    ("standard-four", "standard-one"),
]:
    checks[other + " vs " + reference] = hashes(a.work / other) == hashes(
        a.work / reference
    )
checks["disabled vs archived reference"] = hashes(a.work / "disabled-check") == hashes(
    a.reference
)
print(json.dumps(checks, indent=2))
assert all(checks.values())
