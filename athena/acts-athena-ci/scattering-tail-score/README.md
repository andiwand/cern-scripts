# CKF scattering-tail score: Athena ITk study

Reconstructs **existing** Geant4 ttbar mu200 RDOs (no simulation/digitization) with the CKF
scattering-tail mixture and its predictive score, then tunes offline quality cuts on training
events and evaluates them on disjoint held-out events. Primary pass only; brem recovery off.

Build box root `/home/astefl/source/acts/acts-athena-ci` (`$ACI_BASE`); build
`athena-build-tail-score` (Athena + ACTS `*-tail-score` worktrees, nightly `2026-11-19T2100`,
`x86_64-el9-gcc15-opt`; host TRACCC kept, CUDA/GNN/HIP off). Outputs under `run/scattering-tail-score/`.

## Reconstruction

- `run.sh OUT VARIANT EVENTS SKIP [THREADS=8] [SCORING=1]`: one Reco_tf job, AOD export to
  `rows.tsv` (`extract.py`/`extract.hxx`), exact event-count check, `exit-code`.
  Variants `core4 core5 core7 core10 core14 tail4 tail5 tail7` (measurement/outlier gates
  4/6, 5/7, 7/10, 10/14, 14/20) or `(core|tail)<m>u<o>h<holes>o<outliers>`, e.g. `core10u14h1o2`.
  Env: `LIB=default|onnx|native` (private library, see below), `NN=1` (all-charge pixel NN via
  `nn_config.py`, `NN_MODE=pre|post`), `INPUT=rdo,...` (default: edge-holes ttbar RDOs).
- `batch.py OUT EVENTS SKIP VARIANT... [--parallel 3] [--threads 8] [--env K=V] [--input RDOS]
  [--min-free BYTES] [--max-bytes BYTES]`: parallel `run.sh` into `OUT/<variant>`; the disk
  limits kill a running job. `launch()` is importable.
- `pilot.sh OUT [VARIANT...]`: 5-event scoring on/off pairs (default tail5 core7), then
  `audit_pilot.py OUT` (scoring must not change reconstruction). `ON_ONLY=1` with `LIB`/`NN`
  gives backend pilots for `compare_nn_backend.py A B OUT.json` (ONNX vs native: same tracks,
  links, dimensions; records floating-point differences).

## Tune / freeze / evaluate

`pipeline.sh RUN [--from STEP]` runs train → tune → freeze → validate → evaluate → diagnostics → check:

- train: `batch.py RUN/training 200 0 $VARIANTS` (default the seven core/tail variants).
- tune: `analyze.py tune DIR training.json [--reference-plan RAW/training.json]`: per target
  (98–100% of raw tail5 matches) pick variant/metric/cut minimizing fakes for `core`
  (chi2, chi2/dim), `previous` (tail, chi2 or chi2/dim) and `new` (tail, score/dim).
- freeze: `freeze.py RUN [--also core7] [--extends PARENT]`: re-check training and hash the plan
  before `RUN/validation` exists.
- validate/evaluate: chosen variants on 800 events, skip 200;
  `analyze.py evaluate DIR validation.json --plan training.json` (paired event-cluster uncertainties,
  common-truth resolutions). `diagnostics.py DIR plan out.json`: binned rates at 99.5%.
  `check_main_point.py RUN`: independent counters at 99.5%.

Env: `LIB`, `NN`, `VARIANTS`, `REF` (reference plan for NN studies), `PARENT` (extend a study with
new variants, e.g. `VARIANTS=core14`, reusing its outputs), `ALSO`, `PARALLEL`, `TRAIN_EVENTS`,
`VAL_EVENTS`, `VAL_SKIP`. Example NN study: `LIB=native NN=1 REF=$R/training.json pipeline.sh $R/nn-native`.

## Follow-ups and checks

- `build_nn.py` → `run/.../nn-control` (ONNX NN with Y-pitch and chosen-subcluster-error fixes);
  `build_nn_native.py` + `NativeStudyNN.h` → `nn-native-control` (native kernel objects from
  `athena-build-native-pixel-nn`). Both refuse to overwrite.
- `cross_nn.py RUN [NN_SUBDIR] [RETENTION]`: paired raw vs NN at a common target.
- `hole_scan.py ROOT [--baseline DIR]`: 22-point maxHoles/maxOutliers/outlier-gate scan around
  core10/tail5, training-only choices, audited runs.
- `extras.sh RUN [VARIANT...]`: `extras.py` truth links/hit summaries on retained AODs, then
  `why.py RUN`. Then `loss_stage.py RUN`, `pt_working_points.py NN_RUN [RAW_RUN]`,
  `migration.py RUN` (needs the previous two). `plot_validation.py RUN`: SVG/PDF figures.
- `provenance.py [RUN]`: source commits, input metadata, binary/script hashes.
- `test_scorer.sh` (C++ scorer unit test), `test_analysis.py` (analysis regression).
- IDPVM cross-check of the exporter: `SETS=all ../common/idpvm.sh scattering-tail-score core7_on`
  (uses `env.sh`, pilot AODs), then
  `audit_idpvm.py $R/pilot/core7_on $R/ana/core7_on/idpvm_all.root`.

Definitions: efficiency over stable charged generator particles, pT > 1 GeV, |eta| < 4,
production radius < 300 mm; match probability > 0.5. Fakes: probability < 0.5 or missing,
tracks |eta| < 4. Truth fingerprints survive AOD thinning. Cuts are offline, after
during-finding shared-hit suppression.
