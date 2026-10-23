import argparse

p = argparse.ArgumentParser()
p.add_argument("--work", type=__import__("pathlib").Path, required=True)
a = p.parse_args()
from pathlib import Path
import sys, math, json
from collections import Counter, defaultdict

sys.path.insert(0, str(Path.home() / "cern/scripts/acts/fatras-realism/fatras-secondary-gap"))
from analyse import rows, identity

s = Path.home() / "cern/scripts/acts"
w = a.work
out = {}
for name, path in [
    ("Fatras", s / "fatras-radiative-secondaries/results/2026-10-16/current"),
    ("G4", s / "fatras-soft-secondaries/results/2026-10-15/geant4"),
]:
    c = defaultdict(Counter)
    for ev in range(3):
        t = {
            identity(r): r
            for r in rows(path / f"event{ev:09d}-particles_simulated.csv.gz")
        }
        parents = defaultdict(set)
        for pid, r in t.items():
            if r["particle_type"] != "22" or r["process"] != "3":
                continue
            ke = 1000 * math.sqrt(sum(float(r[k]) ** 2 for k in ["px", "py", "pz"]))
            if ke < 0.1:
                continue
            par = t.get(identity(r, "parent_id_"))
            proc = par["process"] if par else "?"
            species = par["particle_type"] if par else "?"
            for scope in ["above_0.1"] + (["1.022_to_20"] if 1.022 <= ke < 20 else []):
                c[scope][proc + ":" + species] += 1
                parents[scope + "/" + proc + ":" + species].add(
                    identity(par) if par else None
                )
        for k, v in parents.items():
            c["emitting_parents"][k] += len(v)
    out[name] = {k: {p: n / 3 for p, n in sorted(v.items())} for k, v in c.items()}
(w / "photon-parents.json").write_text(json.dumps(out, indent=2))
print(json.dumps(out, indent=2))
