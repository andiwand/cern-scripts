# edge-holes

Edge-hole border width of the ACTS CKF in Athena (branch `edge-hole-border`,
worktree `athena-edgehole`, nightly in `env.sh`). Note:
`atlas/tsi/notebook/2026-11-20_edge-hole-border.md`.

`run/edge-holes/input` holds the full-PU-truth ttbar mu=200 RDOs that the
other studies' `run.sh` read by default.

```bash
C=~/scripts/athena/acts-athena-ci/common
$C/build.sh edge-holes                         # ActsConfig only
./run.sh perf 8 100 e0 e1 h2                   # variants: see run.sh
$C/idpvm.sh edge-holes e0 e1                   # run/edge-holes/ana/<v>/idpvm_*.root
LABELS=labels.txt $C/charts.py $ACI_BASE/run/edge-holes/ana charts.json e0 e1
$C/cycle.sh edge-holes cpu 5 20 e0 e1 && $C/timesum.py $ACI_BASE/run/edge-holes/cpu e0 e1
```
