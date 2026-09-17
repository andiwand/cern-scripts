#!/usr/bin/env python3
"""Fold perf script stacks: shares under TrackFindingRzAlg::makeTrack by direct callee and by leaf."""
import sys, re, collections, subprocess
data = sys.argv[1] if len(sys.argv) > 1 else "perf.data"
proc = subprocess.Popen(["perf", "script", "-i", data, "--no-inline", "-F", "comm,ip,sym,dso"],
                        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, errors="replace")
FRAME = re.compile(r"^\s+[0-9a-f]+\s+(.*?)\s+\((.*)\)\s*$")
def short(s):
    s = re.sub(r"\(.*", "", s)          # drop the argument list
    return s.strip()[:110]
total = 0; stacks = []; cur = None
by_direct = collections.Counter(); by_leaf = collections.Counter(); inclusive = collections.Counter()
n_make = 0; n_find = 0; n_alg = 0
KEYS = ["TrackFindingRzAlg::makeTrack", "TrackFindingRzAlg::execute", "RzTrackFinder::findTrack",
        "TrackFindingRzAlg::fillGrid", "TrackFindingAlg::execute", "OnTrackCalibrator", "VectorMultiTrajectory::addTrackState_impl",
        "freeToBoundJacobian", "transformFreeToBoundParameters", "findSurface", "calculateTrackQuantities", "allocateCalibrated", "pathToPlane", "transport"]
def flush(frames):
    global total, n_make, n_alg, n_find
    if not frames: return
    total += 1
    syms = [short(f) for f in frames]     # leaf first
    seen = set()
    for s in syms:
        for k in KEYS:
            if k in s and k not in seen:
                inclusive[k] += 1; seen.add(k)
    idx = next((i for i, s in enumerate(syms) if "TrackFindingRzAlg::makeTrack" in s), None)
    if idx is None: return
    n_make += 1
    direct = syms[idx - 1] if idx > 0 else "<self>"
    by_direct[direct] += 1
    by_leaf[syms[0] if idx > 0 else "<self>"] += 1
frames = []
for line in proc.stdout:
    if not line.strip():
        flush(frames); frames = []; continue
    m = FRAME.match(line)
    if m: frames.append(m.group(1))
flush(frames)
print(f"samples {total}, under makeTrack {n_make} ({100*n_make/max(1,total):.2f}%)")
print("inclusive shares of the whole job:")
for k in KEYS:
    print(f"  {inclusive[k]:7d} {100*inclusive[k]/max(1,total):6.2f}%  {k}")
print("\nunder makeTrack, by direct callee:")
for s, n in by_direct.most_common(25):
    print(f"  {n:6d} {100*n/max(1,n_make):6.2f}%  {s}")
print("\nunder makeTrack, by leaf:")
for s, n in by_leaf.most_common(30):
    print(f"  {n:6d} {100*n/max(1,n_make):6.2f}%  {s}")
