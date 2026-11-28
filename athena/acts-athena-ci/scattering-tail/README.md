# scattering-tail

ACTS scattering-tail mixture in the CKF (acts#6572 backported onto the
nightly's ACTS in `acts-tail`, Athena worktree `athena-tail`). Notes:
`atlas/tsi/notebook/2026-11-21_scattering-tail.md`; the follow-up score study
(`../scattering-tail-score`) sources this `env.sh`.

```bash
C=~/scripts/athena/acts-athena-ci/common
$C/build.sh scattering-tail                     # ACTS inline, CPU only
$C/acts_unittests.sh acts-tail 'CombinatorialKalman|MeasurementSelector|ScatteringTail|TrackStateCreator|KalmanFitter|Gsf'
$C/fastreco.sh scattering-tail t0 t5 g5         # ttbar mu=200, 1000 events -> run/scattering-tail/f<NN>/<v>
$C/idpvm.sh scattering-tail t0 t5 g5            # over all f<NN> tags (IDPVM_RUNS in env.sh)
LABELS=labels.txt $C/charts.py $ACI_BASE/run/scattering-tail/ana charts.json t0 t5 g5
```

Single particles:

| script | usage |
|---|---|
| `muons.sh <nev> <1\|10\|100>...` | reco variants on the ART single-muon RDOs -> `mu<pt>/<v>` |
| `genall.sh`, `gen.sh <name> <pid> <pt> <job> <nev>` | ITk-only G4 + digi of mu/pi at 1 and 3 GeV (`pyfrag/TailGun.py`) -> `gen/<name>/<job>` |
| `gunreco.sh <name>...` | reco variants on a generated sample -> `g<name>/<v>` |
| `muidpvm.sh <tag>...` | hard-scatter IDPVM -> `ana-mu/<tag>/<v>` |
| `muana.py <ana dir> <tag> <v>...` | efficiency, hits, pull core widths and tails per variant |
