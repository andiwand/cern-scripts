"""Inclusive hit accounting and CPU, with all diagnostic bins retained."""

import argparse
import csv
import gzip
import hashlib
import importlib.util
import json
import statistics
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--work", type=Path, required=True)
a = p.parse_args()
w = a.work
s = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location(
    "inclusive", s / "fatras-secondary-gap/analyse.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
old = json.loads(
    (s / "fatras-photon-column/results/2026-10-16/analysis.json").read_text()
)
d = dict(
    main=old["main"],
    runs={
        "Before": old["runs"]["Current"],
        "Current": module.analyse(w / "current-0"),
        "Geant4": old["runs"]["Geant4"],
    },
    timings={},
)
for name in ["control", "current"]:
    if name == "control":
        # The runner records its source checkout. The actual replayed module
        # comes from the immutable pre-change archive, verified below.
        for i in range(3):
            path = w / f"control-{i}/metadata.json"
            meta = json.loads(path.read_text())
            meta.setdefault("runner_checkout_revision", meta["acts_revision"])
            meta["acts_revision"] = "ae02eeb5fbf266fd3ece0a8bea64f1935d453ba9"
            meta["revision_provenance"] = (
                "Archived module; event CSV hashes verified against accepted ae02 result"
            )
            path.write_text(json.dumps(meta, indent=2))
    times = [
        json.loads((w / f"{name}-{i}/metadata.json").read_text())[
            "sequencer_cpu_seconds"
        ]
        / 3
        for i in range(3)
    ]
    d["timings"][name] = dict(samples=times, median=statistics.median(times))
d["timings"]["main_archived"] = old["timings"]["main_archived"]
d["timings"]["geant4_archived"] = old["timings"]["geant4_archived"]


def hashes(root):
    files = list(root.glob("event*.csv*"))
    if not files:
        return json.loads((root / "csv-sha256.json").read_text())
    result = {}
    for f in files:
        with gzip.open(f, "rb") if f.suffix == ".gz" else f.open("rb") as stream:
            h = hashlib.file_digest(stream, "sha256").hexdigest()
        result[f.name.removesuffix(".gz")] = h
    return result


checks = {}
for name in ["control", "current"]:
    ref = hashes(w / f"{name}-0")
    assert len(ref) == 6
    for i in [1, 2]:
        checks[f"{name} repeat {i}"] = hashes(w / f"{name}-{i}") == ref
checks["control replays ae02eeb5fb"] = hashes(w / "control-0") == hashes(
    s / "fatras-photon-column/results/2026-10-16/current-0"
)
checks["one versus four standard workers"] = (
    hashes(w / "standard-1") == hashes(w / "standard-4")
    and len(hashes(w / "standard-1")) == 6
)
for name in ["Current", "Geant4"]:
    meta = d["runs"][name]["metadata"]
    checks[f"{name} inclusive summary"] = meta["analysis_hit_p_min_GeV"] in (
        None,
        0,
    ) and meta["analysis_hit_pt_min_GeV"] in (None, 0)
# Refresh kernel-source hashes: old bridge builders record only selected trees.
d["source_sha256"] = {
    str(
        f.relative_to(Path(d["runs"]["Current"]["metadata"]["source"]))
    ): hashlib.sha256(f.read_bytes()).hexdigest()
    for f in Path(d["runs"]["Current"]["metadata"]["source"]).glob(
        "Fatras/include/**/*.hpp"
    )
}
source = Path(d["runs"]["Current"]["metadata"]["source"])
for rel in [
    "Core/include/Acts/Propagator/Propagator.ipp",
    "Examples/Algorithms/Fatras/src/FatrasSimulation.cpp",
]:
    d["source_sha256"][rel] = hashlib.sha256((source / rel).read_bytes()).hexdigest()
d["slabs"] = {
    f.stem: {
        "metrics": {
            r["metric"]: {"mean": float(r["mean"]), "sem": float(r["sem"])}
            for r in csv.DictReader(f.open())
        },
        "metadata": json.loads(f.with_suffix(".json").read_text()),
    }
    for f in (w / "slabs").glob("*.csv")
}
d["ablations"] = {
    name: module.analyse(w / name) for name in ["core-only", "no-new-birth"]
}
d["failures"] = {
    name: (w / (name + ".log")).read_text().count("failed to simulate with error")
    for name in ["current-0", "control-0", "core-only", "no-new-birth"]
}
assert all(checks.values()), checks
(w / "analysis.json").write_text(json.dumps(d, indent=2))
(w / "checks.json").write_text(json.dumps(checks, indent=2))
print(d["timings"])
print(checks)
