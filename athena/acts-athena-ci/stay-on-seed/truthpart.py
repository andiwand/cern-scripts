#!/usr/bin/env python3
"""Reconstructable truth particles per |eta| bin, HS and PU.
Reconstructable: IDPVM ITk denominator (status 1, charged, prodR < 300 mm, pT > PTMIN (900 MeV, the seeding cut),
|eta| < 4) and the track-selection hit minimum on clusters: >= 9 / 8 / 7 clusters for |eta| < 2.0 / 2.0-2.6 / above, >= 3 pixel.
Geant4 secondaries (status > 20000) with the same cuts are counted separately. Cluster counts from the P lines of the dump; HS/PU from the AOD (TruthEvents[0]).
usage: truthpart.py <sos.txt with P lines> <AOD> <out.json>"""
import sys, json, collections, os
PTMIN = float(os.environ.get('PTMIN', 900))   # seeding cut minPTSeed
import ROOT
ROOT.xAOD.Init().ignore()
f = ROOT.TFile.Open(sys.argv[2]); t = ROOT.xAOD.MakeTransientTree(f, "CollectionTree")
HS = {}
for i in range(t.GetEntries()):
    t.GetEntry(i); e0 = t.TruthEvents[0]
    HS[t.EventInfo.eventNumber()] = {e0.truthParticle(j).index() for j in range(e0.nTruthParticles()) if e0.truthParticle(j)}
H = collections.defaultdict(collections.Counter); C = collections.Counter()
for l in open(sys.argv[1]):
    if l[0] != 'P': continue
    _, ev, idx, pt, eta, q, st, uid, pr, npix, nstr = l.split()
    ev, idx, pt, eta, q, st, uid, pr, npix, nstr = int(ev), int(idx), float(pt), float(eta), float(q), int(st), int(uid), float(pr), int(npix), int(nstr)
    a = abs(eta)
    sec = st > 20000   # Geant4 secondary (the uid range does not identify them in this sample)
    if (st != 1 and not sec) or q == 0 or pr >= 300 or pt < PTMIN or a >= 4: continue
    tag = ("sec " if sec else "") + ("HS" if idx in HS.get(ev, ()) else "PU")
    need = 9 if a < 2.0 else 8 if a < 2.6 else 7
    ok = npix + nstr >= need and npix >= 3
    b = str(int(a / 0.25)); H[b]["all"] += ok; H[b][tag if ok else "not " + tag] += 1
    if sec and ok: H[b]["sec"] += 1
    C[(tag, ok)] += 1
out = dict(events=len(HS), edges=[i * 0.25 for i in range(17)], bins={b: dict(v) for b, v in sorted(H.items(), key=lambda x: int(x[0]))})
json.dump(out, open(sys.argv[3], "w"), indent=1)
print("events", len(HS), {f"{k[0]} {'reco' if k[1] else 'too few clusters'}": v for k, v in sorted(C.items())})
print(" ".join(f"{b}:{v.get('PU',0)}/{v.get('HS',0)}/{v.get('sec PU',0)}/{v.get('sec HS',0)}" for b, v in out["bins"].items()))
