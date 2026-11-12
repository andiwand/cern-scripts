#!/usr/bin/env python3
"""Efficiency HS/PU (pT>1) per |eta| region from varsum pkl caches. usage: effeta.py name=AOD ..."""
import sys, pickle
R = [("|eta|<1.5", "|eta|<1.5"), ("1.5-2.5", "1.5-2.5"), (">=2.5", ">=2.5")]
print(f"{'variant':18s}" + "".join(f"{'HS '+r:>15s}{'PU '+r:>15s}" for r, _ in R) + f"{'fake>=2.5':>11s}")
for a in sys.argv[1:]:
    n, f = a.split('=', 1); C, _ = pickle.load(open(f + ".truthsum.pkl", 'rb'))
    row = f"{n:18s}"
    for _, k in R:
        for t in ("HS", "PU"):
            row += f"{100*C[f'truth {t} pT>1 {k} matched']/C[f'truth {t} pT>1 {k}']:15.2f}"
    row += f"{100*C['unlinked >=2.5']/C['tracks >=2.5']:11.2f}"
    print(row)
