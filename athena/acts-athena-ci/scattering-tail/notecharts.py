#!/usr/bin/env python3
"""Add the scattering-tail note's own figures to a charts.py output: the efficiency vs fake rate curves of the cut scan
(no tail / ACTS tail / Geant4 tail), the Geant4 vs model tail probabilities and (optionally) CPU.
usage: notecharts.py charts.json <ana dir> <g4 tail.json> [cpu.json]
Reads every <ana dir>/summary_*.txt (charts.py text output) for the integrated numbers."""
import sys, json, glob, os, re

CH, ANA, TAIL = sys.argv[1:4]
CPU = sys.argv[4] if len(sys.argv) > 4 else None
C = json.load(open(CH))
S = {}
for f in glob.glob(os.path.join(ANA, "summary_*.txt")):
    for l in open(f):
        m = re.match(r"(eff all|eff hs|fake|dup) (\w+)\s+([\d.]+)\s+(\d+)", l)
        if m: S[(m.group(1), m.group(2))] = 100 * float(m.group(3)) / int(m.group(4))

FAM = [("no tail", "--grey", [("c35", "3.5/4.6"), ("c4", "4/6"), ("c5", "5/7"), ("t0", "7/10 main"), ("w10", "10/14")], ""),
       ("ACTS tail", "--p2", [("t35", "3.5/4.6"), ("t4", "4/6"), ("t5", "5/7"), ("t1", "7/10")], ""),
       ("Geant4-refitted tail", "--p3", [("g35", "3.5/4.6"), ("g4", "4/6"), ("g5", "5/7")], ""),
       ("ACTS tail 7/10, diagnostics", "--p6", [("d1", "no C+wD"), ("d2", "no hole re-sel.")], "")]


def fam(xk, yk):
    out = []
    for lab, col, vs, dash in FAM:
        pts = [dict(x=round(S[(xk, v)], 5), y=round(S[(yk, v)], 4), t=t) for v, t in vs if (xk, v) in S and (yk, v) in S]
        out.append(dict(label=lab, color=col, pts=pts, dash=dash, line=not lab.endswith("diagnostics")))
    return out


front = [dict(kind="xy", title="Efficiency vs fake rate, hard-scatter + pile-up", xlabel="fake rate", ylabel="efficiency",
              xunit="%", yunit="%", logx=True, series=fam("fake", "eff all")),
         dict(kind="xy", title="Efficiency vs fake rate, hard-scatter", xlabel="fake rate", ylabel="efficiency",
              xunit="%", yunit="%", logx=True, series=fam("fake", "eff hs")),
         dict(kind="xy", title="Efficiency vs duplicate rate, hard-scatter + pile-up", xlabel="duplicate rate", ylabel="efficiency",
              xunit="%", yunit="%", series=fam("dup", "eff all"), col="D")]
C["figs"]["front"] = front
C["notes"]["front"] = ("IDPVM, 1000 ttbar mu=200 events, truth pT > 1 GeV. Each curve is the primary-pass chi2 cut scan "
                       "(Xi2maxSigma/Xi2maxNoAddSigma); the label is the cut. Statistical errors are ~0.03 % points in efficiency "
                       "and ~5-20 % relative in the fake rate. Fake-rate axis logarithmic.")
C.setdefault("more", {})["front"] = "Efficiency vs duplicate rate"

T = json.load(open(TAIL))["curves"]
tp = []
for k, i in (("0.0030", 0), ("0.0100", 1), ("0.0300", 2), ("0.0800", 3)):
    c = T[k]
    ser = [dict(label=lab, color=col, dash=d, pts=[dict(x=n, y=v) for n, v in zip(c["n"], c[key]) if v > 0])
           for lab, col, key, d in (("Geant4 FTFP_BERT", "--p1", "g4", ""), ("ACTS siliconScatteringTail", "--p2", "acts", ""),
                                    ("refit to Geant4", "--p3", "fit", "5 3"), ("Highland Gaussian", "--grey", "gauss", "2 3"))]
    tp.append(dict(kind="xy", title=f"P(|θ| > n σ₀), silicon, x/X0 = {float(k):g}", xlabel="n (σ₀ = Highland)", ylabel="probability",
                   logy=True, ymin=1e-4, ymax=0.1, xmin=2, xmax=15, series=ser, labels=False, col="L" if i < 2 else "D"))
C["figs"]["tail"] = tp
C["notes"]["tail"] = ("Projected angle of a pi+ through a silicon slab, both projections, 1 and 5 GeV together (~4M per thickness). "
                      "σ₀ is the Highland width the ACTS propagator uses; the refit keeps it as the core. Thicker slabs folded below.")
C["more"]["tail"] = "x/X0 = 0.03 and 0.08"

if CPU:
    P = json.load(open(CPU))
    C["figs"]["cpu"] = P["figs"]; C["notes"]["cpu"] = P["note"]
json.dump(C, open(CH, "w"), separators=(",", ":"))
print(CH, sorted(C["figs"]))
