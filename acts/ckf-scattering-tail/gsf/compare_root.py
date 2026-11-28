import sys, uproot, numpy as np
a, b = sys.argv[1], sys.argv[2]
from uproot.containers import STLVector
def flat(x):
    if isinstance(x, STLVector):
        x = list(x)
    if isinstance(x, (np.ndarray, list)) and len(x) and isinstance(x[0], (np.ndarray, list, STLVector)) or (isinstance(x, np.ndarray) and x.dtype == object):
        return b"|".join(flat(y) for y in x) + b"#%d" % len(x)
    return np.asarray(x).tobytes()
for name in ["tracksummary_ckf.root", "tracksummary_ambi.root"]:
    ta, tb = uproot.open(f"{a}/{name}")["tracksummary"], uproot.open(f"{b}/{name}")["tracksummary"]
    assert ta.num_entries == tb.num_entries
    bad = [br for br in ta.keys() if flat(ta[br].array(library="np")) != flat(tb[br].array(library="np"))]
    n = sum(len(x) for x in ta["nMeasurements"].array(library="np"))
    print(name, n, "tracks,", len(ta.keys()), "branches, differing:", bad)
