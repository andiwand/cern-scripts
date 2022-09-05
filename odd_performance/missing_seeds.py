import pathlib
import uproot
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


inputDir = pathlib.Path(__file__).parent / "odd_output"

hits = uproot.open(inputDir / "hits.root")
hits = hits["hits"]
hits = hits.arrays(library="pd")

seeds = uproot.open(inputDir / "performance_seeding_trees.root")
seeds = seeds["track_finder_tracks"]
seeds = seeds.arrays(library="pd")


seeded_events = np.unique(seeds["event_id"])
missing_seeds = np.setdiff1d(hits["event_id"], seeded_events)
print(missing_seeds)

missing_mask = hits["event_id"].isin(missing_seeds)
barrel_mask = (hits["tz"] > -1000) & (hits["tz"] < 1000)

fig1, axs1 = plt.subplots()
fig2, axs2 = plt.subplots()
axs1.scatter(hits[barrel_mask]["tx"], hits[barrel_mask]["ty"], s=3)
axs1.scatter(
    hits[barrel_mask & missing_mask]["tx"], hits[barrel_mask & missing_mask]["ty"], s=3
)
axs2.scatter(hits["tz"].values, np.linalg.norm(hits[["tx", "ty"]], axis=-1), s=3)
axs2.scatter(
    hits[missing_mask]["tz"].values,
    np.linalg.norm(hits[missing_mask][["tx", "ty"]], axis=-1),
    s=3,
)
plt.show()
