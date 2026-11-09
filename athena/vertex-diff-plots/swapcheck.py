#!/usr/bin/env python3
"""Find vertex pairs that change places in the sorted vertex list.

compare_pv.py matches vertices by (run, event, vertex index). If two
vertices swap places (for example because one loses a track and its
sum pT^2 drops), the match pairs two different vertices and the summary
shows a shift of centimetres. This script lists these pairs and gives the
shift table without them.

    swapcheck.py <npz dir> [sample ...]

Needs numpy only (source setup_env.sh compare).
"""
import sys

import numpy as np

SWAP_DZ = 1.0  # mm; a real shift of 1 mm would be far outside the change sizes seen so far


def keys(d):
    return list(zip(d["ev_run"][d["v_ev"]], d["ev_evt"][d["v_ev"]], d["v_i"]))


def check(npz_dir, sample):
    r = np.load(f"{npz_dir}/{sample}_ref.npz")
    n = np.load(f"{npz_dir}/{sample}_new.npz")
    ref_index = {k: j for j, k in enumerate(keys(r))}
    run_r, evt_r = r["ev_run"][r["v_ev"]], r["ev_evt"][r["v_ev"]]

    swaps, ntrk_changed, shifts = [], 0, []
    for k, (run, evt, i) in enumerate(keys(n)):
        j = ref_index.get((run, evt, i))
        if j is None:
            continue
        dz = abs(n["v_z"][k] - r["v_z"][j])
        if dz > SWAP_DZ:
            same_event = (run_r == run) & (evt_r == evt)
            nearest = np.argmin(abs(r["v_z"][same_event] - n["v_z"][k]))
            swaps.append((evt, i, r["v_i"][same_event][nearest],
                          r["v_ntrk"][j], n["v_ntrk"][k], dz))
            continue
        if r["v_ntrk"][j] != n["v_ntrk"][k]:
            ntrk_changed += 1
            continue
        sz = np.sqrt(r["v_czz"][j])
        shifts.append((dz, dz / sz if sz > 0 else 0.0))

    print(f"== {sample}")
    for evt, i, i_ref, nt_r, nt_n, dz in swaps:
        print(f"  swap: event {evt} vertex {i} now matches reference vertex {i_ref}"
              f" (ntrk {nt_r} -> {nt_n}, index-matched |dz| {dz:.1f} mm)")
    a = np.array(shifts)
    changed = a[a[:, 0] > 0]
    print(f"  vertices with same ntrk: {len(a)}, changed: {len(changed)},"
          f" ntrk changed: {ntrk_changed}, swapped: {len(swaps)}")
    if len(changed):
        print(f"  median dz/sz {np.median(changed[:, 1]):.2g}, max dz/sz {a[:, 1].max():.3g},"
              f" max |dz| {a[:, 0].max() * 1e3:.3g} um")


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    samples = sys.argv[2:] or ["q442", "q452", "q449", "q454", "q447"]
    for s in samples:
        check(sys.argv[1], s)


if __name__ == "__main__":
    main()
