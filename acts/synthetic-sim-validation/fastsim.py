"""Read the CSV pair the synthetic event generator writes.

Produced by `ActsBenchmarkSyntheticEventGeneration --dump <prefix>`, which calls
`ActsFatras::Synthetic::writeEventCsv`.
"""

from __future__ import annotations

import numpy as np


class FastSim:
    """The same fields `fullsim_itk.FullSim` carries, for one generated event."""

    def __init__(self) -> None:
        self.num_events = 1
        self.sp_x = np.empty(0)
        self.sp_y = np.empty(0)
        self.sp_z = np.empty(0)
        self.pt = np.empty(0)
        self.eta = np.empty(0)
        self.phi = np.empty(0)
        self.d0 = np.empty(0)
        self.z0 = np.empty(0)
        self.prod_r = np.empty(0)
        self.prod_z = np.empty(0)
        self.primary = np.empty(0, dtype=bool)
        self.num_hits = np.empty(0, dtype=np.int32)


def load(prefix: str, min_pt_gev: float = 0.1, max_abs_eta: float = 4.0) -> FastSim:
    """Read `<prefix>_spacepoints.csv` and `<prefix>_particles.csv`.

    The same selection the full-simulation loader applies is applied here: only
    particles that leave at least one space point are kept, so the two samples
    describe the same population.

    @param prefix the path prefix the generator was dumped with
    @param min_pt_gev the momentum threshold in GeV
    @param max_abs_eta the pseudorapidity acceptance
    @return the distributions
    """
    out = FastSim()

    sp = np.genfromtxt(prefix + "_spacepoints.csv", delimiter=",", names=True)
    out.sp_x = sp["x"]
    out.sp_y = sp["y"]
    out.sp_z = sp["z"]

    p = np.genfromtxt(prefix + "_particles.csv", delimiter=",", names=True)
    selected = (
        (p["pt"] > min_pt_gev)
        & (np.abs(p["eta"]) < max_abs_eta)
        & (p["numHits"] > 0)
    )
    out.pt = p["pt"][selected]
    out.eta = p["eta"][selected]
    out.phi = p["phi"][selected]
    out.d0 = p["d0"][selected]
    out.z0 = p["z0"][selected]
    out.prod_r = p["productionRadius"][selected]
    out.prod_z = p["productionZ"][selected]
    out.primary = p["primary"][selected] > 0.5
    out.num_hits = p["numHits"][selected].astype(np.int32)

    return out
