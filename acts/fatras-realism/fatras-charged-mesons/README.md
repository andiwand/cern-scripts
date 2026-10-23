# Charged mesons in Fatras

**Summary superseded on 14 October 2026:** use
[the inclusive comparison](../fatras-navigation-validation/README.md) and
[its PDF](../fatras-navigation-validation/results/2026-10-14/inclusive_summary.pdf).
It has no input momentum or hit analysis cuts and uses default FTFP_BERT without
our former global time kill, inside the strict ID world. Results below are
historical diagnostics with their explicitly stated selections.

Three separate additions on `feat/fatras-hadronic-interactions`: native charged-pion
muon decays, separately calibrated K+/K- inelastic interactions, and native
charged-kaon decays. Geant4 is an offline reference, not a runtime dependency.
The six kaon modes retain 99.995% of the quoted PDG weights. Three-body channels
use uniform invariant phase space; no form factors, Dalitz slopes, stopped-kaon
capture or muon decay are added. Charged p/pT cuts remain unchanged.

Physics sources:
- https://pdg.lbl.gov/2026/listings/rpp2026-list-pi-plus-minus.pdf
- https://pdg.lbl.gov/2026/listings/rpp2026-list-K-plus-minus.pdf

## Strict inner-detector reference

The historical Geant4 reference used a post-step kill-volume check, which
allowed outside-ID transport and secondary production. All final comparisons
now use a fresh physical Geant4 world cylinder r=1202 mm, half-length=4002 mm,
matching Fatras. `id-world.cpp` verifies all six top-level placements fit
(r<=1200 mm, |z|<=4000 mm) before changing the world solid. No detector material
is removed and no transport observer is added. `audit-boundary.py` checks all
47,420,396 saved birth vertices and 4,182,862 tracker hits: zero outside,
allowing 1 micron for CSV coordinate rounding. The physical world boundary
limits transport itself; checking saved hits alone would be insufficient.

Build the external helper with `build-id-world.py --acts-build BUILD
--output data/2026-10-14/id_world.so` and add that data directory to PYTHONPATH
for Geant4 runs. ACTS source is unchanged. Superseded results are archived under
`results/2026-10-14/unbounded-reference/`. The failed unbounded timing run is
excluded. Historical raw truth in `/private/tmp/fatras-odd-geant4-neutral-parent/`
is retained losslessly as `.csv.gz`.

## ACTS main comparison, 2026-10-14

The default PDFs now use **genuine, unmodified local main**, commit
`300b664a3d9c32ec928208e7eb18df40e7b2721b`, built in a separate checkout.
Current Fatras is `82f3aa8afaa98690024da9f1012e5eee7b6af844`.
Both use the same corrected external beam-pipe material map, ODD revision,
tracker world, 2 T field, seed 42 and 20 identical filtered ttbar + PU200 events.
This isolates the source changes; it is not an out-of-box default-map comparison.
Main has pMin=100 MeV but no pTMin transport option. The common pixel hit-entry
cuts remain p>=100 MeV and pT>=50 MeV. Main lacks the new neutral decay exemptions.

| Configuration | Primary hits/event | Secondary hits/event | Secondary / Geant4 |
| --- | ---: | ---: | ---: |
| Geant4 | 47158.45 | 18402.10 | 100% |
| ACTS main | 48555.55 | 3802.60 | 20.66% |
| Current Fatras | 45808.30 | 14961.30 | 81.30% |

Current versus main: +11158.70 +/-235.06 secondary hits/event (paired event SEM),
closing 76.43% of the original gap. Main records two maximum-step propagation
failures; current records none. Main's accepted secondary hits are all from
conversions. Its CSV schema has no parent identifiers; no absent ancestry is
inferred. The observer-free current run reproduces the earlier validated
40 hit/truth CSVs byte-for-byte.

`results/2026-10-14/charged_meson_diagnostics.pdf` and
`odd_geant4_vs_fatras.pdf` compare Geant4/main/current. The explicitly separate
`charged_meson_ablations.pdf` retains the historical stages below. The two
summary files are `charged-meson-summary-main.json` and
`charged-meson-summary.json`; the latter always describes the ablations.

### Reproduce the main comparison and CPU measurement

`run-comparison.py` takes `--mode main|changed|geant4`, `--source`, `--build`,
`--revision`, `--input`, `--output`, `--material-map`, `--events 20`; changed
Fatras also requires `--table`. It checks the clean source revision and native
binding location. Invoke it through `../fatras-neutral-hadrons/odd/run-env.sh`
with `ACTS_VALIDATION_BUILD` set to the matching build. Use separate output
directories and sequential runs for timing. All modes write standard hit/truth
CSVs with one worker and no external physics observers. Main's older CSV schema
has fewer truth columns. Geant4 uses FTFP_BERT and a 1000 ns time kill.

The main build uses RelWithDebInfo, assertions and log-failure checks enabled,
Python bindings, Fatras, Examples DD4hep/ROOT, JSON/ROOT plugins and ODD; system
Eigen/JSON and the same cached ODD/pybind11 sources and dependency view as dev3.
Only the Python bindings and ODD targets are needed. Build configuration,
logs and generated-header provenance are archived in `results/2026-10-14/main-build/`.
The four generated Core headers were reused only after verifying their generator
sources, helper package and requirements are unchanged from main; this avoids
network-dependent code generation and does not change baseline source code.

`odd/compare.py --geant4 G4 --baseline MAIN --fatras CURRENT --output RESULTS
--events 20 --allow-different-revisions --baseline-label 'ACTS main (300b664a3d)'
--fatras-label 'Current Fatras'` produces the detailed comparison. All final
runs record the same corrected map; no material-map override is required. Input hashes, ODD
revision, field and world checks remain active.

Run `plot.py --results RESULTS --calibration MIDPOINT_JSON` for the main-based
four-page book; add `--ablations` only for the historical ablation book. Main
metadata is checked before a sample is labelled as main, and current/reference
ancestry counts must match the shared comparison cache. Run
`timing.py --main MAIN --changed CURRENT --geant4 G4 --output RESULTS
--host-label 'Apple M3 Pro (12 cores, 18 GiB)'` for CPU JSON and PDF output.

Timing distinguishes process user+system CPU from elapsed time. Setup includes
imports, geometry, table loading and provenance; the event loop includes
initialization, simulation, CSV I/O and finalization. Framework algorithm timings
are elapsed time, excluding CSV I/O, and are **not** separately measured CPU.
One run per variant is a cost snapshot, not a throughput or scaling benchmark.

## CPU snapshot on Apple M3 Pro (12 cores, 18 GiB)

One worker, 20 identical events per run, sequential runs, standard CSV writers.

| Measurement | ACTS main | Current Fatras | Geant4, ID only |
| --- | ---: | ---: | ---: |
| Event-loop process CPU [s/event] | 0.820 | 1.135 | 39.701 |
| Setup process CPU [s/job] | 1.249 | 10.532 | 1.647 |
| Simulation algorithm elapsed [s/event] | 0.404 | 0.597 | 32.558 |
| Maximum process RSS [MiB] | 605 | 1595 | 4628 |

Current event-loop CPU is 38.4% above main and 35.0 times lower than Geant4.
CSV I/O is included in process CPU; simulation-only elapsed time is listed
separately. The current 558 MiB table has a substantial startup cost. Optional
build modules differ, so total setup/RSS changes cannot all be assigned to
physics. Geant4 retains its production/low-energy transport: common hit cuts
do not equalize the amount of work. See `cpu_comparison.pdf`, `cpu-comparison.json`
and archived `timing/` metadata, logs and framework timing files.

## Remaining secondary-hit gaps

The corrected reference leaves 3440.80 secondary pixel hits/event missing;
94.26% of this net deficit is below hit-entry pT=500 MeV.

| Creation process | Geant4 | Current Fatras | Deficit / event |
| --- | ---: | ---: | ---: |
| Conversion | 5216.00 | 3976.70 | 1239.30 |
| Decay | 4906.20 | 3825.00 | 1081.20 |
| Nuclear | 8200.50 | 7159.60 | 1040.90 |
| Other + ionisation | 79.40 | 0 | 79.40 |

1. **Conversion sampler and electron transport.** 969.65 missing hits/event
   come from photons already present in the identical generator input. Missing
   hadronic photons cannot explain most of this gap. Audit the probability
   scale inside the logarithm (positive minimum depth), stretched half-interval
   energy sharing, threshold and energy/recoil consistency. Validate thin/split
   slabs and identical incident photons before measuring ODD recovery and CPU.
2. **Low-momentum transport and existing decays.** Charged-pion decay parents
   contribute 715.95 versus 232.80 hits/event; charged kaons 239.85 versus 130.60.
   Both models already exist. Test bounded half/one/two-turn propagation at fixed
   p/pT cuts, including decay competition, sensor coverage, failures and CPU tails.
   Repeated hits on the same sensor total only 6.35/event across conversion,
   decay and nuclear categories. Later turns may still reach other sensors or
   allow decays, so this does not rule out truncation.
3. **Hadronic species spectra and ranges.** Nuclear-origin hit-producing
   particles are already more numerous in Fatras (2705.80 versus 2601.75), but
   make fewer hits each (2.646 versus 3.152). Pion hits are short by 1506.80;
   proton hits overshoot by 875.20. First isolate pion/proton transport with
   matched incident particles, then validate target-dependent final states and
   momentum sampling. Increasing total multiplicity would target the wrong
   quantity. Local L0 does not determine fragmentation or pion/proton spectra.

Untransported fragments supply 376.05 reference hits/event, 330.75 from
light ions; these average only 1.643 hits per hit-producing ion. They matter
more for occupancy than multi-hit tracks. Missing direct eta/eta-prime/rho0
decays contribute 172.65 hits/event; their extra conversions are small in this
sample. Missing KS/Lambda/anti-Lambda nuclear parents contribute 171.25.
These are direct reference contributions, not guaranteed net recoveries.

`secondary-gaps.py --geant4 G4 --changed CURRENT --output RESULTS --events 20`
produces `secondary-gaps.json` and the three-page `secondary_gaps.pdf`; add
`--plot-only` to redraw saved results. Per-event totals agree with the independent
ancestry analysis. Birth-cut production spans the entire ID and is not pixel
acceptance. Three distinct sensors is a diagnostic, not reconstruction efficiency.
Fatras folds nuclear pi0 decays into the nuclear vertex, so direct photon-parent
labels must not be interpreted as identical shower histories.

A targeted bookkeeping check finds zero surviving incident projectiles in 4608
FTFP_BERT Si pi+/pi-/proton interactions (six momenta, 0.1--10 GeV, 256/node).
Reclassifying a surviving projectile as a descendant is therefore not supported
as the explanation of the proton excess in this scan. The source/log/command
are archived in `leading-projectile-check/`; this is not an all-energy proof.

## Charged-meson ablations, 2026-10-14

Twenty identical ttbar + PU200 events, seed 42, ODD tracker, 2 T. Pixel hit-entry
cuts p >= 100 MeV and pT >= 50 MeV. Fatras uses the previously corrected beam-pipe
map and local L0 scaling of the Si reference. No detector hit tuning.

| Configuration | Primary hits/event | Secondary hits/event | Secondary / Geant4 |
| --- | ---: | ---: | ---: |
| Geant4 | 47158.45 | 18402.10 | 100% |
| Before charged-meson additions | 46350.30 | 13968.95 | 75.91% |
| Plus pion decays | 46150.50 | 14161.60 | 76.96% |
| Plus kaon interactions | 45887.70 | 14780.85 | 80.32% |
| Plus kaon decays | 45808.30 | 14961.30 | 81.30% |

Sequential secondary-hit gains: 192.65 +/-127.79, 619.25 +/-122.61, and
180.45 +/-111.61/event (paired event SEM). Combined: 992.35 +/-111.27, +7.10%,
closing 22.38% of the before-mesons gap. Final coverage 81.30% +/-0.57 percentage
points. Primary hits decrease by 542/event; combined primary+secondary gain is
450.35/event. Decays replace parent tracks and compete with nuclear interactions;
individual additions also change later random-number history. Small-sample
statistical errors do not cover physics-model errors.

Direct final Fatras / Geant4 hits: pion decays 232.80/715.95, kaon decays
130.60/239.85, kaon nuclear 598.45/546.55. These are immediate-parent categories,
not shower ancestry. The old parent-cut/proper-time diagnostic used the unbounded
reference and is retained only in the historical archive; its numbers must not
be interpreted as the recoverable deficit in the corrected reference.

Existing propagator loop protection remains enabled at half a turn. At fixed
momentum in 2 T, this corresponds to 2.439 ns pion and 8.628 ns kaon proper time.
A bounded transport study must measure unique particles/sensors, valid repeated
crossings, CPU tails and failures before relaxing that limit.

## Correctness and approximation checks

- The world-exit check now precedes decay. Examples also supplies its actual
  world volume, checked only when a decay is due. This prevents daughter
  generation outside the tracker after navigation loses its targets. Valid
  decays across inner-volume boundaries are retained. This does not repair
  missed surfaces or locate the exact exit point after navigation loss.
- Explicitly massless neutrinos avoid the particle table's NaN unknown masses;
  neutrinos are returned at the decay vertex for conservation but not transported.
- Lifetime, branching, phase-space, charge, boosted four-momentum, truth and
  replay unit tests pass. The massless three-body invariant-mass distribution
  agrees with the independent analytic density 2(1-s).
- 268 integration cases pass, including charged lifetimes and later daughter
  hits with both Eigen and the Examples Sympy stepper. Required repository
  hooks pass. Final ODD run has no failed tracks; each intermediate ablation
  has one maximum-step failure. The corrected Geant4 reference retains 32 hit-buffer warnings and one QGS
  negative projectile-mass-squared warning (clamped to zero). These are reference limitations.
- Native and Geant4 rest-frame checks use 100000 decays per charge/species.
  Three-pion energy spectra agree well; native semileptonic mean charged-daughter
  energies are 0.13955 versus 0.13249 GeV (electron mode), and 0.17868 versus
  0.16757 GeV (muon mode). These shape differences are a documented limitation
  of uniform phase space. Six branching fractions and both charges are retained.
- Final packaged tools and committed ACTS source reproduce all 60 Fatras hit,
  truth and meson-state CSV files byte-for-byte. The new observer-free current
  timing run also reproduces all 40 hit/truth files. Geant4 was rerun from scratch
  with the corrected physical world; historical Geant4 truth is not reused.

## Calibration and cost

K+/K- each have 100 momentum nodes, 0.1--7000 GeV, 512 FTFP_BERT 11.3.2 Si
outcomes/node, seed 20442. Independent validation: 99 geometric midpoints,
256 outcomes/point, seed 22542. No null collisions. The previous seven channels
are concatenated verbatim. Rare Geant4 Sigma_b0 (PDG 5212, absent from the ACTS
mass table) is folded into the untransported residual, like nuclear fragments;
charge and four-momentum remain accounted for.

761856 combined-table and 101376 midpoint runtime samples pass conservation;
maximum relative residual 1.58e-13. Largest midpoint rate differences are
0.342% for K+ and 5.52% for K- (near 1 GeV); the latter remains a coarse-grid
limitation. Mean charged-multiplicity differences are -0.125 and -0.069. Rates
interpolate, while final states use the lower momentum node and conserve the
new incident four-momentum. This does not validate arbitrary target materials.

Combined text table grows from 400 to 558 MiB. Isolated single-load measurements:
5.62 ->7.70 s, maximum RSS 336.2 ->467.1 MiB. Tables are immutable and shared.
Recorded simulation-algorithm time: 11.25 ->11.95 s for 20 events; total sequencer
including CSV/diagnostics: 21.82 ->24.82 s. The meson observer writes substantially
more states than the old antinucleon observer. Concurrent work and I/O preclude
a controlled throughput claim. The standalone native decay plus histogram loop
costs about 0.17 microseconds/pion and 0.21 microseconds/kaon in this single run;
it is not an end-to-end transport benchmark.

## Reproduction

Reuse `../fatras-neutral-hadrons/{generate,combine,compare,build-check}.py`,
`../fatras-pion-validation/{build-diagnostics,run}.py` and the shared ODD
`../fatras-neutral-hadrons/odd/{ancestry,compare}.py`. The observer now also records
meson decay vertices and proper time. No validation writer is added to ACTS.

1. Build the shared Geant4 generator using its CMakeLists. Run `calibrate.py
   --output DATA --build GENERATOR_BUILD --data-root GEANT4_DATA`.
2. Combine the previous seven-channel table and `silicon-kaons.table` using
   `combine.py`; run the compiled `check.cpp` on the combined and midpoint
   tables. `check.cpp TABLE --load-only` measures parsing/validation without
   subsequent kinematic sampling. Run `compare.py TRAINING MIDPOINTS --output JSON`.
3. Build the shared diagnostics module and use `run-env.sh run.py MODE` with
   `--projectiles 211 -211 321 -321 --diagnostic-prefix meson`, the same input
   directory, 20 events, the corrected material map and `--reference-material`.
   Inputs here: `/private/tmp/fatras-odd-inputs-final`. Historical Geant4 diagnostics
   in `/private/tmp/fatras-meson-geant4` are superseded. Use `run-comparison.py`
   and the physical world helper for the final reference in
   `/private/tmp/fatras-timing-geant4-id`.
4. ACTS `17706df312` supplies pion decays and kaon interactions with the final
   world guard. Old versus nine-channel tables give the first two ablations.
   `1fae8bd106` adds kaon decays; `82f3aa8afa` adds Sympy regression coverage.
   The ablation baseline is the archived antinucleon run, not ACTS main. Metadata records revisions,
   dirty state, table/input/map hashes and raw locations.
5. Run shared `odd/ancestry.py` for each variant. Archive as
   `{geant4,baseline,pion,kaon,full}-ancestry.json`. Run `decay-attribution.py
   --input G4_WITH_VERIFIED_TRUTH --output JSON` for the cut/late-decay diagnostic.
6. Build `decay-reference.cpp` with `build-decay-reference.py --acts-build BUILD
   --geant4-lib LIBDIR --output EXECUTABLE`; run with the G4 dataset environment
   and output CSV path. `plot.py --results RESULTS --calibration MIDPOINT_JSON
   --ablations` makes the historical four-page ablation book. Shared `odd/compare.py` makes the
   full 11-page ODD book; use explicit revision/material-map overrides.

Local ignored artifacts: `data/2026-10-14/`, `results/2026-10-14/`. PDFs:
`charged_meson_diagnostics.pdf` and `odd_geant4_vs_fatras.pdf`. JSON summaries,
source/runtime metadata, hashes, timing logs, G4 vertices and replay manifests
are archived alongside. `RootNuclearInteractionParametersWriter` is untouched.
