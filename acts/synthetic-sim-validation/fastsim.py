"""Read the CSV pair the synthetic event generator writes.

Produced by `ActsBenchmarkSyntheticEventGeneration --dump <prefix>`, which calls
`ActsFatras::Synthetic::writeEventCsv`.
"""

from __future__ import annotations

import glob

import numpy as np
import pandas as pd

import sample


def _read_csv(path: str) -> dict:
    """Read one of the generator's CSV files, by column name.

    `pandas` and not `numpy.genfromtxt`, which parses a line at a time in Python
    and costs half a second per event here -- half a minute over a validation
    sample, against a second or two for the same files.

    @param path the file
    @return the columns, keyed by their header
    """
    frame = pd.read_csv(path)
    return {name: frame[name].to_numpy() for name in frame.columns}


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
        sp = _read_csv(path)

        particles = path[:-len("_spacepoints.csv")] + "_particles.csv"
        p = _read_csv(particles)
        selected = (
            (p["pt"] > min_pt_gev)
            & (np.abs(p["eta"]) < max_abs_eta)
            & (p["numHits"] > 0)
        )

        # The generator produces primaries below this threshold and beyond this
        # eta, so the acceptance has to be applied on this side too. Taken off
        # the particle each space point names rather than off the space point,
        # which carries no momentum of its own.
        in_acceptance = ((p["pt"] > min_pt_gev)
                         & (np.abs(p["eta"]) < max_abs_eta))
        sp_primary = sp["primary"] > 0.5

        out.add_event(
            sp_x=sp["x"], sp_y=sp["y"], sp_z=sp["z"],
            sp_primary=sp_primary,
            sp_accepted=sp_primary & in_acceptance[sp["particle"]],
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
