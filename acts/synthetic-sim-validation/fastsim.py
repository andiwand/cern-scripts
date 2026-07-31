"""Read the CSV pair the synthetic event generator writes.

Produced by `ActsBenchmarkSyntheticEventGeneration --dump <prefix>`, which calls
`ActsFatras::Synthetic::writeEventCsv`.
"""

from __future__ import annotations

import numpy as np

import sample


def load(prefix: str, min_pt_gev: float = 0.1,
         max_abs_eta: float = 4.0) -> sample.Sample:
    """Read `<prefix>_spacepoints.csv` and `<prefix>_particles.csv`.

    The same selection the full-simulation loaders apply is applied here: only
    particles that leave at least one space point are kept, so the samples
    describe the same population.

    @param prefix the path prefix the generator was dumped with
    @param min_pt_gev the momentum threshold in GeV
    @param max_abs_eta the pseudorapidity acceptance
    @return the distributions of the one dumped event
    """
    sp = np.genfromtxt(prefix + "_spacepoints.csv", delimiter=",", names=True)

    p = np.genfromtxt(prefix + "_particles.csv", delimiter=",", names=True)
    selected = (
        (p["pt"] > min_pt_gev)
        & (np.abs(p["eta"]) < max_abs_eta)
        & (p["numHits"] > 0)
    )

    out = sample.Sample()
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
