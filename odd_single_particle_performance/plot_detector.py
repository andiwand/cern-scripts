#!/usr/bin/env python3

import matplotlib.pyplot as plt
from scipy.stats import norm
import uproot
import awkward as ak
import numpy as np
import argparse


def etaToSlope(eta):
    return np.tan(2 * np.arctan(np.exp(-eta)))


parser = argparse.ArgumentParser()
parser.add_argument("hits")
parser.add_argument("--more-hits")
args = parser.parse_args()

hits = uproot.open(args.hits)
hits = ak.to_dataframe(hits["hits"].arrays(library="ak"))

if args.more_hits:
    morehits = uproot.open(args.more_hits)
    morehits = ak.to_dataframe(morehits["hits"].arrays(library="ak"))

fig_xy = plt.figure("XY")

mask_xy = (hits["tz"] > -550) & (hits["tz"] < 550)

plt.scatter(hits[mask_xy]["tx"], hits[mask_xy]["ty"], s=1, c="k")
if args.more_hits:
    plt.scatter(morehits["tx"], morehits["ty"], s=10, c="g")

fig_rz = plt.figure("RZ")

plt.scatter(hits["tz"], np.hypot(hits["tx"], hits["ty"]), s=1, c="k")
if args.more_hits:
    plt.scatter(morehits["tz"], np.hypot(morehits["tx"], morehits["ty"]), s=10, c="g")
for eta in [0, 1, 2, 3, 4]:
    slope = etaToSlope(eta)
    plt.axline((0, 0), slope=slope, color="red", linestyle="--")
    plt.axline((0, 0), slope=-slope, color="red", linestyle="--")
plt.ylim((0, None))

plt.show()
