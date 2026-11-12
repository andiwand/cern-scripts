#!/usr/bin/env python3
"""Track truth categories, duplicates, paired efficiency between two AODs.
usage: truthsum.py <AOD_A> <AOD_B> [container]"""
import sys, collections, ctypes, math, pickle
import ROOT
ROOT.xAOD.Init().ignore()
cont = sys.argv[3] if len(sys.argv) > 3 else "InDetTrackParticles"
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
CA, TA = scan(sys.argv[1]); CB, TB = scan(sys.argv[2])
keys = list(dict.fromkeys(list(CA) + list(CB)))
print(f"{'':32s} {'A':>10s} {'B':>10s} {'B/A-1':>8s}")
for k in keys:
    a, b = CA[k], CB[k]
    print(f"{k:32s} {a:10d} {b:10d} {(b/a-1)*100 if a else 0:+7.2f}%")
print(f"unlinked fraction (fake)       A {CA['unlinked']/CA['tracks']:.4f}  B {CB['unlinked']/CB['tracks']:.4f}")
for tag in ("HS", "PU"):
    print(f"efficiency {tag}                  A {CA[f'truth {tag} pT>1 matched']/max(1,CA[f'truth {tag} pT>1']):.4f}  B {CB[f'truth {tag} pT>1 matched']/max(1,CB[f'truth {tag} pT>1']):.4f}")
print(f"duplicate rate                 A {CA['particles w/ >1 (duplicate)']/CA['particles w/ >=1 p>0.5 track']:.4f}  B {CB['particles w/ >1 (duplicate)']/CB['particles w/ >=1 p>0.5 track']:.4f}")
print(f"shared hits / track            A {CA['sharedHits']/CA['tracks']:.4f}  B {CB['sharedHits']/CB['tracks']:.4f}")
onlyA = [k for k in TA if TA[k][2] and not TB.get(k, (0, 0, False))[2]]
onlyB = [k for k in TB if TB[k][2] and not TA.get(k, (0, 0, False))[2]]
print(f"paired: truth found only in A {len(onlyA)}, only in B {len(onlyB)}")
for tag in ("HS", "PU"):
    print(f"  {tag}: only A {sum(1 for k in onlyA if TA[k][3]==tag)}, only B {sum(1 for k in onlyB if TB[k][3]==tag)}")
if len(onlyA) + len(onlyB) < 60:
    for k in onlyA: print("  onlyA", k, f"pt={TA[k][0]/1000:.2f} eta={TA[k][1]:+.2f} {TA[k][3]}")
    for k in onlyB: print("  onlyB", k, f"pt={TB[k][0]/1000:.2f} eta={TB[k][1]:+.2f} {TB[k][3]}")
for tag in ("HS", "PU"):
    for eb in ("|eta|<1.5", "1.5-2.5", ">=2.5"):
        oa = [k for k in onlyA if TA[k][3]==tag and etab(abs(TA[k][1]))==eb]; ob = [k for k in onlyB if TB[k][3]==tag and etab(abs(TB[k][1]))==eb]
        print(f"  {tag} {eb:9s}: only A {len(oa)}, only B {len(ob)}")
