# Fatras transport performance

External, **single-worker, immutable-geometry** feasibility tools. They reuse the
existing frozen ACTS validation ABI and direct Geant4 hadronic backend. They are
not a production navigator or a general ACTS build. No new physics tables.

## Accepted optimisation

`--variant cache --query-cache --surface-pruning` retains numerical propagation
and all physics/step/loop settings. It caches each volume's candidate list, reuses
per-track buffers and a conservative nearby candidate set, and rejects line
segments that cannot reach an infinite plane or cylindrical shell before the
exact ACTS intersection. Unsupported surfaces remain in the exact search.
Candidate order and intersection decisions remain unchanged. Geometry transforms
and candidate lists must not change during a run. Caches/counters are deliberately
not exposed to multiple workers; production integration needs context-aware,
thread-safe ownership.

On three ttbar + PU200 events, three alternating sequential repetitions give:

- Numerical soft transport: median **25.47 CPU s/event**, range 24.82–31.60.
- Optimised navigation: median **11.39 CPU s/event**, range 10.39–12.66.
- Every repeated particle/hit CSV is byte-identical. Same five failed charged
  propagations across three events; same 34581 secondary pixel hits/event.
- Exact intersection candidates: 3.818 billion -> 34.765 million over three
  events. Numerical stepping and generated particle counts are unchanged.
- 20000 randomized forward/backward queries retain every brute-force
  intersection and match uncached spatial queries; also pass AddressSanitizer
  (linked ACTS libraries are not instrumented).

## Helix experiment — not selected as the reference

`--variant helix` reuses ACTS HelixStepper with a current-momentum angular cap
and smaller trials after reverse navigation corrections. The latter prevents
exact forward/backward cycles caused by a blind-step chord crossing a surface
that the curved arc skirts. The cap also constrains reverse steps. The generic
fixes are separate ACTS commits on `feat/fatras-transport`; the builder also
supports the original d419e58b19 source used for the ablations.

This experiment is validated only in the constant 2 T field. It rejects volume
material instead of silently dropping its effects; surface material, scattering,
energy loss, decay, daughter creation and hit recording stay in SimulationActor.
It still uses chord-based navigation, not exact helix/surface intersection.

- 5 mm / 0.25 rad: 8.39 CPU s/event, 33479 secondary pixel hits/event, nine
  failed charged propagations across three events. One timing, not a precise
  speedup estimate; changing transport also changes random draws.
- 5 mm / 0.05 rad: 17.22 CPU s/event, 34874 secondary pixel hits/event, fourteen
  failed propagations. Tightening the cap removes the useful speed advantage.
- After reverse refinement, all 1440 stable probes finish. Relative to the
  0.25 mm numerical probe, 5 mm numerical loses 95 crossings and adds 1;
  0.25 rad helix loses 209 and adds 2; 0.05 rad loses 96 and adds 4.
- A 20 mm / 0.25 rad probe loses 1203 crossings: rejected before a full-event
  benchmark. Larger blind steps are not a validated speed optimisation.

The approximately 1 s CPU/event target is not met. Further large gains need
curved-path-aware surface search / local event-driven transport, or a separately
validated correlated soft-hit handoff. These tools do not introduce noise hits
or additional particle cuts.

## Reproduction

Prepare the all-physics bridge using adjacent `fatras-soft-secondaries/build.py`
and its documented source/build/Geant4-library arguments. Then:

```sh
python build.py --source SOURCE --bridge BRIDGE --output WORK/pruned-build \
  --variant cache --query-cache --surface-pruning
python run.py --source SOURCE --module WORK/pruned-build --output WORK/pruned-check
python build.py --source SOURCE --bridge BRIDGE --output WORK/helix-build \
  --variant helix --max-angle .25 --query-cache --surface-pruning
python run.py --source SOURCE --module WORK/helix-build --output WORK/helix-check
```

`probe.py --output INPUT` creates 1440 stable charged probes, pT 0.2 MeV–1 GeV,
eta 0/1/2, eight azimuths, three birth radii, both charges. Pass this input to
`run.py --transport-only --events 1`. `--step` changes the search and maximum
step together. `measure.py` alternates baseline/pruned three-event runs; run it
without other builds or simulations. Paths and compiler flags are recorded.

`report.py --work RECORDS --output REPORT` produces the inclusive PDF and JSON;
it also reads archived `.csv.gz` and hash-only duplicate runs. It uses the pinned
ACTS-main and default Geant4 ID-only reference from the soft-secondary study.
No summary hit cuts. Main CPU covers five events; other physics comparisons
cover three. Exact equality to the numerical prototype is not independent
physics validation. Its p/pT thresholds and finite four-turn budget remain.

Artifacts in `results/2026-10-16/` include the complete selected event outputs,
timings, probe results, hashes for duplicate runs, build records and test logs.
These are validation outputs, not simulation input data. Normal project CI,
general field/alignment support, multiworker navigation and reconstruction
validation remain outside this prototype.
