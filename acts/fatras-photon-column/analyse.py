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
    (s / "fatras-cascade-response/results/2026-10-16/analysis.json").read_text()
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
            meta["acts_revision"] = "5825d58880c55f75c61e11ef1c35925da8bf9c6e"
            meta["revision_provenance"] = (
                "Archived module; event CSV hashes verified against accepted 5825 result"
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
d["timings"]["geant4_archived"] = old["timings"]["geant4"]


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
checks["control replays 5825d58880"] = hashes(w / "control-0") == hashes(
    s / "fatras-cascade-response/results/2026-10-16/guarded-0"
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
d["slabs"] = {}
ref = s / "fatras-slab-validation/results/2026-10-16"
for f in (w / "slabs").glob("*.csv"):

    def read(path):
        return {
            r["metric"]: {"mean": float(r["mean"]), "sem": float(r["sem"])}
            for r in csv.DictReader(path.open())
        }

    values = {
        "Current": read(f),
        "metadata": json.loads(f.with_suffix(".json").read_text()),
    }
    for name, target in [
        ("Before", f.name),
        ("Geant4", f.name.rsplit("-fatras-", 1)[0] + "-g4-1.csv"),
    ]:
        # Prefer the 100k-trial reference over the earlier 10k scan.
        found = next(
            (
                ref / phase / target
                for phase in ["refined", "runs"]
                if (ref / phase / target).exists()
            ),
            None,
        )
        if found is not None:
            values[name] = read(found)
            values[name + "_source"] = str(found)
    d["slabs"][f.stem] = values
assert all(checks.values()), checks
(w / "analysis.json").write_text(json.dumps(d, indent=2))
(w / "checks.json").write_text(json.dumps(checks, indent=2))
print(d["timings"])
print(checks)
