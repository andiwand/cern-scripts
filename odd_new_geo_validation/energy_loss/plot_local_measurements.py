import pathlib

import uproot

import awkward as ak
import numpy as np
import pandas as pd

import matplotlib.pyplot as plt


inputDir = pathlib.Path(__file__).parent / "root_files"

measurements = uproot.open(inputDir / "measurements.root")
trackstates = uproot.open(inputDir / "trackstates_kalman.root")
trackstates = ak.to_dataframe(
    trackstates["trackstates"].arrays(library="awkward"), how="outer"
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

for k in ["vol5", "vol4", "vol9", "vol10"]:
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
    data = measurements[k].arrays(columns, library="np")
    data = pd.DataFrame(data)

    id_columns = ["volume_id", "layer_id", "surface_id"]
    for ids in np.unique(data[id_columns], axis=0):
        mask_m = np.all(data[id_columns] == ids, axis=1)
        mask_t = np.all(
            trackstates[["volume_id", "layer_id", "module_id"]] == ids, axis=1
        )
        mask_t_e = mask_t & (trackstates["event_nr"] == 2)

        plt.figure()
        plt.title(",".join(map(str, ids)))
        plt.xlabel("loc0")
        plt.ylabel("loc1")
        plt.axis("equal")
        plt.scatter(
            data[mask_m]["rec_loc0"],
            data[mask_m]["rec_loc1"],
            alpha=0.5,
            label="measurement",
        )
        plt.scatter(
            trackstates[mask_t]["eLOC0_prt"],
            trackstates[mask_t]["eLOC1_prt"],
            alpha=0.2,
            label="kalman predicted",
        )
        plt.scatter(
            trackstates[mask_t]["eLOC0_flt"],
            trackstates[mask_t]["eLOC1_flt"],
            alpha=0.2,
            label="kalman filtered",
        )
        plt.scatter(
            trackstates[mask_t]["eLOC0_smt"],
            trackstates[mask_t]["eLOC1_smt"],
            alpha=0.2,
            label="kalman smoothed",
        )
        plt.scatter(data[mask_m]["true_loc0"], data[mask_m]["true_loc1"], label="true")
        # plt.scatter(trackstates[mask_t_e]['eLOC0_prt'], trackstates[mask_t_e]['eLOC1_prt'], s=100, label='special kalman predicted')
        # plt.scatter(trackstates[mask_t_e]['eLOC0_flt'], trackstates[mask_t_e]['eLOC1_flt'], s=100, label='special kalman filtered')
        plt.legend()

plt.show()
