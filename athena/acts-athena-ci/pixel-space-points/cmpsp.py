#!/usr/bin/env python3
"""Compare the pixel space point variances of two AODs, entry by entry."""
import sys, ROOT, array
ROOT.gROOT.SetBatch(True)

def load(path):
    f = ROOT.TFile.Open(path)
    t = f.Get("CollectionTree")
    if t is None:
        raise SystemExit(f"no CollectionTree in {path}")
    return f, t

def branches(t, pat):
    return [b.GetName() for b in t.GetListOfBranches() if pat in b.GetName()]

if len(sys.argv) < 3:
    fa, ta = load(sys.argv[1])
    print("\n".join(branches(ta, "ITkPixelSpacePoints")))
    raise SystemExit

fa, ta = load(sys.argv[1])
fb, tb = load(sys.argv[2])
names = [n for n in branches(ta, "ITkPixelSpacePointsAux") if n.split(".")[-1] in ("varianceR", "varianceZ", "radius")]
print("comparing:", names)
na, nb = ta.GetEntries(), tb.GetEntries()
print(f"entries {na} vs {nb}")
worst = {}
ndiff = {}
ntot = 0
for i in range(min(na, nb)):
    ta.GetEntry(i); tb.GetEntry(i)
    for n in names:
        va = getattr(ta, n); vb = getattr(tb, n)
        if len(va) != len(vb):
            print(f"event {i} {n}: size {len(va)} vs {len(vb)}"); continue
        if n == names[0]: ntot += len(va)
        w = worst.get(n, 0.0); d = ndiff.get(n, 0)
        for a, b in zip(va, vb):
            if a != b:
                d += 1
                den = abs(a) if a else 1.0
                w = max(w, abs(a - b) / den)
        worst[n] = w; ndiff[n] = d
print(f"space points compared: {ntot}")
for n in names:
    print(f"  {n.split('.')[-1]:12s} differing values: {ndiff.get(n,0)}   max rel dev: {worst.get(n,0):.3e}")
