import argparse

p = argparse.ArgumentParser(
    description="Diagnostic replay of the two bremsstrahlung photon supplies"
)
p.add_argument("--work", type=__import__("pathlib").Path, required=True)
p.add_argument(
    "--module",
    type=__import__("pathlib").Path,
    default=__import__("pathlib").Path.home()
    / "cern/scripts/acts/fatras-realism/fatras-radiative-secondaries/results/2026-10-16/pruned-build",
)
a = p.parse_args()
from pathlib import Path
import csv, gzip, json, subprocess, sys

w = a.work
s = Path.home() / "cern/scripts/acts"
src = Path.home() / "cern/source/acts/acts/fatras-soft"
build = Path.home() / "cern/build/acts/acts/dev3"
fields = "particle_id_pv,particle_id_sv,particle_id_part,particle_id_gen,particle_id_subpart,particle_type,process,vx,vy,vz,vt,px,py,pz,m,q".split(
    ","
)
for label, ref in [
    ("g4", s / "fatras-soft-secondaries/results/2026-10-15/geant4"),
    ("fatras", s / "fatras-radiative-secondaries/results/2026-10-16/current"),
]:
    inp = w / (label + "-photon-input")
    inp.mkdir(exist_ok=True)
    source = ref / "event000000000-particles_simulated.csv.gz"
    count = 0
    with gzip.open(source, "rt") as f, (inp / "event000000000-particles.csv").open(
        "w"
    ) as g:
        writer = csv.DictWriter(g, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in csv.DictReader(f):
            if (
                row["particle_type"] != "22"
                or row["process"] != "3"
                or sum(float(row[k]) ** 2 for k in ["px", "py", "pz"]) < 1e-8
            ):
                continue
            count += 1
            r = {k: row[k] for k in fields}
            r.update(
                particle_id_pv=1,
                particle_id_sv=0,
                particle_id_part=count,
                particle_id_gen=0,
                particle_id_subpart=0,
                process=0,
            )
            writer.writerow(r)
    (inp / "probes.json").write_text(
        json.dumps(
            {
                "sample": "All retained bremsstrahlung photons >=100 keV from reference event 0; diagnostic source replay, no hit cuts",
                "source": str(source),
                "count": count,
            },
            indent=2,
        )
    )
for label in ["g4", "fatras"]:
    out = w / (label + "-photons-in-fatras")
    cmd = [
        sys.executable,
        str(s / "fatras-radiative-secondaries/run.py"),
        "--source",
        str(src),
        "--module",
        str(a.module),
        "--output",
        str(out),
        "--events",
        "1",
        "--input",
        str(w / (label + "-photon-input")),
    ]
    (w / (out.name + ".command.json")).write_text(json.dumps(cmd, indent=2))
    subprocess.run(cmd, check=True)
out = w / "g4-photons-in-g4"
cmd = [
    str(s / "fatras-neutral-hadrons/odd/run-env.sh"),
    str(s / "fatras-material-locality/run-observer.py"),
    "--observer-module",
    str(s / "fatras-material-locality/results/2026-10-16"),
    "--mode",
    "geant4",
    "--source",
    str(src),
    "--revision",
    "0429b7c1e1",
    "--build",
    str(build),
    "--input",
    str(w / "g4-photon-input"),
    "--output",
    str(out),
    "--events",
    "1",
    "--threads",
    "1",
    "--material-map",
    str(s / "fatras-pion-validation/data/2026-10-14/odd-material-beampipe.root"),
    "--module-dir",
    str(s / "fatras-charged-mesons/data/2026-10-14"),
]
(w / (out.name + ".command.json")).write_text(json.dumps(cmd, indent=2))
with (w / (out.name + ".log")).open("w") as log:
    subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, check=True)

meta = out / "metadata.json"
data = json.loads(meta.read_text())
data["sample"] = (
    "Diagnostic G4 bremsstrahlung-photon bank from reference event 0, energy >=100 keV"
)
meta.write_text(json.dumps(data, indent=2))
