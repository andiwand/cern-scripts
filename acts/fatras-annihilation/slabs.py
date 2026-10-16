import subprocess, json, time, csv
from pathlib import Path
import argparse

p = argparse.ArgumentParser(
    description="Controlled positron and electromagnetic cascade slabs"
)
p.add_argument("--work", type=Path, required=True)
w = p.parse_args().work
o = w / "slabs"
o.mkdir(exist_ok=True)
for pdg, e, t in [
    (-11, 0, 1),
    (-11, 0.01, 1),
    (-11, 1, 10),
    (-11, 20, 30),
    (22, 20, 30),
    (11, 20, 30),
]:
    for profile in ["transport", "annihilation-transport", "full"]:
        if e == 0 and profile == "transport":
            continue
        for b in ["fatras", "g4"]:
            f = o / f"{pdg}-{e}-{t}-{profile}-{b}.csv"
            cmd = [
                str(w / "slab-build/slab"),
                b,
                "G4_Si",
                str(pdg),
                str(e),
                str(t),
                "20000",
                "1",
                profile,
                "cascade",
                "54421",
                str(f),
            ]
            now = time.monotonic()
            with f.with_suffix(".log").open("w") as log:
                subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, check=True)
            f.with_suffix(".json").write_text(
                json.dumps(
                    dict(command=cmd, wall_seconds=time.monotonic() - now), indent=2
                )
            )
            d = {r["metric"]: float(r["mean"]) for r in csv.DictReader(f.open())}
            print(f.stem, d, flush=True)
