# GBTS seed split in Athena (ITk)

Note: `acts/notebook/2026-11-17_gbts-barrel-seed-split.md` (section "Athena A/B") and `acts/notebook/2026-11-17_gbts-seed-split-reroll.md` in the notes repo.

Nightly 2026-11-16T2100 (ACTS v48.5.0), worktree `athena-gbtssplit` (branch `gbts-seed-split-flag`), build
`athena-build-gbtssplit` with `package_filter.txt` (ActsPatternRecognition + ActsTrackReconstruction, nightly ACTS).
`athena.patch` is the full Athena diff:

- `GbtsSeedingTool`: `maxSeedSplitEta`, `maxInvRadDiff`, `minSplitSeedSize`, `maxSplitSeedSize` (ACTS split knobs).
- `GbtsSplitDiagAlg` (throwaway): per pixel seed at |eta| < 0.8, the three sub-triplet curvatures of the ACTS
  split check, SP truth and the TrackFindingAlg seed destiny -> `gbtssplit.txt`.
- `TrackFindingAlg`: `retrySubSeedsMinSize`, `retrySubSeedsMaxAbsEta` - if the CKF finds no track for a seed with
  >= N SPs, retry without the first, then without the middle SP.

Scripts:

- `build.sh`, `env.sh`
- `run.sh <tag> <nthreads> <nevents> <variant>...` - variants in `post()`; full-truth sample via `INPUT_RDO`
- `cycle.sh` (split on/off), `cycle2.sh <tag> <ncycles> <nevents> <variant>...` - serial CPU, alternating
- `splitsum.py [--pu] name=dir ...` - paired efficiency per |eta|, lost/gained by pT, track quality
- `diagana.py <off-diag> <on-diag>` - purity and flag rate of the unsplit seeds, seeds of lost/gained particles
- `diagdst.py <off-diag> <on-diag>` - seed destinies of lost/gained particles
- `timesum2.py <dir> <ref> <variant>...` - per-algorithm CPU normalised to ActsPixelClusterizationAlg
- `acts_unittests.sh` - ACTS seeding unit tests on `acts-pr/` (PR https://github.com/acts-project/acts/pull/6552)
