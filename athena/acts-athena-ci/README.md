# acts-athena-ci work scripts

Scripts for local Athena builds with a custom ACTS, run out of the
[acts-athena-ci](https://gitlab.cern.ch/acts/acts-athena-ci) checkout on the
build box. They used to live loose in that checkout; the repo itself keeps only
its CI and the generic recipe (`env.sh`, `runenv.sh`, `dobuild.sh`,
`dorun.sh`, `package_filters_*.txt`, see its `CLAUDE.md`).

- `ACI_BASE` = `/home/astefl/source/acts/acts-athena-ci`: the checkout, which
  holds the ACTS and Athena worktrees (`acts*/`, `athena*/`) and the build
  directories (`athena-build*/`). The `*env.sh` scripts export it.
- Job output always goes to `$ACI_BASE/run/<tag>`; nothing is written here.
  The Python summaries read from there too (override with `ACI_RUN`).
- Paths are absolute: the scripts assume this folder at
  `/home/astefl/scripts/athena/acts-athena-ci`.
- Build scripts follow one pattern per work tree: `<x>env.sh` (asetup the
  nightly, export the trees), `<x>config.sh`, `<x>build.sh`, `<x>runenv.sh`
  (env plus the build's `setup.sh`). Source the env inside every command:
  shell state does not persist.

Notes on each piece of work are in `andiwand/cern-notes`
(`atlas/tsi/notebook/`).

## common

| script | usage |
|---|---|
| `fingerprint.sh <log>` | algorithm statistics tables of a `log.RAWtoALL`, timestamps stripped: diff two to check the physics output is unchanged |

## rz-track-finder

RZ track finder in Athena (`ActsTrk::TrackFindingRzAlg`), A/B against the CKF.
Two trees: "old" = `acts-rz`/`athena-rz` on nightly 2026-09-04
(`rz-on-v47.6.1`), "new" = `acts-rz2`/`athena-rz2` on nightly 2026-09-15
(`rz-on-v47.7.0`).

| script | usage |
|---|---|
| `rzenv.sh`, `rzconfig.sh`, `rzbuild.sh`, `rzrunenv.sh` | old tree, build `athena-build-rz` |
| `rz2env.sh`, `rz2config.sh`, `rz2build.sh`, `rz2runenv.sh` | new tree, build `athena-build-rz2` (no GPU packages) |
| `rz2test.sh` | build and run the RZ unit tests of `acts-rz2` |
| `rzmaintest.sh` | the same for `acts-rz-main` (ACTS main plus the RZ commits) |
| `rz2_job.sh <old\|newgrid\|new> <ckf\|rz> <ttbar\|pt10\|pt100> <nev> <dir> [idpvm] [postExec]` | one reconstruction on either build; `newgrid` forces GridTriplet pixel seeding on both ACTS passes, `new` runs the GBTS default |
| `rz2_cycle.sh <tag> <cycles> [nev]` | alternating old / newgrid / new x CKF / RZ ttbar timing, into `<tag><side>_<finder>_<i>` |
| `rz2_phys.sh <tag> [parallel]` | reco + IDPVM, all sides and finders, ttbar and single muons |
| `rz2_physsum.py <tag> [sample ...]` | IDPVM table: efficiencies, hits, core resolutions and pulls, finder counts |
| `rz2_hitseta.py label=dir ...` | hits and holes per track in bins of \|eta\| |
| `rzsum.py <tag>` | normalised timing of `<tag>_{ckf,rz}_*`, per seed run on |
| `rzidpvm.py a/idpvm.root b/idpvm.root` | IDPVM group comparison (used by `rz2_physsum.py`) |
| `cmpidpvm.py <dir> ...` | IDPVM headline numbers per eta profile |
| `d0res.py <dir> ...` | integrated core widths of residuals and pulls |
| `rz_common.sh <ckf\|rz> [nev] [preExec]` | ttbar reco in the current directory (used by the scans and profiling) |
| `rzmu_digi.sh <pt10\|pt100> [nev]` | single muon HITS -> RDO into `run/mu_<pt>` |
| `rzbins.sh <tag> [nev]` | measurement binning scan |
| `rzscan.sh [nev]`, `rzstop.sh [nev]` | parallel cut and branch-stopper scans, finder counts only |
| `rzspot.sh <ckf\|rz> <threads> <nev>`, `rzspotcycle.sh <tag> <cycles> <threads> <nev>` | SPOT-style multithreaded throughput |
| `rzprof.sh [nev]` | `perf record` at 3999 Hz with DWARF stacks into `run/profhi_rz` |
| `rzfold.py perf.data [--inline]` | fold the profile under `TrackFindingRzAlg::execute` into phases |
| `rzcallers.py perf.data <symbol> ...` | callers of a symbol |
| `foldmk.py perf.data` | the same for `makeTrack` |

The scans and profiling source the old tree's `rzrunenv.sh`; swap in
`rz2runenv.sh` for the new one.

## pixel-space-points

ACTS vs Athena pixel space point formation (MR 90483), nightly 2026-08-27,
build `athena-build`.

| script | usage |
|---|---|
| `pixenv.sh`, `pixconfig.sh`, `pixbuild.sh`, `pixrunenv.sh` | the build |
| `pix_common.sh <core\|trk> [nev] [preExec]` | ttbar reco in the current directory |
| `pixcycle.sh <tag> <cycles> [nev]` | alternating ActsCore / ActsTrk timing |
| `pixsum.py <tag>` | normalised timing summary |
| `pixspot.sh <core\|trk> <threads> <nev>` | SPOT-style check |
| `cmpsp.py a.root b.root` | pixel space point variances of two AODs, entry by entry |

## strip-space-points

ACTS vs Athena strip space point formation (August 2026), with the
repo's own `runenv.sh`.

| script | usage |
|---|---|
| `st_core.sh`, `st_trk.sh` | 20 ttbar events, single threaded, ActsCore / ActsTrk strip formation |
| `stgap0_core.sh`, `stgap0_trk.sh`, `stgap0_scalar.sh` | the same with `StripGapParameter=0`: both must agree exactly; `scalar` is the plain-double kernel |
| `stpix_on.sh`, `stpix_off.sh` | ACTS pixel tool with / without the per-module surface cache |
| `all_core.sh`, `all_trk.sh` | strip and pixel strategy switched together |
| `gap0_core.sh`, `gap0_trk.sh` | 5 events, validation flags, gap 0: the exact comparison |
| `stcycle.sh <tag> <first> <last> <script> ...` | alternating cycles of the above (replaces the `perfloop*.sh` drivers) |
| `stprof.sh` | `perf record` of the gap-0 jobs |

## gbts

GBTS seeding: the PR 5767/5773 A/B (August, nightly 2026-08-10, builds
`athena-build` from `acts/` and `athena-build-base` from `acts-base/`) and the
strip seeding / layer tool work (September, nightly 2026-09-02).

| script | usage |
|---|---|
| `config_gbts.sh`, `build_gbts.sh` | configure / build both A/B builds |
| `timeone.sh <pr\|base> <Gbts\|GbtsFtf> <tag> [nev]` | one timing job on either build |
| `gbts_time.sh <Gbts\|GbtsFtf> [nev]` | the reco behind it, in the current directory |
| `time5773.sh`, `timelegacy.sh` | alternating base / PR / FTF, and ACTS vs FTF, cycles |
| `summarize.py` | seeding and clusterization CPU of `base_N`, `pr_N`, `ftf_N` |
| `gbtsenv.sh`, `gbtsconfig.sh`, `gbtsbuild.sh`, `gbtsrunenv.sh` | strip seeding build `athena-build-gbts` |
| `pinconfig.sh`, `pinbuild.sh`, `package_filters_gbts_pin.txt` | the Acts packages alone against the nightly's own ACTS |
| `actstest.sh` | build `ActsUnitTestGbtsSeeding` against `acts/` |
| `gbts_layer_check.sh <base\|pin> [nev]` | GBTS on the primary pass, nightly alone or with the pin build |
| `gbts_strip.sh [nev]` | GBTS with the strip path on the LRT pass |
| `strip_exp.sh <tag> <grid\|gbts> <on\|off> [nev]`, `strip_go.sh ...` | primary-pass strip seeding study; `strip_go.sh` wraps it into `run/exp_<tag>` |
| `strip_time.sh [cycles] [nev]` | alternating timing for that study |

## isometry-6040

ACTS PR 6040 (Transform3 isometry) in Athena, build `athena-build-6040`.

| script | usage |
|---|---|
| `env6040.sh`, `config6040.sh`, `build6040.sh [targets]`, `runenv6040.sh`, `package_filters_6040.txt` | the build (`-k 0`, extra ninja targets passed through) |
| `reco6040.sh <pr\|base> [nev]` | ttbar reco with the PR build or the nightly |
