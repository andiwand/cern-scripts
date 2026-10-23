# Fatras soft-secondary validation

Algorithmic ionisation, independent photon acceptance, native muon/pi0 Dalitz
and stopped-parent decays. External validation tools only; no physics tables
are shipped or read by these new models.

`build-series.py --source SOURCE --build BUILD --work WORK --geant4-lib LIB`
builds the macOS validation bridge against the recorded d25514208b ACTS build.
This is not a substitute for a normal ACTS build. It compiles the new physics
and uses the existing `fatras-runtime-model` and `fatras-low-momentum` tools.
The latter is a single-worker bounded-search experiment, not production
navigation. Standard navigation supports the normal ACTS worker pool.

For each `--case standard|photon|ionisation|all|soft|geant4`, run:

```
python run.py --source SOURCE --build BUILD --work WORK --case CASE \
  --input UNFILTERED_INPUTS --material-map MATERIAL_MAP --events 3
```

- `standard`: all new physics, production navigation, p>=100 MeV, pT>=50 MeV.
- `photon`: bounded navigation, independent photon acceptance; legacy Landau
  and ca045e1435 native decays for ablation.
- `ionisation`: also enable explicit ionisation, electron kinetic cut100 keV.
- `all`: also use the new native decays, including pi0s from nuclear interactions.
- `soft`: all physics, charged p>=0.2 MeV, pT>=0.05 MeV. Experimental/expensive;
  no claim of converged inclusive transport.
- Bounded cases otherwise use p>=20 MeV, pT>=5 MeV, 5 mm search/step limit,
  four turns and 50000 steps. Photon threshold is 2me in every new case.
- Geant4 is default FTFP_BERT, with no added time/momentum cuts, confined to
  the physical ODD ID using the existing `id_world` validation module.
- The generator inputs and all written hits remain unfiltered. Physics
  acceptance and finite path budgets are reported limitations, not plot cuts.

Use `--threads 4 --output WORK/standard-four` for the standard-navigation replay
check; compare all event CSV hashes with the single-worker output. Bounded
navigation and the G4 reference require one worker.

`report.py --work WORK --output REPORT --reference INCLUSIVE_SUMMARY_JSON`
produces `soft_secondaries.pdf` and `summary.json`. The genuine ACTS-main
reference is archived at 300b664a3d; its CPU covers five events, while this study
uses three. This is a pinned main snapshot, not a rebuild of current main. The prior bounded control is read from the existing low-momentum
validation results. Keep reference provenance; do not label a changed physics
branch as ACTS main. Process-birth and momentum decompositions overlap.

`build-reference.py` takes the same source/build/library paths and an `--output`
directory. Run its `ionisation-reference` under the existing `run-env.sh`
environment and capture stdout as `ionisation-reference.csv`. The comparison
uses one million thin-silicon trials per species/energy/cut point, against G4
analytic cross sections and mean losses. It does not impose the trial cut on
the inclusive Geant4 simulation.

Results under `results/2026-10-15/` include immutable run metadata, truth/hit
CSV archives, exact build/run commands, unit/replay checks and the PDF. Runtime
physics remains algorithmic; these files are validation output only. Frozen
bridge libraries must be rebuilt when the source changes. Normal project CI
and detector digitisation/reconstruction validation remain required.

`late-photons.py --source SOURCE --build BUILD --work WORK --material-map MAP`
checks a 300-photon sample at time zero and 10 microseconds. It requires the
standard bridge and verifies equal hit identities/kinematics, with shifted hit
times, beyond the configured neutral-hadron time budget.
