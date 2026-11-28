# Dense material: Sympy stepper against Geant4

Harness comparing the dense-material Sympy stepper (energy loss, stopping-power
gradients, threshold saltation, scattering) with Geant4 slab transport. Notes:
`acts/notebook/2026-10-31_sympy-dense-material-geant4.md` and its
`-residuals` companion in the notes repo. The ACTS side is the draft stack
acts#6431 (material derivatives), #6432 (error control) and #6433 (dense
Jacobian transport); the full tree is local branch
`preserve-sympy-dense-stepper-fixes`.

- `scattering.cpp`: standalone Geant4 slab driver,
  `scattering MATERIAL P_GEV LENGTH_MM STEP_MM MODE EVENTS SEED CUT_MM OUTPUT`.
  Each event is 12 little-endian doubles: status (0 none, 1 downstream slab
  exit, 2 screen), exit y,z [mm], exit direction y,z, exit momentum [MeV],
  screen y,z [mm], screen direction y,z, material path [mm], screen momentum
  [MeV]; NaN where unavailable. Read with `np.fromfile(p).reshape(-1, 12)`.
  Modes: `constant`, `ion`, `full`, `msc`, `ioncsda`, `constant_uncut`
  (raised range cut), `constant_all` (electron energy cut 1e9 MeV after
  initialisation). Every process list and actual cut is printed in the log.
- `acts.cpp`: ACTS material accumulator, mean-loss Sympy trajectory, analytic
  endpoint-flow Jacobian and finite differences.
- `rates.cpp`: Geant4 unrestricted stopping powers against the ACTS Bethe
  expression, and a G4-ionisation momentum history through the ACTS
  scattering accumulator.
- `run_samples.py WORK`: the 43 Geant4 samples (150k events each, four in
  parallel, ~620 MB) plus cut checks, from `WORK/build/scattering`.
- `analyse.py WORK`: core widths, block errors, quantile widths, RMS,
  acceptance and path; skips incomplete outputs. `comparison_common.py` holds
  the fit helpers (snapshot of the thesis helper).

## Run

Needs the ACTS ci-dependencies view, Geant4 11.3 and an ACTS tree with the
fixes (CMake cache `ACTS_SOURCE`, `ACTS_BUILD`, default dev3).

```sh
here=~/cern/scripts/acts/sympy-dense-material-validation
src=~/cern/source/acts/acts/dev3
work=~/cern/data/sympy-dense-material-validation
mkdir -p "$work/generated/codegen"
PYTHONPATH="$src/codegen/src" ~/cern/venv/bin/python \
  "$src/Core/src/Propagator/generate_sympy_stepper.py" \
  "$work/generated/codegen/sympy_stepper_math.hpp"
cmake -S "$here" -B "$work/build" -G Ninja -DPATCHED_CODEGEN="$work/generated"
cmake --build "$work/build" -j 4
source ~/cern/data/geant4/11.3/env.sh
"$work/build/acts" "$work"
"$work/build/rates" "$work"
python3 "$here/run_samples.py" "$work"
MPLCONFIGDIR="$work/mpl" ~/cern/source/acts/ci-dependencies/.python-env/bin/python \
  "$here/analyse.py" "$work"
```
