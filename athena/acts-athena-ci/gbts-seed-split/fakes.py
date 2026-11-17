#!/usr/bin/env python3
"""Fake rate from truthMatchProbability over all tracks (linked or not; unlinked tracks are mostly unstored
Geant4 secondaries with prob ~1). usage: fakes.py dir...   (cached in dir/fakes.pkl)"""
import sys, os, pickle, collections
EB = [0, 0.6, 1.5, 2.5, 4.0]
def scan(d):
    c = os.path.join(d, "fakes.pkl")
    if os.path.exists(c): return pickle.load(open(c, "rb"))
    import ROOT
    ROOT.xAOD.Init().ignore()
    f = ROOT.TFile.Open(os.path.join(d, "myAOD.pool.root")); t = ROOT.xAOD.MakeTransientTree(f, "CollectionTree")
    C = collections.Counter()
    for i in range(t.GetEntries()):
        t.GetEntry(i)
        for tp in t.InDetTrackParticles:
            a = abs(tp.eta()); b = next(f"{lo}-{hi}" for lo, hi in zip(EB, EB[1:]) if a < hi or hi == EB[-1])
            p = tp.auxdataConst['float']('truthMatchProbability')
            linked = bool(ROOT.xAOD.TruthHelpers.getTruthParticle(tp))
            for k in (b, "all"):
                C[(k, "trk")] += 1; C[(k, "p<0.5")] += p < 0.5; C[(k, "p<0.7")] += p < 0.7; C[(k, "unlinked")] += not linked
    pickle.dump(C, open(c, "wb")); return C
R = [(d, scan(d)) for d in sys.argv[1:]]
ref = R[0][1]
print(f"{'':16s}" + "".join(f"{k:>34s}" for k in [f"{lo}-{hi}" for lo, hi in zip(EB, EB[1:])] + ["all"]))
for d, C in R:
    row = f"{os.path.basename(d):16s}"
    for k in [f"{lo}-{hi}" for lo, hi in zip(EB, EB[1:])] + ["all"]:
        n = C[(k, "trk")]; row += f"  {n:7d} f.5 {100*C[(k,'p<0.5')]/n:5.3f}% f.7 {100*C[(k,'p<0.7')]/n:5.2f}%"
    print(row)
print("extra tracks vs first: total / fake(p<0.5) / p<0.7 / unlinked")
for d, C in R[1:]:
    print(f"  {os.path.basename(d):16s} {C[('all','trk')]-ref[('all','trk')]:+7d} {C[('all','p<0.5')]-ref[('all','p<0.5')]:+6d} {C[('all','p<0.7')]-ref[('all','p<0.7')]:+6d} {C[('all','unlinked')]-ref[('all','unlinked')]:+6d}")
