# Fatras realism tools

Tools to validate ACTS Fatras against Geant4: standalone model references,
matched-material slabs, synthetic scans, and inclusive ODD simulations with
their accounting and plots. Everything is in `common/`; the commands below
run from there. Each script's `--help` documents its options. Study
conclusions live in the notes repository, not here.

## Setup

- `paths.py` holds the defaults; override with `ACTS_VALIDATION_SOURCE`,
  `ACTS_VALIDATION_BUILD` (needs `compile_commands.json`), `GEANT4_LIB`,
  `FATRAS_DATA` (default `~/cern/data/fatras-realism`).
- `run-env.sh SCRIPT ARGS` runs Python with the ACTS build and Geant4 datasets
  (`GEANT4_INSTALL`, `ACTS_PYTHON`). `inclusive_run.py` calls it itself.
- Write outputs to `~/cern/data/fatras-realism/<topic>/...`, not into this repo.
- Default inputs read from `FATRAS_DATA`: generator inputs
  `fatras-runtime-model/results/2026-10-15/inputs`, repaired material map
  `fatras-pion-validation/data/2026-10-14/odd-material-beampipe.root`,
  `id_world.so` in `fatras-charged-mesons/data/2026-10-14`.

## Inclusive ODD comparison (no cuts)

```sh
run-env.sh odd_run.py generate --output GEN --events 5     # Pythia8 ttbar + PU200
python3 prepare_inputs.py GEN INPUTS                       # births inside the ID only
python3 inclusive_run.py --mode main --source MAIN_SRC --build MAIN_BUILD --input INPUTS --output RUNS/main
python3 inclusive_run.py --mode changed --table TABLE --input INPUTS --output RUNS/fatras
python3 inclusive_run.py --mode geant4 --input INPUTS --output RUNS/geant4
python3 inclusive_summary.py --run "ACTS main" RUNS/main --run Fatras RUNS/fatras \
  --run "Geant4 ID" RUNS/geant4 --output RUNS/summary
python3 inclusive_accounting.py summary --run Fatras RUNS/fatras --run Geant4 RUNS/geant4 --output RUNS/acc.json
```

`--mode live` uses the on-demand Geant4 hadronic backend instead of a table.
`inclusive_accounting.py revisits|carriers|observer` add repeated-visit,
carrier and Geant4-creator breakdowns (`--observer-module` on the Geant4 run).

## Iterating on Fatras physics without rebuilding ACTS

```sh
python3 bridge_build.py --source SRC --work W        # W/bridge, W/pruned-build
python3 inclusive_run.py --mode live --source SRC --module-dir W/pruned-build --soft --output W/current
python3 inclusive_run.py --mode live --source SRC --module-dir W/bridge --threads 4 --output W/standard-4
python3 repeat_inclusive.py --work W --source SRC --variant control=OLD/pruned-build \
  --variant current=W/pruned-build --standard W/bridge   # alternating CPU repeats
python3 worker_scan.py run --output W/scaling --source SRC --module-dir W/bridge
```

The bridge links against the frozen `d25514208b` Examples ABI of the local
build. Options: `--ion-cut`, `--photon-cut`, `--legacy-decays`,
`--em none|compton|radiation`, `--navigator none|cache`. Runtime switches on
`inclusive_run.py`: `--photon-cut-MeV`, `--disable-compton`, `--brems-cut-MeV`
(`inf` = legacy radiation), `--disable-annihilation`, `--navigation-*`,
`--transport-only` (with `transport_probes.py` inputs). The bounded navigator
is single-worker and fixed-geometry only.

## Model references and slabs

```sh
run-env.sh build_reference.py compton --work W --run   # ionisation|compton|radiation|annihilation|decay
python3 build_reference.py slab --work W
run-env.sh slab_scan.py run --work W --preset standard
run-env.sh slab_scan.py run --work W --folder e20 --pdg 11 --energy 20 --slices 1 1000 --profile common full
python3 slab_scan.py collect --work W                  # W/analysis.json
```

## Matched ODD comparison (filtered inputs)

```sh
python3 prepare_inputs.py GEN INPUTS --matched         # p >= 100 MeV, charged pT >= 50 MeV
run-env.sh odd_run.py geant4 --input INPUTS --output R/geant4
run-env.sh odd_run.py fatras-em --input INPUTS --output R/em
run-env.sh odd_run.py fatras --input INPUTS --table TABLE --reference-material --output R/fatras
python3 odd_compare.py --geant4 R/geant4 --em R/em --fatras R/fatras --output R/plots
```

`material_coverage.py MAP OUT --table TABLE` audits table/material matching;
`repair_beampipe_map.py` fills the empty ODD beam-pipe map bins.

## Hadronic interaction tables (`tables/`)

```sh
cmake -S tables -B GEN -DGeant4_DIR=...; cmake --build GEN
python3 tables/generate.py --build GEN --data-root G4DATA --projectiles 2112 130 --output t.table
python3 tables/calibrate.py --build GEN --data-root G4DATA --name kaons --projectiles 321 -321 --seed 20442 --output D
python3 tables/compare.py D/silicon-kaons.table D/silicon-kaons-midpoints.table --output cmp.json
python3 tables/plot_calibration.py midpoint=cmp.json --output calibration.pdf
python3 tables/combine.py A.table B.table --output all.table          # disjoint channels
python3 tables/extend_table.py BASE.table HIGH.table --output ext.table
python3 acts_compile.py --output check tables/check.cpp && ./check all.table
```

## Synthetic scans and other builds

`fatras_scan.py --variant em|hadronic|decays --output DIR` compiles
`scan/<variant>.cpp` against the build and scans p/pT cuts (four-layer
silicon, no Geant4). `acts_compile.py` compiles any standalone file with
the build's flags, e.g. the Geant4 plugins:

```sh
python3 acts_compile.py --template geant4-plugin --shared --acts --geant4 run geometry global --output id_world.so g4/id-world.cpp
python3 acts_compile.py --template geant4-plugin --shared --acts --geant4 --output gap_observer.so g4/observer.cpp
python3 acts_compile.py -I bridge --output cache-test bridge/cache-test.cpp   # navigator index test
```
