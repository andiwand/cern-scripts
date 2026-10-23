import sys
import numpy as np
import uproot
import awkward as ak

def robust_width(x):
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if x.size == 0:
        return float("nan"), 0
    med = np.median(x)
    return 1.4826 * np.median(np.abs(x - med)), x.size

def load(path):
    f = uproot.open(path)
    print(path, [k for k in f.keys()])
    t = f["trackstates"]
    return t

def summarize(t, label):
    keys = t.keys()
    out = {}
    for par in ["eLOC0", "eLOC1", "ePHI", "eTHETA", "eQOP"]:
        for kind in ["pull", "res"]:
            k = f"{kind}_{par}_smt"
            if k not in keys:
                continue
            arr = ak.flatten(t[k].array(), axis=None)
            w, n = robust_width(arr)
            out[k] = (w, n)
    print(f"== {label}")
    for k, (w, n) in out.items():
        print(f"  {k:18s} width {w:.5g}  n {n}")
    return out

a = summarize(load(sys.argv[1]), "baseline")
b = summarize(load(sys.argv[2]), "joiner")
print("== ratio joiner/baseline")
for k in a:
    if k in b and a[k][0] > 0:
        print(f"  {k:18s} {b[k][0]/a[k][0]:.4f}")

# perigee comparison from the summaries
for name in ["tracksummary_ckf.root"]:
    ta = uproot.open(sys.argv[1].replace("trackstates_ckf.root", name))["tracksummary"]
    tb = uproot.open(sys.argv[2].replace("trackstates_ckf.root", name))["tracksummary"]
    for k in ["eLOC0_fit", "eQOP_fit", "nMeasurements", "chi2Sum"]:
        if k in ta.keys():
            xa = ak.flatten(ta[k].array(), axis=None)
            xb = ak.flatten(tb[k].array(), axis=None)
            same = len(xa) == len(xb) and np.allclose(np.asarray(xa, float), np.asarray(xb, float), rtol=0, atol=1e-12, equal_nan=True)
            print(f"  summary {k:14s} n {len(xa)} vs {len(xb)} identical {same}")
