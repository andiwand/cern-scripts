# Inclusive Fatras validation and navigation diagnostics

**Primary summary:** `results/2026-10-14/inclusive_summary.pdf`. It has no input
momentum selection or hit momentum/time/multiplicity cuts. It compares genuine
ACTS main, current Fatras and default FTFP_BERT on five identical generator events
inside the ID. The physical ID world is enforced; Geant4 has no extra global time
kill. Its standard physics-list cuts remain (the runtime reports a 10000 ns
neutron tracking limit). Native Fatras acceptance is a model limitation to measure,
not a selection applied to Geant4 or to these summary plots.

`prepare-inclusive-inputs.py` starts from the raw generator CSVs and removes only
births outside the ID. It retains all momenta, species and at-rest particles.
`run-inclusive-comparison.py` runs main/current/Geant4 sequentially; its local
paths match the neighbouring packages. `summary-inclusive.py` produces cached
JSON and the no-cut PDF, checking input hashes and the saved Geant4 ID boundary.

```sh
python prepare-inclusive-inputs.py --source /private/tmp/fatras-odd-inputs-raw \
  --output /private/tmp/fatras-odd-inclusive-inputs
python run-inclusive-comparison.py --input /private/tmp/fatras-odd-inclusive-inputs \
  --output-prefix /private/tmp/fatras-inclusive-default --events 5 --revision d25514208b
python summary-inclusive.py --main /private/tmp/fatras-inclusive-default-main \
  --fatras /private/tmp/fatras-inclusive-default-changed \
  --geant4 /private/tmp/fatras-inclusive-default-geant4 --output results/2026-10-14
```

The shared `fatras-charged-mesons/run-comparison.py` now defaults to no extra
Geant4 time kill and rejects a momentum-prefiltered Geant4 input unless explicitly
requested for a historical replay. Use `--geant4-time-max-ns 1000
--allow-prefiltered-input` to reproduce the old reference configuration.

**Separate diagnostic:** `navigation_diagnostics_with_cuts.pdf` intentionally
retains the old sample's input filtering/time limit and the accepted-track metric.
Those results are not the new inclusive reference. The following sections record
that controlled study and its limitations.

## Historical charged-navigation study

External experiment for ACTS `feat/fatras-hadronic-interactions`, 14 October 2026.
The physics event library is an existing diagnostic input, not a proposed ACTS
runtime distribution. No additional physics tables are introduced here.

`build.py` builds a temporary Python algorithm from the checked-out Fatras
algorithm, replacing its charged propagator with `audit-propagator.hpp`.
Both branches use SympyStepper and the same Fatras actors. Dispatch is once at
particle birth: TryAll below the configured pT, standard Navigator otherwise.
There is no handoff when a particle subsequently slows. Neutral transport and
neutral cuts are unchanged. The standard branch reproduces the old run's first
two events byte for byte (truth and hit CSVs; see baseline-replay.json).

ACTS commit d25514208b fixes moving an rvalue propagator into SingleParticleSimulation;
this is needed for the noncopyable TryAll navigator. A real TryAll Fatras integration
case is included there; all 270 Fatras integration cases passed. The experimental
backend, selection knobs and measurement tools stay outside ACTS.

## Reproduce the historical navigation diagnostic

Local dependencies are those of the neighbouring `fatras-charged-mesons` and
`fatras-neutral-refinement` validations. `run-scan.py` records the full invocation,
uses the existing run-env.sh and one worker, and currently contains local paths.
The configured source revision must match a clean checkout. Build products are
ignored. Example (replace SOURCE, BUILD and REVISION with the intended checkout):

```sh
python build.py --source SOURCE --build BUILD --output build
python run-scan.py --variant native --events 20 --revision REVISION \
  --output /private/tmp/fatras-nav-native --max-steps 5000
python run-scan.py --variant tryall --events 5 --revision REVISION \
  --output /private/tmp/fatras-nav-tryall --try-all-pt-max .5 \
  --far-limit-mm 20 --step-mm 20 --max-steps 5000
python prepare-results.py /private/tmp/fatras-nav-native \
  /private/tmp/fatras-nav-tryall --output results/2026-10-14
```

`prepare-results.py` analyses common-cut secondary pixel hits and then compresses
truth CSVs losslessly, verifying decompressed SHA256 before removing the redundant
plain file. It leaves hits plain. Its reference is the preceding 20-event physics
validation. It uses paired event differences, not raw means across unequal samples.
Run timing jobs sequentially, without concurrent analysis/compression/compilation.
CPU includes CSV output; it is event-loop CPU, not just propagation time.

`reference-cuts.py` walks strict-ID Geant4 ancestry using birth momenta. Its result
is exposure to birth cuts, not a recoverable-hit estimate or a test of later slowing.
`inclusive.py` measures the separate deficit below the common hit-entry cuts.
`plot.py` produces the multi-page PDF from these result JSONs.

```sh
python reference-cuts.py --input /private/tmp/fatras-timing-geant4-id \
  --events 20 --output results/2026-10-14/reference-cuts.json
python inclusive.py --fatras /private/tmp/fatras-refinement-prompt \
  --geant4 /private/tmp/fatras-timing-geant4-id \
  --output results/2026-10-14/inclusive.json --reference-processes
python plot.py --results results/2026-10-14 \
  --reference ../fatras-neutral-refinement/results/2026-10-14/secondary-gaps.json
```

## Deterministic probe

`probe.py --input DIR` generates 432 stable muons across pT, eta, phi and displaced
vertices. Use run-scan.py with `--input DIR --transport-only --events 1`, charged
cuts .001/.001 GeV, maximum 5000 steps and the chosen loop fraction. For TryAll set
`--try-all-pt-max 1000` and both far limit/maximum step to 10, 5 or 2.5 mm. Analyse with
`probe.py --input DIR --runs RUN1 RUN2 RUN3 --output results/2026-10-14/probe.json`.
This isolates navigator behavior without cascades or random scattering. It compares
inclusive pixel crossings and unique sensors; it is not a Geant4 ground-truth test.

## Interpretation limits

- Physics sample: same 20 ttbar+PU200 inputs, seed 42, 2 T, corrected ODD material map.
- Accepted hits: pixel volumes 16–18, hit-entry p >=100 MeV and pT >=50 MeV.
- Lower charged cuts: p >=20 MeV, pT >=5 MeV; do not change the hit cuts.
- TryAll 20 mm uses 5 events; the longer 10 mm test uses 3. Report paired SEM and
  exact sample sizes. Changing transport changes random histories/cascades.
- Loop fraction is a path budget based on initial momentum; four turns is not an
  unlimited or fully converged treatment of charged stopping. Global path limits remain.
- Far limit filters intersection results, not the number of volume candidates
  tested; TryAll can be very expensive even with a short far limit.
- Failed particles are counted, including max-step failures. Steps/path statistics
  cover successful propagations only. Global counters require one worker.
- Strict Geant4 reference uses the physical ID world r=1202 mm, |z|=4002 mm.
  ACTS-main baseline is 300b664a3d9c32ec928208e7eb18df40e7b2721b.
- Current physics still uses the 561 MiB Si event library from the preceding
  refinement package. Do not copy it into this package or treat it as a shipping solution.

## Findings (diagnostic, not a production default)

The previous common-cut comparison omitted 22,008.65 Geant4 soft secondary
pixel hits/event. They account for 89.34% of the inclusive deficit. Of these,
11,527.45 are tagged ionisation and 7,465.75 conversion; 94.4% are electrons or
positrons. Missing soft-particle production therefore matters alongside transport.
Only 142.25 accepted reference hits/event have a charged carrier/ancestor born
below the original cuts; this does not measure subsequent slowing.

| Trial | Events | Paired accepted-hit gain/event | CPU s/event | Failed particles |
| --- | ---: | ---: | ---: | ---: |
| Standard navigator, 5000-step budget | 20 | 0 | 1.083 | 1 |
| Standard, one-turn budget | 20 | 230 +/-140 | 1.156 | 1 |
| Standard, one turn, lower charged cuts | 20 | 275 +/-144 | 1.263 | 2 |
| Standard, four turns, lower charged cuts | 20 | 438 +/-139 | 1.449 | 41 |
| TryAll 20 mm, half turn, original cuts | 5 | 177 +/-108 | 54.497 | 0 |
| TryAll 10 mm, four turns, lower cuts | 3 | 1607 +/-463 | 149.648 | 2 |

Gains use the preceding current-physics run on exactly the same events; errors
are paired event SEM, not 95% intervals. On the same three events, the last trial
gains 1497 +/-241 hits/event over standard navigation with identical cuts and loop
budget. Current / standard-long / TryAll-long / ID-only Geant4 accepted means on
these three events are 14457.3 /14567.7 /16064.7 /16401.0. Inclusive means are
14457.3 /18922.0 /21774.3 /36030.7. TryAll adds about 190 +/-80 particles/event
crossing at least three sensors; only 5.33 repeated sensor hits/event are counted.
Transport settings also change stochastic cascades: do not extrapolate this
three-event gain to the full sample or call it complete Geant4 agreement.

Twenty-event event-loop CPU reference: ACTS main 0.820, current physics 1.124,
strict-ID Geant4 39.701 s/event. The TryAll tests are too costly for a production
Fatras default. A shorter far limit does not provide spatial candidate pruning.
Use TryAll as a diagnostic for a bounded, efficient nearby-surface search.

The separate stable-muon probe finds substantially more sensor crossings with
TryAll. Its detailed per-particle sets and step-size comparisons are in probe.json;
similar totals do not imply identical sets or exact step-size convergence.

Shipping decision: do not grow a mandatory custom event file. The 561 MiB replay
library is a validation oracle. A deployable replacement needs algorithmic final
states (with compact validated constants in code), or an explicitly supported
adapter to suitable existing Geant4 data. Rate files alone do not specify the
correlated final states represented by the event library. No replacement model
has been implemented or validated in this navigation study.

Probe totals: standard 1150 crossings; TryAll at 10/5/2.5 mm gives
1710/1711/1728, all unique particle–sensor pairs, no failed particles. At 2.5 mm
TryAll recovers all standard pairs and adds 578. Ten particles change sensor sets
between 5 and 2.5 mm (23 added, six lost pairs): not exact step-size convergence.
The broad navigation deficit is much larger than this remaining step dependence.
`run-probes.py` reproduces all four configurations sequentially.
Hadronic table domains remain unchanged; lower charged cuts do not enable
hadronic interactions below their tabulated momentum range.

Reference caveat discovered during the configuration audit: all historical
navigation comparisons above used shared input filtered at p>=100 MeV and
charged pT>=50 MeV (V0/pi0 exceptions), and Geant4 had an explicit 1000 ns time
kill. The inclusive hit counts remove analysis cuts only; they are not a fully
inclusive generator/default-transport reference. Keep this diagnostic separate
from the new inclusive summary. New summary plots must not apply momentum cuts.
The generator helper uses fixed 200 pileup interactions, not the Poisson
multiplicity stated in older metadata; checked at generation commit d41a146baac.
Completed native-control hit CSVs were losslessly gzipped after analysis.
