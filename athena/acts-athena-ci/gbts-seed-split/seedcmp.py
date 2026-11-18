#!/usr/bin/env python3
"""Seeding efficiency ACTS vs legacy: fraction of particles (pT > 1 GeV, |eta| < 0.6, HS + PU, from the splitsum truth)
with at least one pure seed (every SP of the seed from that one particle).
ACTS: SeedTruthDumpAlg lines "P ev key nsp uid pt eta" (key 0 pixel, 1 strip).
Legacy: SeedMakerValidation.root seeds, SPs matched by position to the ACTS-job pixel SPs with truth ("Q ev x y z uid pt eta";
the legacy PRD truth resolves only hard-scatter particles here).
Also majority matching from "M ev key nsp nbest uid pt eta" lines.\nusage: seedcmp.py <acts seeds dir> <legacy seeds dir> <truth dir with splitsum_pu.pkl> [--test]"""
import sys, os, pickle, collections
import numpy as np
dA, dL, dT = sys.argv[1:4]; TEST = "--test" in sys.argv
def tkey(ev, uid, pt, eta, idx):
    c = [k for k in idx.get((ev, uid), []) if abs(k[2] - pt) < 1. and abs(k[3] - eta) < 1e-3]
    return c[0] if c else None
if not TEST:
    _, truth = pickle.load(open(os.path.join(dT, "splitsum_pu.pkl"), "rb"))
    D = {k for k, v in truth.items() if v[1] in ("0.0-0.3", "0.3-0.6")}
    idx = collections.defaultdict(list)
    for k in D: idx[(k[0], k[1])].append(k)
# ACTS
A = collections.defaultdict(set); AM = collections.defaultdict(set)
for line in open(os.path.join(dA, "seedtruth.txt")):
    f = line.split()
    if f[0] == "P": A[int(f[2])].add((int(f[1]), int(f[4]), float(f[5]), float(f[6])))
    elif f[0] == "M": AM[int(f[2])].add((int(f[1]), int(f[5]), float(f[6]), float(f[7])))   # >= 3 SPs and >= 50%
# legacy SP truth
Q = collections.defaultdict(list)
for line in open(os.path.join(dA, "seedtruth.txt")):
    f = line.split()
    if f[0] != "Q": continue
    Q[int(f[1])].append((float(f[2]), float(f[3]), float(f[4]), int(f[5]), float(f[6]), float(f[7])))
from scipy.spatial import cKDTree
KT = {}
for ev, q in Q.items():
    a = np.array([x[:3] for x in q]); KT[ev] = (cKDTree(a), q)
import ROOT
f = ROOT.TFile.Open(os.path.join(dL, "SeedMakerValidation.root"))
t = [k.ReadObj() for k in f.GetListOfKeys() if k.ReadObj().InheritsFrom("TTree")][0]
LG = collections.defaultdict(set); n = nm = nsp = 0; dmin = []
for e in t:
    ev = int(e.eventNumber)
    if ev not in KT: continue
    tree, q = KT[ev]; n += 1
    parts = None
    for x, y, z in ((e.x1, e.y1, e.z1), (e.x2, e.y2, e.z2), (e.x3, e.y3, e.z3)):
        nsp += 1
        d, i = tree.query([x, y, z], k=8, distance_upper_bound=0.05)
        hit = [q[j] for dd, j in zip(d, i) if np.isfinite(dd)]
        if hit: nm += 1
        if TEST and len(dmin) < 20000: dmin.append(d[0])
        s = {(h[3], h[4], h[5]) for h in hit}
        parts = s if parts is None else parts & s
    for uid, pt, eta in parts or ():
        rs = (e.r1, e.r2, e.r3); typ = 0 if max(rs) < 330 else 1 if min(rs) > 330 else 2   # by SP radius: pixel / strip / mixed
        if abs(eta) < 0.8 and pt > 900: LG[typ].add((ev, uid, pt, eta))
print(f"legacy seeds {n}, SPs matched to a truth SP within 0.05 mm: {100*nm/max(nsp,1):.1f}%")
if TEST:
    dm = np.array(dmin); print("nearest truth SP distance quantiles:", np.quantile(dm[np.isfinite(dm)], [0.5, 0.9, 0.99]) if np.isfinite(dm).any() else "none within 0.05")
    sys.exit()
def eff(S):
    hit = {tkey(ev, uid, pt * 1., eta, idx) for ev, uid, pt, eta in S} - {None}
    return hit
AP, AS = eff(A[0]), eff(A[1])
print("legacy pure seeds by type (0 pixel, 1 strip, 2 mixed, by SP radius):", {k: len(v) for k, v in LG.items()})
LP, LS = eff(LG.get(0, set())), eff(LG.get(1, set()) | LG.get(2, set()))
N = len(D)
pc = lambda s: f"{100*len(s)/N:6.2f}%"
print(f"particles {N}  (pT > 1 GeV, |eta| < 0.6, HS + PU), fraction with >= 1 pure seed:")
print(f"{'':10s} {'pixel':>8s} {'strip':>8s} {'any':>8s}")
print(f"{'ACTS':10s} {pc(AP):>8s} {pc(AS):>8s} {pc(AP | AS):>8s}")
print(f"{'legacy':10s} {pc(LP):>8s} {pc(LS):>8s} {pc(LP | LS):>8s}")
print(f"{'legacy-ACTS':10s} {100*(len(LP)-len(AP))/N:+7.2f}% {100*(len(LS)-len(AS))/N:+7.2f}% {100*(len(LP|LS)-len(AP|AS))/N:+7.2f}%")
LA, AA = LP | LS, AP | AS
print(f"any seed: legacy only {len(LA - AA)}, ACTS only {len(AA - LA)}")
AMP, AMS = eff(AM[0]), eff(AM[1])
print(f"\nmajority matching (>= 3 SPs of the particle and >= 50% of the seed's SPs; legacy 3-SP seeds: same as pure):")
print(f"{'':10s} {'pixel':>8s} {'strip':>8s} {'any':>8s}")
print(f"{'ACTS':10s} {pc(AMP):>8s} {pc(AMS):>8s} {pc(AMP | AMS):>8s}")
print(f"{'legacy':10s} {pc(LP):>8s} {pc(LS):>8s} {pc(LP | LS):>8s}")
print(f"{'legacy-ACTS':10s} {100*(len(LP)-len(AMP))/N:+7.2f}% {100*(len(LS)-len(AMS))/N:+7.2f}% {100*(len(LP|LS)-len(AMP|AMS))/N:+7.2f}%")
