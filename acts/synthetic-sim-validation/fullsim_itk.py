"""Extract ITk full-simulation distributions from a GNN4ITk Athena dump.

The dump is what `ActsExamples::RootAthenaDumpReader` reads, so the branch names
here are the ones documented in `Examples/Io/Root/src/RootAthenaDumpReader.cpp`.
Only what the comparison against the synthetic generator needs is read.
"""

from __future__ import annotations

import numpy as np
import uproot

TREE = "GNN4ITk"

#: Barcodes below this come from the generator, above it from the detector
#: simulation. This is the long-standing Athena convention, and the dump agrees
#: with it: the production radius of the low-barcode particles is at most a few
#: mm while the high-barcode ones sit at a median of 160 mm.
PRIMARY_BARCODE_LIMIT = 200_000

BRANCHES = [
    "CLx",
    "CLy",
    "CLz",
    "CLhardware",
    "CLbarrel_endcap",
    "CLlayer_disk",
    "CLparticleLink_barcode",
    "CLparticleLink_eventIndex",
    "Part_event_number",
    "Part_barcode",
    "Part_pt",
    "Part_eta",
    "Part_vx",
    "Part_vy",
    "Part_vz",
    "Part_radius",
    "Part_px",
    "Part_py",
    "Part_pz",
    "Part_charge",
    "Part_status",
]


class FullSim:
    """Flat, per-event-concatenated arrays of one full-simulation sample."""

    def __init__(self) -> None:
        self.num_events = 0
        # space points, i.e. pixel clusters
        self.sp_x: list[np.ndarray] = []
        self.sp_y: list[np.ndarray] = []
        self.sp_z: list[np.ndarray] = []
        # particles
        self.pt: list[np.ndarray] = []
        self.eta: list[np.ndarray] = []
        self.phi: list[np.ndarray] = []
        self.d0: list[np.ndarray] = []
        self.z0: list[np.ndarray] = []
        self.prod_r: list[np.ndarray] = []
        self.prod_z: list[np.ndarray] = []
        self.primary: list[np.ndarray] = []
        self.num_hits: list[np.ndarray] = []

    def finish(self) -> "FullSim":
        for name in (
            "sp_x", "sp_y", "sp_z", "pt", "eta", "phi", "d0", "z0",
            "prod_r", "prod_z", "primary", "num_hits",
        ):
            setattr(self, name, np.concatenate(getattr(self, name)))
        return self


def _perigee(vx, vy, vz, px, py, pz):
    """Transverse and longitudinal impact parameters of a straight line.

    The synthetic generator reports the perigee parameters of the helix. For a
    production point this close to the beam line the curvature correction is far
    below the width of the distributions being compared, so the straight-line
    expressions are used.

    @return (phi, d0, z0)
    """
    phi = np.arctan2(py, px)
    pt = np.hypot(px, py)
    # signed transverse distance of the production point from the beam axis,
    # measured perpendicular to the momentum
    d0 = vx * np.sin(phi) - vy * np.cos(phi)
    # walk back along the track to the point of closest approach
    longitudinal = vx * np.cos(phi) + vy * np.sin(phi)
    with np.errstate(divide="ignore", invalid="ignore"):
        z0 = vz - longitudinal * pz / pt
    return phi, d0, z0


def load(path: str, num_events: int | None = None, min_pt_mev: float = 100.0,
         max_abs_eta: float = 4.0) -> FullSim:
    """Read a dump and return the distributions to compare against.

    Particles are restricted to charged, final-state ones that leave at least one
    pixel cluster, which is the population the synthetic generator's particle
    list corresponds to. Without the hit requirement the full-simulation sample
    is dominated by particles that never reach the detector at all.

    @param path the dump file
    @param num_events how many events to read, all of them if None
    @param min_pt_mev the momentum threshold in MeV
    @param max_abs_eta the pseudorapidity acceptance
    @return the distributions
    """
    out = FullSim()
    tree = uproot.open(path)[TREE]
    stop = None if num_events is None else num_events

    for batch in tree.iterate(BRANCHES, entry_stop=stop, step_size=1,
                              library="np"):
        for i in range(len(batch["Part_pt"])):
            _load_event(out, {k: v[i] for k, v in batch.items()},
                        min_pt_mev, max_abs_eta)
            out.num_events += 1

    return out.finish()


def _load_event(out: FullSim, ev, min_pt_mev: float, max_abs_eta: float) -> None:
    # `CLhardware` holds one string per cluster, "PIXEL" or "STRIP". A pixel
    # cluster is one space point, which is what the synthetic generator produces.
    hardware = np.asarray([str(h) for h in ev["CLhardware"]])
    is_pixel = hardware == "PIXEL"

    out.sp_x.append(ev["CLx"][is_pixel].astype(np.float32))
    out.sp_y.append(ev["CLy"][is_pixel].astype(np.float32))
    out.sp_z.append(ev["CLz"][is_pixel].astype(np.float32))

    # Count pixel clusters per particle. The key is the (interaction, barcode)
    # pair, not the barcode: barcodes are unique only within one interaction, and
    # a pile-up event has of order two hundred of them. Keying on the barcode
    # alone merges particles across interactions and inflates the hit count by
    # more than an order of magnitude.
    hits: dict[tuple[int, int], int] = {}
    for keep, indices, barcodes in zip(is_pixel,
                                       ev["CLparticleLink_eventIndex"],
                                       ev["CLparticleLink_barcode"]):
        if not keep:
            continue
        for index, barcode in zip(indices, barcodes):
            key = (int(index), int(barcode))
            hits[key] = hits.get(key, 0) + 1

    barcode = ev["Part_barcode"]
    charge = ev["Part_charge"]
    status = ev["Part_status"]
    pt = ev["Part_pt"]
    eta = ev["Part_eta"]

    num_hits = np.array(
        [hits.get((int(e), int(b)), 0)
         for e, b in zip(ev["Part_event_number"], barcode)],
        dtype=np.int32,
    )

    is_primary = barcode < PRIMARY_BARCODE_LIMIT
    # A generator particle is final state when its HepMC status is 1; the others
    # are the intermediate quarks and gluons of the record. Detector secondaries
    # do not carry a HepMC status at all - theirs encodes the Geant4 process, so
    # the values run 20001, 100001, ... - so the cut only applies to primaries.
    # Requiring status 1 of everything removes every secondary.
    plausible = np.where(is_primary, status == 1, True)

    # charged, inside the generator's acceptance, and leaving a mark
    selected = (
        (np.abs(charge) > 0.5)
        & plausible
        & (pt > min_pt_mev)
        & np.isfinite(eta)
        & (np.abs(eta) < max_abs_eta)
        & (num_hits > 0)
    )

    phi, d0, z0 = _perigee(
        ev["Part_vx"][selected], ev["Part_vy"][selected], ev["Part_vz"][selected],
        ev["Part_px"][selected], ev["Part_py"][selected], ev["Part_pz"][selected],
    )

    out.pt.append(pt[selected] / 1000.0)  # MeV -> GeV
    out.eta.append(eta[selected])
    out.phi.append(phi.astype(np.float32))
    out.d0.append(d0.astype(np.float32))
    out.z0.append(z0.astype(np.float32))
    out.prod_r.append(ev["Part_radius"][selected])
    out.prod_z.append(ev["Part_vz"][selected])
    out.primary.append(is_primary[selected])
    out.num_hits.append(num_hits[selected])
