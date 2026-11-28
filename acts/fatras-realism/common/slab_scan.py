#!/usr/bin/env python3
"""Matched-material Fatras / Geant4 homogeneous-slab scans.

Build the harness first:  build_reference.py slab --work WORK
Run inside run-env.sh (Geant4 datasets).

  slab_scan.py run --work WORK --folder NAME [grid options]
      Cartesian product of --backend/--material/--pdg/--energy/--thickness/
      --slices/--profile/--mode; one CSV/LOG/JSON per setting in WORK/NAME.
  slab_scan.py run --work WORK --folder NAME --cases CASES.json
      Explicit list of settings: [{"backend": "g4", "material": "G4_Si", ...}].
  slab_scan.py run --work WORK --preset standard
      The 232-setting Si/Cu photon/electron scan (folder "runs").
  slab_scan.py collect --work WORK
      Validate every setting below WORK and write WORK/analysis.json.

Settings with an existing JSON are skipped. Profiles: common (ionisation,
brems, conversion, Compton; no multiple scattering), transport (common +
scattering), extended, full (G4EmStandardPhysics), annihilation,
annihilation-transport, photoelectric. Modes: primary (daughters killed) or
cascade. Production cuts and scoring thresholds are 100 keV.
"""

import argparse, csv, hashlib, itertools, json, math, subprocess, time
from pathlib import Path

KEYS = ["backend", "material", "pdg", "energy_MeV", "thickness_mm", "n", "slices", "profile", "mode"]


def standard():
    cases = []
    for mat in ["G4_Si", "G4_Cu"]:
        for pdg, energies in [(22, [0.2, 1, 5, 20]), (11, [1, 5, 20])]:
            for e in energies:
                for t in [0.3, 3, 30]:
                    for backend, slices in [("g4", 1), ("fatras", 1), ("fatras", 20), ("fatras", 100)]:
                        cases.append((backend, mat, pdg, e, t, 10000, slices, "common", "primary"))
    for pdg in [22, 11]:
        for e in [5, 20]:
            for t in [3, 30]:
                for profile in ["common", "full"]:
                    for backend, slices in [("g4", 1), ("fatras", 1), ("fatras", 20), ("fatras", 100)]:
                        cases.append((backend, "G4_Si", pdg, e, t, 10000, slices, profile, "cascade"))
    return [dict(zip(KEYS, c)) for c in cases]


def run(a):
    binary = a.work / "slab"
    if a.preset == "standard":
        cases, folder = standard(), a.folder or "runs"
    elif a.cases:
        cases, folder = json.loads(a.cases.read_text()), a.folder or a.cases.stem
    else:
        grid = itertools.product(
            a.backend, a.material, a.pdg, a.energy, a.thickness, [a.n], a.slices, a.profile, a.mode
        )
        cases, folder = [dict(zip(KEYS, c)) for c in grid], a.folder or "slabs"
    out = a.work / folder
    out.mkdir(parents=True, exist_ok=True)
    for i, c in enumerate(cases):
        c = {**dict(angular_variance=a.angular_variance, fractional_loss=a.fractional_loss), **c}
        name = "{mode}-{profile}-{material}-{pdg}-{energy_MeV:g}-{thickness_mm:g}-{backend}-{slices}".format(**c)
        if c["angular_variance"] is not None:
            name += f"-{c['angular_variance']:g}-{c['fractional_loss']:g}"
        target = out / f"{name}.csv"
        meta = target.with_suffix(".json")
        seed = a.seed + i
        command = [str(binary), *(str(c[k]) for k in KEYS), str(seed), str(target)]
        if c["angular_variance"] is not None:
            command += [str(c["angular_variance"]), str(c["fractional_loss"])]
        if not meta.exists():
            start = time.monotonic()
            with target.with_suffix(".log").open("w") as log:
                subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
            values = {x["metric"]: float(x["mean"]) for x in csv.DictReader(target.open())}
            if c["profile"] == "common":
                assert values["photoelectric"] == 0 and values["annihilation"] == 0
            if c["backend"] == "g4":
                assert "CUTS_MeV 0.1 0.1 0.1" in target.with_suffix(".log").read_text()
            meta.write_text(
                json.dumps(
                    dict(
                        c,
                        seed=seed,
                        command=command,
                        wall_seconds=time.monotonic() - start,
                        binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),
                    ),
                    indent=2,
                )
            )
        print(folder, i + 1, len(cases), name, flush=True)


def collect(a):
    records = []
    for meta in sorted(a.work.rglob("*.json")):
        d = json.loads(meta.read_text())
        if "backend" not in d or not meta.with_suffix(".csv").exists():
            continue
        d["file"] = str(meta.with_suffix(".csv").relative_to(a.work))
        d["metrics"] = {}
        for row in csv.DictReader(meta.with_suffix(".csv").open()):
            assert int(row["n"]) == d["n"]
            v = {key: float(row[key]) for key in ["mean", "sem"]}
            assert all(math.isfinite(x) and x >= 0 for x in v.values()), meta
            d["metrics"][row["metric"]] = v
        if d["backend"] == "g4":
            assert "CUTS_MeV 0.1 0.1 0.1" in meta.with_suffix(".log").read_text()
        if d["profile"] == "common":
            assert all(d["metrics"][k]["mean"] == 0 for k in ["photoelectric", "annihilation"])
        assert d["metrics"]["escape_energy_MeV"]["mean"] <= abs(d["energy_MeV"]) * (1 + 1e-6) or d["pdg"] == -11, meta
        records.append(d)
    (a.work / "analysis.json").write_text(
        json.dumps(
            {
                "records": records,
                "checks": {
                    "settings": len(records),
                    "primary_trials": sum(r["n"] for r in records),
                    "finite_nonnegative_metrics": True,
                    "matched_g4_cuts": True,
                    "disabled_mechanisms_absent": True,
                },
            },
            indent=2,
        )
    )
    print(len(records), "settings;", sum(r["n"] for r in records), "primary trials; checks passed")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", required=True)
    r = sub.add_parser("run")
    r.add_argument("--work", type=Path, required=True)
    r.add_argument("--folder")
    r.add_argument("--preset", choices=["standard"])
    r.add_argument("--cases", type=Path)
    r.add_argument("--backend", nargs="+", default=["fatras", "g4"])
    r.add_argument("--material", nargs="+", default=["G4_Si"])
    r.add_argument("--pdg", type=int, nargs="+", default=[22, 11])
    r.add_argument("--energy", type=float, nargs="+", default=[20.0], help="MeV")
    r.add_argument("--thickness", type=float, nargs="+", default=[30.0], help="mm")
    r.add_argument("--n", type=int, default=100000)
    r.add_argument("--slices", type=int, nargs="+", default=[1])
    r.add_argument("--profile", nargs="+", default=["common"])
    r.add_argument("--mode", nargs="+", default=["cascade"])
    r.add_argument("--seed", type=int, default=100000, help="Seed of the first setting")
    r.add_argument("--angular-variance", type=float, help="Fatras electron step angular limit")
    r.add_argument("--fractional-loss", type=float, default=0.02, help="with --angular-variance")
    c = sub.add_parser("collect")
    c.add_argument("--work", type=Path, required=True)
    a = p.parse_args()
    run(a) if a.command == "run" else collect(a)


if __name__ == "__main__":
    main()
