#!/usr/bin/env python3
"""Efficiency / duplicates / track quality per |eta| for GBTS seed split variants, paired against the first.
usage: splitsum.py [--pu] name=dir ...   (dir holds myAOD.pool.root; cached in dir/splitsum.pkl)
--pu: count pile-up truth too (full-truth sample); otherwise hard scatter only."""
import sys, os, pickle, collections, ctypes, math
EB = [0, 0.3, 0.6, 1.0, 1.5, 2.5, 4.0]
def eb(a):
    for lo, hi in zip(EB, EB[1:]):
        if a < hi: return f"{lo:.1f}-{hi:.1f}"
    return None
def scan(d, pu):
    cache = os.path.join(d, "splitsum%s.pkl" % ("_pu" if pu else ""))
    if os.path.exists(cache) and os.path.getmtime(cache) > os.path.getmtime(os.path.join(d, "myAOD.pool.root")):
        return pickle.load(open(cache, "rb"))
    import ROOT
    ROOT.xAOD.Init().ignore()
    def u8(tp, s):
        c = ctypes.c_uint8(0)
        return c.value if tp.summaryValue(c, getattr(ROOT.xAOD, s)) else 0
    f = ROOT.TFile.Open(os.path.join(d, "myAOD.pool.root")); t = ROOT.xAOD.MakeTransientTree(f, "CollectionTree")
    C = collections.Counter(); truth = {}
    for i in range(t.GetEntries()):
        t.GetEntry(i); ev = t.EventInfo.eventNumber()
        best = {}; ntrk = collections.Counter()
        for tp in t.InDetTrackParticles:
            b = eb(abs(tp.eta()))
            prob = tp.auxdataConst['float']('truthMatchProbability') if tp.isAvailable['float']('truthMatchProbability') else -1
            tru = ROOT.xAOD.TruthHelpers.getTruthParticle(tp)
            npix = u8(tp, "numberOfPixelHits"); nsct = u8(tp, "numberOfSCTHits")
            nph = u8(tp, "numberOfPixelHoles"); nsh = u8(tp, "numberOfSCTHoles")
            C[f"trk {b}"] += 1; C["trk"] += 1
            C[f"trk {b} hits"] += npix + nsct; C[f"trk {b} pixhits"] += npix; C[f"trk {b} holes"] += nph + nsh
            C[f"trk {b} shared"] += u8(tp, "numberOfPixelSharedHits") + u8(tp, "numberOfSCTSharedHits")
            if tru and prob > 0.5:
                k = (ev, tru.index()); ntrk[k] += 1
                q = (prob, npix + nsct, nph + nsh, npix, u8(tp, "numberOfInnermostPixelLayerHits"), u8(tp, "numberOfNextToInnermostPixelLayerHits"))
                if k not in best or q > best[k]: best[k] = q
            elif tru: C[f"trk {b} lowprob"] += 1
            else: C[f"trk {b} unlinked"] += 1
        hs = set()
        e0 = t.TruthEvents[0]
        for j in range(e0.nTruthParticles()):
            q = e0.truthParticle(j)
            if q: hs.add(q.index())
        for p in t.TruthParticles:
            if p.status() != 1 or p.charge() == 0 or p.pt() < 1000 or abs(p.eta()) > 4.0: continue
            if p.uid() < 0 or p.uid() > 200000: continue
            tag = "HS" if p.index() in hs else "PU"
            if tag == "PU" and not pu: continue
            k = (ev, p.index()); b = eb(abs(p.eta()))
            truth[(ev, p.uid(), round(p.pt(), 1), round(p.eta(), 4))] = (tag, b, p.pt(), best.get(k), ntrk[k])
    r = (C, truth); pickle.dump(r, open(cache, "wb")); return r
args = [a for a in sys.argv[1:] if not a.startswith("--")]; pu = "--pu" in sys.argv
runs = [(a.split("=", 1)[0], scan(a.split("=", 1)[1], pu)) for a in args]
bins = [f"{lo:.1f}-{hi:.1f}" for lo, hi in zip(EB, EB[1:])]
tags = ["HS", "PU"] if pu else ["HS"]
def eff(T, tag, b):
    n = [v for v in T.values() if v[0] == tag and (b is None or v[1] == b)]
    m = sum(1 for v in n if v[3]); return m, len(n)
for tag in tags:
    print(f"== efficiency {tag} pT>1 GeV (matched prob>0.5); diff vs {runs[0][0]} with paired counts lost/gained")
    print(f"{'|eta|':9s}" + "".join(f"{n:>24s}" for n, _ in runs))
    for b in bins + [None]:
        row = f"{b or 'all':9s}"
        m0, n0 = eff(runs[0][1][1], tag, b)
        for k, (n, (C, T)) in enumerate(runs):
            m, nn = eff(T, tag, b)
            if k == 0: row += f"{m/nn:14.4f} ({nn:6d}) "
            else:
                T0 = runs[0][1][1]
                keys = [x for x in T if T[x][0] == tag and (b is None or T[x][1] == b)]
                lost = sum(1 for x in keys if x in T0 and T0[x][3] and not T[x][3])
                gain = sum(1 for x in keys if x in T0 and not T0[x][3] and T[x][3])
                row += f"{(m/nn - m0/n0)*100:+8.2f}% -{lost:4d} +{gain:4d}  "
        print(row)
print("== tracks: count, duplicate rate (particles with >1 matched track), mean hits / pixel hits / holes / shared, unlinked")
for b in bins + [None]:
    print(f"-- |eta| {b or 'all'}")
    for n, (C, T) in runs:
        sel = [v for v in T.values() if (b is None or v[1] == b) and v[3]]
        dup = sum(1 for v in sel if v[4] > 1) / max(1, len(sel))
        hits = sum(v[3][1] for v in sel) / max(1, len(sel)); pix = sum(v[3][3] for v in sel) / max(1, len(sel)); hol = sum(v[3][2] for v in sel) / max(1, len(sel))
        key = f"trk {b}" if b else "trk"
        nt = C[key] if b else C["trk"]
        extra = f"  trk-avg hits {C[key+' hits']/max(1,nt):5.2f} holes {C[key+' holes']/max(1,nt):5.3f} shared {C[key+' shared']/max(1,nt):5.3f} unlinked {C[key+' unlinked']/max(1,nt):6.4f}" if b else ""
        print(f"  {n:10s} trk {nt:7d}  matched-truth: dup {dup:6.4f} hits {hits:5.2f} pix {pix:5.2f} holes {hol:5.3f}{extra}")

PT = [1, 1.5, 2, 3, 5, 1e9]
def ptb(pt):
    for lo, hi in zip(PT, PT[1:]):
        if pt / 1000 < hi: return f"{lo}-{hi if hi < 1e8 else 'inf'}"
print(f"== particles at |eta| < 0.6 found in one variant only, vs {runs[0][0]}, by truth pT [GeV]; and track inner-layer hits")
T0 = runs[0][1][1]
for n, (C, T) in runs[1:]:
    lost = collections.Counter(); gain = collections.Counter(); li = collections.Counter(); gi = collections.Counter()
    for x, v in T.items():
        if v[1] not in ("0.0-0.3", "0.3-0.6") or x not in T0: continue
        a, b = T0[x][3], v[3]
        if a and not b: lost[(v[0], ptb(v[2]))] += 1; li[(a[4], a[5])] += 1
        if b and not a: gain[(v[0], ptb(v[2]))] += 1; gi[(b[4], b[5])] += 1
    print(f"-- {n}: lost {sum(lost.values())} gained {sum(gain.values())}")
    for tag in tags:
        print("   " + tag + " " + "  ".join(f"{p}: -{lost[(tag, p)]}/+{gain[(tag, p)]}" for p in [ptb(x * 1000 + 1) for x in PT[:-1]]))
    print(f"   lost: track in {runs[0][0]} had (L0, L1) hits {dict(li)};  gained: track in {n} had {dict(gi)}")
