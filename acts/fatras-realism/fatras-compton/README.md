# Fatras native Compton validation

External tools for the native, code-only Compton kernel on `feat/fatras-compton`.
They use the established d25514208b frozen-build ABI bridge and the accepted
numerical low-momentum navigator with candidate caching/pruning. They do not
modify the installed ACTS build or introduce runtime physics data. The native
kernel has no G4 dependency; the existing hadronic backend still uses G4.

## Reproduce

```
python3 build.py --source SOURCE --work WORK
python3 run.py --source SOURCE --module WORK/pruned-build --output WORK/compton-100
python3 run.py --source SOURCE --module WORK/pruned-build --output WORK/disabled-check --disable-compton --photon-cut-MeV 1.0219979
python3 run.py --source SOURCE --module WORK/pruned-build --output WORK/compton-50 --photon-cut-MeV .05
python3 run.py --source SOURCE --module WORK/pruned-build --output WORK/compton-200 --photon-cut-MeV .2
python3 run.py --source SOURCE --module WORK/pruned-build --output WORK/compton-pair-cut --photon-cut-MeV 1.0219979
```

Run three alternating control/Compton repetitions without concurrent builds or
simulations for timing. Use `repeat-control-{1,2}` and `repeat-compton-{1,2}` for
the additional repeats recognised by the report. Event CSVs must match exactly
within each setting. Disabling Compton at the old photon threshold must match
the archived `fatras-transport-performance/results/2026-10-16/pruned-check`
reference. `run.py` refuses to overwrite a run directory.

The bounded navigator uses one worker, fixed geometry, charged p >= 0.2 MeV,
pT >= 0.05 MeV, a 5 mm step/search limit, four turns and 50000 steps. Ionisation
electron production starts at 100 keV. Photon retention/production defaults to
100 keV; it is independent of charged acceptance. All input events and output
hits remain unfiltered. The detector and material map remain unchanged.

For a separate standard-navigation worker replay:

```
python3 run.py --source SOURCE --module WORK/bridge --output WORK/standard-one --standard --threads 1
python3 run.py --source SOURCE --module WORK/bridge --output WORK/standard-four --standard --threads 4
```

This uses the common runner's higher charged thresholds (p >= 100 MeV, pT >= 50 MeV); it does not
establish multiworker support for the bounded-navigation prototype. New photon
settings are supplied before algorithm construction through the validation
bridge. The copied common runner omits the new Compton field from the frozen
base Config, whose ABI predates it. This is an explicit compatibility adapter,
not a production API or runtime patch to the physics model.

## Cross sections and report

```
python3 build-reference.py --source SOURCE --build BUILD --output WORK --geant4-lib G4_LIB
G4LEDATA=G4_EMLOW_DIR G4ENSDFSTATEDATA=G4_ENSDF_DIR WORK/compton-reference > WORK/reference.csv
python3 verify.py --work WORK
python3 analyse.py --work WORK
MPLCONFIGDIR=/tmp/fatras-compton-mpl python3 plot.py --work WORK --output WORK/compton.pdf
python3 archive.py --work WORK --source SOURCE --output results/2026-10-16
```

The cross-section executable compares the analytic free-electron rate with
installed G4KleinNishinaModel. It does not change the G4 event configuration.
Native tests additionally check independent quadrature and sampled moments,
energy/momentum conservation, truth, survival, conversion competition and
four-worker deterministic replay.

The four-page PDF includes genuine pinned ACTS main (300b664a3d), changed Fatras
and default FTFP_BERT Geant4 physically confined to the ODD ID. The old changed
Fatras is explicitly an ablation control, not the main baseline. All summary
hits are included; region/process plots partition secondaries. Main/G4 CPU
comes from archived five-/three-event measurements; the new control/current
measurements repeat the same three events. All times include sequencer
initialisation, transport, CSV output and finalisation; setup is separate.

The simple kernel ignores atomic binding, Doppler broadening, polarisation and
relaxation. It also retains one interaction per surface slab, with no daughter
transport through the remaining birth slab. Material is still absent from
sensitive sensor surfaces in this map. Do not interpret G4 process contributions
as guaranteed recoverable hit gains, or retune rates to fit the total count.

The archive contains optional validation output, compressed CSVs, build/run
records, tests and source hashes. Repeated runs use hash manifests instead of
duplicating event files. No archive or reference CSV is read by Fatras. Full
normal-build CI and general geometry/navigation validation remain required.
