"""Matched-material EM slab scan, convergence and mechanism attribution."""

import argparse, csv, hashlib, json, subprocess, time
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--work", type=Path, required=True)
p.add_argument(
    "--phase", choices=["scan", "refined", "attribution", "all"], default="all"
)
a = p.parse_args()
w = a.work


def cases(phase):
    result = []
    if phase == "scan":
        for mat in ["G4_Si", "G4_Cu"]:
            for pdg, energies in [(22, [0.2, 1, 5, 20]), (11, [1, 5, 20])]:
                for e in energies:
                    for t in [0.3, 3, 30]:
                        for backend, slices in [
                            ("g4", 1),
                            ("fatras", 1),
                            ("fatras", 20),
                            ("fatras", 100),
                        ]:
                            result.append(
                                (
                                    backend,
                                    mat,
                                    pdg,
                                    e,
                                    t,
                                    10000,
                                    slices,
                                    "common",
                                    "primary",
                                )
                            )
        for pdg in [22, 11]:
            for e in [5, 20]:
                for t in [3, 30]:
                    for profile in ["common", "full"]:
                        for backend, slices in [
                            ("g4", 1),
                            ("fatras", 1),
                            ("fatras", 20),
                            ("fatras", 100),
                        ]:
                            result.append(
                                (
                                    backend,
                                    "G4_Si",
                                    pdg,
                                    e,
                                    t,
                                    10000,
                                    slices,
                                    profile,
                                    "cascade",
                                )
                            )
    elif phase == "refined":
        for pdg, e, t, mat in [
            (22, 1, 30, "G4_Si"),
            (22, 20, 30, "G4_Si"),
            (11, 20, 30, "G4_Si"),
            (22, 5, 30, "G4_Cu"),
            (22, 5, 3, "G4_Cu"),
        ]:
            for mode in (["primary", "cascade"] if mat == "G4_Si" else ["primary"]):
                for backend, slices in [
                    ("g4", 1),
                    ("fatras", 1),
                    ("fatras", 100),
                    ("fatras", 1000),
                ]:
                    result.append(
                        (backend, mat, pdg, e, t, 100000, slices, "common", mode)
                    )
        for pdg in [22, 11]:
            for profile in ["extended", "full"]:
                result.append(
                    ("g4", "G4_Si", pdg, 20, 30, 100000, 1, profile, "cascade")
                )
            for slices in [100, 1000]:
                result.append(
                    ("fatras", "G4_Si", pdg, 20, 30, 100000, slices, "full", "cascade")
                )
    else:
        for pdg in [22, 11]:
            for profile in ["annihilation", "photoelectric"]:
                result.append(
                    ("g4", "G4_Si", pdg, 20, 30, 100000, 1, profile, "cascade")
                )
        result.append(("fatras", "G4_Si", 11, 20, 30, 20000, 10000, "full", "cascade"))
    return result


for phase in (["scan", "refined", "attribution"] if a.phase == "all" else [a.phase]):
    folder = w / ("runs" if phase == "scan" else phase)
    folder.mkdir(exist_ok=True)
    base_seed = {"scan": 100000, "refined": 200000, "attribution": 300000}[phase]
    batch = cases(phase)
    for i, c in enumerate(batch):
        backend, mat, pdg, e, t, n, slices, profile, mode = c
        name = f"{mode}-{profile}-{mat}-{pdg}-{e:g}-{t:g}-{backend}-{slices}"
        out = folder / f"{name}.csv"
        log = out.with_suffix(".log")
        meta = out.with_suffix(".json")
        command = [
            str(w / "slab"),
            backend,
            mat,
            str(pdg),
            str(e),
            str(t),
            str(n),
            str(slices),
            profile,
            mode,
            str(base_seed + i),
            str(out),
        ]
        if not meta.exists():
            start = time.monotonic()
            with log.open("w") as f:
                subprocess.run(command, stdout=f, stderr=subprocess.STDOUT, check=True)
            values = {x["metric"]: float(x["mean"]) for x in csv.DictReader(out.open())}
            if profile == "common":
                assert values["photoelectric"] == 0 and values["annihilation"] == 0
            if backend == "g4":
                assert "CUTS_MeV 0.1 0.1 0.1" in log.read_text()
            meta.write_text(
                json.dumps(
                    dict(
                        backend=backend,
                        material=mat,
                        pdg=pdg,
                        energy_MeV=e,
                        thickness_mm=t,
                        n=n,
                        slices=slices,
                        profile=profile,
                        mode=mode,
                        seed=base_seed + i,
                        command=command,
                        wall_seconds=time.monotonic() - start,
                        binary_sha256=hashlib.sha256(
                            (w / "slab").read_bytes()
                        ).hexdigest(),
                    ),
                    indent=2,
                )
            )
        print(phase, i + 1, len(batch), name, flush=True)
