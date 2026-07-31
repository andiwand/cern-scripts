"""Extract ITk full-simulation distributions from a GNN4ITk Athena dump.

The dump is what `ActsExamples::RootAthenaDumpReader` reads, so the branch names
here are the ones documented in `Examples/Io/Root/src/RootAthenaDumpReader.cpp`.
Only what the comparison against the synthetic generator needs is read.
"""

from __future__ import annotations

import numpy as np
import uproot

import sample

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


def load(path: str, num_events: int | None = None, min_pt_mev: float = 100.0,
         max_abs_eta: float = 4.0) -> sample.Sample:
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
    out = sample.Sample()
    tree = uproot.open(path)[TREE]
    stop = None if num_events is None else num_events

    for batch in tree.iterate(BRANCHES, entry_stop=stop, step_size=1,
                              library="np"):
        for i in range(len(batch["Part_pt"])):
            _load_event(out, {k: v[i] for k, v in batch.items()},
                        min_pt_mev, max_abs_eta)

    return out.finish()


def _load_event(out: sample.Sample, ev, min_pt_mev: float,
                max_abs_eta: float) -> None:
    # `CLhardware` holds one string per cluster, "PIXEL" or "STRIP". A pixel
    # cluster is one space point, which is what the synthetic generator produces.
    hardware = np.asarray([str(h) for h in ev["CLhardware"]])
    is_pixel = hardware == "PIXEL"

    # Count pixel clusters per particle. The key is the (interaction, barcode)
    # pair, not the barcode: barcodes are unique only within one interaction, and
    # a pile-up event has of order two hundred of them. Keying on the barcode
    # alone merges particles across interactions and inflates the hit count by
    # more than an order of magnitude.
    hits: dict[tuple[int, int], int] = {}
    # Whether each pixel cluster came from a generator particle. Half of them
    # carry no truth link at all, and those are not primary: they follow the
    # linked secondaries in r and |z| and are larger, so they are secondaries
    # the dump did not record rather than noise.
    sp_primary = []
    for keep, indices, barcodes in zip(is_pixel,
                                       ev["CLparticleLink_eventIndex"],
                                       ev["CLparticleLink_barcode"]):
        if not keep:
            continue
        from_generator = False
        for index, barcode in zip(indices, barcodes):
            key = (int(index), int(barcode))
            hits[key] = hits.get(key, 0) + 1
            from_generator = from_generator or barcode < PRIMARY_BARCODE_LIMIT
        sp_primary.append(from_generator)

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

    phi, d0, z0 = sample.perigee(
        ev["Part_vx"][selected], ev["Part_vy"][selected], ev["Part_vz"][selected],
        ev["Part_px"][selected], ev["Part_py"][selected], ev["Part_pz"][selected],
    )

    out.add_event(
        # `CLhardware` marks the pixel clusters, one of which is one space point
        sp_x=ev["CLx"][is_pixel].astype(np.float32),
        sp_y=ev["CLy"][is_pixel].astype(np.float32),
        sp_z=ev["CLz"][is_pixel].astype(np.float32),
        sp_primary=np.asarray(sp_primary, dtype=bool),
        pt=pt[selected] / 1000.0,  # MeV -> GeV
        eta=eta[selected],
        phi=phi.astype(np.float32),
        d0=d0.astype(np.float32),
        z0=z0.astype(np.float32),
        prod_r=ev["Part_radius"][selected],
        prod_z=ev["Part_vz"][selected],
        primary=is_primary[selected],
        num_hits=num_hits[selected],
    )
