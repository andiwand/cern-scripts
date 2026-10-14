#!/usr/bin/env python3
"""Join pion interactions to truth/hits and separate coverage from conditional yield."""
import argparse, json
from pathlib import Path
import numpy as np
import pandas as pd

BAR = ["particle_id_" + x for x in ["pv", "sv", "part", "gen", "subpart"]]
PAR = [x.replace("particle_id", "parent_id") for x in BAR]
BINS = np.array([0, 0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50, 100, 1000, 7000, 1e9])


def analyse(event, mode, diagnostics, truth, output):
    stem = f"event{event:09d}"
    particles = pd.read_csv(
        truth / f"{stem}-particles_simulated.csv",
        usecols=BAR
        + PAR
        + ["particle_type", "process", "q", "px", "py", "pz", "vx", "vy", "vz", "vt"],
    )
    hits = pd.read_csv(
        truth / f"{stem}-hits.csv",
        usecols=BAR + ["geometry_id", "tpx", "tpy", "tpz"],
        dtype={"geometry_id": "uint64"},
    )
    ids = pd.MultiIndex.from_frame(particles[BAR])
    assert ids.is_unique
    w = ids.get_indexer(pd.MultiIndex.from_frame(hits[BAR]))
    assert np.all(w >= 0)
    vol = hits.geometry_id.to_numpy() >> np.uint64(56)
    common = (
        np.isin(vol, [16, 17, 18])
        & (np.sqrt(hits.tpx**2 + hits.tpy**2 + hits.tpz**2) >= 0.1)
        & (np.hypot(hits.tpx, hits.tpy) >= 0.05)
        & (hits.particle_id_gen > 0)
    )
    counts = np.bincount(w[common], minlength=len(particles))
    states = pd.read_csv(diagnostics / f"{stem}-pion_states.csv")
    if mode == "geant4":
        reactions = pd.read_csv(diagnostics / f"{stem}-pion_interactions.csv")
        paths = pd.read_csv(diagnostics / f"{stem}-pion_paths.csv")
    else:
        reactions = (
            states.loc[(states.outcome == 1) & (states.p_final > 0)]
            .copy()
            .reset_index(drop=True)
        )
        reactions = reactions.rename(
            columns={"p_final": "p", "pt_final": "pt", "t_ns": "t_ns"}
        )
        reactions["subtype"] = 121
        reactions["leading_alive"] = False
        reactions["leading_p"] = 0
        reactions["leading_pt"] = 0
        reactions["material"] = "mapped"
        paths = states.copy()
        paths["n_inelastic"] = ((paths.outcome == 1) & (paths.p_final > 0)).astype(int)
        paths["first_l0"] = paths.l0
    index = pd.MultiIndex.from_frame(reactions[BAR])
    parent_index = pd.MultiIndex.from_frame(particles[PAR])
    eligible = (particles.process == 4).to_numpy() & parent_index.isin(index)
    children = particles.loc[eligible].copy()
    children["hits"] = counts[eligible]
    groups = {
        key: np.asarray(value)
        for key, value in reactions.groupby(BAR, sort=False).indices.items()
    }
    association = np.full(len(children), -1, dtype=int)
    ambiguous = np.zeros(len(children), bool)
    positions = reactions[["x", "y", "z", "t_ns"]].to_numpy()
    positions[:, 3] *= 299.792458
    childpositions = children[["vx", "vy", "vz", "vt"]].to_numpy()
    for key, ix in children.groupby(PAR, sort=False).indices.items():
        candidates = groups[key]
        distance = np.linalg.norm(
            childpositions[ix, None, :] - positions[candidates][None, :, :], axis=2
        )
        best = distance.argmin(axis=1)
        good = distance[np.arange(len(ix)), best] < 5e-4
        association[ix[good]] = candidates[best[good]]
        if len(candidates) > 1:
            for row, j in enumerate(ix):
                close = candidates[distance[row] < 5e-5]
                if len(close) > 1 and len(set(reactions.subtype.to_numpy()[close])) > 1:
                    ambiguous[j] = True
    result = {
        "event": event,
        "nuclear_pion_hits": int(children.hits.sum()),
        "unmatched_hits": int(children.hits.to_numpy()[association < 0].sum()),
        "ambiguous_hits": int(children.hits.to_numpy()[ambiguous].sum()),
    }
    valid = (association >= 0) & ~ambiguous
    pchild = np.linalg.norm(children[["px", "py", "pz"]], axis=1)
    ptchild = np.hypot(children.px, children.py)
    fragments = children.particle_type.abs().to_numpy() >= 1000000000
    charged = children.q.to_numpy() != 0
    accepted = charged & ~fragments & (pchild >= 0.1) & (ptchild >= 0.05)
    n = len(reactions)
    for name, weights in [
        ("charged", charged & ~fragments),
        ("accepted", accepted),
        ("hits", children.hits.to_numpy()),
    ]:
        reactions["truth_" + name] = np.bincount(
            association[valid], weights=np.asarray(weights)[valid], minlength=n
        )
    momenta = children[["px", "py", "pz"]].to_numpy()
    safe = np.maximum(association, 0)
    direction = reactions[["dx", "dy", "dz"]].to_numpy()[safe]
    angle = np.arccos(
        np.clip(np.sum(momenta * direction, axis=1) / np.maximum(pchild, 1e-30), -1, 1)
    )
    for name, weights in [
        ("accepted_pt_sum", np.asarray(ptchild) * accepted),
        ("accepted_angle_sum", angle * accepted),
    ]:
        reactions["truth_" + name] = np.bincount(
            association[valid], weights=weights[valid], minlength=n
        )
    leading = (
        reactions.leading_alive.to_numpy().astype(bool)
        & (reactions.leading_p >= 0.1)
        & (reactions.leading_pt >= 0.05)
    )
    reactions["inclusive_accepted"] = reactions.truth_accepted + leading
    # Disjoint attribution; keep non-inelastic and fragments explicit.
    category = np.full(len(children), "in-domain accepted", dtype=object)
    rp = reactions.p.to_numpy()[safe]
    rpt = reactions.pt.to_numpy()[safe]
    sub = reactions.subtype.to_numpy()[safe]
    category[~accepted] = "daughter below production cuts"
    category[(rp < 0.1) | (rpt < 0.05)] = "parent below transport cuts"
    category[rp > 20] = "parent above 20 GeV"
    category[fragments] = "nuclear fragment"
    category[sub != 121] = "other hadronic process"
    category[sub == 111] = "elastic"
    category[sub == 151] = "at-rest capture"
    category[ambiguous] = "ambiguous vertex"
    category[association < 0] = "unmatched vertex"
    result["hit_categories"] = {
        k: int(children.hits.to_numpy()[category == k].sum())
        for k in [
            "in-domain accepted",
            "parent above 20 GeV",
            "parent below transport cuts",
            "daughter below production cuts",
            "nuclear fragment",
            "elastic",
            "at-rest capture",
            "other hadronic process",
            "ambiguous vertex",
            "unmatched vertex",
        ]
    }
    result["inelastic_momentum_hist"] = np.histogram(
        reactions.loc[reactions.subtype == 121, "p"], BINS
    )[0].tolist()
    result["interaction_hit_momentum_hist"] = np.histogram(
        reactions.loc[reactions.subtype == 121, "p"],
        BINS,
        weights=reactions.loc[reactions.subtype == 121, "truth_hits"],
    )[0].tolist()
    primary = paths.particle_id_gen == 0
    result["primary_pions"] = int(sum(primary))
    result["primary_pion_p_hist"] = np.histogram(paths.loc[primary, "p0"], BINS)[
        0
    ].tolist()
    result["primary_inelastic_p_hist"] = np.histogram(
        paths.loc[primary & (paths.n_inelastic > 0), "p0"], BINS
    )[0].tolist()
    result["primary_first_l0_sum_hist"] = np.histogram(
        paths.loc[primary, "p0"], BINS, weights=paths.loc[primary, "first_l0"]
    )[0].tolist()
    result["primary_interaction_fraction"] = float(
        np.mean(paths.loc[primary, "n_inelastic"] > 0)
    )
    reactions.to_csv(output / f"{stem}-{mode}-reactions.csv", index=False)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--mode", choices=["geant4", "baseline", "extended", "corrected"], required=True
    )
    p.add_argument("--diagnostics", type=Path, required=True)
    p.add_argument("--truth", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--events", type=int, default=20)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=True)
    rows = []
    for event in range(a.events):
        r = analyse(event, a.mode, a.diagnostics, a.truth, a.output)
        rows.append(r)
        print(a.mode, event, r["hit_categories"], flush=True)
    (a.output / f"{a.mode}-pion-summary.json").write_text(
        json.dumps(
            {
                "events": rows,
                "momentum_bins": BINS.tolist(),
                "incident_momentum": "G4 pre-step momentum on the interaction-ending step; Fatras momentum at nuclear sampling after EM losses. G4 finite-step continuous losses are not resolved.",
            },
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
