import argparse

p = argparse.ArgumentParser()
p.add_argument("--work", type=__import__("pathlib").Path, required=True)
a = p.parse_args()
from pathlib import Path
import csv, json, sys
from collections import Counter

sys.path.insert(0, str(Path.home() / "cern/scripts/acts/fatras-realism/fatras-secondary-gap"))
from analyse import rows, identity

w = a.work
out = {}
for name in ["g4-photons-in-fatras", "fatras-photons-in-fatras", "g4-photons-in-g4"]:
    p = w / name
    t = {identity(r): r for r in rows(p / "event000000000-particles_simulated.csv")}
    c = Counter()
    for h in rows(p / "event000000000-hits.csv"):
        r = t[identity(h)]
        c["process/" + r["process"]] += 1
        if r["process"] == "6" and r["particle_type"] == "11":
            c["other_electron"] += 1
    if (p / "observer.tsv").exists():
        for r in csv.DictReader((p / "observer.tsv").open(), delimiter="\t"):
            c["exact/" + r["creator"]] += 1
            if r["creator"] == "compt":
                c[
                    "compton/"
                    + ("sensor" if "ActsSensitive#" in r["birth_volume"] else "passive")
                ] += 1
    out[name] = dict(c)
(w / "photon-replay-summary.json").write_text(json.dumps(out, indent=2))
print(json.dumps(out, indent=2))
