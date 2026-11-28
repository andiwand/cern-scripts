"""Small regression check for duplicate-aware cuts and probability-based fakes."""

import numpy as np
from analyze import PDT, RDT, EDT, counts, threshold, selection, best

p = np.zeros(2, dtype=PDT)
p["id"] = [10, 11]
p["run"] = 1
p["event"] = 2
r = np.zeros(5, dtype=RDT)
r["run"] = 1
r["event"] = 2
r["index"] = np.arange(5)
r["id"] = [10, 10, 11, 0, 0]
r["prob"] = [0.9, 0.8, 0.7, 0.1, 0.9]
r["chi2"] = [10, 2, 3, 1, 2]
r["score"] = r["chi2"]
r["dim"] = 1
r["eta"] = 0
x = {"P": p, "R": r, "E": np.array([(1, 2, 2, 5)], dtype=EDT)}
assert threshold(x, "chi2", 2) == 3
c = counts(x, "chi2", 3)
assert (c["matched"], c["fakes"], c["tracks"], c["duplicates"]) == (2, 1, 4, 0), c
assert best(selection(x, "none", 0))[1, 2, 10]["index"] == 0
assert counts(x, "none", 0)["duplicates"] == 1
print("Analysis regression checks passed")
