#!/usr/bin/env python3
"""CPU figure for the scattering-tail note: track-finding CPU vs efficiency and vs fake rate, per tail family.
usage: cpuchart.py <cpu_rel.json> <ana dir> <out cpu.json>
cpu_rel.json: {variant: {ActsTrackFindingAlg: % vs main, ..., n: runs}} (relative to t0 of the same cycle set)."""
import sys, json, glob, os, re
CPU, ANA, OUT = sys.argv[1:4]
P = json.load(open(CPU))
S = {}
for f in glob.glob(os.path.join(ANA, "summary_*.txt")):
    for l in open(f):
        m = re.match(r"(eff all|fake) (\w+)\s+([\d.]+)\s+(\d+)", l)
        if m: S[(m.group(1), m.group(2))] = 100 * float(m.group(3)) / int(m.group(4))
FAM = [("no tail", "--grey", [("c35", "3.5/4.6"), ("c4", "4/6"), ("c5", "5/7"), ("t0", "main"), ("w10", "10/14")]),
       ("ACTS tail", "--p2", [("t35", "3.5/4.6"), ("t4", "4/6"), ("t5", "5/7"), ("t1", "7/10")]),
       ("Geant4-refitted tail", "--p3", [("g35", "3.5/4.6"), ("g4", "4/6"), ("g5", "5/7")])]
def ser(yk, nd):
    return [dict(label=lab, color=col, dash="", line=True,
                 pts=[dict(x=P[v]["ActsTrackFindingAlg"], y=round(S[(yk, v)], nd), t=t) for v, t in vs if v in P and (yk, v) in S])
            for lab, col, vs in FAM]
figs = [dict(kind="xy", title="Efficiency vs track-finding CPU", xlabel="ActsTrackFindingAlg CPU vs main", ylabel="efficiency",
             xunit="%", yunit="%", series=ser("eff all", 4)),
        dict(kind="xy", title="Fake rate vs track-finding CPU", xlabel="ActsTrackFindingAlg CPU vs main", ylabel="fake rate",
             xunit="%", yunit="%", logy=True, series=ser("fake", 5), col="D")]
note = ("20 ttbar mu=200 events, --multithreaded False, alternating runs, normalised to ActsPixelClusterizationAlg, relative to main "
        "measured in the same cycles. c5/t5/t1/w10: 3 cycles; the rest 2 cycles (g35, g5, t35: 1 run each) because the machine "
        "got loaded by another user. Run-to-run scatter ~0.5 %. Efficiency hard-scatter + pile-up from the 1000-event IDPVM.")
json.dump(dict(figs=figs, note=note, more="Fake rate vs CPU"), open(OUT, "w"))
print(OUT)
