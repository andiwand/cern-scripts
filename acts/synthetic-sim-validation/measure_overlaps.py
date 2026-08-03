#!/usr/bin/env python3
"""Measure module overlap in the ITk dump: how many clusters one layer crossing
actually leaves, and where the extra ones sit relative to the first.

A particle hits the same layer twice for two reasons and only one is overlap. It
grazes the edge of a module and catches its neighbour - in phi, the shingling
within a stave or ring, or in eta, the next module along - or it curls back. The
module identifiers separate them: an overlap partner is an adjacent module, a
re-crossing is not, and `--min-pt` keeps the curlers out of the fitted number.

    ./measure_overlaps.py '~/Downloads/*DumpGNNITk_v9.root' --events 10
"""

from __future__ import annotations

import argparse
import glob
import os

import numpy as np
import uproot

TREE = "GNN4ITk"
PRIMARY_BARCODE_LIMIT = 200_000

BRANCHES = [
    "CLx", "CLy", "CLz", "CLhardware", "CLbarrel_endcap", "CLlayer_disk",
    "CLeta_module", "CLphi_module",
    "CLparticleLink_barcode", "CLparticleLink_eventIndex",
    "Part_event_number", "Part_barcode", "Part_pt", "Part_eta", "Part_charge",
]

#: The classes an extra cluster on a layer can fall into
CLASSES = ("phi", "eta", "far")


def _clusters_by_particle(ev):
    """Group the pixel clusters of one event by the primary that made them.

    @param ev the dump's branches for one event
    @return {(interaction, barcode): [(bec, layer, etaMod, phiMod, x, y, z)]}
    """
    hardware = np.asarray([str(h) for h in ev["CLhardware"]])
    out: dict[tuple[int, int], list] = {}
    for i in np.flatnonzero(hardware == "PIXEL"):
        hit = (int(ev["CLbarrel_endcap"][i]), int(ev["CLlayer_disk"][i]),
               int(ev["CLeta_module"][i]), int(ev["CLphi_module"][i]),
               float(ev["CLx"][i]), float(ev["CLy"][i]), float(ev["CLz"][i]))
        for index, barcode in zip(ev["CLparticleLink_eventIndex"][i],
                                  ev["CLparticleLink_barcode"][i]):
            if barcode < PRIMARY_BARCODE_LIMIT:
                out.setdefault((int(index), int(barcode)), []).append(hit)
    return out


def _classify(first, other, phi_modules: int):
    """Which kind of neighbour a second cluster on the same layer is.

    @param first the cluster taken as the crossing
    @param other the second cluster
    @param phi_modules how many modules the ring or stave holds, for the wrap
    @return "phi", "eta" or "far"
    """
    if first[2] == other[2]:
        gap = abs(first[3] - other[3])
        gap = min(gap, phi_modules - gap) if phi_modules else gap
        return "phi" if gap == 1 else "far"
    if abs(first[2] - other[2]) == 1 and first[3] == other[3]:
        return "eta"
    return "far"


def _offset(first, other):
    """The second cluster's position relative to the first, in the frame the
    generator would displace a hit in.

    @return (dr, rdphi, dz)
    """
    r0 = np.hypot(first[4], first[5])
    r1 = np.hypot(other[4], other[5])
    dphi = np.arctan2(other[5], other[4]) - np.arctan2(first[5], first[4])
    dphi = (dphi + np.pi) % (2 * np.pi) - np.pi
    return r1 - r0, 0.5 * (r0 + r1) * dphi, other[6] - first[6]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dump", help="the dump file, or a glob over several")
    parser.add_argument("--events", type=int, default=10)
    parser.add_argument("--min-pt", type=float, default=1000.0,
                        help="MeV; above the curlers, so that a second cluster "
                             "on a layer is overlap and not a re-crossing")
    args = parser.parse_args()

    paths = sorted(glob.glob(os.path.expanduser(args.dump)))
    if not paths:
        raise FileNotFoundError(args.dump)

    # modules seen per (bec, layer, etaModule), which is the phi segmentation
    segmentation: dict[tuple[int, int, int], set] = {}
    # crossings and extra clusters by class, per (bec, layer)
    counts: dict[tuple[int, int], np.ndarray] = {}
    # the offset differs by region, so it is kept per region as well as overall
    regions = ("all", "barrel", "endcap 3+", "endcap 0-2")
    offsets = {region: {name: [] for name in CLASSES} for region in regions}

    remaining = args.events
    for one in paths:
        if remaining <= 0:
            break
        tree = uproot.open(one)[TREE]
        stop = min(tree.num_entries, remaining)
        for batch in tree.iterate(BRANCHES, entry_stop=stop, step_size=1,
                                  library="np"):
            for i in range(len(batch["Part_pt"])):
                ev = {k: v[i] for k, v in batch.items()}
                by_particle = _clusters_by_particle(ev)

                for hits in by_particle.values():
                    for bec, layer, eta_mod, phi_mod, *_ in hits:
                        segmentation.setdefault((bec, layer, eta_mod),
                                                set()).add(phi_mod)

                kinematics = {}
                for e, b, pt, eta, q in zip(ev["Part_event_number"],
                                            ev["Part_barcode"], ev["Part_pt"],
                                            ev["Part_eta"], ev["Part_charge"]):
                    if abs(q) > 0.5 and np.isfinite(eta) and abs(eta) < 4.0 \
                            and pt >= args.min_pt:
                        kinematics[(int(e), int(b))] = (float(pt), float(eta))

                for key, hits in by_particle.items():
                    if key not in kinematics:
                        continue
                    on_layer: dict[tuple[int, int], list] = {}
                    for hit in hits:
                        on_layer.setdefault(hit[:2], []).append(hit)

                    for layer, group in on_layer.items():
                        # the innermost cluster is the crossing, the rest are
                        # read against it
                        group.sort(key=lambda h: (abs(h[6]), h[2], h[3]))
                        row = counts.setdefault(layer, np.zeros(4))
                        row[0] += 1
                        n_phi = len(segmentation.get(
                            (layer[0], layer[1], group[0][2]), ()))
                        region = ("barrel" if layer[0] == 0 else
                                  "endcap 3+" if layer[1] >= 3 else
                                  "endcap 0-2")
                        for other in group[1:]:
                            kind = _classify(group[0], other, n_phi)
                            row[1 + CLASSES.index(kind)] += 1
                            offset = _offset(group[0], other)
                            offsets["all"][kind].append(offset)
                            offsets[region][kind].append(offset)
        remaining -= stop

    print("extra clusters per layer crossing, primaries above %.1f GeV\n"
          % (args.min_pt / 1000.0))
    print("%-14s %10s %8s %8s %8s %8s"
          % ("layer", "crossings", "phi", "eta", "far", "phiMods"))
    total = np.zeros(4)
    for (bec, layer), row in sorted(counts.items()):
        name = "barrel" if bec == 0 else "endcap%+d" % np.sign(bec)
        modules = [len(v) for (b, l, _e), v in segmentation.items()
                   if (b, l) == (bec, layer)]
        print("%-14s %10.0f %8.3f %8.3f %8.3f %8d"
              % ("%s %d" % (name, layer), row[0], row[1] / row[0],
                 row[2] / row[0], row[3] / row[0],
                 max(modules) if modules else 0))
        total += row
    print("%-14s %10.0f %8.3f %8.3f %8.3f"
          % ("all", total[0], total[1] / total[0], total[2] / total[0],
             total[3] / total[0]))

    for label in regions:
        table = offsets[label]
        print("\noffset of an extra cluster [mm], %s" % label)
        print("%-6s %8s %8s %8s %8s %8s %8s"
              % ("class", "n", "dr", "rdphi", "dz", "|dr|", "|rdphi|"))
        for name in CLASSES:
            values = np.asarray(table[name])
            if not len(values):
                continue
            print("%-6s %8d %8.2f %8.2f %8.2f %8.2f %8.2f"
                  % (name, len(values), np.median(values[:, 0]),
                     np.median(values[:, 1]), np.median(values[:, 2]),
                     np.median(np.abs(values[:, 0])),
                     np.median(np.abs(values[:, 1]))))


if __name__ == "__main__":
    main()
