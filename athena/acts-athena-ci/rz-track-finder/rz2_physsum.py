#!/usr/bin/env python3
"""One table per sample over every side and finder of rz2_phys.sh.

usage: rz2_physsum.py <tag> [sample ...]
Integrated efficiencies and fake rates (passed over total), mean hits per
track, iterative-Gaussian core widths of the residuals and pulls, and the
track count from the AOD's primary track collection.
"""
import os
import re
import sys

import ROOT

ROOT.gROOT.SetBatch(True)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rzidpvm import average  # noqa: E402

BASE = "SquirrelPlots/Tracks/Matched/Resolutions/Primary/"
EFF = [
    ("eff loose", "SquirrelPlots/Tracks/Efficiency/efficiency_vs_eta"),
    ("eff tight", "SquirrelPlots/TightPrimary/Tracks/Efficiency/efficiency_vs_eta"),
    ("fake", "SquirrelPlots/Tracks/FakeRate/fakerate_vs_eta"),
]
HITS = [
    ("pix hits", "SquirrelPlots/Tracks/Selected/HitsOnTracks/nPixelHits"),
    ("strip hits", "SquirrelPlots/Tracks/Selected/HitsOnTracks/nSCTHits"),
    ("pix holes", "SquirrelPlots/Tracks/Selected/HitsOnTracks/nPixelHoles"),
    ("strip holes", "SquirrelPlots/Tracks/Selected/HitsOnTracks/nSCTHoles"),
]
SIDES = [("old", "old"), ("newgrid", "new grid"), ("new", "new gbts")]
FINDERS = ("ckf", "rz")
RZLINE = re.compile(r"RZ track finding: (\d+) seeds, (\d+) tracks.*?"
                    r"([0-9.]+) measurements and ([0-9.]+) holes per track.*?"
                    r"\(([0-9.]+)%\)")
CKFTRK = re.compile(r"\|\s*selected tracks\s*\|\s*(\d+)")


def corewidth(h, nsig=3.0, iters=6):
    if not h or h.GetEntries() < 20:
        return float("nan")
    lo, hi = h.GetXaxis().GetXmin(), h.GetXaxis().GetXmax()
    mu, sg = h.GetMean(), h.GetRMS()
    for _ in range(iters):
        r = h.Fit("gaus", "QNS", "", max(lo, mu - nsig * sg),
                  min(hi, mu + nsig * sg))
        if int(r) != 0:
            break
        mu, sg = r.Parameter(1), r.Parameter(2)
    return sg


def row_of(d):
    out = {}
    f = ROOT.TFile.Open(os.path.join(d, "idpvm.root"))
    if not f or f.IsZombie():
        return None
    for name, path in EFF:
        h = f.Get(path)
        out[name] = average(h)[0] if h else float("nan")
    for name, path in HITS:
        h = f.Get(path)
        out[name] = h.GetMean() if h else float("nan")
    for v in ("d0", "z0", "phi", "theta"):
        scale = 1000.0 if v in ("d0", "z0") else 1.0
        out[f"res {v}"] = corewidth(f.Get(BASE + f"res_{v}")) * scale
    for v in ("d0", "z0", "phi", "theta"):
        out[f"pull {v}"] = corewidth(f.Get(BASE + f"pull_{v}"))
    log = os.path.join(d, "log.RAWtoALL")
    with open(log, errors="replace") as fl:
        text = fl.read()
    m = RZLINE.search(text)
    if m:
        out["tracks"] = int(m.group(2))
        out["meas/trk"] = float(m.group(3))
        out["dedup %"] = float(m.group(5))
    else:
        c = CKFTRK.findall(text)
        out["tracks"] = int(c[0]) if c else float("nan")
    return out


FMT = {"res d0": "{:.2f}", "res z0": "{:.2f}", "res phi": "{:.3e}",
       "res theta": "{:.3e}", "tracks": "{:.0f}", "dedup %": "{:.1f}"}


def main():
    tag = sys.argv[1]
    samples = sys.argv[2:] or ["pt10", "pt100", "ttbar"]
    base = os.environ.get("ACI_RUN", "/home/astefl/source/acts/acts-athena-ci/run")
    for sample in samples:
        cols, rows = [], []
        for side, label in SIDES:
            for v in FINDERS:
                d = os.path.join(base, f"{tag}_{sample}_{side}_{v}")
                r = row_of(d) if os.path.exists(os.path.join(d, "idpvm.root")) else None
                if r is None:
                    continue
                cols.append(f"{label} {v}")
                rows.append(r)
        if not rows:
            continue
        keys = []
        for r in rows:
            keys += [k for k in r if k not in keys]
        print(f"=== {sample}  (res d0/z0 in um)")
        print(f"{'':12s}" + "".join(f"{c:>15s}" for c in cols))
        for k in keys:
            cells = []
            for r in rows:
                x = r.get(k, float("nan"))
                cells.append(FMT.get(k, "{:.4f}").format(x))
            print(f"{k:12s}" + "".join(f"{c:>15s}" for c in cells))
        print()


if __name__ == "__main__":
    main()
