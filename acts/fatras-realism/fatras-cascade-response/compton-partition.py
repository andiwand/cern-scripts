import argparse

p = argparse.ArgumentParser()
p.add_argument("--work", type=__import__("pathlib").Path, required=True)
a = p.parse_args()
import csv, gzip, json, math, sys
from pathlib import Path
from collections import Counter, defaultdict

sys.path.insert(0, str(Path.home() / "cern/scripts/acts/fatras-realism/fatras-secondary-gap"))
from analyse import rows, identity

s = Path.home() / "cern/scripts/acts"
w = a.work
c = defaultdict(Counter)
edges = [0.04, 0.1, 0.2, 1, 5, 20, 100]
group = lambda e: next((i for i, x in enumerate(edges) if e < x), len(edges))
for r in csv.DictReader(
    gzip.open(
        s
        / "fatras-material-locality/results/2026-10-16/geant4-observed/observer.tsv.gz",
        "rt",
    ),
    delimiter="\t",
):
    if r["creator"] != "compt":
        continue
    loc = "sensor" if "ActsSensitive#" in r["birth_volume"] else "passive"
    ke = float(r["birth_ke_MeV"])
    origin = r["parent_creator"]
    origin = (
        "nuclear"
        if "Inelastic" in origin or "Capture" in origin or "Nuclear" in origin
        else origin
    )
    for scope in ["all", loc]:
        c["G4/" + scope + "/parent"][origin] += 1
        c["G4/" + scope + "/energy"][group(ke)] += 1
        c["G4/" + scope + "/energy-parent"][f"{group(ke)}/{origin}"] += 1
for ev in range(3):
    path = s / "fatras-radiative-secondaries/results/2026-10-16/current"
    t = {
        identity(r): r for r in rows(path / f"event{ev:09d}-particles_simulated.csv.gz")
    }
    for h in rows(path / f"event{ev:09d}-hits.csv.gz"):
        r = t[identity(h)]
        if r["process"] != "6" or r["particle_type"] != "11":
            continue
        parent = t.get(identity(r, "parent_id_"))
        while (
            parent is not None
            and parent["process"] == "6"
            and parent["particle_type"] == "22"
        ):
            parent = t.get(identity(parent, "parent_id_"))
        origin = {"0": "primary", "1": "Decay", "3": "eBrem", "4": "nuclear"}.get(
            parent["process"] if parent else "?", "unknown"
        )
        p = math.sqrt(sum(float(r[k]) ** 2 for k in ["px", "py", "pz"]))
        m = float(r["m"])
        ke = 1000 * p * p / (math.hypot(p, m) + m)
        c["Fatras/all/parent"][origin] += 1
        c["Fatras/all/energy"][group(ke)] += 1
        c["Fatras/all/energy-parent"][f"{group(ke)}/{origin}"] += 1
out = {k: {str(kk): v / 3 for kk, v in sorted(count.items())} for k, count in c.items()}
(w / "compton-partition.json").write_text(
    json.dumps({"energy_edges_MeV": edges, "mean": out}, indent=2)
)
for k, v in out.items():
    if "energy-parent" not in k:
        print(k, v)
