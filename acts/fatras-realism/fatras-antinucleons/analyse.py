#!/usr/bin/env python3
"""Attribute accepted pixel hits to antinucleon collision processes and transport cuts."""

import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd

BAR = ["particle_id_" + k for k in ("pv", "sv", "part", "gen", "subpart")]
PAR = [k.replace("particle_id", "parent_id") for k in BAR]
PDGS = (-2212, -2112)


def analyse(folder, event, diagnostics=None):
    stem = f"event{event:09d}"
    p = pd.read_csv(folder / f"{stem}-particles_simulated.csv")
    h = pd.read_csv(
        folder / f"{stem}-hits.csv",
        usecols=BAR + ["geometry_id", "tpx", "tpy", "tpz"],
        dtype={"geometry_id": "uint64"},
    )
    ids = pd.MultiIndex.from_frame(p[BAR])
    assert ids.is_unique
    hi = ids.get_indexer(pd.MultiIndex.from_frame(h[BAR]))
    assert np.all(hi >= 0)
    common = (
        np.isin(h.geometry_id.to_numpy() >> np.uint64(56), [16, 17, 18])
        & (np.linalg.norm(h[["tpx", "tpy", "tpz"]], axis=1) >= 0.1)
        & (np.hypot(h.tpx, h.tpy) >= 0.05)
    )
    counts = np.bincount(hi[common], minlength=len(p))
    parents = ids.get_indexer(pd.MultiIndex.from_frame(p[PAR]))
    parent_pdg = np.zeros(len(p), dtype=int)
    found = parents >= 0
    parent_pdg[found] = p.particle_type.to_numpy()[parents[found]]
    secondary = p.particle_id_gen.to_numpy() > 0
    nuclear = secondary & (p.process.to_numpy() == 4)
    result = {
        "event": event,
        "secondary_hits": int(counts[secondary].sum()),
        "primary_hits": int(counts[~secondary].sum()),
        "unresolved_nuclear_hits": int(counts[nuclear & ~found].sum()),
        "nuclear_parent_hits": {
            str(int(k)): int(counts[nuclear & (parent_pdg == k)].sum())
            for k in np.unique(parent_pdg[nuclear])
        },
    }
    if diagnostics is None:
        return result
    r = pd.read_csv(diagnostics / f"{stem}-antinucleon_interactions.csv")
    children = p.loc[nuclear & np.isin(parent_pdg, PDGS)].copy()
    children["hits"] = counts[nuclear & np.isin(parent_pdg, PDGS)]
    groups = r.groupby(BAR, sort=False).indices
    xyz = r[["x", "y", "z", "t_ns"]].to_numpy()
    xyz[:, 3] *= 299.792458
    vertex = children[["vx", "vy", "vz", "vt"]].to_numpy()
    matched = np.full(len(children), -1, dtype=int)
    ambiguous = np.zeros(len(children), bool)
    for key, ix in children.groupby(PAR, sort=False).indices.items():
        candidates = groups.get(key)
        if candidates is None or len(candidates) == 0:
            continue
        distance = np.linalg.norm(
            vertex[ix, None, :] - xyz[candidates][None, :, :], axis=2
        )
        best = distance.argmin(axis=1)
        good = distance[np.arange(len(ix)), best] < 5e-4
        matched[ix[good]] = candidates[best[good]]
        for row, j in enumerate(ix):
            close = candidates[distance[row] < 5e-5]
            ambiguous[j] = len(set(r.subtype.to_numpy()[close])) > 1
    # Start with unmatched, including events with zero recorded interactions.
    categories = np.full(len(children), "unmatched vertex", dtype=object)
    valid = np.flatnonzero(matched >= 0)
    if len(valid):
        reaction = r.iloc[matched[valid]]
        momentum = reaction.p.to_numpy()
        pdg = reaction.pdg.to_numpy()
        mass = np.where(pdg == -2212, 0.93827208816, 0.93956542052)
        kinetic = momentum**2 / (np.hypot(momentum, mass) + mass)
        accepted_parent = np.where(
            pdg == -2212,
            (momentum >= 0.1) & (reaction.pt.to_numpy() >= 0.05),
            kinetic >= 0.010,
        )
        child = children.iloc[valid]
        accepted_child = (
            (child.q.to_numpy() != 0)
            & (np.linalg.norm(child[["px", "py", "pz"]], axis=1) >= 0.1)
            & (np.hypot(child.px, child.py) >= 0.05)
        )
        cat = np.full(len(valid), "in-flight, within model cuts", dtype=object)
        cat[~accepted_child] = "daughter below production cuts"
        cat[~accepted_parent | (reaction.t_ns.to_numpy() > 1000)] = (
            "parent below transport cuts"
        )
        cat[(momentum < 0.1) | (momentum > 7000)] = "outside table momentum range"
        cat[child.particle_type.abs().to_numpy() >= 1000000000] = "nuclear fragment"
        sub = reaction.subtype.to_numpy()
        cat[sub != 121] = "other hadronic process"
        cat[sub == 111] = "elastic"
        cat[sub == 151] = "at-rest annihilation"
        categories[valid] = cat
    categories[ambiguous] = "ambiguous vertex"
    result["geant4_categories"] = {
        str(k): int(children.hits.to_numpy()[categories == k].sum())
        for k in np.unique(categories)
    }
    result["geant4_process_interactions"] = {
        f"{pdg}:{sub}": int(n)
        for (pdg, sub), n in r.groupby(["pdg", "subtype"]).size().items()
    }
    assert sum(result["geant4_categories"].values()) == sum(
        result["nuclear_parent_hits"].get(str(k), 0) for k in PDGS
    )
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--truth", type=Path, required=True)
    p.add_argument("--diagnostics", type=Path)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--events", type=int, default=20)
    a = p.parse_args()
    rows = []
    for e in range(a.events):
        row = analyse(a.truth, e, a.diagnostics)
        rows.append(row)
        print(e, row, flush=True)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps({"events": rows}, indent=2) + "\n")


if __name__ == "__main__":
    main()
