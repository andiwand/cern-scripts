#!/usr/bin/env python3
"""Finding efficiency, fake and duplicate rates per variant, with PyROOT."""

import json
import pathlib
import sys

import ROOT

d = pathlib.Path(sys.argv[1])
out = {}
for vdir in sorted(x for x in d.iterdir() if x.is_dir()):
    v = vdir.name
    res = {}
    for kind, fname in [("ckf", f"performance_finding_{v}_ckf.root"),
                        ("ambi", f"performance_finding_{v}_ambi.root"),
                        ("seed", f"performance_{v}_seeding.root")]:
        f = ROOT.TFile.Open(str(vdir / fname))
        if not f:
            continue
        r = {}
        for name in ["eff_particles", "fakeratio_tracks", "duplicateratio_tracks"]:
            o = f.Get(name)
            if o:
                r[name] = float(o.GetVal()) if hasattr(o, "GetVal") else float(o[0])
        e = f.Get("trackeff_vs_eta")
        if e:
            total = e.GetTotalHistogram()
            passed = e.GetPassedHistogram()
            for lo, hi in [(0, 1.6), (1.6, 2.0), (2.0, 3.0)]:
                t = p = 0.0
                for b in range(1, total.GetNbinsX() + 1):
                    c = abs(total.GetBinCenter(b))
                    if lo <= c < hi:
                        t += total.GetBinContent(b)
                        p += passed.GetBinContent(b)
                r[f"eff_eta_{lo}_{hi}"] = p / t if t else float("nan")
            r["n_particles"] = total.GetEntries()
        res[kind] = r
    out[v] = res
print(json.dumps(out, indent=1))
(d / "eff.json").write_text(json.dumps(out, indent=1))
