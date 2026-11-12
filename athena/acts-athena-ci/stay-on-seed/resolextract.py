#!/usr/bin/env python3
"""Per-track residuals vs truth for matched tracks (probability > 0.5) of prompt charged primaries.
Columns: eta_true, pt_true[GeV], prob, d0 res [mm], z0 res [mm], phi res [rad], theta res [rad], pT*(q/pT) res, nPix, nStrip
usage: resolextract.py <AOD> <out.npy>"""
import sys, math, ctypes
import numpy as np
import ROOT
ROOT.xAOD.Init().ignore()
f = ROOT.TFile.Open(sys.argv[1]); t = ROOT.xAOD.MakeTransientTree(f, "CollectionTree")
c8 = ctypes.c_uint8(0)
def u8(tp, s): return c8.value if tp.summaryValue(c8, getattr(ROOT.xAOD, s)) else 0
out = []
for i in range(t.GetEntries()):
    t.GetEntry(i)
    for tp in t.InDetTrackParticles:
        if not tp.isAvailable['float']('truthMatchProbability'): continue
        prob = tp.auxdataConst['float']('truthMatchProbability')
        if prob <= 0.5: continue
        p = ROOT.xAOD.TruthParticle_v1 and ROOT.xAOD.TruthHelpers.getTruthParticle(tp)
        if not p or p.status() != 1 or p.charge() == 0 or not p.hasProdVtx(): continue
        v = p.prodVtx()
        if math.hypot(v.x(), v.y()) > 2.0 or p.pt() < 1000 or abs(p.eta()) > 4: continue
        x0, y0 = v.x() - tp.vx(), v.y() - tp.vy(); phi = p.phi(); th = 2 * math.atan(math.exp(-p.eta()))
        d0t = -x0 * math.sin(phi) + y0 * math.cos(phi)
        z0t = (v.z() - tp.vz()) - (x0 * math.cos(phi) + y0 * math.sin(phi)) / math.tan(th)
        qpt_t = p.charge() / (p.pt() / 1000.); qpt_r = tp.qOverP() * 1000. / math.sin(tp.theta())
        dphi = (tp.phi0() - phi + math.pi) % (2 * math.pi) - math.pi
        out.append((p.eta(), p.pt() / 1000., prob, tp.d0() - d0t, tp.z0() - z0t, dphi, tp.theta() - th, (qpt_r - qpt_t) / abs(qpt_t),
                    u8(tp, "numberOfPixelHits"), u8(tp, "numberOfSCTHits")))
np.save(sys.argv[2], np.array(out, dtype=np.float32))
print(sys.argv[1], len(out))
