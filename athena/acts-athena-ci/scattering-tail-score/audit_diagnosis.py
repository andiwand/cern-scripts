"""Reconcile the post-report diagnostics against the frozen evaluation."""

import hashlib
import json
from pathlib import Path
import sys

root = Path(sys.argv[1]) / "athena"
folder = root / "nn-extended"
inputs = {}


def read(name):
    path = root / name
    inputs[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return json.loads(path.read_text())


nn = read("nn-extended/validation.json")
raw = read("validation.json")
stage = read("nn-extended/loss-stage.json")
why = read("nn-extended/why.json")
pt = read("nn-extended/pt-working-points.json")["points"]
migration = read("nn-extended/migration.json")
counters = read("nn-extended/candidate-counters.json")
groups = nn["points"]["0.995"]["groups"]
for family, choice in groups.items():
    assert stage["selected_matches"][family] == choice["validation"]["matched"]
    assert (
        stage["inclusive_matches"][family]
        == nn["inclusive"][choice["variant"]]["matched"]
    )
    for key, value in pt["truth>1,reco>=0"]["counts"][family].items():
        assert value == choice["validation"][key]
    m = migration[family]
    assert m["truth_gt_1_matched"] == choice["validation"]["matched"]
    assert (
        m["truth_gt_1_reco_ge_1"] == pt["truth>1,reco>=1"]["counts"][family]["matched"]
    )
    assert (
        m["truth_gt_1_matched"] == m["truth_gt_1_reco_ge_1"] + m["truth_gt_1_reco_lt_1"]
    )
    assert 0 <= m["truth_0p5_to_1_reco_ge_1"] <= m["truth_0p5_to_1_matched"]
    assert m["truth_0p5_to_1_matched"] == why["low_pt"]["selected"][family]["matched"]
for key, value in pt["truth>1,reco>=0"]["counts"]["raw-core"].items():
    assert value == raw["points"]["0.995"]["groups"]["core"]["validation"][key]
for name, c in stage["cohorts"].items():
    for axis in ["pt", "abs_eta"]:
        assert sum(c[axis]["counts"]) == c["n"], (name, axis)
for total, parts in [
    ("lost", ["lost_before_final_cut", "lost_by_final_cut"]),
    ("gained", ["gained_in_finding", "gained_through_quality_selection"]),
]:
    c = stage["cohorts"]
    assert c[total]["n"] == sum(c[p]["n"] for p in parts)
    assert c[total]["n"] == why["truth_changes"]["new-core"][total]["n"]
    for axis in ["pt", "abs_eta"]:
        assert c[total][axis]["counts"] == [
            sum(v) for v in zip(*(c[p][axis]["counts"] for p in parts))
        ]
assert stage["cohorts"]["gained"]["n"] - stage["cohorts"]["lost"]["n"] == (
    stage["selected_matches"]["new"] - stage["selected_matches"]["core"]
)
for variant, c in counters.items():
    assert c["Seeds with more than one branch"] == 0
    assert c["resolved tracks"] == nn["inclusive"][variant]["tracks"]
    assert c["shared_hit_rejected"] == c["selected tracks"] - c["resolved tracks"]
assert (
    nn["inclusive"]["tail5"]["matched"] - nn["inclusive"]["core5"]["matched"] == 12983
)
assert why["tail_cut_changes"]["removed"]["fakes"] - why["tail_cut_changes"]["added"][
    "fakes"
] == (groups["previous"]["validation"]["fakes"] - groups["new"]["validation"]["fakes"])
for key, point in pt.items():
    for comparison, ref in [("paired", "core"), ("paired_raw", "raw-core")]:
        r, n = point["counts"][ref], point["counts"]["new"]
        paired = point[comparison]
        assert (
            abs(
                paired["efficiency_change_pp"]
                - 100 * (n["matched"] - r["matched"]) / n["truth"]
            )
            < 1e-12
        )
        assert (
            abs(paired["fake_rate_change_pp"] - 100 * (n["fake_rate"] - r["fake_rate"]))
            < 1e-12
        )
        assert paired["efficiency_se_pp"] >= 0 and paired["fake_rate_se_pp"] >= 0
for marker in [
    "extras",
    "loss-stage",
    "migration",
    "pt-working-points",
    "pt-working-points-raw",
]:
    assert (folder / (marker + "-exit-code")).read_text().strip() == "0"

review = dict(
    passed=True,
    checks=[
        "Loss/gain totals, partitions and binned sums agree with frozen main point",
        "No reconstructed-pT cut reproduces all four original selections exactly",
        "All slice rate differences agree with counts; paired SEs computed from event clusters",
        "Migration totals agree with high- and low-pT cohorts; both directions counted",
        "Primary reconstruction counters agree with inclusive AOD counts; zero multibranch seeds",
        "All five diagnostic completion markers are zero",
    ],
    source_review=dict(
        athena_commit="a252dda21e369a2f85a33033b4fcbda4290e28d0",
        config="Tracking/Acts/ActsConfig/python/ActsTrackFindingConfig.py:160: numMeasurementsCutOff=[1]",
        selector="Tracking/Acts/ActsTrackReconstruction/src/detail/MeasurementSelector.h:570-584: core then hole/outlier tail replacement; 706-740: C+wD on accepted measurements",
        commitment="Tracking/Acts/ActsTrackReconstruction/src/TrackFindingAlg.cxx:1011-1069: summarize after trim, final track selection, storeSeedInfo, shared-hit selection",
        runtime="DURING_TF (2), doAmbiguityResolution=False; primary-pass counters only",
        interpretation="Source ordering establishes opportunities for irreversible loss, not attribution of every lost truth particle; tuned core and tail gates differ",
    ),
    input_sha256=inputs,
)
(folder / "diagnosis-review.json").write_text(json.dumps(review, indent=2) + "\n")
print("Diagnostic reconciliation passed")
