"""Build a concise, data-backed report; retain the chronological notebook separately."""

import json
from pathlib import Path
import sys
import re

root = Path(sys.argv[1])
a = root / "athena"
read = lambda path: json.loads((a / path).read_text())
raw = read("validation.json")
nn = read("nn-extended/validation.json")
cross = read("nn-extended/cross-calibration.json")
high = read("nn-extended/cross-calibration-0.998.json")
audit = read("nn-extended/final-audit.json")
diagnosis = read("nn-extended/diagnosis-review.json")
assert audit["checks"].endswith("pass")
assert diagnosis["passed"]
labels = {"core": "Nominal CKF", "previous": "Previous tails", "new": "Tails + score"}
gates = {"4": "4/6", "5": "5/7", "7": "7/10", "10": "10/14", "14": "14/20"}


def table(headers, rows):
    return "\n".join(
        ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
        + ["| " + " | ".join(map(str, row)) + " |" for row in rows]
    )


def difference(r):
    return f"{r['efficiency_change_pp']:+.5f} ± {r['efficiency_se_pp']:.5f} pp efficiency; {r['fake_rate_change_pp']:+.5f} ± {r['fake_rate_se_pp']:.5f} pp fake rate"


main_rows = []
for calibration, study in [("Raw", raw), ("NN", nn)]:
    for family, c in study["points"]["0.995"]["groups"].items():
        v = c["validation"]
        gate = gates[c["variant"].removeprefix("core").removeprefix("tail")]
        metric = "T/D" if family == "new" else "χ²/D"
        assert c["metric"] == ("score/dim" if family == "new" else "chi2/dim")
        main_rows.append(
            [
                f"{calibration} / {labels[family]}",
                gate,
                f"{metric} ≤ {c['cut']:.4f}",
                f"{v['matched']:,}",
                f"{100*v['efficiency']:.4f}%",
                f"{v['fakes']:,} / {v['tracks']:,}",
                f"{100*v['fake_rate']:.5f}%",
            ]
        )
scan_rows = []
for retention, point in nn["points"].items():
    r = point["paired"]["new-core"]["rates"]
    scan_rows.append(
        [
            f"{100*float(retention):g}%",
            point["groups"]["core"]["validation"]["fakes"],
            point["groups"]["new"]["validation"]["fakes"],
            f"{r['efficiency_change_pp']:+.5f} ± {r['efficiency_se_pp']:.5f}",
            f"{r['fake_rate_change_pp']:+.5f} ± {r['fake_rate_se_pp']:.5f}",
        ]
    )
resolution_rows = []
for prefix, calibration in [("raw", "Raw"), ("nn", "NN")]:
    for family in labels:
        p = cross["common_profiles"][prefix + "-" + family]
        resolution_rows.append(
            [f"{calibration} / {labels[family]}"]
            + [
                f"{scale*p[field]['width68']:.2f} / {scale*p[field]['width95']:.2f}"
                for field, scale in [("d0res", 1000), ("z0res", 1000), ("qptres", 100)]
            ]
        )
prompt = cross["common_profiles"]["nn-core"]["d0res"]["n"]
new_vs_nominal = cross["paired"]["nn-new minus nn-core"]
new_vs_previous = nn["points"]["0.995"]["paired"]["new-previous"]["rates"]
score = cross["score_profiles"]["nn-new"]
text = f"""# CKF scattering-tail score: ODD and Athena ITk

**Finding:** The cumulative mixture score rejects many of the tail model's extra fakes,
but the tested configuration does not establish a better efficiency/fake tradeoff
than tuned nominal CKF for the inclusive selection, including with NN calibration.
However, an exploratory reconstructed-pT≥1 GeV selection improves both efficiency
and fake rate; narrower resolution widths and reduced threshold migration warrant
a focused follow-up.

**Recommendation:** Keep nominal CKF as the performance baseline and leave tail
handling/score opt-in. First test a tail-aware refit with nominal hit assignments
and track acceptance held fixed. This tests whether the benefit comes from the fit.
Do not add score terms or broadly retune the mixture yet.

## Original full-simulation comparison

Existing Geant4 ITk ttbar μ=200 RDOs; no new simulation. Freeze cuts on 200 events,
evaluate on 800 others: **1,058,358 selected truth particles**. The NN follow-up
reuses an already inspected sample and is exploratory. Main target: exactly
223,010 training matches (99.5% of the raw tail5 reference). Displayed cuts are
rounded; frozen plans contain the exact values.

{table(['Calibration / handling', 'Gate [σ]', 'Final cut', 'Matched', 'Efficiency', 'Fakes / tracks', 'Fake rate'], main_rows)}

With NN, new minus nominal: **{difference(new_vs_nominal)}**.
Efficiency is compatible; fake count rises from 472 to 620 (**31%**).
Against previous NN tails, fakes fall from 1,102 to 620 (**44%**), with
{difference(new_vs_previous)}. Errors are paired event-cluster standard errors
(one sigma), not confidence intervals for the complete scan.

### Original gate scan across six targets

Targets denote training retention, not absolute efficiency. Nominal gates and
χ² or χ²/D cuts are optimized independently; previous tails use fit quality,
new tails use T/D. Evaluation efficiencies are never forced to agree afterward.

{table(['Training target', 'Nominal fakes', 'New fakes', 'Δ efficiency [pp]', 'Δ fake rate [pp]'], scan_rows)}

Before hole/outlier tuning, five points favour nominal in both central values. At 99.8%, new has fewer fakes
than NN nominal but loses 449 matches. The original raw nominal gives
**883,266 matches / 816 fakes**, versus **883,222 / 896** for NN + new score:
{difference(high['paired']['nn-new minus raw-core'])}. Thus this crossover does
not establish an overall improvement. The comparison uses a discrete gate scan:
NN nominal selects 14/20σ here; raw nominal selects 10/14σ. Intermediate NN gates
were not tested.

### Resolutions on identical truth

Central 68.27% / 95% interval half-widths on the same **{prompt:,} prompt particles**
reconstructed by all six main-point selections; descriptive widths, no uncertainty
bands. Relative q/pT residual is `(reco − truth) / abs(truth)`.

{table(['Calibration / handling', 'd0 [µm]', 'z0 [µm]', 'Relative q/pT [%]'], resolution_rows)}

Previous tail handling already gives the width improvement; the score changes it
little. Associations also change, so this does not isolate a fit-only benefit.

## Why inclusive finding still loses

At identical NN gates 5/7σ, before the offline cut, tails yield **12,983** more
truth matches but increase fakes **115→1,406**. The model helps real tracks;
it also accepts unrelated hits. At the tuned main point, new versus nominal
exchanges **8,798 gained / 8,833 lost** particles, mostly true pT=1–2 GeV.
**5,398 losses (61%) are already absent before the final cut**; 3,435 are removed
by it. These tuned gates differ, so this is a loss-stage decomposition, not a
causal attribution to one algorithm component.

Source and logs explain why a late cut has limited reach:

- `numMeasurementsCutOff=[1]`; all five audited settings report zero seeds with
  multiple branches. On a hole/outlier, tail selection replaces the core choice;
  it does not retain a hole alternative. A locally plausible wrong hit can change
  subsequent propagation. Covariance inflation C+wD also applies to accepted core hits.
- This run uses **during-finding shared-hit suppression**, not a standalone greedy
  ambiguity solver. Seed information is committed before shared-hit rejection;
  the studied quality cuts run afterward, offline. At the same 5/7σ gate, shared-hit
  rejections rise **41,983→56,547**. Late cuts cannot recover discarded paths or
  previously skipped seeds. These counters do not identify each lost truth particle.
- T models signal scattering, **not signal versus unrelated hits**. Surviving
  NN + new fakes have mean Σw **{score['fake_tracks']['mean_tail_weight']:.2f}**, versus
  **{score['selected_truth_tracks']['mean_tail_weight']:.2f}** for selected-truth tracks.
  Normalizing by the core peak removes the absolute prediction-volume penalty.
  A per-hit signal/background score would instead contain
  `−2 log(P_D L/ρ) = t + log det(2π S0) − 2 log(P_D) + 2 log(ρ)`, with detection
  probability P_D and local hit density ρ in the same measurement coordinates.
  Holes, gate acceptance and track length need consistent treatment. This is a
  proposed model, not a validated replacement or proof of the dominant failure.

An earlier non-NN, different-mixture ablation supports the hole mechanism:
disabling hole re-selection changed efficiency/fake rate from 83.73%/0.089% to
83.38%/0.042% (nominal 83.02%/0.018%). It is not a current-NN measurement.

### Historical threshold check and possible alternatives

The earlier post-hoc reco pT≥1 GeV slice gave NN new versus nominal **834,521
versus 831,622 matches**, **147 versus 181 fakes**. Both upward and downward
threshold crossings decreased; away from the threshold there was no general
finding gain. This slice was not independently tuned and does not determine the
current recommendation: **the hole/outlier scan keeps every pT selection fixed**.
Full threshold and migration counts remain linked below.

A tail-aware refit with nominal hit assignments and acceptance fixed could isolate
the resolution benefit. Applying final quality cuts before seed/shared-hit
commitment could reduce interference, but cannot recover discarded hole paths.
An occupancy-aware signal/background likelihood is a larger finding project;
another χ² term or more Gaussian components alone does not address that distinction.
These remain unimplemented options, not demonstrated improvements. NN cluster
response and scattering noise also act differently: enlarging prediction covariance
gives a measurement more influence; a measurement-error tail would give it less.

### Cluster-response control

Reuse 5,000 full-simulation 10 GeV muons, including 320 fixed delta-like tags
(raw >5σ cluster residual plus cell proximity). No final quality cut; same seeds
and strip calibration. These tags are a proxy, not exact delta-ray or merged-cluster truth.

| Calibration / handling | Gate [σ] | Matched / 5,000 | Tagged / 320 |
|---|---|---:|---:|
| Raw / nominal | 7/10 | 4,991 | 319 |
| Raw / nominal | 4/6 | 4,978 | 313 |
| Raw / tails | 4/6 | 4,983 | 315 |
| NN / nominal | 7/10 | 4,991 | 319 |
| NN / nominal | 4/6 | 4,979 | 319 |
| NN / tails | 4/6 | 4,985 | 319 |

Tight raw gates lose six tagged muons. NN at 4/6 recovers all six, but loses five
other matches: **net +1**. Tagged gain: +1.875 ± 0.759 pp; all fake counts are zero.
This supports the proposed cluster-tail/gate mechanism, while leaving its pileup
impact and merged-cluster contribution unresolved.

## ODD context

20 ttbar events each at PU200/400, Fatras GeneralMixture, shared digitization/seeds.
PU400 has 1.95× the measurement occupancy of PU200; equivalence to Geant4 ITk
occupancy is not established. The live absolute budget T≤80 removes nine of 149
previous-tail fakes at PU400 while losing seven matches; PU200 gives no fake reduction.
Common-truth resolution differences are small.

A later two-fold T/D scan at PU400 gives (matches, fakes): nominal **31,694 / 132**,
previous **31,685 / 96**, new **31,685 / 84**, from 34,306 selected particles.
That exploratory gain motivated Athena, but the 20 events were already inspected.
The earlier ODD plots and full counters remain in the additional figures and notebook.

## Score and implementation

Use the final calibrated measurement against the original prediction, before
covariance inflation/filtering:

```
r = z − H x_pred
S0 = R + H C Hᵀ; S1 = S0 + H D_tail Hᵀ
L = (1−ε) N(r; 0, S0) + ε N(r; 0, S1)
w = ε N(r; 0, S1) / L
t = −2 log[L / N(0; 0, S0)]; T = Σt
```

`w` is posterior to the measurement although computed before filtering. Σw is a
soft tail-use diagnostic, not a physical kink count. T already includes residual
cost; a second χ² term would add another tunable weight. T is not χ² distributed.
D in T/D denotes **summed measurement dimension**, not fit degrees of freedom.
The partial ratio is non-monotonic, so T/D is only a final cut here.

ACTS uses optional dynamic columns in the creator/branch stopper; no new CKF actor.
Branch prefixes are inherited, accepted hits counted once, holes/outliers skipped,
and sums recomputed after trimming/joining. Scoring defaults off; a finite absolute
T budget supports live pruning. Athena records the final score for this offline study.
Bremsstrahlung multi-component finding is unsupported. A C++/Python callable
customizes `(weight, widthScale)` of the two-component model; it does not add an
arbitrary number of Gaussians or replace the Highland core.

## Methods and review

- Athena truth: stable charged generator particles, pT>1 GeV, |η|<4, production
  radius<300 mm when available. Match probability >0.5; efficiency counts unique
  truth matches. Fake: probability <0.5 or non-finite, regardless of truth-link
  availability; denominator reconstructed |η|<4 tracks. Exactly 0.5 is neither.
  ODD instead requires pT≥1 GeV, |η|<3 and ≥9 measurements.
- Resolution: one highest-probability track per truth particle; ties use χ²/D then
  index. Prompt radius<0.1 mm; straight-line truth perigee relative to track reference.
- Athena primary pass uses the Geant4-refitted tail mixture; secondary tails and
  bremsstrahlung recovery disabled. NN is before selection at all charges/sizes,
  with corrected Y pitch and chosen-subcluster uncertainty. Seeds and strips fixed.
- Scan nominal gates 4/6, 5/7, 7/10, 10/14σ, extended to 14/20σ for NN; tail gates
  4/6, 5/7, 7/10σ. Minimize training fake count at six fixed match targets. Raw
  nominal cannot reach the highest target in its original scan; no result is invented.
- Native NN reuses the same four models as ONNX. Three 200-event controls preserve
  matched/fake counts; 4/6 and 5/7 associations agree exactly. At 7/10 native drops
  one unlinked probability-0.889 track, which is not fake. Remaining full links and
  eight hit summaries agree after accounting for it. Fits are not bit-identical:
  p99 |ΔpT|=0.00184 MeV; maximum relative difference 0.228% in that control.
- Four focused C++ suites, custom-model Python/pilot checks and analysis fixtures
  pass. Scoring on/off preserves pilot tracking; official IDPVM pilot counters agree.
  All final reconstructions/exports pass. Independent main-point counts, paired
  rates, unchanged/intermediate points, frozen hashes and NN configuration/model
  hashes pass the final audit.
- Follow-up audits reconcile loss partitions, threshold counts, both migration
  directions and reconstruction counters. Cleanup frees 15.016 GiB of regenerable
  objects/training outputs. A further 14.837 GiB of completed AODs is removed;
  numerical exports, configurations, logs, source and runtime libraries remain.
  The compact scan archive verifies 666 files; four new NPZ exports and two useful
  AODs have verified local copies. The 13.136 GiB temporary working copy is removed.

ACTS `ac589a82fe`; Athena study `a252dda21e3` with ACTS `b4bd622c24` (v48.5.0),
nightly `2026-11-19T2100`. Scripts: `acts/ckf-scattering-tail/score` and
`athena/acts-athena-ci/scattering-tail-score` in https://github.com/andiwand/cern-scripts.

[Raw results](athena/validation.json) · [Final NN results](athena/nn-extended/validation.json) ·
[NN frozen plan](athena/nn-extended/frozen-plan.json) · [Paired comparison](athena/nn-extended/cross-calibration.json) ·
[High point](athena/nn-extended/cross-calibration-0.998.json) · [Audit](athena/nn-extended/final-audit.json) ·
[Muon control](athena/gun-delta-results.json) · [Raw diagnosis](athena/why.json) ·
[NN diagnosis](athena/nn-extended/why.json) · [Loss stages](athena/nn-extended/loss-stage.json) ·
[pT selections](athena/nn-extended/pt-working-points.json) · [Migration](athena/nn-extended/migration.json) ·
[Diagnostic review](athena/nn-extended/diagnosis-review.json) ·
[Earlier ablation](../../../atlas/tsi/notebook/2026-11-21_scattering-tail.md) ·
[Provenance](athena/provenance.json) · [Cleanup manifest](athena/cleanup.json).

Vector exports: [raw tradeoff](athena/tradeoff.pdf), [NN tradeoff](athena/nn-tradeoff.pdf),
[NN resolutions](athena/nn-resolutions.pdf). The [chronological notebook](../{root.name}.md)
retains intermediate tables, original software details and links to all earlier studies.
"""
if (a / "hole-scan/validation.json").exists():
    scan = read("hole-scan/validation.json")
    scan_audit = read("hole-scan/final-audit.json")
    assert scan_audit["checks"].endswith("pass")
    assert all(
        point["paired"]["new-core"]["rates"]["efficiency_change_pp"] < 0
        and point["paired"]["new-core"]["rates"]["fake_rate_change_pp"] > 0
        for point in scan["points"].values()
    )
    begin = text.index("**Finding:**")
    end = text.index("## Original full-simulation comparison", begin)
    text = (
        text[:begin]
        + """**Finding:** The hole/outlier scan substantially narrows the gap: at the main
working point, tails + score gives **880,501 matches / 492 fakes**, versus tuned
NN + nominal CKF's **880,685 / 472**. Across all six targets, nominal retains the
better central values for both efficiency and fake rate. All pT selections stay fixed.
At the three highest targets the differences are compatible with near-parity;
there is no demonstrated finding advantage from the tested tail model.

**Recommendation:** Keep nominal CKF and stop tuning this CKF-tail approach for
now. Retain the useful nominal hole/outlier tuning for fresh-sample confirmation.
The remaining resolution benefit motivates, at most, a separate fixed-hit refit
study; it does not justify more finding complexity.

"""
        + text[end:]
    )
    scan_main = []
    for family, c in scan["points"]["0.995"]["groups"].items():
        match = re.fullmatch(r"(?:core|tail)(\d+)u(\d+)h(\d+)o(\d+)", c["variant"])
        if match:
            lower, upper, holes, outliers = match.groups()
            config = f"{lower}/{upper}σ; H{holes}/O{outliers}"
        else:
            lower = c["variant"].removeprefix("core").removeprefix("tail")
            config = f"{gates[lower]}σ; H1/O1"
        v = c["validation"]
        scan_main.append(
            [
                labels[family],
                config,
                f"{'T/D' if family == 'new' else ('χ²/D' if c['metric'] == 'chi2/dim' else 'χ²')} ≤ {c['cut']:.4f}",
                f"{v['matched']:,}",
                f"{v['fakes']:,} / {v['tracks']:,}",
                f"{100*v['fake_rate']:.5f}%",
            ]
        )
    scan_points = []
    for retention, point in scan["points"].items():
        r = point["paired"]["new-core"]["rates"]
        scan_points.append(
            [
                f"{100*float(retention):g}%",
                point["groups"]["core"]["validation"]["fakes"],
                point["groups"]["new"]["validation"]["fakes"],
                f"{r['efficiency_change_pp']:+.5f} ± {r['efficiency_se_pp']:.5f}",
                f"{r['fake_rate_change_pp']:+.5f} ± {r['fake_rate_se_pp']:.5f}",
            ]
        )
    latest = scan["points"]["0.995"]
    latest_resolution_rows = []
    for family in labels:
        profiles = latest["groups"][family]["common_resolutions"]
        latest_resolution_rows.append(
            [labels[family]]
            + [
                f"{scale*profiles[field]['width68']:.2f} / {scale*profiles[field]['width95']:.2f}"
                for field, scale in [("d0res", 1000), ("z0res", 1000), ("qptres", 100)]
            ]
        )
    latest_prompt = latest["groups"]["core"]["common_resolutions"]["d0res"]["n"]
    scan_section = f"""## Hole/outlier scan: pT selection unchanged

22 new settings plus eight existing NN settings. Around nominal 10σ and tail 5σ
measurement gates, vary upper gates 10/14/20σ and 5/7/10σ respectively, each with
maximum (holes,outliers)=(1,1),(2,1),(1,2). At the original split also test
(0,1),(1,0),(2,2). Equal local scan structure; not an exhaustive grid at every gate.
H/O denotes the maximum holes/outliers; per-subdetector and combined-count
limits stay fixed. All other primary-pass flags, NN configuration and library
hashes agree. With equal gates, changing O1→O2 produces identical exported arrays,
as there is no outlier interval.

Tune on the original 200 training events at the same six targets; freeze choices
before reconstructing selected settings on 800 evaluation events. These events
were already inspected, so the follow-up remains exploratory. Main target:

{table(['Handling', 'Gate / maximum counts', 'Final cut', 'Matched', 'Fakes / tracks', 'Fake rate'], scan_main)}

Main-point new minus nominal: **{difference(latest['paired']['new-core']['rates'])}**.

Relative to the earlier new-score setting, main-point fakes fall **620→492**
with **149 fewer matches**. The nominal main choice stays unchanged. At the highest
target, nominal 10/10σ H2/O1 gives **885,140 matches / 664 fakes**, improving both
central values over its earlier 99.8% point (**883,671 / 1,048**). Thus this tuning
helps nominal too; the tail gain alone is not evidence for a better final tradeoff.
The hole/outlier policy mattered, but this scan does not identify the remaining
loss mechanism. The diagnosis below refers to the original comparison.

New minus independently retuned NN nominal at all targets:

{table(['Training target', 'Nominal fakes', 'New fakes', 'Δ efficiency [pp]', 'Δ fake rate [pp]'], scan_points)}

At the three highest targets, each efficiency and fake-rate difference is below
two paired standard errors: these results do not establish a remaining penalty,
but also provide no evidence of an advantage. The lower targets favour nominal.

[Design](athena/hole-scan/design.json) · [Frozen choices](athena/hole-scan/frozen-plan.json) ·
[Results and resolutions](athena/hole-scan/validation.json) · [Review](athena/hole-scan/final-audit.json) ·
[Raw-baseline control](athena/hole-scan/cross-calibration.json) ·
[Scan tradeoff PDF](athena/hole-scan/tradeoff.pdf) ·
[Scan resolutions PDF](athena/hole-scan/resolutions.pdf) ·
[Additional cleanup](athena/hole-scan/cleanup-additional.json) ·
[Final storage review](athena/hole-scan/final-storage-review.json).

"""
    # Keep the latest resolution cohort explicit and avoid duplicating old tables.
    start = text.index("### Resolutions on identical truth")
    end = text.index("## Why inclusive finding still loses", start)
    text = text[:start] + text[end:]
    scan_section += f"""### Resolutions after the scan

Central 68.27% / 95% interval half-widths on the same **{latest_prompt:,} prompt
particles** reconstructed by all three scan main-point selections. Relative q/pT
residual is `(reco − truth) / abs(truth)`. Widths are descriptive, without error bands.

{table(['Handling', 'd0 [µm]', 'z0 [µm]', 'Relative q/pT [%]'], latest_resolution_rows)}

Tail handling retains narrower d0 and q/pT widths, with little z0 change. Previous
handling already provides this benefit; the score mainly changes selection.
Associations differ, so narrower widths do not isolate a fit-only benefit. Earlier
six-mode widths and their different common-truth cohort remain in the linked data.

"""
    # Keep the historical main comparison; the latest scan owns the full six-point table.
    text = text.replace(
        table(
            [
                "Training target",
                "Nominal fakes",
                "New fakes",
                "Δ efficiency [pp]",
                "Δ fake rate [pp]",
            ],
            scan_rows,
        ),
        "Full earlier six-point results remain in the linked NN result file.",
    )
    text = text.replace(
        "## Why inclusive finding still loses",
        scan_section + "## Diagnosis from the original comparison",
    )
(root / "report.md").write_text(text)
print(root / "report.md", len(text.split()), "words")
