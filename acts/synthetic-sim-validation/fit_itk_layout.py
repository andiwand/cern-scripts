#!/usr/bin/env python3
"""Derive an ITk pixel layout from a GNN4ITk full-simulation dump.

The ODD and Generic layouts in `ActsFatras::Synthetic` are checked against their
real geometry, because ACTS can build both. The ITk has no description in the
repository, so its layout was originally written from published numbers. The dump
does contain the cluster positions though, and it groups them by
`CLbarrel_endcap` and `CLlayer_disk`, so the layout can be read off the data
instead of guessed.

Prints a `BarrelEndcapDescription` ready to paste into
`Fatras/src/Synthetic/DetectorLayout.cpp`.
"""

from __future__ import annotations

import argparse

import numpy as np
import uproot

TREE = "GNN4ITk"
BRANCHES = ["CLx", "CLy", "CLz", "CLhardware", "CLbarrel_endcap", "CLlayer_disk"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dump", help="the GNN4ITk dump ROOT file")
    parser.add_argument("--events", type=int, default=2)
    parser.add_argument("--quantile", type=float, default=0.005,
                        help="quantile trimmed off each end when reporting an "
                             "extent, so that a few stray clusters do not set it")
    args = parser.parse_args()

    tree = uproot.open(args.dump)[TREE]
    r_by_group: dict[tuple[int, int], list[np.ndarray]] = {}
    z_by_group: dict[tuple[int, int], list[np.ndarray]] = {}

    for batch in tree.iterate(BRANCHES, entry_stop=args.events, step_size=1,
                              library="np"):
        for i in range(len(batch["CLx"])):
            ev = {k: v[i] for k, v in batch.items()}
            pixel = np.asarray([str(h) for h in ev["CLhardware"]]) == "PIXEL"
            r = np.hypot(ev["CLx"], ev["CLy"])[pixel]
            z = ev["CLz"][pixel]
            bec = ev["CLbarrel_endcap"][pixel]
            layer = ev["CLlayer_disk"][pixel]
            for key in set(zip(bec.tolist(), layer.tolist())):
                sel = (bec == key[0]) & (layer == key[1])
                r_by_group.setdefault(key, []).append(r[sel])
                z_by_group.setdefault(key, []).append(z[sel])

    lo, hi = args.quantile, 1.0 - args.quantile
    print("%-22s %9s %9s %9s %9s %9s %9s"
          % ("group", "n/event", "r mean", "r lo", "r hi", "z mean", "|z| lo"))
    barrel, disks = [], {}
    for key in sorted(r_by_group):
        r = np.concatenate(r_by_group[key])
        z = np.concatenate(z_by_group[key])
        bec, layer = key
        name = ("barrel" if bec == 0 else "endcap%+d" % np.sign(bec)) + " L%d" % layer
        rq = np.quantile(r, [lo, hi])
        zq = np.quantile(z, [lo, hi])
        print("%-22s %9.0f %9.2f %9.2f %9.2f %9.1f %9.1f"
              % (name, len(r) / args.events, r.mean(), rq[0], rq[1],
                 z.mean(), np.quantile(np.abs(z), lo)))
        if bec == 0:
            barrel.append((layer, r.mean(), np.quantile(np.abs(z), hi)))
        elif bec > 0:
            disks[layer] = (np.abs(z).mean(), rq[0], rq[1])

    print()
    print("barrel radii  : %s"
          % ", ".join("%.1f" % r for _, r, _ in sorted(barrel)))
    print("barrel |z| max: %.1f (the layers differ; this is the largest)"
          % max(h for _, _, h in barrel))
    print()
    print("The barrel is a set of cylinders and matches the synthetic model, but")
    print("the endcap does not. Each `CLlayer_disk` group of the ITk pixel endcap")
    print("is a ring at roughly fixed radius spanning a long range in z - the")
    print("inclined and ring sections - rather than a planar disk at fixed z.")
    print("Compare the r and z extents above: for example endcap L0 sits at")
    print("r = 33..53 mm across |z| = 261 mm and beyond, which is a cylinder, not")
    print("a disk.")
    print()
    print("So the nine planar disks of `itkPixelDescription()` are a stand-in for")
    print("that structure, not a description of it, which is what its doc comment")
    print("says and what `secondaryRate` is documented to absorb. Expect the total")
    print("space point count to agree and the z distribution not to.")


if __name__ == "__main__":
    main()
