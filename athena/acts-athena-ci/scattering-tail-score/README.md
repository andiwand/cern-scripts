# CKF scattering-tail score: Athena ITk study

Reconstruct **existing** Geant4 ttbar pileup-200 RDOs; no simulation or digitization.
Threadripper root: `/home/astefl/source/acts/acts-athena-ci`.
Source branches: `study/ckf-tail-score`; Athena `a252dda21e3`, ACTS `b4bd622c24`
(v48.5.0). Nightly `2026-11-19T2100`, `x86_64-el9-gcc15-opt`.
Build recipe: `athena-build-tail-score/build.sh`; retain host TRACCC, disable
CUDA/GNN/HIP. Existing worktrees and outputs are not overwritten.

- `run.sh OUT VARIANT EVENTS SKIP [THREADS=8] [SCORING=1]`: reconstruction,
  AOD export, exact event-count check, logs and exit marker. Accepts core4/5/7/10
  and tail4/5/7. Tail mixture is the previous study's Geant4 refit; primary pass
  only. Bremsstrahlung recovery is disabled in every variant.
- `pilot.sh`, `audit_pilot.py`: five-event scoring-on/off comparison.
  `test_scorer.sh` and `test_analysis.py`: focused implementation/analysis checks.
  `check_idpvm.sh`, `audit_idpvm.py`: official IDPVM counter cross-check.
- `train.sh`: 200 shared training events, seven measurement-cut settings.
  `analyze.py tune DIR training.json`: choose cuts at six retained-match targets
  using training data only. Minimize fake count; break ties by excess retained
  matches then track count. Both baselines may use chi2 or chi2/dimension;
  new handling uses predictive mixture score/dimension.
- `freeze.py RUN`: audit and hash the plan before creating held-out output.
  `finish.sh`: detached continuation for this run (contains its training PID).
  Runs selected configurations plus core7 on 800 events with `skip=200`, then
  analyzes them. `finish-exit-code=0` means the pipeline completed.
- `analyze.py evaluate DIR validation.json --plan training.json`: verify shared
  truth and disjoint events; evaluate frozen choices, paired event-cluster
  uncertainties and inclusive/common-truth resolutions.
- `diagnostics.py DIR training.json diagnostics.json`: binned rates/resolutions
  at the predeclared 99.5% training-retention point.
- `render_report.py NOTE.md`: local standalone HTML with embedded data and
  interactive SVG (`report.js`). Requires `markdown_it`. `check_html.mjs` tests
  it in local Chrome. `plot_validation.py ARTIFACTS/athena` exports SVG/PDF figures.

Efficiency: stable charged generator particles, pT>1 GeV, |eta|<4, production
radius<300 mm when a vertex exists. Match probability >0.5. Fakes: probability
<0.5 or unavailable, regardless of link validity; denominator tracks |eta|<4.
Truth fingerprints survive AOD thinning; uid or container index alone do not.
Normalized cuts are offline after during-finding shared-hit suppression. No branch
pruning or ambiguity rerun. Prompt resolutions use production radius<0.1 mm, a straight-line
truth perigee reference, and one best-probability track per particle; raw units
are mm for d0/z0 and a fraction for relative q/pT.

Report and data: `~/cern/notes/acts/notebook/2026-11-27_ckf-scattering-tail-score*`
on the laptop; numerical exports, provenance and selected AODs remain in remote
`run/scattering-tail-score`. Cleanup manifests identify removed AODs.

NN / cluster-response follow-up:

- `build_nn.py`: private ONNX library with the previously validated Y-pitch and
  chosen-subcluster-error fixes. `run_nn.sh` installs all-charge/all-size pixel
  NN **before** selection in the primary pass; seed policy and strips stay fixed.
- `build_nn_native.py`, `NativeStudyNN.h`: private adapter reusing the unchanged
  native kernel objects from `athena-native-pixel-nn` d68d964a937. Native constructors
  check their outputs against ONNX; `nn_native_config.py` resolves/hashes the same
  configured models. `resume_nn_native.py` records the initial wrapper-command fix.
- `nn_native_finish.sh`: same seven training gates, original raw matched-particle
  targets, independent 800-event evaluation. Requires pilot and three 200-event
  ONNX/native decision comparisons before tuning. `nn_analyze.py` reuses the original
  definitions; its vectorized counters were checked against the regression fixture.
  `review_nn_training.py` checks original truth, settings and model hashes.
- `nn_finish.sh` was superseded after native pilot agreement. Its dispatchers were
  stopped; the running core4/core5/core7 ONNX controls were preserved. See
  remote `nn/handoff.json`; the main NN results live under `nn-native/`.
- `cross_nn.py RUN [nn-extended] [retention=0.995]`: common-target, paired raw/NN differences and common-truth
  resolution/tail-weight profiles. This follow-up reuses an already inspected
  sample and is exploratory even though each cut uses training events only.
- `gun_batch.py`: existing mu10 inputs, raw/NNpre × core4/core7/tail4, five groups
  of 1,000 events each; no simulation. Output budget 2 GiB, free-space reserve
  22 GiB, checked every five seconds. `gun_census.py` freezes old raw-cluster tags
  and physical identities. `gun_analyze.py` measures final-track losses/recoveries
  with no offline quality cut. The delta-like proxy is not an exact truth label;
  group IDs are needed because run/event numbers repeat between files.

Final NN nominal control:

- `nn_native_continue.sh` resumes only after the explicit one-track backend review
  (`review_nn_backend_difference.py`). The original strict-stop record is retained.
- `nn_nominal_wide.sh`, `run_nn_wide.sh`, `extend_nn_nominal.py` add a 14/20σ
  nominal gate, needed to reach the highest two original training targets. The
  expanded plan is frozen from training only, verifies unchanged tail choices,
  and reuses existing validation outputs. Results live in `nn-extended/`.
- `nn_analyze.py` caches one immutable selection/ranking during evaluation to avoid
  repeated sorting. Tuning is unaffected; the original analysis fixture still
  passes, and final main-point counts are independently checked.
- `finish_nn_comparison.sh` waits for the two recorded reconstruction controllers,
  evaluates the expanded pool, and writes `comparison-exit-code`. Its main-point
  counter check asserts agreement with the full evaluator. `audit_nn_final.py RUN`
  then verifies all completion markers, frozen plans, NN mode/model/library hashes,
  independent counters, paired uncertainties, and unchanged/intermediate points.
  Final analyses may run concurrently after reconstruction: input caches publish
  atomically. `nn_highpoint.sh` checks the existing 99.8% target against both raw
  and NN nominal CKF. It does not tune evaluation cuts.

Post-report diagnosis and concise report:

- `extras_nn.sh`, `why.py`: full truth links, low-pT truth and hit summaries from
  retained validation AODs. `loss_stage.py DIR` partitions main-point gains/losses
  before versus at the offline quality cut; it cannot identify internal loss causes.
- `pt_working_points.py NN_DIR [RAW_DIR]`: reconstructed-pT slices using the same
  frozen quality cuts; applies the pT cut to efficiency and fakes. This is post-hoc
  exploration, not an independently tuned threshold working point.
- `migration.py NN_DIR`: count both migration directions across 1 GeV using the
  full truth links. Associations differ between modes; this is not a fit-only test.
- `audit_diagnosis.py ARTIFACT_DIR`: reconcile partitions, counts, primary-pass
  reconstruction counters and completion markers against the final evaluation.
- `write_report.py ARTIFACT_DIR`, then `render_report.py NOTE.md --report-text
  ARTIFACT_DIR/report.md`: concise report plus standalone interactive SVG HTML;
  retain the chronological notebook. `check_html.mjs HTML [SCREENSHOT]` checks
  legend interaction, accessible points and absence of bitmap figures.


Hole/outlier follow-up (pT unchanged):

- `hole_scan.py RUN/hole-scan` runs a predeclared 22-configuration local scan,
  reuses the eight existing NN settings, freezes training-only choices at all
  six original targets, then reconstructs only selected evaluation settings.
- `run_hole_scan.sh OUT core10u14h1o2|tail5u7h2o1 EVENTS SKIP [THREADS]`
  varies only the two residual gates and maximum holes/outliers. NN and pT
  settings are unchanged. Per-run audits compare all other primary-pass flags,
  event/truth identities, score dimensions, NN configuration and library hash.
- Four 4-thread training jobs / two 8-thread evaluation jobs. New training AODs
  are removed only after export/audit, with hashes retained. Starts require
  12 GiB free; running jobs stop if free disk falls below 8 GiB.
- No resume over incomplete outputs: inspect `STOP`, logs and exit markers
  before any recovery. Existing evaluation data were previously inspected;
  results are exploratory even though choices use training only.

- `resume_hole_scan.py` handles the recorded disk-reserve stop after frozen
  training choices. The recovery uses a verified temporary copy and retains
  original files; `exit-code` and `review-exit-code` in that copy are authoritative.
- `audit_hole_scan.py` verifies all frozen choices, 73 primary-pass flags, event
  identities, counters, independent main-point counts, unchanged earlier results
  and exact equal-gate controls. No pT settings change.
- `archive_hole_scan.py` persists the completed temporary scan and verifies every
  retained file by SHA256. Keep analyzed arrays as NPZ plus configuration/logs;
  the new nominal H2 and new-score H2 AODs have verified persistent local backups.
  Omit duplicate validation TSVs and the two other regenerable AODs.
  Archive the original disk-stop markers before clearing them. Temporary cleanup
  follows only after both the persistent archive and local result copies pass.
