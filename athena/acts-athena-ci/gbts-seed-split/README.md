# GBTS seed split in Athena (ITk)

Note: `acts/notebook/2026-11-17_gbts-barrel-seed-split.md` (section "Athena A/B"), `acts/notebook/2026-11-17_gbts-seed-split-reroll.md` and
`acts/notebook/2026-11-17_ckf-strip-entry.md` in the notes repo.

Nightly 2026-11-16T2100 (ACTS v48.5.0), worktree `athena-gbtssplit` (branch `gbts-seed-split-flag`), build
`athena-build-gbtssplit` with `package_filter.txt` (ActsPatternRecognition + ActsTrackReconstruction, nightly ACTS).
`athena.patch` is the full Athena diff:

- `GbtsSeedingTool`: `maxSeedSplitEta`, `maxInvRadDiff`, `minSplitSeedSize`, `maxSplitSeedSize` (ACTS split knobs).
- `GbtsSplitDiagAlg` (throwaway): per pixel seed at |eta| < 0.8, the three sub-triplet curvatures of the ACTS
  split check, SP truth and the TrackFindingAlg seed destiny -> `gbtssplit.txt`.
- `TrackFindingAlg`: `retrySubSeedsMinSize`, `retrySubSeedsMaxAbsEta` - if the CKF finds no track for a seed with
  >= N SPs, retry without the first, then without the middle SP.
- `TrackFindingAlg` `traceFile` (+ hook in `detail/MeasurementSelector.h`, `detail/CkfTrace.h`): CKF trace of pixel
  seeds with >= 4 SPs at |eta| < `traceMaxAbsEta` - every non-forced surface visit with all candidates, the chi2 of
  the seed particle's own hit, and every branch-stopper decision.
- `TrackFindingBaseAlg` `branchLayers`: flattened (volume, layer, nMeasurements) triplets, measurements kept per
  surface on those ACTS layers (strip barrel: volume 23, layers 2/4/6/8).

Scripts:

- `build.sh`, `env.sh`
- `run.sh <tag> <nthreads> <nevents> <variant>...` - variants in `post()`; full-truth sample via `INPUT_RDO`;
  `run2.sh`, `run3.sh` add the CKF knob (`tr-*`, `t-*`) and GBTS cut (`g-*`) variants
- `cycle.sh` (split on/off), `cycle2.sh <tag> <ncycles> <nevents> <variant>...` - serial CPU, alternating
- `splitsum.py [--pu] name=dir ...` - paired efficiency per |eta|, lost/gained by pT, track quality
- `diagana.py <off-diag> <on-diag>` - purity and flag rate of the unsplit seeds, seeds of lost/gained particles
- `diagdst.py <off-diag> <on-diag>` - seed destinies of lost/gained particles
- `cycle3.sh`, `cycle4.sh` - `cycle2.sh` on `run2.sh` / `run3.sh`
- `tracean.py <trace>` - failure rate and hole classes of pure seeds; `failclass.py <trace> [--recoverable]` - cause
  per failing seed; `tracecmp.py <retry trace>` - full attempt vs recovering sub-seed
- `fakes.py dir...` - fake rate from truthMatchProbability over all tracks; `fakes4.py <dir>` - 4-SP seed composition;
  `seedpurity.py <dump>` - seed purity by size (any pixel seeder), layer-skipping 4-SP seeds
- `timesum2.py <dir> <ref> <variant>...` - per-algorithm CPU normalised to ActsPixelClusterizationAlg
- `acts_unittests.sh` - ACTS seeding unit tests on `acts-pr/` (PR https://github.com/acts-project/acts/pull/6552)
