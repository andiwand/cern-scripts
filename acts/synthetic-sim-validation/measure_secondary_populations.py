#!/usr/bin/env python3
"""What the reference's secondaries are made of, measured on ColliderML.

Three questions the fit cannot answer, all of them about the *shape* of the
secondary population rather than its normalisation, and all of them needing
parent links and no truth-link threshold - which is ColliderML and not the ITk
dump:

1. **Is the transverse kick a property of the interaction or of the daughter?**
   The generator draws it independently of the daughter's own momentum, which
   puts a floor of a couple of hundred MeV under every secondary it makes. A
   daughter cannot carry a kick larger than its momentum, so the question is
   whether `kT` or `kT / p` is the stable variable.
2. **How fast does the spread of the momentum law grow with the parent?**
   `secondaryMomentumSpread` is one number.
3. **What is the soft population?** Two thirds of the reference's secondaries
   are below a hundred MeV and the generator has almost none. They are what a
   stub channel would stand for, so its yield, its cluster count and how far its
   clusters sit from the production point are read off here.

    ./measure_secondary_populations.py --events 20
"""

from __future__ import annotations

import argparse

import numpy as np
import pyarrow.parquet as pq

import fullsim_colliderml as cml

#: Solenoid field of the Open Data Detector
B_FIELD_T = 2.0
#: Radius of curvature in mm of a unit charge with a transverse momentum in GeV
RADIUS_PER_PT = 1.0e3 / (0.299792458 * B_FIELD_T)

PARTICLE_COLUMNS = ["particle_id", "parent_id", "charge", "primary", "pdg_id",
                    "vx", "vy", "vz", "px", "py", "pz"]
HIT_COLUMNS = ["x", "y", "z", "particle_id", "volume_id", "layer_id"]
#: The pixel volumes of the Open Data Detector
PIXEL_VOLUMES = (16, 17, 18)


def parent_direction_at(parent, point):
    """Unit momentum direction of a parent where its daughter was produced.

    The parent has turned in the solenoid between its own vertex and the
    production point, by the angle its transverse chord subtends. Ignoring that
    biases the opening angle by more than the opening angle itself for a parent
    of a few GeV.

    @param parent columns of the parent, as arrays
    @param point the production point, as (x, y, z) arrays
    @return the unit direction, as (x, y, z) arrays
    """
    pt = np.hypot(parent["px"], parent["py"])
    radius = np.maximum(pt * RADIUS_PER_PT, 1e-6)
    chord = np.hypot(point[0] - parent["vx"], point[1] - parent["vy"])
    gamma = 2.0 * np.arcsin(np.clip(chord / (2.0 * radius), -1.0, 1.0))
    phi = np.arctan2(parent["py"], parent["px"]) - np.sign(parent["charge"]) * gamma
    total = np.maximum(np.hypot(pt, parent["pz"]), 1e-9)
    sin_theta = pt / total
    return (sin_theta * np.cos(phi), sin_theta * np.sin(phi),
            parent["pz"] / total)


def log_spread(values):
    """Half-width of the central 68 % in e-folds, i.e. a log-normal sigma read
    off the sample rather than fitted.

    @param values positive values
    @return the spread, or nan for an empty sample
    """
    values = values[values > 0.0]
    if len(values) < 20:
        return float("nan")
    logs = np.log(values)
    return 0.5 * (np.quantile(logs, 0.84) - np.quantile(logs, 0.16))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events", type=int, default=20)
    parser.add_argument("--local", default=None)
    args = parser.parse_args()

    particles = pq.ParquetFile(cml._shard("ttbar", "pu200", "particles",
                                          args.local))
    hits = pq.ParquetFile(cml._shard("ttbar", "pu200", "tracker_hits",
                                     args.local))

    daughter_p, kick, longitudinal, parent_p = [], [], [], []
    neutral_parent = charged_parent = 0
    soft_pt, soft_hits, soft_reach, soft_layers = [], [], [], []
    all_pt = []
    num_events = 0

    for particle_batch, hit_batch in zip(
            particles.iter_batches(batch_size=1, columns=PARTICLE_COLUMNS),
            hits.iter_batches(batch_size=1, columns=HIT_COLUMNS)):
        if num_events >= args.events:
            break
        num_events += 1
        # `to_pylist` and not `asarray` on the batch: a column is a list per
        # event, and arrow hands back its own scalars otherwise
        raw_particles = particle_batch.to_pylist()[0]
        raw_hits = hit_batch.to_pylist()[0]
        part = {name: np.asarray(raw_particles[name])
                for name in PARTICLE_COLUMNS}
        hit = {name: np.asarray(raw_hits[name]) for name in HIT_COLUMNS}
        pixel = np.isin(hit["volume_id"], PIXEL_VOLUMES)
        hit = {name: value[pixel] for name, value in hit.items()}

        identifier = part["particle_id"]
        order = np.argsort(identifier)
        sorted_id = identifier[order]

        def rows(wanted):
            """Rows of the particle table for a set of ids, and whether each was
            found."""
            where = np.clip(np.searchsorted(sorted_id, wanted), 0,
                            len(sorted_id) - 1)
            found = sorted_id[where] == wanted
            return order[where], found

        pt = np.hypot(part["px"], part["py"])
        momentum = np.hypot(pt, part["pz"])
        secondary = (~part["primary"].astype(bool)) & (part["charge"] != 0)

        # --- 1 and 2: the kinematics against a resolvable parent -------------
        index, found = rows(part["parent_id"])
        has_parent = secondary & found & (index != np.arange(len(identifier)))
        parent_charge = np.where(has_parent, part["charge"][index], 0.0)
        neutral_parent += int(np.sum(has_parent & (parent_charge == 0)))
        charged_parent += int(np.sum(has_parent & (parent_charge != 0)))

        usable = has_parent & (parent_charge != 0) & (momentum > 0.0)
        if np.any(usable):
            parent = {name: part[name][index][usable]
                      for name in ("px", "py", "pz", "vx", "vy", "vz",
                                   "charge")}
            axis = parent_direction_at(
                parent, (part["vx"][usable], part["vy"][usable],
                         part["vz"][usable]))
            px, py, pz = (part["px"][usable], part["py"][usable],
                          part["pz"][usable])
            along = px * axis[0] + py * axis[1] + pz * axis[2]
            total = np.hypot(np.hypot(px, py), pz)
            across = np.sqrt(np.maximum(total ** 2 - along ** 2, 0.0))
            daughter_p.append(total)
            kick.append(across)
            longitudinal.append(along)
            parent_p.append(np.hypot(np.hypot(parent["px"], parent["py"]),
                                     parent["pz"]))

        # --- 3: the soft population and its clusters ------------------------
        all_pt.append(pt[secondary])
        counts = {}
        layers = {}
        reach = {}
        hit_index, hit_found = rows(hit["particle_id"])
        for j in np.nonzero(hit_found)[0]:
            row = hit_index[j]
            if not secondary[row]:
                continue
            counts[row] = counts.get(row, 0) + 1
            layers.setdefault(row, set()).add(
                (int(hit["volume_id"][j]), int(hit["layer_id"][j])))
            distance = np.hypot(np.hypot(hit["x"][j] - part["vx"][row],
                                         hit["y"][j] - part["vy"][row]),
                                hit["z"][j] - part["vz"][row])
            reach[row] = max(reach.get(row, 0.0), distance)
        for row, count in counts.items():
            if pt[row] < 0.1:
                soft_pt.append(pt[row])
                soft_hits.append(count)
                soft_layers.append(len(layers[row]))
                soft_reach.append(reach[row])

    print(f"{num_events} events\n")

    parent_share = neutral_parent + charged_parent
    print("parent of a charged secondary")
    print(f"  neutral {neutral_parent / max(parent_share, 1):.3f}"
          f"   charged {charged_parent / max(parent_share, 1):.3f}")

    total = np.concatenate(daughter_p)
    across = np.concatenate(kick)
    along = np.concatenate(longitudinal)
    pp = np.concatenate(parent_p)
    print(f"\n1. the kick against the daughter's own momentum "
          f"({len(total)} daughters of a charged parent)")
    print(f"  {'daughter p [GeV]':<20}{'n':>8}{'median kT':>12}"
          f"{'median kT/p':>14}")
    edges = [0.0, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 1e9]
    for lo, hi in zip(edges[:-1], edges[1:]):
        pick = (total >= lo) & (total < hi)
        if pick.sum() < 20:
            continue
        print(f"  {lo:6.2f} - {hi:<11.2f}{pick.sum():8d}"
              f"{np.median(across[pick]):12.4f}"
              f"{np.median(across[pick] / total[pick]):14.4f}")
    print(f"  {'all':<20}{len(total):8d}{np.median(across):12.4f}"
          f"{np.median(across / total):14.4f}")
    print("  a Rayleigh scale of 0.21 GeV has a median of 0.247 GeV")

    print("\n2. the momentum law against the parent")
    print("  the daughter's *total* momentum, which is what has to be drawn "
          "once the\n  kick is part of it rather than added to it")
    print(f"  {'parent p [GeV]':<20}{'n':>8}{'median p':>12}{'spread':>10}"
          f"{'median kT':>12}")
    edges = [0.1, 0.3, 1.0, 3.0, 10.0, 30.0, 1e9]
    for lo, hi in zip(edges[:-1], edges[1:]):
        pick = (pp >= lo) & (pp < hi)
        if pick.sum() < 20:
            continue
        print(f"  {lo:6.2f} - {hi:<11.2f}{pick.sum():8d}"
              f"{np.median(total[pick]):12.4f}"
              f"{log_spread(total[pick]):10.2f}"
              f"{np.median(across[pick]):12.4f}")
    scale = np.median(total[(pp >= 0.9) & (pp < 1.1)]) if np.any(
        (pp >= 0.9) & (pp < 1.1)) else float("nan")
    print(f"  median at a parent of one GeV: {scale:.4f} GeV")

    pt_all = np.concatenate(all_pt)
    print(f"\n3. the soft population, per event")
    print(f"  charged secondaries              "
          f"{len(pt_all) / num_events:9.0f}")
    for cut in (0.005, 0.02, 0.05, 0.1):
        share = np.mean(pt_all < cut)
        print(f"    below {cut * 1e3:5.0f} MeV                "
              f"{np.sum(pt_all < cut) / num_events:9.0f}   ({share:.3f})")
    soft_hits = np.asarray(soft_hits)
    soft_layers = np.asarray(soft_layers)
    soft_reach = np.asarray(soft_reach)
    soft_pt = np.asarray(soft_pt)
    print(f"\n  of those below 100 MeV that leave a pixel cluster: "
          f"{len(soft_hits) / num_events:.0f} per event")
    print(f"  {'pT [MeV]':<16}{'n':>8}{'clusters':>10}{'layers':>9}"
          f"{'reach [mm]':>12}")
    edges = [0.0, 0.005, 0.02, 0.05, 0.1]
    for lo, hi in zip(edges[:-1], edges[1:]):
        pick = (soft_pt >= lo) & (soft_pt < hi)
        if pick.sum() < 5:
            continue
        print(f"  {lo * 1e3:5.0f} - {hi * 1e3:<8.0f}{pick.sum():8d}"
              f"{soft_hits[pick].mean():10.2f}{soft_layers[pick].mean():9.2f}"
              f"{np.median(soft_reach[pick]):12.1f}")
    print(f"  {'all below 100':<16}{len(soft_hits):8d}"
          f"{soft_hits.mean():10.2f}{soft_layers.mean():9.2f}"
          f"{np.median(soft_reach):12.1f}")


if __name__ == "__main__":
    main()
