#!/usr/bin/env python3
"""Take the ITk dump's secondary component apart, and score models against it.

    ./secondary_anatomy.py anatomy --fullsim <dump>.root --events 5
    ./secondary_anatomy.py scan    --fullsim <dump>.root --events 5

`anatomy` needs only uproot and reads the reference: how the pixel clusters
split into primary, secondary and unlinked, where the secondaries are produced,
and what produced them.

`scan` additionally needs `acts.fatras.synthetic`, and scores the shipped model
against the reference with each of its two secondary terms taken back out.

Two things about the scoring are the point of the exercise.

The bands are coarse. A radial bin narrow enough to fall inside one layer
measures the half-millimetre between the model's layer radius and the
reference's cluster positions, which the *primary* clusters show just as
strongly as the secondaries and which no secondary model can move. On forty
bins that noise is the whole objective: it sits at 0.13 for every variant
below, including ones that differ by a factor two in the forward region.

And what is scored is the non-primary component on its own, not the total. The
total is matched by construction - `secondaryRate` is re-solved for it - so a
model that puts its secondaries in the wrong place scores the same as one that
does not, as long as it makes the right number of them.
"""

from __future__ import annotations

import argparse
from collections import Counter

import numpy as np
import uproot

TREE = "GNN4ITk"

#: Barcodes below this come from the generator, above it from the detector
#: simulation. See `fullsim_itk.py`.
PRIMARY_BARCODE_LIMIT = 200_000

#: Coarse enough that no band splits a layer. See the module docstring.
R_BANDS = np.array([25.0, 60.0, 110.0, 150.0, 200.0, 250.0, 320.0])
Z_BANDS = np.array([0.0, 250.0, 500.0, 1000.0, 1500.0, 2000.0, 2500.0, 3000.0])

BRANCHES = [
    "CLx", "CLy", "CLz", "CLhardware", "CLpixel_count",
    "CLparticleLink_barcode", "CLparticleLink_eventIndex",
    "Part_event_number", "Part_barcode", "Part_pt", "Part_eta", "Part_charge",
    "Part_radius", "Part_vx", "Part_vy", "Part_vz", "Part_pdg_id",
    "Part_vParentBarcode",
]

#: Parents whose secondaries are decays rather than material interactions
NEUTRAL_HADRON = {310, 130, 2112, -2112, 3122, -3122, 3322, 3312, -3312}


def read(path: str, num_events: int):
    """Read one dump into the per-cluster and per-secondary arrays below.

    @param path the dump file
    @param num_events how many events to read
    @return a dict of arrays, all concatenated over events
    """
    tree = uproot.open(path)[TREE]
    n_ev = 0
    cl = {k: {"r": np.zeros(len(R_BANDS) - 1),
              "z": np.zeros(len(Z_BANDS) - 1), "n": 0, "size": 0.0}
          for k in ("primary", "secondary", "unlinked")}
    prod_r, prod_z, sec_pt, sec_hits = [], [], [], []
    species, parents = Counter(), Counter()
    parent_hits = Counter()

    for batch in tree.iterate(BRANCHES, entry_stop=num_events, step_size=1,
                              library="np"):
        for i in range(len(batch["Part_pt"])):
            ev = {k: v[i] for k, v in batch.items()}
            n_ev += 1
            _read_event(ev, cl, prod_r, prod_z, sec_pt, sec_hits,
                        species, parents, parent_hits)

    for v in cl.values():
        v["size"] /= max(v["n"], 1)
        for key in ("r", "z"):
            v[key] /= n_ev
        v["n"] /= n_ev
    return dict(n_ev=n_ev, clusters=cl, species=species, parents=parents,
                parent_hits=parent_hits,
                prod_r=np.concatenate(prod_r), prod_z=np.concatenate(prod_z),
                sec_pt=np.concatenate(sec_pt),
                sec_hits=np.concatenate(sec_hits))


def _read_event(ev, cl, prod_r, prod_z, sec_pt, sec_hits, species,
                parents, parent_hits) -> None:
    hardware = np.asarray([str(h) for h in ev["CLhardware"]])
    is_pixel = hardware == "PIXEL"

    barcode = ev["Part_barcode"]
    evnum = ev["Part_event_number"]
    pdg = ev["Part_pdg_id"]
    charge = ev["Part_charge"]
    primary_of = {(int(e), int(b)): int(b) < PRIMARY_BARCODE_LIMIT
                  for e, b in zip(evnum, barcode)}
    index_of = {(int(e), int(b)): j
                for j, (e, b) in enumerate(zip(evnum, barcode))}

    r = np.hypot(ev["CLx"], ev["CLy"])
    z = np.abs(ev["CLz"])
    hits: dict[tuple[int, int], int] = {}
    groups: dict[str, list[int]] = {k: [] for k in cl}

    for j in np.flatnonzero(is_pixel):
        links = list(zip(ev["CLparticleLink_eventIndex"][j],
                         ev["CLparticleLink_barcode"][j]))
        if not links:
            groups["unlinked"].append(j)
            continue
        is_pri = False
        for index, b in links:
            key = (int(index), int(b))
            hits[key] = hits.get(key, 0) + 1
            is_pri = is_pri or primary_of.get(key, False)
        groups["primary" if is_pri else "secondary"].append(j)

    for key, idx in groups.items():
        idx = np.asarray(idx, dtype=int)
        cl[key]["r"] += np.histogram(r[idx], bins=R_BANDS)[0]
        cl[key]["z"] += np.histogram(z[idx], bins=Z_BANDS)[0]
        cl[key]["n"] += len(idx)
        cl[key]["size"] += float(ev["CLpixel_count"][idx].sum())

    num_hits = np.array([hits.get((int(e), int(b)), 0)
                         for e, b in zip(evnum, barcode)])
    sel = ((np.abs(charge) > 0.5) & (barcode >= PRIMARY_BARCODE_LIMIT)
           & (num_hits > 0))
    prod_r.append(ev["Part_radius"][sel])
    prod_z.append(np.abs(ev["Part_vz"][sel]))
    sec_pt.append(ev["Part_pt"][sel] / 1000.0)
    sec_hits.append(num_hits[sel])
    for j in np.flatnonzero(sel):
        species[int(pdg[j])] += 1
        parent = ev["Part_vParentBarcode"][j]
        kind = "unknown"
        if len(parent) > 0:
            pj = index_of.get((int(evnum[j]), int(parent[0])))
            if pj is not None:
                p = int(pdg[pj])
                if p == 22:
                    kind = "photon"
                elif abs(charge[pj]) > 0.5:
                    kind = "charged"
                elif p in NEUTRAL_HADRON:
                    kind = "neutral"
        parents[kind] += 1
        parent_hits[kind] += int(num_hits[j])


def anatomy(data) -> None:
    """Print what the reference's secondary component is made of."""
    cl = data["clusters"]
    total = sum(v["n"] for v in cl.values())
    print("pixel clusters per event: %.0f" % total)
    for k in ("primary", "secondary", "unlinked"):
        print("  %-10s %8.0f  %5.1f%%   mean cluster size %.2f px"
              % (k, cl[k]["n"], 100 * cl[k]["n"] / total, cl[k]["size"]))
    print("\nThe unlinked clusters follow the linked secondaries, not the")
    print("primaries: unlinked/secondary by band, which is flat if they are")
    print("the same population seen twice.")
    print("  r [mm]   " + "  ".join(
        "%.0f-%.0f %.1f" % (R_BANDS[i], R_BANDS[i + 1],
                            cl["unlinked"]["r"][i] / cl["secondary"]["r"][i])
        for i in range(len(R_BANDS) - 1)))
    print("  |z| [mm] " + "  ".join(
        "%.0f-%.0f %.1f" % (Z_BANDS[i], Z_BANDS[i + 1],
                            cl["unlinked"]["z"][i] / cl["secondary"]["z"][i])
        for i in range(len(Z_BANDS) - 1)))

    print("\nwhere the secondaries are produced, clusters per event")
    edges = np.array([0, 23, 27, 31, 40, 60, 90, 110, 120, 133, 150, 200,
                      250, 320, 3000])
    h = np.histogram(data["prod_r"], bins=edges,
                     weights=data["sec_hits"].astype(float))[0]
    h = h / data["n_ev"]
    for i in range(len(edges) - 1):
        print("  r %5.0f-%-6.0f %8.0f  %5.1f%%  %s"
              % (edges[i], edges[i + 1], h[i], 100 * h[i] / h.sum(),
                 "#" * int(round(40 * h[i] / h.max()))))
    print("  inside the beam pipe, i.e. a decay rather than an interaction: "
          "%.1f%%" % (100 * h[0] / h.sum()))

    print("\nwhat produced them")
    tot = sum(data["parents"].values())
    toth = sum(data["parent_hits"].values())
    for k in ("charged", "photon", "neutral", "unknown"):
        print("  %-8s %5.1f%% of particles, %5.1f%% of clusters"
              % (k, 100 * data["parents"][k] / tot,
                 100 * data["parent_hits"][k] / toth))
    print("  species: " + ", ".join(
        "%d %.0f%%" % (k, 100 * v / sum(data["species"].values()))
        for k, v in data["species"].most_common(6)))
    print("  muons, i.e. pion and kaon decay in flight: %.1f%%"
          % (100 * (data["species"][13] + data["species"][-13])
             / sum(data["species"].values())))


def model_profile(event):
    """Band the generated space points by whether they come from a primary."""
    sp = event.spacePoints
    n = len(sp)
    x = np.fromiter((s.x for s in sp), np.float32, n)
    y = np.fromiter((s.y for s in sp), np.float32, n)
    z = np.abs(np.fromiter((s.z for s in sp), np.float32, n))
    r = np.hypot(x, y)
    pid = np.asarray(event.particleIds, dtype=np.int64)
    primary = np.fromiter((p.primary for p in event.particles), bool,
                          len(event.particles))
    is_pri = primary[pid]
    out = {}
    for key, mask in (("primary", is_pri), ("other", ~is_pri)):
        out[key] = {"r": np.histogram(r[mask], bins=R_BANDS)[0].astype(float),
                    "z": np.histogram(z[mask], bins=Z_BANDS)[0].astype(float),
                    "n": float(mask.sum())}
    out["all"] = {"n": float(n)}
    return out


def objective(reference, model) -> float:
    """Mean squared log-ratio of two banded profiles, each self-normalised."""
    total = 0.0
    for axis in ("r", "z"):
        u = np.asarray(reference[axis], float)
        v = np.asarray(model[axis], float)
        both = (u > 0) & (v > 0)
        u, v = u[both] / u[both].sum(), v[both] / v[both].sum()
        total += np.mean(np.log(v / u) ** 2)
    return total / 2


def scan(data) -> None:
    """Score model variants against the reference."""
    from acts.fatras import synthetic as syn

    cl = data["clusters"]
    reference = {
        "other": {"r": cl["secondary"]["r"] + cl["unlinked"]["r"],
                  "z": cl["secondary"]["z"] + cl["unlinked"]["z"],
                  "n": cl["secondary"]["n"] + cl["unlinked"]["n"]},
        "primary": cl["primary"],
    }
    target = sum(v["n"] for v in cl.values())
    layout = syn.makeItkPixelLayout()

    def variant(**fields):
        config = syn.EventConfig.itkPixelTtbarPu200()
        for name, value in fields.items():
            if not hasattr(config, name):
                raise SystemExit("EventConfig has no '%s'" % name)
            setattr(config, name, float(value))
        # the count is matched by construction, so the score is shape only
        for _ in range(3):
            summary = syn.summarize(syn.generateEvent(layout, config), 1.0)
            config.secondaryRate = max(1e-4, config.secondaryRate
                                       * (target - summary.primaryHits)
                                       / summary.secondaryHits)
        return config

    print("%-38s %7s %8s %8s" % ("", "rate", "obj", "hits/sec"))
    for name, fields in (
        ("as shipped", {}),
        ("without the decays", dict(decayYield=0.0)),
        ("without the forward material", dict(forwardMaterialScale=0.0)),
        ("without either", dict(decayYield=0.0, forwardMaterialScale=0.0)),
    ):
        config = variant(**fields)
        event = syn.generateEvent(layout, config)
        p = model_profile(event)
        hits = np.fromiter((q.numHits for q in event.particles), np.int32,
                           len(event.particles))
        primary = np.fromiter((q.primary for q in event.particles), bool,
                              len(event.particles))
        sel = (~primary) & (hits > 0)
        print("%-38s %7.3f %8.4f %8.2f"
              % (name, config.secondaryRate,
                 objective(reference["other"], p["other"]), hits[sel].mean()))
    print("reference hits per secondary: %.2f" % data["sec_hits"].mean())


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=("anatomy", "scan"))
    parser.add_argument("--fullsim", required=True)
    parser.add_argument("--events", type=int, default=5)
    args = parser.parse_args()

    data = read(args.fullsim, args.events)
    print("%d events\n" % data["n_ev"])
    if args.mode == "anatomy":
        anatomy(data)
    else:
        scan(data)


if __name__ == "__main__":
    main()
