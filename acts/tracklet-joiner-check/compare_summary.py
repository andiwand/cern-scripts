import sys
import numpy as np
import uproot
import awkward as ak

def load(path):
    t = uproot.open(path)["tracksummary"]
    ev = np.asarray(ak.flatten(ak.broadcast_arrays(t["event_nr"].array(), t["nMeasurements"].array())[0], axis=None))
    cols = {}
    for k in ["nMeasurements", "nHoles", "chi2Sum", "eLOC0_fit", "eLOC1_fit", "ePHI_fit", "eTHETA_fit", "eQOP_fit"]:
        cols[k] = np.asarray(ak.flatten(t[k].array(), axis=None), dtype=float)
    order = np.lexsort((cols["eQOP_fit"], cols["eLOC0_fit"], cols["nMeasurements"], ev))
    return ev[order], {k: v[order] for k, v in cols.items()}

eva, a = load(sys.argv[1])
evb, b = load(sys.argv[2])
print("tracks", len(eva), len(evb), "events equal", np.array_equal(eva, evb))
for k in a:
    same = np.allclose(a[k], b[k], rtol=0, atol=1e-12, equal_nan=True)
    maxd = np.nanmax(np.abs(a[k] - b[k])) if len(a[k]) == len(b[k]) else float("nan")
    print(f"  {k:14s} identical {same}  max abs diff {maxd:.3g}")
