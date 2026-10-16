"""Deterministic charged probes spanning soft loopers and displaced tracks."""

import argparse
import csv
import math
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--output", type=Path, required=True)
a = p.parse_args()
a.output.mkdir(parents=True, exist_ok=True)
rows = []
for pt in [.0002, .0005, .001, .005, .02, .05, .1, .2, .5, 1.]:
    for eta in [0., 1., 2.]:
        for j in range(8):
            for radius in [0., 40., 120.]:
                for charge in [-1, 1]:
                    rows.append([1, 0, len(rows) + 1, 0, 0, -13 * charge, 0,
                        radius, 0, 0, 0, pt * math.cos(j * math.pi / 4),
                        pt * math.sin(j * math.pi / 4), pt * math.sinh(eta), .105658375, charge])
with (a.output / "event000000000-particles.csv").open("w") as f:
    writer = csv.writer(f, lineterminator="\n")
    writer.writerow("particle_id_pv,particle_id_sv,particle_id_part,particle_id_gen,particle_id_subpart,particle_type,process,vx,vy,vz,vt,px,py,pz,m,q".split(","))
    writer.writerows(rows)
print(f"Wrote {len(rows)} stable charged transport probes")
