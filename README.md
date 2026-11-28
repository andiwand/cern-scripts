# Script and code collection from my time at CERN

Scripts kept for future use. Finished one-off studies are removed; git
history has them, the conclusions are in the notes repo (`~/cern/notes`).
Data does not live here: runs write to `~/cern/data/<folder>/`.

## Layout

- `acts/`: ACTS development
  - `setup-dev.sh <name>` / `setup-perf.sh <name>` (run from `~/cern`): clone
    and configure a dev (RelWithDebInfo, assertions) or perf (Release, frame
    pointers) tree; `DEPS=spack` (default) or `DEPS=install`.
  - `activate.sh`: environment for a tree built against `~/cern/install`;
    `deps/`: building those dependencies, or LCG 105 from cvmfs.
  - `benchmark/`: interleaved A/B timing of two clones (`ab.sh`,
    `full_chain_perf.py`, `compare_ab.py`) and the navigation benchmark.
  - `navigation-ab/`: propagation fingerprint on the ODD to prove a navigator
    change is a no-op.
  - `runge-kutta-validation/`: stepper accuracy/Jacobian/cost driver.
  - `sympy-dense-material-validation/`: dense-material stepper vs Geant4 slabs.
  - `synthetic-sim-validation/`: fit and validate the synthetic space point
    generator against full simulation.
  - `seed-parameter-resolution/`: seed parameter estimate resolution per
    space point selection.
  - `rz-track-finder/`, `ckf-scattering-tail/`: benchmarks of open ACTS work.
  - `fatras-realism/`: Fatras physics studies, see its README.
- `athena/`: Athena builds, benchmarks and ACTS-in-Athena studies.
- `colliderml/`: Snakemake pipeline of the ColliderML ODD performance plots.
- `notebooks/`: SPOT CPU trend (`spot-graph`), Fatras vs Geant4 material
  tracks, ITk material map plots. Data in `~/cern/data/notebooks`.
- `root/root_diff.py`: branch-by-branch diff of two ROOT files (exit code).
- `generic/`: `activate_and_run.sh ENV CMD...`, `profile.sh PID` (macOS
  `sample` to flame graph), `remove_log_timestamps.sh LOG`.
- `tmux/acts-athena-ci.sh`: tmux session for the acts-athena-ci checkout.

## Setup

Clear notebook output before committing: `.gitattributes` runs the
`strip-notebook-output` filter, configured as in
https://stackoverflow.com/a/73218382.
