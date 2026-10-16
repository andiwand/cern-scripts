from pathlib import Path
import argparse, subprocess, csv, time, json

p = argparse.ArgumentParser(
    description="Matched electron material transport slabs and step refinement"
)
p.add_argument("--work", type=Path, required=True)
w = p.parse_args().work
outdir = w / "slabs"
outdir.mkdir(exist_ok=True)
cases = []
for pdg, energy, thickness in [
    (11, 20, 30),
    (22, 20, 30),
    (11, 1, 0.3),
    (11, 20, 0.3),
    (22, 1, 30),
]:
    for profile in ["common", "transport", "full"]:
        for backend in ["fatras", "g4"]:
            cases.append(
                (backend, pdg, energy, thickness, profile, 1, 0.04, 0.02, 50000)
            )
for profile in ["common", "transport"]:
    for slices, angular, loss in [(1000, 0.04, 0.02), (1, 0.01, 0.01)]:
        cases.append(("fatras", 11, 20, 30, profile, slices, angular, loss, 50000))
for backend, pdg, energy, thickness, profile, slices, angular, loss, trials in cases:
    out = (
        outdir
        / f"{pdg}-{energy}-{thickness}-{profile}-{backend}-{slices}-{angular}-{loss}.csv"
    )
    cmd = [
        str(w / "final-slab-build/slab"),
        backend,
        "G4_Si",
        str(pdg),
        str(energy),
        str(thickness),
        str(trials),
        str(slices),
        profile,
        "cascade",
        "54421",
        str(out),
        str(angular),
        str(loss),
    ]
    start = time.monotonic()
    with out.with_suffix(".log").open("w") as f:
        subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, check=True)
    d = {r["metric"]: float(r["mean"]) for r in csv.DictReader(out.open())}
    out.with_suffix(".json").write_text(
        json.dumps(dict(command=cmd, wall_seconds=time.monotonic() - start), indent=2)
    )
    print(
        out.stem,
        round(time.monotonic() - start, 2),
        {
            k: d[k]
            for k in [
                "compton",
                "escape_charged",
                "primary_exit_MeV",
                "primary_escape",
                "primary_exit_sin2",
            ]
        },
        flush=True,
    )
