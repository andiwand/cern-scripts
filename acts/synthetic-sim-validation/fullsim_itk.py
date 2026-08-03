"""Extract ITk full-simulation distributions from a GNN4ITk Athena dump.

The dump is what `ActsExamples::RootAthenaDumpReader` reads, so the branch names
here are the ones documented in `Examples/Io/Root/src/RootAthenaDumpReader.cpp`.
Only what the comparison against the synthetic generator needs is read.
"""

from __future__ import annotations

import numpy as np
import glob
import os

import awkward as ak

import uproot

import sample

TREE = "GNN4ITk"

#: Events per read. Larger amortises the basket decompression; the whole
#: batch is held in memory, and a pile-up event is a few tens of megabytes.
BATCH_SIZE = 10

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
         max_abs_eta: float = 4.0, skip_events: int = 0) -> sample.Sample:
    """Read a dump and return the distributions to compare against.

    Particles are restricted to charged, final-state ones that leave at least one
    pixel cluster, which is the population the synthetic generator's particle
    list corresponds to. Without the hit requirement the full-simulation sample
    is dominated by particles that never reach the detector at all.

    Both counts are spread evenly over the files rather than paid out of the
    front, so that a fit and the validation of it see the same mix of them. The
    files are separate Athena jobs and their primary multiplicities differ by a
    few percent, which a sample taken from one file alone carries whole.

    @param path the dump file, or a shell glob over several of them
    @param num_events how many events to read in total, all of them if None
    @param skip_events how many to pass over in each file first, so that a fit
           and the validation of it can be given different events
    @param min_pt_mev the momentum threshold in MeV
    @param max_abs_eta the pseudorapidity acceptance
    @return the distributions
    """
    paths = sorted(glob.glob(os.path.expanduser(path)))
    if not paths:
        raise FileNotFoundError(path)

    def share(total: int, index: int) -> int:
        """`total` split across the files, the remainder going to the first."""
        base, extra = divmod(total, len(paths))
        return base + (1 if index < extra else 0)

    out = sample.Sample()
    for index, one in enumerate(paths):
        tree = uproot.open(one)[TREE]
        available = tree.num_entries
        start = min(share(skip_events, index), available)
        stop = (available if num_events is None
                else min(available, start + share(num_events, index)))
        if start >= stop:
            continue
        # `library="ak"` is the whole of the read cost. Under `"np"` uproot has
        # to materialise every cluster's variable-length truth link list as its
        # own object, which is five million Python-level reads for three events;
        # awkward keeps it in the vectorised path.
        for batch in tree.iterate(BRANCHES, entry_start=start,
                                  entry_stop=stop, step_size=BATCH_SIZE,
                                  library="ak"):
            for i in range(len(batch)):
                _load_event(out, batch[i], min_pt_mev, max_abs_eta)

    return out.finish()


def _load_event(out: sample.Sample, ev, min_pt_mev: float,
                max_abs_eta: float) -> None:
    # `CLhardware` holds one string per cluster, "PIXEL" or "STRIP". A pixel
    # cluster is one space point, which is what the synthetic generator produces.
    is_pixel = np.asarray(ev["CLhardware"] == "PIXEL")

    # The truth links of the pixel clusters, one variable-length list each. Kept
    # jagged and reduced with awkward rather than looped over: a pile-up event
    # holds a quarter of a million clusters, and touching them one at a time in
    # Python is the whole cost of reading the dump.
    indices = ev["CLparticleLink_eventIndex"][is_pixel]
    barcodes = ev["CLparticleLink_barcode"][is_pixel]

    barcode = np.asarray(ev["Part_barcode"])
    charge = np.asarray(ev["Part_charge"])
    status = np.asarray(ev["Part_status"])
    pt = np.asarray(ev["Part_pt"])
    eta = np.asarray(ev["Part_eta"])

    # A particle is named by the (interaction, barcode) pair, not the barcode:
    # barcodes are unique only within one interaction, and a pile-up event has
    # of order two hundred of them. Keying on the barcode alone merges particles
    # across interactions and inflates the hit count by more than an order of
    # magnitude. The pair packs into one integer so the matching is a sort.
    stride = np.int64(1) << 32
    part_key = (np.asarray(ev["Part_event_number"]).astype(np.int64) * stride
                + barcode.astype(np.int64))
    link_key = (np.asarray(ak.flatten(indices)).astype(np.int64) * stride
                + np.asarray(ak.flatten(barcodes)).astype(np.int64))

    # Whether each pixel cluster came from a generator particle. Half of them
    # carry no truth link at all, and those are not primary: they follow the
    # linked secondaries in r and |z| and are larger, so they are secondaries
    # the dump did not record rather than noise.
    sp_primary = np.asarray(ak.any(barcodes < PRIMARY_BARCODE_LIMIT, axis=-1))

    # The primaries the generator is configured to make. A twelfth of the dump's
    # primary clusters come from outside this and it cannot produce them at all.
    accepted = np.unique(part_key[
        (barcode < PRIMARY_BARCODE_LIMIT)
        & (np.abs(charge) > 0.5) & (status == 1) & (pt > min_pt_mev)
        & np.isfinite(eta) & (np.abs(eta) < max_abs_eta)])
    sp_accepted = np.asarray(ak.any(
        ak.unflatten(np.isin(link_key, accepted),
                     np.asarray(ak.num(barcodes, axis=-1))),
        axis=-1))

    # Clusters per particle, counted per link so that a cluster shared between
    # two particles counts for both, as the dump's own bookkeeping has it.
    linked, counts = np.unique(link_key, return_counts=True)
    where = np.searchsorted(linked, part_key)
    inside = where < len(linked)
    clamped = np.where(inside, where, 0)
    num_hits = np.where(inside & (linked[clamped] == part_key),
                        counts[clamped], 0).astype(np.int32)

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

    # the dump's momenta are in MeV, and `perigee` needs GeV to turn them into
    # a radius of curvature
    phi, d0, z0 = sample.perigee(
        np.asarray(ev["Part_vx"])[selected], np.asarray(ev["Part_vy"])[selected], np.asarray(ev["Part_vz"])[selected],
        np.asarray(ev["Part_px"])[selected] / 1000.0, np.asarray(ev["Part_py"])[selected] / 1000.0,
        np.asarray(ev["Part_pz"])[selected] / 1000.0, charge[selected],
    )

    out.add_event(
        # `CLhardware` marks the pixel clusters, one of which is one space point
        sp_x=np.asarray(ev["CLx"])[is_pixel].astype(np.float32),
        sp_y=np.asarray(ev["CLy"])[is_pixel].astype(np.float32),
        sp_z=np.asarray(ev["CLz"])[is_pixel].astype(np.float32),
        sp_primary=np.asarray(sp_primary, dtype=bool),
        sp_accepted=np.asarray(sp_accepted, dtype=bool),
        pt=pt[selected] / 1000.0,  # MeV -> GeV
        eta=eta[selected],
        phi=phi.astype(np.float32),
        d0=d0.astype(np.float32),
        z0=z0.astype(np.float32),
        prod_r=np.asarray(ev["Part_radius"])[selected],
        prod_z=np.asarray(ev["Part_vz"])[selected],
        primary=is_primary[selected],
        num_hits=num_hits[selected],
    )
