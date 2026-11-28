# strip-branching

Keep several measurements per surface on the first strip layers in the CKF
(branch `strip-entry-branching`, worktree `athena-branching`). Note:
`atlas/tsi/notebook/2026-11-20_strip-entry-branching.md`.

```bash
C=~/scripts/athena/acts-athena-ci/common
$C/build.sh strip-branching            # ActsTrackReconstruction (package_filter.txt), athena-build-branching
$C/build.sh strip-branching mr         # MR build: + ActsConfig against the nightly's ACTS (package_filter_mr.txt), athena-build-branching-mr
$C/fastreco.sh strip-branching b0 bP2  # 1000 events -> run/strip-branching/f<NN>/<v>; REDO=1 re-runs failed files
./run.sh perf 8 100 b0 bP2             # one job per variant; variants: see run.sh
$C/idpvm.sh strip-branching b0 bP2
```
