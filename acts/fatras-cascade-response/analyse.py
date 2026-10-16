"""Inclusive accounting plus diagnostic spectra; no analysis hit cuts."""

import argparse, importlib.util, json, math, statistics, sys
from pathlib import Path
from collections import Counter

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--work", type=Path, required=True)
a = p.parse_args()
w = a.work
s = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location(
    "inclusive_analysis", s / "fatras-secondary-gap/analyse.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
analyse, rows, identity = module.analyse, module.rows, module.identity
old = json.loads(
    (s / "fatras-radiative-secondaries/results/2026-10-16/analysis.json").read_text()
)
variant = next(
    name for name in ["guarded", "optimized", "current"] if (w / f"{name}-0").exists()
)
accepted = w / f"{variant}-0"
current = analyse(accepted)
result = {
    "main": old["main"],
    "runs": {
        "Before": old["runs"]["current"],
        "Current": current,
        "Geant4": old["runs"]["Geant4"],
        "Stopping only": json.loads((w / "stopping-analysis.json").read_text())["runs"][
            "current"
        ],
    },
    "timings": {},
    "spectra": {},
}
for name in ["control", "current"]:
    times = [
        json.loads((w / f"{name}-{i}/metadata.json").read_text())[
            "sequencer_cpu_seconds"
        ]
        / 3
        for i in range(3)
    ]
    result["timings"][name] = {"samples": times, "median": statistics.median(times)}
if (w / "optimized-0").exists():
    result["timings"]["unoptimized"] = result["timings"]["current"]
    times = [
        json.loads((w / f"optimized-{i}/metadata.json").read_text())[
            "sequencer_cpu_seconds"
        ]
        / 3
        for i in range(3)
    ]
    result["timings"]["current"] = {
        "samples": times,
        "median": statistics.median(times),
    }
if (w / "guarded-0").exists():
    result["timings"]["optimized_before_guard"] = result["timings"]["current"]
    times = [
        json.loads((w / f"guarded-{i}/metadata.json").read_text())[
            "sequencer_cpu_seconds"
        ]
        / 3
        for i in range(3)
    ]
    result["timings"]["current"] = {
        "samples": times,
        "median": statistics.median(times),
    }
result["timings"]["geant4"] = (
    json.loads((w / "geant4-refreshed/metadata.json").read_text())[
        "sequencer_cpu_seconds"
    ]
    / 3
)
result["timings"]["main_archived"] = old["main"]["cpu_s_per_event"]
for name, path in [
    ("Current", accepted),
    ("Before", s / "fatras-radiative-secondaries/results/2026-10-16/current"),
    ("Geant4", s / "fatras-soft-secondaries/results/2026-10-15/geant4"),
]:
    counts = Counter()
    parents = Counter()
    for ev in range(3):
        f = path / f"event{ev:09d}-particles_simulated.csv"
        if not f.exists():
            f = f.with_suffix(".csv.gz")
        truth = {identity(r): r for r in rows(f)}
        for pid, r in truth.items():
            if r["particle_type"] != "22" or r["process"] != "3":
                continue
            energy = 1000 * math.sqrt(sum(float(r[k]) ** 2 for k in ["px", "py", "pz"]))
            if energy >= 0.1:
                counts["brems_above_100keV"] += 1
            if 1.022 <= energy < 20:
                counts["brems_1.022_20MeV"] += 1
        f = path / f"event{ev:09d}-hits.csv"
        if not f.exists():
            f = f.with_suffix(".csv.gz")
        for h in rows(f):
            r = truth[identity(h)]
            if r["particle_type"] != "11" or r["process"] != "6":
                continue
            par = truth.get(identity(r, "parent_id_"))
            while par and par["particle_type"] == "22" and par["process"] == "6":
                par = truth.get(identity(par, "parent_id_"))
            parents[par["process"] if par else "?"] += 1
    result["spectra"][name] = {
        "photons": {k: v / 3 for k, v in counts.items()},
        "other_electron_hits_parent_process": {k: v / 3 for k, v in parents.items()},
    }
(w / "analysis.json").write_text(json.dumps(result, indent=2))
print(result["timings"])
