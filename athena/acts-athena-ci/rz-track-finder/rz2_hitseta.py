#!/usr/bin/env python3
"""Hits and holes per track in bins of |eta|, several IDPVM files side by side.

usage: rz2_hitseta.py label=dir [label=dir ...]
Merges the signed-eta profile bins into |eta| ranges so that the barrel and
the endcaps read off directly.
"""
import sys

import ROOT

ROOT.gROOT.SetBatch(True)

BASE = "SquirrelPlots/Tracks/Selected/HitsOnTracks/"
VARS = ["nPixelHits", "nSCTHits", "nPixelHoles", "nSCTHoles"]
EDGES = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0]


def merged(profile):
    """(sum of weights x mean, sum of weights) per |eta| range."""
    out = [[0.0, 0.0] for _ in range(len(EDGES) - 1)]
    for i in range(1, profile.GetNbinsX() + 1):
        n = profile.GetBinEntries(i)
        if n <= 0:
            continue
        a = abs(profile.GetXaxis().GetBinCenter(i))
        for k in range(len(EDGES) - 1):
            if EDGES[k] <= a < EDGES[k + 1]:
                out[k][0] += n * profile.GetBinContent(i)
                out[k][1] += n
                break
    return out


def main():
    runs = [a.split("=", 1) for a in sys.argv[1:]]
    files = {label: ROOT.TFile.Open(f"{d}/idpvm.root") for label, d in runs}
    for var in VARS:
        print(f"=== {var} per track")
        print(f"{'|eta|':>10s}" + "".join(f"{label:>12s}" for label, _ in runs))
        cols = []
        for label, _ in runs:
            h = files[label].Get(BASE + f"{var}_vs_eta")
            cols.append(merged(h) if h else None)
        for k in range(len(EDGES) - 1):
            row = f"{EDGES[k]:4.1f}-{EDGES[k + 1]:<4.1f} "
            for c in cols:
                if c is None or c[k][1] == 0:
                    row += f"{'-':>12s}"
                else:
                    row += f"{c[k][0] / c[k][1]:12.3f}"
            print(row)
        print()


if __name__ == "__main__":
    main()
