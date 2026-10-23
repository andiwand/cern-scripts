#!/usr/bin/env python3
"""Attribute common-cut pixel hits to their immediate parent, without inferring ancestry."""

import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd

BAR = ["particle_id_" + x for x in ("pv", "sv", "part", "gen", "subpart")]
PARENT = [x.replace("particle_id_", "parent_id_") for x in BAR]
PROCESSES = [
    "undefined",
    "decay",
    "conversion",
    "bremsstrahlung",
    "nuclear",
    "ionisation",
    "other",
]
GROUPS = [
    "neutron",
    "K-long",
    "charged pion",
    "proton",
    "charged kaon",
    "antibaryon",
    "other",
    "unresolved",
]


def group(pdg):
    out = np.full(len(pdg), "other", dtype=object)
    out[np.isin(np.abs(pdg), [211])] = "charged pion"
    out[pdg == 2212] = "proton"
    out[np.isin(np.abs(pdg), [321])] = "charged kaon"
    out[np.isin(pdg, [-2212, -2112])] = "antibaryon"
    out[pdg == 2112] = "neutron"
    out[pdg == 130] = "K-long"
    out[pdg == 0] = "unresolved"
    return out


def analyse(folder, event):
    stem = f"event{event:09d}"
    truth_path = folder / f"{stem}-particles_simulated.csv"
    if not truth_path.exists():
        truth_path = truth_path.with_suffix(".csv.gz")
    p = pd.read_csv(
        truth_path,
        usecols=BAR + PARENT + ["particle_type", "process", "px", "py", "pz"],
    )
    h = pd.read_csv(
        folder / f"{stem}-hits.csv",
        usecols=BAR + ["geometry_id", "tpx", "tpy", "tpz", "tz"],
        dtype={"geometry_id": "uint64"},
    )
    ids = pd.MultiIndex.from_frame(p[BAR])
    assert ids.is_unique
    vol = h.geometry_id.to_numpy() >> np.uint64(56)
    momentum = np.sqrt(h.tpx**2 + h.tpy**2 + h.tpz**2)
    mask = (
        np.isin(vol, [16, 17, 18])
        & (momentum >= 0.1)
        & (np.hypot(h.tpx, h.tpy) >= 0.05)
    )
    h = h.loc[mask]
    where = ids.get_indexer(pd.MultiIndex.from_frame(h[BAR]))
    assert np.all(where >= 0)
    truth = p.iloc[where]
    parent = ids.get_indexer(pd.MultiIndex.from_frame(truth[PARENT]))
    parent_pdg = np.zeros(len(parent), dtype=int)
    parent_p = np.full(len(parent), np.nan)
    found = parent >= 0
    parent_pdg[found] = p.particle_type.to_numpy()[parent[found]]
    pp = p.loc[:, ["px", "py", "pz"]].to_numpy()
    parent_p[found] = np.linalg.norm(pp[parent[found]], axis=1)
    parent_group = group(parent_pdg)
    process = truth.process.to_numpy()
    secondary = h.particle_id_gen.to_numpy() > 0
    result = {
        "event": event,
        "primary": int(sum(~secondary)),
        "secondary": int(sum(secondary)),
        "process": {},
        "parent_pdg": {},
        "nuclear_parent": {},
        "nuclear_parent_outside_grid": {},
        "nuclear_parent_z": {},
        "nuclear_parent_p": {},
    }
    z_bins = [0, 500, 1000, 1600]
    p_bins = [0, 0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 100, 1e6]
    for code, name in enumerate(PROCESSES):
        m = secondary & (process == code)
        result["process"][name] = int(sum(m))
        values, counts = np.unique(parent_pdg[m], return_counts=True)
        result["parent_pdg"][name] = {str(v): int(n) for v, n in zip(values, counts)}
    for name in GROUPS:
        m = secondary & (process == 4) & (parent_group == name)
        result["nuclear_parent"][name] = int(sum(m))
        result["nuclear_parent_outside_grid"][name] = int(
            sum(m & ((parent_p < 0.1) | (parent_p > 20)))
        )
        result["nuclear_parent_z"][name] = np.histogram(
            np.abs(h.tz.to_numpy()[m]), z_bins
        )[0].tolist()
        result["nuclear_parent_p"][name] = np.histogram(parent_p[m], p_bins)[0].tolist()
    result["nuclear_hit_generation"] = np.bincount(
        h.particle_id_gen.to_numpy()[secondary & (process == 4)], minlength=10
    ).tolist()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--events", type=int, default=20)
    a = parser.parse_args()
    rows = []
    for event in range(a.events):
        rows.append(analyse(a.input, event))
        print(event, rows[-1]["nuclear_parent"], flush=True)
    a.output.write_text(
        json.dumps(
            {
                "source": str(a.input),
                "events": rows,
                "caveats": "Immediate parent only. Parent momentum is at creation, not interaction. Missing parent IDs remain unresolved. G4 nuclear category includes processes beyond inelastic scattering.",
            },
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
