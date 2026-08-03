"""Read the CSV pair the synthetic event generator writes.

Produced by `ActsBenchmarkSyntheticEventGeneration --dump <prefix>`, which calls
`ActsFatras::Synthetic::writeEventCsv`.
"""

from __future__ import annotations

import glob

import numpy as np

import sample


def load(prefix: str, min_pt_gev: float = 0.1,
         max_abs_eta: float = 4.0) -> sample.Sample:
    """Read every `<prefix>*_spacepoints.csv` and its particle file.

    `dump_fastsim.py --events N` numbers the pairs `<prefix>-000`, `-001`, and
    so on; a single event keeps the bare prefix. Both are picked up here, and
    each pair becomes one event of the sample so that the per-event
    normalisation stays right.

    The same selection the full-simulation loaders apply is applied here: only
    particles that leave at least one space point are kept, so the samples
    describe the same population.

    @param prefix the path prefix the generator was dumped with
    @param min_pt_gev the momentum threshold in GeV
    @param max_abs_eta the pseudorapidity acceptance
    @return the distributions of the dumped events
    """
    paths = sorted(glob.glob(prefix + "*_spacepoints.csv"))
    if not paths:
        raise FileNotFoundError("no %s*_spacepoints.csv" % prefix)

    out = sample.Sample()
    for path in paths:
        sp = np.genfromtxt(path, delimiter=",", names=True)

        particles = path[:-len("_spacepoints.csv")] + "_particles.csv"
        p = np.genfromtxt(particles, delimiter=",", names=True)
        selected = (
            (p["pt"] > min_pt_gev)
            & (np.abs(p["eta"]) < max_abs_eta)
            & (p["numHits"] > 0)
        )

        out.add_event(
            sp_x=sp["x"], sp_y=sp["y"], sp_z=sp["z"],
            sp_primary=sp["primary"] > 0.5,
            pt=p["pt"][selected],
            eta=p["eta"][selected],
            phi=p["phi"][selected],
            d0=p["d0"][selected],
            z0=p["z0"][selected],
            prod_r=p["productionRadius"][selected],
            prod_z=p["productionZ"][selected],
            primary=p["primary"][selected] > 0.5,
            num_hits=p["numHits"][selected].astype(np.int32),
        )
    return out.finish()
