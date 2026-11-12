#!/usr/bin/env python3
"""Track truth categories, duplicates, paired efficiency between two AODs.
usage: truthsum.py <AOD_A> <AOD_B> [container]"""
import sys, collections, ctypes, math, pickle
import ROOT
ROOT.xAOD.Init().ignore()
cont = "InDetTrackParticles"
def u8(tp, s):
    c = ctypes.c_uint8(0)
    return c.value if tp.summaryValue(c, getattr(ROOT.xAOD, s)) else 0
def etab(a): return "|eta|<1.5" if a < 1.5 else "1.5-2.5" if a < 2.5 else ">=2.5"
def scan(fn):
    f = ROOT.TFile.Open(fn); t = ROOT.xAOD.MakeTransientTree(f, "CollectionTree")
    C = collections.Counter(); matched = {}; trk = {}
    for i in range(t.GetEntries()):
        t.GetEntry(i)
        ev = t.EventInfo.eventNumber()
        nper = collections.Counter()
        for tp in getattr(t, cont):
            prob = tp.auxdataConst['float']('truthMatchProbability') if tp.isAvailable['float']('truthMatchProbability') else -1
            tru = ROOT.xAOD.TruthHelpers.getTruthParticle(tp)
            b = etab(abs(tp.eta()))
            nsh = u8(tp, "numberOfPixelSharedHits") + u8(tp, "numberOfSCTSharedHits")
            nh = u8(tp, "numberOfPixelHits") + u8(tp, "numberOfSCTHits")
            C["tracks"] += 1; C["tracks " + b] += 1; C["sharedHits"] += nsh; C["hits"] += nh
            if tru:
                C["linked"] += 1
                if prob > 0.5:
                    C["linked p>0.5"] += 1; nper[tru.index()] += 1
                    key = (ev, tru.index())
                    if key not in matched or prob > matched[key]: matched[key] = prob
                else:
                    C["linked p<0.5 (fake)"] += 1; C["fake " + b] += 1
                    if prob < 0.2: C["linked p<0.2"] += 1
                C["linked " + b] += 1
            else:
                C["unlinked"] += 1; C["unlinked " + b] += 1
        for uid, n in nper.items():
            C["particles w/ >=1 p>0.5 track"] += 1
            if n > 1: C["particles w/ >1 (duplicate)"] += 1; C["extra duplicate tracks"] += n - 1
        # truth denominator
        hs = set()
        e0 = t.TruthEvents[0]
        for j in range(e0.nTruthParticles()):
            q = e0.truthParticle(j)
            if q: hs.add(q.index())
        for p in t.TruthParticles:
            if p.status() != 1 or p.charge() == 0 or p.pt() < 1000 or abs(p.eta()) > 4.0: continue
            if p.uid() < 0 or p.uid() > 200000: continue
            tag = "HS" if p.index() in hs else "PU"
            k = (ev, p.index()); found = k in matched
            C[f"truth {tag} pT>1"] += 1; C[f"truth {tag} pT>1 matched"] += found
            C[f"truth {tag} pT>1 {etab(abs(p.eta()))}"] += 1; C[f"truth {tag} pT>1 {etab(abs(p.eta()))} matched"] += found
            trk[k] = (p.pt(), p.eta(), found, tag)
    return C, trk
