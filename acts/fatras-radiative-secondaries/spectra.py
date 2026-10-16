from pathlib import Path
from collections import Counter, defaultdict
import csv, gzip, json, math
import argparse

p = argparse.ArgumentParser(
    description="Produced photon and ionisation spectra; no hit selections"
)
p.add_argument("--work", type=Path, required=True)
a = p.parse_args()
w = a.work
runs = {
    "Previous": Path.home()
    / "cern/scripts/acts/fatras-compton/results/2026-10-16/compton-100",
    "Coupled": w / "current",
    "G4": Path.home()
    / "cern/scripts/acts/fatras-soft-secondaries/results/2026-10-15/geant4",
}
result = {}
for name, path in runs.items():
    c = Counter()
    energy = Counter()
    parentke = Counter()
    for ev in range(3):
        p = path / f"event{ev:09d}-particles_simulated.csv"
        if not p.exists():
            p = p.with_suffix(".csv.gz")
        with gzip.open(p, "rt") if p.suffix == ".gz" else p.open() as f:
            for r in csv.DictReader(f):
                pdg = int(r["particle_type"])
                process = int(r["process"])
                if pdg != 22 and process != 5:
                    continue
                momentum2 = sum(float(r[k]) ** 2 for k in ["px", "py", "pz"])
                m = float(r["m"])
                ke = (
                    1000 * momentum2 / (math.sqrt(momentum2 + m * m) + m)
                    if momentum2 > 0
                    else 0
                )
                b = next(
                    (
                        i
                        for i, v in enumerate([0.1, 0.2, 1.022, 5, 20, 100, 1000])
                        if ke < v
                    ),
                    7,
                )
                key = f"{pdg}/{process}/{b}"
                c[key] += 1
                energy[key] += ke
    result[name] = {
        "counts": {k: v / 3 for k, v in c.items()},
        "kinetic_MeV": {k: v / 3 for k, v in energy.items()},
    }
    print(
        name,
        {k: round(v / 3) for k, v in c.items() if k.startswith("22/3/")},
        flush=True,
    )
(w / "spectra.json").write_text(json.dumps(result, indent=2))
