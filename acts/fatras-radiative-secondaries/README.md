# Radiation-model discrepancy investigation

Native interaction corrections on `fix/fatras-radiative-secondaries`, following
`fatras-compton`. Geometry and material placement remain unchanged. The work fixes
bremsstrahlung energy conservation and replaces the one-photon inclusive-loss
approximation with explicit screened photons, interleaved with ionisation when
both explicit loss models are enabled. It does not claim to close the hit gap.

## Reproduction

Use a fresh `WORK` directory and the `fatras-soft` source worktree:

```sh
python build.py --source SOURCE --work WORK
python run.py --source SOURCE --module WORK/pruned-build --output WORK/current
python run.py --source SOURCE --module WORK/pruned-build --output WORK/legacy-fixed --brems-cut-MeV inf
```

Repeat each three-event run four times, with suffixes `-repeat-1` through `-repeat-4`.
Alternate controls/current sequentially, without concurrent compilation or
analysis. `legacy-fixed` retains the legacy radiation model with the kinetic
energy conservation fix. It is an ablation control, not the ACTS-main baseline.

```sh
python run.py --source SOURCE --module WORK/bridge --output WORK/standard-1 --standard --threads 1
python run.py --source SOURCE --module WORK/bridge --output WORK/standard-4 --standard --threads 4
python verify.py --work WORK
python build-reference.py --source SOURCE --build BUILD --output WORK --geant4-lib G4_LIB
G4LEDATA=G4_EMLOW G4ENSDFSTATEDATA=G4_ENSDF WORK/radiation-reference > WORK/reference.csv
python analyse.py --work WORK
python spectra.py --work WORK
MPLCONFIGDIR=/tmp/fatras-radiation-mpl python plot.py --work WORK --output WORK/radiation.pdf --preview
python archive.py --work WORK --source SOURCE --diagnostics DIAGNOSTIC_WORK --output results/YYYY-MM-DD
```

The numerical bounded navigator retains one worker, four turns, 50000 steps,
5 mm search/step, charged p >= 0.2 MeV and pT >= 0.05 MeV. Standard-navigation
worker replay uses the common runner's p >= 100 MeV and pT >= 50 MeV. This is not a
multithreading claim for the bounded-navigation prototype. Photon transport and
explicit production both use 100 keV in the accepted run; ionisation production
uses 100 keV. No output hits are filtered.

Builds use the established d25514208b frozen ACTS ABI adapter and compile the
changed physics sources explicitly. The new production threshold and Compton
flag are carried by the compiled adapter because the installed base Config
predates them. The installed build remains unchanged. Full normal-build CI is
not replaced by these checks.

A fresh G4 timing replay uses the unchanged common reference runner:

```sh
../fatras-neutral-hadrons/odd/run-env.sh ../fatras-runtime-model/run.py \
  --mode geant4 --source SOURCE --revision COMMIT --build BUILD \
  --input ../fatras-runtime-model/results/2026-10-15/inputs \
  --output WORK/geant4-refreshed --events 3 --threads 1 \
  --material-map ../fatras-pion-validation/data/2026-10-14/odd-material-beampipe.root \
  --module-dir ../fatras-charged-mesons/data/2026-10-14
```

The PDF retains genuine pinned ACTS main (300b664a3d) and default FTFP_BERT G4,
physically confined to the ODD ID. Main/G4 reference hits are the same first three
ttbar + fixed PU200 events. CPU includes sequencer initialisation, simulation,
CSV output and finalisation; imports and geometry setup are separate. Archived
versus fresh timings are explicitly distinguished. If G4 is rerun for timing,
its CSV hashes must match the archived reference before reusing the hit summary.
The 16 October archive includes a fresh default G4 run and five alternating
Fatras timings because the initial timings varied substantially. `verify.py`
checks the G4 replay as well. The pinned main build was no longer present; its
CPU remains archived and is labelled accordingly.

`reference.cpp` compares electron/positron photon-production rates in C, Si, Cu
and Pb against G4 Seltzer–Berger, above several explicit photon energies. This
kernel comparison does not modify the inclusive G4 simulation. Native Thomas–
Fermi screening is less accurate at low energy/high Z; no fitted detector yield
or new runtime table is introduced. The existing hadronic backend still uses G4.

Photon birth spectra include under/overflow and are diagnostic partitions.
Retained truth is affected by production/transport acceptance. Hit counts remain
inclusive. G4 retains a scattered photon's identity while Fatras creates a
photon descendant, so first-generation Compton truth counts are not directly
comparable. Process labels on hits identify carrier birth, not causal cascade
contributions. Random histories change between physics settings.

Archives contain optional validation output and SHA256 inventories, not runtime
physics inputs. Repeated CSVs are deduplicated into hash manifests. The previous
Compton and G4 archives remain the reference sources.
