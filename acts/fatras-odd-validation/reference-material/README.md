# ODD validation of the local-L0 reference-material approximation

13 October 2026. ACTS commits:

- `1634b1a22d`: reference-target selection, separate rate interpolation, local
  nuclear thickness and unit tests.
- `b37ce6a08d`: Examples/Python flag and model documentation.

This is the next controlled comparison after the baseline in
`../results/2026-10-13/`. Both Fatras curves enable native V0 decays and use the
same silicon pion/proton library. The grey curve requires exact Ar/Z matching;
the orange curve sets `nuclearInteractionUseReferenceMaterial=True`. It uses
local thickness/L0 and the reference library's dimensionless rate correction,
final states and remnant. It does not fit an A/Z dependence or add neutral
projectiles. The model's 0.1–20 GeV calibration domain is unchanged.

Same 20 ttbar + PU200 events, exact input CSV hashes, ODD v6 geometry, 2 T field,
pMin=100 MeV, charged pTMin=50 MeV as the baseline. The existing Geant4 sample
is reused. No calibration constants are changed or fitted to these events.

## Results

Common hit-entry p>=100 MeV and pT>=50 MeV; mean pixel hits/event:

| Component | Geant4 | Exact material | Local L0 / reference target |
|---|---:|---:|---:|
| Generator particles | 47191.40 | 48504.55 | 46469.95 |
| Simulation secondaries | 18195.55 | 7429.45 | 12142.65 |
| Immediate nuclear-origin secondaries | 8077.55 | 0 | 4816.40 |

Secondary coverage rises from 40.83% +/- 0.42 percentage points to
66.73% +/- 0.67 (event statistics only). The secondary rate increases by 63.4%.
The primary ratio changes from 1.0278 to 0.9847 +/- 0.0010.
There are 190370 nuclear-created Fatras particles, compared with zero under
exact material matching. This is not a count of interactions or accepted tracks.

The nuclear-origin hit deficit remains about 3261/event. Decay-origin and
conversion-origin deficits also remain. Creation processes are immediate
origins, not full ancestry. This comparison cannot identify the incident
projectile species responsible for each missing nuclear hit. It supports the
usefulness of this approximation, not accuracy for every material or spectrum.
Neutral-hadron interactions remain the next planned addition.

## Reproduction

The scripts are versioned separately here to preserve the original baseline
scripts and their manifest. Requirements and environment locations are the same
as the parent validation README. Use the retained exact inputs or unpack
`../results/2026-10-13/inputs.tar.gz` into a new directory.

```bash
table="$HOME/cern/scripts/acts/fatras-hadronic/data/2026-10-13/silicon-dense.table"
./run-env.sh run.py fatras --input /tmp/odd-input --output /tmp/odd-local-l0 \
  --events 20 --table "$table" --reference-material

~/cern/venv/bin/python compare.py \
  --geant4 /private/tmp/fatras-odd-geant4-final-v3 \
  --baseline /private/tmp/fatras-odd-fatras-final \
  --fatras /tmp/odd-local-l0 --events 20 --output /tmp/odd-local-l0-plots \
  --baseline-label 'Fatras + V0, exact Si match' \
  --fatras-label 'Fatras + V0, local L0' --allow-different-revisions
```

`--allow-different-revisions` explicitly permits reuse of the older reference;
checks on geometry, field, event count, seed and exact input selection remain.
Without it, differing ACTS revisions fail the comparison. Run metadata retains
all source revisions. `--baseline` aliases the original `--em` option, and the
historical array/JSON key `fatras-em` now refers to the **exact-material native
V0 baseline**, not the EM-only run. Persisted plot-config.json records the labels.

Replot all PDFs from the archived compact arrays:

```bash
~/cern/venv/bin/python compare.py --cached --events 20 \
  --output ../results/2026-10-13-local-l0
```

Results include the combined 11-page PDF and individual hit, kinematic,
production, occupancy, momentum/time and layer plots. The material-bin audit
is omitted here: exact matching is no longer the applicability criterion.
The log axes use the smallest positive central bin to set the lower display
limit, avoiding nearly-zero uncertainty edges flattening sparse spectra.

## Validation and limits

- Nine nuclear-interaction test cases / 31642 assertions pass. Tests cover
  effective-material L0 scaling, identical decisions and final states at equal
  nuclear thickness, split-slab survival, rate interpolation, conservation,
  unsupported inputs without RNG consumption and ambiguous reference targets.
- All 260 Fatras integration cases / 26298 assertions pass. Required pre-commit
  checks pass. The real Examples/Python bindings are rebuilt and exercised.
- Exact-material replay of event 0 gives byte-identical particle and hit CSVs
  to the original baseline. All 20 new events finish; one particle reaches the
  maximum step count. Unique truth IDs, hit truth links, input hashes and
  per-event accounting pass. PDFs are visually checked.
- This is a silicon final-state approximation for arbitrary effective materials,
  not an A/Z-dependent calibration. Only charged pions and protons interact.
  Other limitations of the parent baseline apply, including tracker-only
  geometry, mapped surface versus volume materials, momentum cuts, native V0
  decay scope, Geant4's 14 hit-buffer warnings and step-level time cutoff.
- Raw new simulation CSVs remain at `/private/tmp/fatras-odd-local-l0`; compact
  arrays and provenance are archived. The old Geant4/strict CSV locations are
  recorded in run-metadata.json. The source tree is clean after the two commits.
- Timings are diagnostic, not an isolated CPU benchmark: the replay briefly ran
  concurrently, and the old timing comes from a different concurrent run.
