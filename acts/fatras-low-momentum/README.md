# Low-momentum transport: bounded-search feasibility

External experiment, 15 October 2026. ACTS branch `feat/fatras-threaded-hadronic`,
commit `ca045e1435`. Production code is unchanged by this navigation experiment.

`build.py` generates a copy of `TryAllNavigator` and replaces only its candidate
lookup with a conservative BVH. Rectangle/trapezoid plane bounds use transformed
bounding rectangles; all other surfaces and nonzero boundary tolerances remain
in the unpruned list. Candidate order is restored before exact intersection tests.
Both forward queries and backward blind-step checks are indexed. All stepping,
material and hit decisions remain in the existing ACTS implementation.

The index is cached per volume. **One worker and immutable geometry only.** It is
not valid for event-dependent alignment and is not a proposed production API.
The wrapper selects navigation once at charged-particle birth (pT<500 MeV by
default); it does not switch when a particle later slows. Fixed steps, loop
budgets, transport thresholds and failures remain important limitations.

## Build and run

First build the adjacent `fatras-runtime-model/build-bridge.py` validation bridge.
It uses the pinned d25514208b ABI of the existing local build, not a general
replacement for a normal ACTS build. Then:

```sh
python build.py --source SOURCE --bridge LIVE_BRIDGE --output BUILD
../fatras-neutral-hadrons/odd/run-env.sh run.py \
  --mode live --source SOURCE --build ACTS_BUILD --revision REVISION \
  --input INPUT --material-map MATERIAL_MAP --module-dir BUILD \
  --output OUTPUT --events 3 --threads 1 \
  --navigation-mode 2 --navigation-step 5 --navigation-pt-max .5 \
  --p-min .02 --pt-min .005 --loops 4 --max-steps 50000
```

Mode 0 uses standard navigation, 1 uses full TryAll, 2 uses bounded search.
`--transport-only` disables interactions and decays. The existing
`fatras-navigation-validation/probe.py` generates the 432 stable-muon probe.

`report.py --work RECORDS --reference INCLUSIVE_REFERENCE_JSON --output REPORT`
produces the inclusive PDF and numerical summaries from the archived run records.
The record commands contain the original temporary paths; use their settings
with the current paths when replaying. `provenance.json` identifies the permanent
source and archived exact build/run scripts. No additional physics data file is
required: collision runs use the direct Geant4 hadronic backend.

## Result and limits

- Probe: byte-identical full TryAll/bounded CSVs at 5 and 2.5 mm. Candidate tests
  fall by 99.3%; CPU 13.75 -> 0.24 s and 25.51 -> 0.40 s respectively.
- Collision event 0, same 5 mm/5000-step configuration: byte-identical CSVs,
  215.63 -> 7.65 CPU s, including output (28.2x speedup).
- Three matched inclusive events, 50000-step cap: 22111 / 22491 secondary pixel
  hits/event at 5 / 2.5 mm, versus current default transport 14334 and Geant4 38683.
  CPU 9.05 / 15.66 s/event versus current default 1.24 s/event. One failed charged
  trajectory in each three-event bounded run. No analysis momentum/time cuts.
- Raising the cap from 5000 removes most failures but does not establish step-size
  convergence or physical stopping. The full TryAll equivalence is a search
  correctness check, not independent physics ground truth.
- About 91% of charged propagation time is spent above 50 MeV birth pT. Fixed tiny
  steps and later slowing must be addressed before making this a default.
- Geant4 ionisation-born pixel hits (10907/event) correspond to 67% of the net
  remaining gap at 2.5 mm. Fatras still creates no explicit ionisation electrons.
  Navigation alone cannot recover these hits; process attribution is not a
  promise that adding one process recovers the same count unchanged.

PDF: `results/2026-10-15/low_momentum_feasibility.pdf`. Main and Geant4 are the
archived inclusive reference with matching input hashes. Geant4 uses the physical
ODD ID world, default FTFP_BERT, no added global time kill. Archived reference CPU
covers five events; new navigation CPU covers three. These are feasibility
measurements on an Apple M3 Pro, not an HL-LHC reconstruction validation.
