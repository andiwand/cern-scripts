# acts-athena-ci work scripts

Scripts for local Athena builds with a custom ACTS, run out of the
[acts-athena-ci](https://gitlab.cern.ch/acts/acts-athena-ci) checkout on the
build box. The checkout itself keeps only its CI and the generic recipe
(`env.sh`, `runenv.sh`, `dobuild.sh`, `dorun.sh`, `package_filters_*.txt`, see
its `CLAUDE.md`).

- `ACI_BASE` = `/home/astefl/source/acts/acts-athena-ci`: the checkout, which
  holds the ACTS and Athena worktrees (`acts*/`, `athena*/`) and the build
  directories (`athena-build*/`).
- Job output goes to `$ACI_BASE/run/<study>/<tag>`; nothing is written here.
- Paths are absolute: the scripts assume this folder at
  `/home/astefl/scripts/athena/acts-athena-ci`.
- The reco job script is `mr92381/spotjob.sh <nthreads> <nevents> <mt|serial>`
  (reads `INPUT_RDO`, `EXTRA_PRE`, `EXTRA_POST`); it lives only on the build
  box, override with `SPOTJOB`.

Notes on each piece of work are in the notes repo (`atlas/tsi/notebook/`).

## A study

`<study>/env.sh` sets `NIGHTLY_NAME`, sources the checkout's `env.sh` and
defines the build (`BUILD_SRC`, `BUILD_DIR`, `BUILD_ARGS`, optional
`IDPVM_RUNS`); `<study>/package_filter.txt` is its package filter.
`<study>/run.sh` sets `STUDY`, defines `variant()` and sources `common/run.sh`;
`<study>/labels.txt` names the variants for the charts. To start a new one,
copy `edge-holes/`.

## common

| script | usage |
|---|---|
| `build.sh <study> [<flavour>]` | configure (once; `CFG=1` again) and build the study's worktree; a flavour builds into `$BUILD_DIR-<flavour>` with `package_filter_<flavour>.txt` and `$BUILD_ARGS_<flavour>` |
| `runenv.sh <study>` | source it: the study's `env.sh` plus its build's `setup.sh` |
| `run.sh` | driver behind `<study>/run.sh <tag> <nthreads> <nevents> <variant>...`: one job per variant, `PAR` at a time, `INPUT_RDO` (default: `run/edge-holes/input`, full-PU-truth ttbar mu=200), `MODE` |
| `fastreco.sh <study> <variant>...` | 1000 events as one job per input file -> `f<NN>/<v>`; `JOBS`, `NT`, `REDO=1` re-runs only the failed ones |
| `cycle.sh <study> <tag> <ncycles> <nev> <variant>...` | serial CPU cycles of `<study>/run.sh` (`RUN=` another runner), alternating variants |
| `idpvm.sh <study> <variant>...` | IDPVM over `run/<study>/<tag>/<v>/myAOD.pool.root` into `run/<study>/ana/<v>/idpvm_{hs,all,lrt}.root`; `RUNS`, `SETS` |
| `acts_unittests.sh <acts tree> <regex>` | build and run the matching ACTS unit tests of a tree; `INTEGRATION=1`, `STUDY`, `CACHE` |
| `timesum.py <dir> <variant>...` | per-algorithm CPU of `cycle.sh` runs, normalised to `ActsPixelClusterizationAlg`, vs the first variant |
| `statsum.py <alg> <label>=<log>,...` | sum of an ACTS algorithm's finalize statistics table over logs |
| `fingerprint.sh <log>` | algorithm statistics tables of a `log.RAWtoALL`, timestamps stripped: diff two to check the physics output is unchanged |
| `pairedeff.py [--pu] <name>=<dir>...` | efficiency, duplicates and track quality per \|eta\| from AODs, paired particle by particle against the first |
| `fakes.py <dir>...` | fake rate from `truthMatchProbability` over all tracks of AODs |
| `lrtfakes.py out.json <v>=<aod>,...` | LRT fake rate vs eta/pT/d0 from AODs (parallel, `NPROC`) |
| `idpvmtable.py <idpvm.root>...` | eta-averaged IDPVM headline numbers side by side |
| `corewidth.py <idpvm.root>...` | iterative-Gaussian core widths of the d0/z0/phi/theta residuals and pulls |
| `charts.py <ana dir> out.json <v0> <v>...` | chart data from IDPVM outputs, differences vs `v0`; `LABELS=<study>/labels.txt` |
| `md2html.py note.md style.html out.html [charts.json charts.js]` | standalone note page with inline SVG charts (`charts.js`) |
| `perfcallers.py perf.data <symbol>...` | callers of symbols in a `perf record -g` profile; `UNDER=<frame>` restricts to samples below it |

## Studies

| folder | what |
|---|---|
| `edge-holes` | edge-hole border width of the CKF; owns the shared ttbar input |
| `strip-branching` | several measurements per surface on the first strip layers |
| `scattering-tail` | scattering-tail mixture in the CKF, ttbar and single particles |
| `scattering-tail-score` | follow-up: tail score, NN and hole scan |
| `native-pixel-nn` | native pixel NN inference in Athena |
| `nn-inference` | helpers `native-pixel-nn` uses from the NN latency study |
