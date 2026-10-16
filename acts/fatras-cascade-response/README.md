# Fatras stopping and conversion-cascade response

Interaction-only follow-up to `fatras-radiative-secondaries`. The ODD geometry,
material map, low-momentum navigation budget and default ID-confined G4 physics
stay unchanged. No required runtime data files or G4 dependencies are added to
the native kernels.

Two ACTS corrections, a performance follow-up and a G4 concurrency fix on `fix/fatras-radiative-secondaries`:

- `6ef70ee729`: bound electron/positron ionisation integration by the changing
  energy, fixing lost knock-on production and false survivors in stopping slabs.
- `cd100d7886`: consume conversion daughters' actual remaining birth column,
  with the existing charged physics and outgoing-direction incidence correction.
  Slab-position records are local to the primary cascade, not thread-local.
- `0148026d64`: skip soft-only stopping tails when the exit state is already
  determined; 12,000 resolved-model cases and event replay check equivalence.

- `5825d58880`: exclude initializing-thread G4 calls from worker G4 calls.
  This fixes a reproduced duplicate-ion registration abort (Na25, PART122).
  Worker calls remain concurrent; native EM/transport do not take the lock.

The accepted implementation doubles much of the missing bremsstrahlung supply
and increases direct Compton hits. It does **not** close the inclusive hit gap;
removing incorrect survivors also removes hits. Geometry remains deferred.

## Inclusive reproduction

These tools use the established local ACTS/G4 environment and frozen d25514208b
ABI bridge. `SOURCE` is the `fatras-soft` worktree, `WORK` is a fresh directory.
The particle ABI is unchanged. Normal clean-build CI is still outstanding.

```sh
python ../fatras-radiative-secondaries/build.py --source SOURCE --work WORK/final-build
python measure.py --work WORK
python verify.py --work WORK
python analyse.py --work WORK
MPLCONFIGDIR=/tmp/fatras-cascade-mpl python plot.py --work WORK --output WORK/cascade.pdf --preview
```

`measure.py` alternates three control/current timings, then checks standard
navigation with one/four workers and reruns default G4 in the physical ID world.
It expects the local `~/cern/source/acts/acts/fatras-soft` source path. The
control module is the archived accepted radiation implementation, not ACTS main.
Its separately recorded `compiled_physics_revision` prevents confusing the
current runner checkout with the historical compiled control.

The PDF includes genuine pinned ACTS main `300b664a3d`, current Fatras and G4.
Main CPU remains archived over five events; all hit comparisons use the same
first three ttbar + fixed PU200 events. Summaries include **all written hits**.
G4 uses default FTFP_BERT with no added production/momentum/time cuts; its world
is r < 1202 mm, |z| < 4002 mm. Fresh G4 CSVs must match the archived reference.
Fatras keeps p >= 0.2 MeV, pT >= 0.05 MeV, photon production/retention 100 keV,
5 mm cached/pruned navigation, four turns and 50000 steps. One/four-worker replay
uses standard navigation at p >= 100 MeV and pT >= 50 MeV; bounded low-p
navigation is still a single-worker prototype.

## Controlled interaction experiments

```sh
python build-kernels.py --source SOURCE --output WORK
G4ENSDFSTATEDATA=G4_ENSDF G4LEDATA=G4_EMLOW WORK/stopping > WORK/stopping-after.csv
WORK/compton-column > WORK/compton-column.csv
```

Run `stopping` against the preceding source (`0429b7c1e1`) for
`stopping-before.csv`. It compares one column with 100/1000 slices in Si and Cu,
e-/e+, 0.3–20 MeV, three thicknesses and 2000 trials per setting. It also
integrates G4 Moller–Bhabha rates along the **mean CSDA stopping path**; that
integral is not a full stochastic G4 simulation. Radiation is disabled here.

The Compton experiment keeps a prescribed material path column, continuing the
outgoing photon between slices down to 100 keV. It excludes absorption and
spatial scattering transport. Its recoil threshold is diagnostic only; it does
not filter the inclusive hit summaries.

The accepted three-event stopping-only ablation is retained as
`stopping-inclusive/` plus `stopping-analysis.json`. The conversion-column
prototype in the archive is diagnostic evidence; the production result must
reproduce its six CSVs. `verify.py` expects these diagnostic records alongside
the measurement directories. `analyse.py` and `plot.py` also use these inputs.

## Compton source and response diagnosis

```sh
python compton-partition.py --work WORK
python photon-parents.py --work WORK
python photon-replay.py --work WORK
python analyse-replay.py --work WORK
```

The first two scripts decompose the accepted **preceding** radiation reference
and the exact G4 process observer. Photon replay uses every retained brems photon
above 100 keV from event 0 as a diagnostic input bank. It runs both photon banks
through preceding Fatras and the G4 bank through default G4, with observational
callbacks for exact Compton/photoelectric attribution. These are controlled
source replays, not additive corrections to the inclusive ttbar event.

To measure native Compton optical columns without changing random draws, use
`build-trace.py --source PRECEDING_SOURCE --module PRECEDING_MODULE --work WORK`,
then run the common radiation runner for one event with
`FATRAS_COMPTON_TRACE=WORK/compton-columns.csv`. Use the output name
`WORK/trace-current`, then `analyse-columns.py --work WORK`; both CSVs must match
the preceding reference exactly. Source and module must both be at `0429b7c1e1`.
The estimated second-scatter opportunities ignore cuts, absorption and changed
path direction; they are not a physical bound on recoverable detector hits.

Compton, bremsstrahlung and ionisation daughters still skip their remaining
birth column. Conversion daughters now consume it. The planar surface model
still omits within-slab spatial paths, finite lateral edges and material time.
No cross-section or multiplicity is rescaled to fit detector hit counts.

## Evidence archive

```sh
python archive.py --work WORK --source SOURCE --output results/YYYY-MM-DD
python verify.py --work results/YYYY-MM-DD
```

Archives are optional validation outputs, not runtime physics inputs. Event CSVs
are compressed; duplicate replays are retained as SHA256 manifests. Source,
commands, logs, kernel tests and build records accompany the PDF. Scripts and
notes record the observed CPU cost and the unresolved inclusive/shape gap.

The 16 October archive also retains the intermediate unoptimised timings in
`current-0..2` and the optimized timings in `optimized-0..2`, then the final guarded timings in
`guarded-0..2`. Both
must reproduce the former byte-for-byte. `measure-optimized.py` reproduces that
follow-up if the intermediate runs exist (`--variant optimized` or `guarded`).
Build the chosen source to `WORK/VARIANT-build` before invoking it.
`analyse.py` prefers guarded metadata/timings when present.
`optimized-standard-4.log` records the intermittent pre-fix crash; do not treat
it as a passing check. Final guarded standard runs compare one worker against
three fresh four-worker processes. A direct G4 regression also synchronizes
four workers with the initializing thread over 200 previously unwarmed seeds. The earlier `fast-stop-0` is a rejected diagnostic
that exposed floating-point residual momentum; it is not a timing reference.

`check-soft-stop.py --source SOURCE --work WORK` compares the accepted shortcut
with `cd100d7886` after `build-kernels.py` creates the compile configuration. It
scans C/Si/Cu/Pb, e-/e+, 300 energies from just above I to beta*gamma=1, and five
column lengths. The script requires the standard G4 data environment for its
NIST material definitions.
