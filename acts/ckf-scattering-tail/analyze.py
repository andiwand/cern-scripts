#!/usr/bin/env python3
"""Counts and post-ambiguity score scans; no chi2-distribution assumption."""
import argparse
import json
from pathlib import Path

import awkward as ak
import numpy as np
import uproot

p = argparse.ArgumentParser()
p.add_argument("run", type=Path)
p.add_argument("--output", type=Path)
a = p.parse_args()
events = [
    json.loads(line) for line in (a.run / "diagnostics.jsonl").read_text().splitlines()
]
config = json.loads((a.run / "config.json").read_text())
out = {"events": len(events), "pileup": config["pu"], "variants": {}, "occupancy": {}}
for layer, modules in config["modules"].items():
    counts = np.array([e["occupancy"].get(layer, 0) for e in events])
    out["occupancy"][layer] = {
        "hits_per_event": float(counts.mean()),
        "hits_per_module": float(counts.mean() / modules),
        "modules": modules,
    }


def keys(arrays, names):
    return list(zip(*(np.asarray(arrays[n]).tolist() for n in names)))


event_results = {}
truth_selection = None
for collection in events[0]["tracks"]:
    perf = uproot.open(a.run / (collection + "_performance.root"))
    matching = perf["matchingdetails"].arrays(library="np")
    particle_keys = keys(
        matching,
        [
            "event_nr",
            "particle_id_vertex_primary",
            "particle_id_vertex_secondary",
            "particle_id_particle",
            "particle_id_generation",
            "particle_id_sub_particle",
        ],
    )
    selected = set(particle_keys)
    if truth_selection is None:
        truth_selection = selected
    assert selected == truth_selection, "Truth denominator differs across variants"
    tree = uproot.open(a.run / (collection + "_tracks.root"))["tracksummary"]
    branches = [
        "track_nr",
        "trackClassification",
        "nMeasurements",
        "chi2Sum",
        "NDF",
        "majorityParticleId_vertex_primary",
        "majorityParticleId_vertex_secondary",
        "majorityParticleId_particle",
        "majorityParticleId_generation",
        "majorityParticleId_sub_particle",
    ]
    jagged = tree.arrays(["event_nr"] + branches)
    flat = {b: ak.to_numpy(ak.flatten(jagged[b])) for b in branches}
    flat["event_nr"] = np.repeat(
        ak.to_numpy(jagged["event_nr"]), ak.to_numpy(ak.num(jagged["track_nr"]))
    )
    track_keys = keys(
        flat,
        [
            "event_nr",
            "majorityParticleId_vertex_primary",
            "majorityParticleId_vertex_secondary",
            "majorityParticleId_particle",
            "majorityParticleId_generation",
            "majorityParticleId_sub_particle",
        ],
    )
    classification = flat["trackClassification"]
    assert np.isin(classification, [1, 2, 3]).all(), "Unclassified tracks"
    fake = classification == 3
    associated = np.isin(classification, [1, 2])
    lookup = {
        (e["event"], r[0]): r[1:] for e in events for r in e["tracks"][collection]
    }
    rows = [
        lookup[(int(e), int(t))] for e, t in zip(flat["event_nr"], flat["track_nr"])
    ]

    def metrics(keep):
        found = {k for k, m in zip(track_keys, keep & associated) if m} & selected
        return {
            "tracks": int(keep.sum()),
            "fake_tracks": int((keep & fake).sum()),
            "duplicate_tracks": int((keep & associated).sum())
            - len({k for k, m in zip(track_keys, keep & associated) if m}),
            "matched_particles": len(found),
            "particles": len(selected),
            "efficiency": len(found) / len(selected) if selected else None,
            "fake_fraction": (
                float((keep & fake).sum() / keep.sum()) if keep.any() else None
            ),
        }

    found = {k for k, m in zip(track_keys, associated) if m} & selected
    event_results[collection] = [
        {
            "found": {k for k in found if k[0] == e["event"]},
            "particles": sum(k[0] == e["event"] for k in selected),
            "fake": int((fake & (flat["event_nr"] == e["event"])).sum()),
            "tracks": int((flat["event_nr"] == e["event"]).sum()),
        }
        for e in events
    ]
    result = metrics(np.ones(len(rows), dtype=bool))
    assert result["matched_particles"] == int(matching["matched"].sum()), (
        collection,
        result,
    )
    if rows and rows[0][0] is not None:
        score = np.array([r[0] for r in rows])
        tail_weight = np.array([r[2] for r in rows])
        log_likelihood = np.array([r[1] for r in rows])
        assert np.isfinite(score).all() and (score >= 0).all(), collection
        assert np.isfinite(log_likelihood).all(), collection
        assert ((tail_weight >= 0) & (tail_weight <= flat["nMeasurements"])).all()
        assert np.array_equal([r[3] for r in rows], flat["nMeasurements"])
        variant = collection.split("_")[0]
        if variant.startswith("tail") and variant[4:]:
            assert (score <= float(variant[4:])).all(), collection
        result["score_quantiles"] = {
            name: np.quantile(score[mask], [0.5, 0.9, 0.95, 0.99]).tolist()
            for name, mask in [("associated", associated), ("fake", fake)]
            if mask.any()
        }
        result["tail_weight_quantiles"] = np.quantile(
            tail_weight, [0.5, 0.9, 0.99]
        ).tolist()
        thresholds = [20, 30, 40, 50, 60, 70, 80, 100, 120, 160, 240]
        result["scan"] = {str(c): metrics(score <= c) for c in thresholds}
        result["fit_chi2_scan"] = {
            str(c): metrics(flat["chi2Sum"] <= c) for c in thresholds
        }
        result["tail_weight_scan"] = {
            str(c): metrics(tail_weight <= c) for c in [0.25, 0.5, 1, 2, 3, 5]
        }
    out["variants"][collection] = result
    print(
        collection,
        {
            k: v
            for k, v in result.items()
            if k not in ["scan", "fit_chi2_scan", "tail_weight_scan"]
        },
    )

# Paired event bootstrap; exploratory intervals, not a threshold optimization.
out["comparisons"] = {}
rng = np.random.default_rng(42)
samples = rng.integers(0, len(events), size=(10000, len(events)))
for base, test in [
    ("core15", "tail"),
    ("core25", "tail"),
    ("core49", "tail"),
    ("tail", "tail80"),
]:
    bk, tk = base + "_ambi", test + "_ambi"
    if bk not in event_results or tk not in event_results:
        continue
    b, t = event_results[bk], event_results[tk]

    def rates(rows, numerator, denominator):
        n = np.array(
            [len(r["found"]) if numerator == "found" else r[numerator] for r in rows]
        )
        d = np.array([r[denominator] for r in rows])
        return 100 * n[samples].sum(axis=1) / d[samples].sum(axis=1)

    out["comparisons"][test + "_minus_" + base] = {
        "matched_gained": sum(len(y["found"] - x["found"]) for x, y in zip(b, t)),
        "matched_lost": sum(len(x["found"] - y["found"]) for x, y in zip(b, t)),
        "efficiency_delta_pp_95ci": np.quantile(
            rates(t, "found", "particles") - rates(b, "found", "particles"),
            [0.025, 0.975],
        ).tolist(),
        "fake_fraction_delta_pp_95ci": np.quantile(
            rates(t, "fake", "tracks") - rates(b, "fake", "tracks"), [0.025, 0.975]
        ).tolist(),
    }

# The paired pilot must leave every stored branch bit-identical when only
# diagnostic scoring is enabled. The score column itself is intentionally new.
if "unscored" in config["variants"] and "tail" in config["variants"]:
    for stage in ["ckf", "ambi"]:
        left = uproot.open(a.run / ("tail_" + stage + "_tracks.root"))[
            "tracksummary"
        ].arrays()
        right = uproot.open(a.run / ("unscored_" + stage + "_tracks.root"))[
            "tracksummary"
        ].arrays()
        # Compare buffers byte-for-byte, including identical NaN payloads.
        lf, ln, lb = ak.to_buffers(left)
        rf, rn, rb = ak.to_buffers(right)
        assert lf == rf and ln == rn and lb.keys() == rb.keys(), stage
        assert all(lb[k].tobytes() == rb[k].tobytes() for k in lb), stage
    out["scoring_observation_only"] = True

path = a.output or a.run / "summary.json"
path.write_text(json.dumps(out, indent=2, allow_nan=False) + "\n")
print(path)
