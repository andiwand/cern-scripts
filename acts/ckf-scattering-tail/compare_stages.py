#!/usr/bin/env python3
"""Compare per-event checksums of each stage between repeated runs."""
import hashlib
import sys

import numpy as np
import uproot

STAGES = [
    ("particles_generated.root", "particles", ["particle_hash", "px", "py", "pz", "vx", "vy", "vz"]),
    ("particles_generated_selected.root", "particles", ["particle_hash", "px", "py", "pz"]),
    ("particles_simulated.root", "particles", ["particle_hash", "px", "py", "pz"]),
    ("simhits.root", "hits", ["barcode_vertex_primary", "barcode_particle", "geometry_id", "tx", "ty", "tz", "tpx", "deltapx"]),
    ("particles_selected.root", "particles", ["particle_hash", "px"]),
]


def digests(path, tree, branches):
    t = uproot.open(path)[tree]
    if tree == "hits":
        a = t.arrays(["event_id"] + branches, library="np")
        out = {}
        ev = a["event_id"]
        for e in np.unique(ev):
            m = ev == e
            cols = [np.asarray(a[b][m]) for b in branches]
            # order-independent: sort rows
            arr = np.rec.fromarrays(cols)
            arr.sort()
            out[int(e)] = (int(m.sum()), hashlib.md5(arr.tobytes()).hexdigest()[:10])
        return out
    a = t.arrays(["event_id"] + branches, library="np")
    out = {}
    for i, e in enumerate(a["event_id"]):
        cols = [np.asarray(a[b][i]) for b in branches]
        arr = np.rec.fromarrays(cols)
        arr.sort()
        out[int(e)] = (len(arr), hashlib.md5(arr.tobytes()).hexdigest()[:10])
    return out


runs = sys.argv[1:]
for fname, tree, branches in STAGES:
    ds = [digests(f"{r}/{fname}", tree, branches) for r in runs]
    events = sorted(ds[0])
    diff = [e for e in events if len({d.get(e) for d in ds}) > 1]
    print(f"{fname:36s} events {len(events)}  differing: {diff}")
    for e in diff[:4]:
        print("    event", e, [d.get(e) for d in ds])
