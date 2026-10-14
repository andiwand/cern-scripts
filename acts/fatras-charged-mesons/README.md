# Charged mesons in Fatras

Three separate additions on `feat/fatras-hadronic-interactions`: native charged-pion
muon decays, separately calibrated K+/K- inelastic interactions, and native
charged-kaon decays. Geant4 is an offline reference, not a runtime dependency.
The six kaon modes retain 99.995% of the quoted PDG weights. Three-body channels
use uniform invariant phase space; no form factors, Dalitz slopes, stopped-kaon
capture or muon decay are added. Charged p/pT cuts remain unchanged.

Physics sources:
- https://pdg.lbl.gov/2026/listings/rpp2026-list-pi-plus-minus.pdf
- https://pdg.lbl.gov/2026/listings/rpp2026-list-K-plus-minus.pdf

## Measurements, 2026-10-14

Twenty identical ttbar + PU200 events, seed 42, ODD tracker, 2 T. Pixel hit-entry
cuts p >= 100 MeV and pT >= 50 MeV. Fatras uses the previously corrected beam-pipe
map and local L0 scaling of the Si reference. No detector hit tuning.

| Configuration | Primary hits/event | Secondary hits/event | Secondary / Geant4 |
| --- | ---: | ---: | ---: |
| Geant4 | 47191.40 | 18195.55 | 100% |
| Previous Fatras | 46350.30 | 13968.95 | 76.77% |
| Plus pion decays | 46150.50 | 14161.60 | 77.83% |
| Plus kaon interactions | 45887.70 | 14780.85 | 81.23% |
| Plus kaon decays | 45808.30 | 14961.30 | 82.23% |

Sequential secondary-hit gains: 192.65 +/-127.79, 619.25 +/-122.61, and
180.45 +/-111.61/event (paired event SEM). Combined: 992.35 +/-111.27, +7.10%,
closing 23.48% of the previous gap. Final coverage 82.23% +/-0.81 percentage
points. Primary hits decrease by 542/event; combined primary+secondary gain is
450.35/event. Decays replace parent tracks and compete with nuclear interactions;
individual additions also change later random-number history. Small-sample
statistical errors do not cover physics-model errors.

Direct final Fatras / Geant4 hits: pion decays 232.80/712.90, kaon decays
130.60/236.80, kaon nuclear 598.45/509.55. These are immediate-parent categories,
not shower ancestry. The remaining pion gap is not explained by parent cuts:
708.00 reference hits/event have accepted incident pion kinematics, 4.25 do not,
and 0.65 have no matched decay vertex. Corresponding kaon values are 186.45,
49.60 and 0.75. Pre-step incident momentum does not resolve continuous loss
within the decay-ending step.

Existing propagator loop protection remains enabled at half a turn. In uniform
2 T and at fixed momentum, this corresponds to 2.439 ns pion proper time and
8.628 ns kaon proper time. Reference accepted decay-parent hits beyond these
proper times contribute 230.80 and 10.10/event. This is a diagnostic proxy,
not an exact recoverable gain: energy loss, scattering, daughter looping and
world exit also matter. Do not disable navigation/loop safeguards without a
separate CPU and correctness study.

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
  has one maximum-step failure. Geant4 retains 14 hit-buffer warnings.
- Native and Geant4 rest-frame checks use 100000 decays per charge/species.
  Three-pion energy spectra agree well; native semileptonic mean charged-daughter
  energies are 0.13955 versus 0.13249 GeV (electron mode), and 0.17868 versus
  0.16757 GeV (muon mode). These shape differences are a documented limitation
  of uniform phase space. Six branching fractions and both charges are retained.
- All 20 Geant4 hit files match the earlier reference byte-for-byte. Only then
  reuse its full particle truth. Final packaged tools and committed ACTS source
  reproduce all 60 Fatras hit, truth and meson-state CSV files byte-for-byte.

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
   Inputs here: `/private/tmp/fatras-odd-inputs-final`. Geant4 diagnostics:
   `/private/tmp/fatras-meson-geant4`. Reused verified truth:
   `/private/tmp/fatras-odd-geant4-neutral-parent`.
4. ACTS `17706df312` supplies pion decays and kaon interactions with the final
   world guard. Old versus nine-channel tables give the first two ablations.
   `1fae8bd106` adds kaon decays; `82f3aa8afa` adds Sympy regression coverage.
   Baseline is the archived antinucleon run. Runtime metadata records revisions,
   dirty state, table/input/map hashes and raw locations.
5. Run shared `odd/ancestry.py` for each variant. Archive as
   `{geant4,baseline,pion,kaon,full}-ancestry.json`. Run `decay-attribution.py
   --input G4_WITH_VERIFIED_TRUTH --output JSON` for the cut/late-decay diagnostic.
6. Build `decay-reference.cpp` with `build-decay-reference.py --acts-build BUILD
   --geant4-lib LIBDIR --output EXECUTABLE`; run with the G4 dataset environment
   and output CSV path. `plot.py --results RESULTS --calibration MIDPOINT_JSON`
   makes the four-page diagnostics book. Shared `odd/compare.py` makes the
   full 11-page ODD book; use explicit revision/material-map overrides.

Local ignored artifacts: `data/2026-10-14/`, `results/2026-10-14/`. PDFs:
`charged_meson_diagnostics.pdf` and `odd_geant4_vs_fatras.pdf`. JSON summaries,
source/runtime metadata, hashes, timing logs, G4 vertices and replay manifests
are archived alongside. `RootNuclearInteractionParametersWriter` is untouched.
