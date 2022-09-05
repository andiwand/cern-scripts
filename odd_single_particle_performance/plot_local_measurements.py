#!/usr/bin/env python3

import argparse
import uproot
import awkward as ak
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


id_columns_m = ["volume_id", "layer_id", "surface_id"]
id_columns_t = ["volume_id", "layer_id", "module_id"]

parser = argparse.ArgumentParser()
parser.add_argument("measurements")
parser.add_argument("trackstates")
args = parser.parse_args()

measurements = uproot.open(args.measurements)
print(measurements.keys())
measurements_all = []
for k in [
    "vol16",
    "vol17",
    "vol18",
    "vol23",
    "vol24",
    "vol25",
    #'vol28', 'vol29', 'vol30',
]:
    columns = [
        "event_nr",
        "volume_id",
        "layer_id",
        "surface_id",
        "true_loc0",
        "true_loc1",
        "rec_loc0",
        "rec_loc1",
        "var_loc0",
        "var_loc1",
    ]
    measurements_all.append(pd.DataFrame(measurements[k].arrays(columns, library="np")))
measurements = pd.concat(measurements_all)

trackstates = uproot.open(args.trackstates)
trackstates = ak.to_dataframe(
    trackstates["trackstates"].arrays(library="ak"), how="outer"
)
trackstates.reset_index(drop=True, inplace=True)

with pd.option_context("display.max_rows", None, "display.max_columns", None):
    print(
        trackstates[trackstates["event_nr"] == 2][
            [
                "volume_id",
                "layer_id",
                "eLOC0_prt",
                "eLOC1_prt",
                "ePHI_prt",
                "eTHETA_prt",
                "eQOP_prt",
                "err_eLOC0_prt",
                "err_eLOC1_prt",
                "err_ePHI_prt",
                "err_eTHETA_prt",
                "err_eQOP_prt",
                "eLOC0_flt",
                "eLOC1_flt",
                "ePHI_flt",
                "eTHETA_flt",
                "eQOP_flt",
                "err_eLOC0_flt",
                "err_eLOC1_flt",
                "err_ePHI_flt",
                "err_eTHETA_prt",
                "err_eQOP_flt",
            ]
        ]
    )

for ids in np.unique(
    np.concatenate(
        (measurements[id_columns_m].values, trackstates[id_columns_t].values)
    ),
    axis=0,
):
    mask_m = np.all(measurements[id_columns_m] == ids, axis=1)
    mask_t = np.all(trackstates[id_columns_t] == ids, axis=1)

    plt.figure(",".join(map(str, ids)))
    plt.title(",".join(map(str, ids)))

    plt.xlabel("loc0")
    plt.ylabel("loc1")
    plt.axis("equal")

    plt.scatter(
        measurements[mask_m]["true_loc0"],
        measurements[mask_m]["true_loc1"],
        label="true",
    )
    plt.scatter(
        measurements[mask_m]["rec_loc0"],
        measurements[mask_m]["rec_loc1"],
        alpha=0.5,
        label="measurement",
    )
    """
    plt.scatter(
        trackstates[mask_t]["eLOC0_prt"],
        trackstates[mask_t]["eLOC1_prt"],
        alpha=0.2,
        label="kalman predicted",
    )
    """
    """
    plt.scatter(
        trackstates[mask_t]["eLOC0_flt"],
        trackstates[mask_t]["eLOC1_flt"],
        alpha=0.2,
        label="kalman filtered",
    )
    """
    plt.scatter(
        trackstates[mask_t]["eLOC0_smt"],
        trackstates[mask_t]["eLOC1_smt"],
        alpha=0.2,
        label="kalman smoothed",
    )

    plt.legend()

plt.show()
