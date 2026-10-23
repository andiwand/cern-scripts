import pandas as pd, numpy as np, json
from pathlib import Path
import argparse

parser = argparse.ArgumentParser(
    description="Attribute charged-meson decay hits to parent cuts and late decays"
)
parser.add_argument("--input", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--events", type=int, default=20)
a = parser.parse_args()
folder = a.input
BAR = ["particle_id_" + s for s in ["pv", "sv", "part", "gen", "subpart"]]
PAR = [s.replace("particle_id", "parent_id") for s in BAR]
rows = []
for event in range(a.events):
    stem = f"event{event:09d}"
    p = pd.read_csv(folder / f"{stem}-particles_simulated.csv")
    h = pd.read_csv(
        folder / f"{stem}-hits.csv",
        usecols=BAR + ["geometry_id", "tpx", "tpy", "tpz"],
        dtype={"geometry_id": "uint64"},
    )
    r = pd.read_csv(folder / f"{stem}-meson_interactions.csv")
    r = r[r.process == "Decay"]
    ids = pd.MultiIndex.from_frame(p[BAR])
    ri = pd.MultiIndex.from_frame(r[BAR])
    hi = ids.get_indexer(pd.MultiIndex.from_frame(h[BAR]))
    assert np.all(hi >= 0)
    cut = (
        np.isin(h.geometry_id.to_numpy() >> np.uint64(56), [16, 17, 18])
        & (np.linalg.norm(h[["tpx", "tpy", "tpz"]], axis=1) >= 0.1)
        & (np.hypot(h.tpx, h.tpy) >= 0.05)
    )
    counts = np.bincount(hi[cut], minlength=len(p))
    parents = ids.get_indexer(pd.MultiIndex.from_frame(p[PAR]))
    ppdg = np.zeros(len(p), int)
    found = parents >= 0
    ppdg[found] = p.particle_type.to_numpy()[parents[found]]
    row = {"event": event}
    for pdg in [211, 321]:
        mask = (p.process == 1) & (p.particle_id_gen > 0) & (np.abs(ppdg) == pdg)
        child = p[mask]
        hits = counts[mask]
        rx = np.full(len(child), -1, int)
        groups = r.groupby(BAR, sort=False).indices
        xyz = r[["x", "y", "z", "t_ns"]].to_numpy()
        xyz[:, 3] *= 299.792458
        vtx = child[["vx", "vy", "vz", "vt"]].to_numpy()
        for key, ix in child.groupby(PAR, sort=False).indices.items():
            candidates = groups.get(key)
            if candidates is None:
                continue
            d = np.linalg.norm(vtx[ix, None, :] - xyz[candidates][None, :, :], axis=2)
            best = d.argmin(axis=1)
            good = d[np.arange(len(ix)), best] < 5e-4
            rx[ix[good]] = candidates[best[good]]
        categories = np.full(len(child), "unmatched", object)
        matched = rx >= 0
        v = r.iloc[rx[matched]]
        categories[matched] = "within parent cuts"
        categories[np.flatnonzero(matched)[(v.p < 0.1) | (v.pt < 0.05)]] = (
            "parent below cuts"
        )
        cat = {str(c): int(hits[categories == c].sum()) for c in np.unique(categories)}
        half_turn_ns = (
            np.pi
            * ({211: 0.13957039, 321: 0.493677}[pdg])
            / (0.000299792458 * 2 * 299.792458)
        )
        late = (
            (v.proper_time_ns.to_numpy() > half_turn_ns)
            & (v.p.to_numpy() >= 0.1)
            & (v.pt.to_numpy() >= 0.05)
        )
        row[str(pdg)] = {
            "hit_categories": cat,
            "accepted_hits_after_half_turn_proper_time": int(
                hits[np.flatnonzero(matched)[late]].sum()
            ),
            "half_turn_proper_time_ns": half_turn_ns,
            "g4_decays": int((r.pdg.abs() == pdg).sum()),
            "g4_accepted_decays": int(
                ((r.pdg.abs() == pdg) & (r.p >= 0.1) & (r.pt >= 0.05)).sum()
            ),
        }
    rows.append(row)
a.output.write_text(json.dumps({"events": rows}, indent=2) + "\n")
for pdg in ["211", "321"]:
    print(
        pdg,
        {
            c: sum(r[pdg]["hit_categories"].get(c, 0) for r in rows) / a.events
            for c in set().union(*(r[pdg]["hit_categories"] for r in rows))
        },
    )
    print(
        {
            c: np.mean([r[pdg][c] for r in rows])
            for c in [
                "g4_decays",
                "g4_accepted_decays",
                "accepted_hits_after_half_turn_proper_time",
                "half_turn_proper_time_ns",
            ]
        }
    )
