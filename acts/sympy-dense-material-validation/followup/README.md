# Remaining Sympy/Geant4 material differences, 2026-10-31

Appendix in `acts/notebook/2026-10-31_sympy-dense-material-geant4.md` and its
static HTML in https://github.com/andiwand/cern-notes. Numerical outputs and
logs: `acts/notebook/2026-10-31_sympy-dense-material-residuals/` there.

This follows the initial validation in the parent directory. The ACTS patch
includes stopping-power gradients, adaptive loss error control, and threshold
saltation. Use the complete archived patch or the current modified dev3 tree.

## Reproduction

```sh
study=$HOME/cern/scripts/acts/sympy-dense-material-validation/followup
source_dir=$HOME/cern/source/acts/acts/dev3
work=/tmp/sympy-material-followup
mkdir -p "$work/generated/codegen"
PYTHONPATH="$source_dir/codegen/src" "$HOME/cern/venv/bin/python" \
  "$source_dir/Core/src/Propagator/generate_sympy_stepper.py" \
  "$work/generated/codegen/sympy_stepper_math.hpp"
cmake -S "$study" -B "$work/build" -G Ninja -DPATCHED_CODEGEN="$work/generated"
cmake --build "$work/build" -j 4
source "$HOME/cern/data/geant4/11.3/env.sh"
"$work/build/acts" "$work"
"$work/build/rates" "$work"
python3 "$study/run_samples.py" "$work"
analysis_python=$HOME/cern/source/acts/ci-dependencies/.python-env/bin/python
MPLCONFIGDIR="$work/mpl" "$analysis_python" "$study/analyse.py" "$work"
```

`run_samples.py` launches four serial Geant4 jobs concurrently; each uses
150,000 events and records its own seed, process flags, and material constants.
Dependencies and version: ACTS base 5bbaa63f with archived patch, Geant4 11.3.2,
Eigen; Python NumPy, SciPy, pandas, uproot, awkward, Matplotlib, markdown-it-py.
The fitting helper is a snapshot of the corrected thesis helper at 2d1f78b6.

The report generator needs the earlier `threshold-before.csv` as
`$work/before-threshold-fix/threshold.csv` and the unit/material/integration
logs from the parent harness, plus cut-check logs. Run `report.py "$work"` to
write a Markdown/embedded-image HTML appendix and its assets under
`$work/publish`. It does not edit an existing dated note automatically.

## Driver and binary format

`scattering MATERIAL P_GEV LENGTH_MM STEP_MM MODE EVENTS SEED CUT_MM OUTPUT`

Each event is 12 native little-endian doubles, one row even for a failed
screen crossing. Columns: status (0 none, 1 downstream slab exit, 2 screen),
exit y,z [mm], exit direction y,z, exit momentum [MeV], screen y,z [mm],
screen direction y,z, actual material path [mm], screen momentum [MeV].
NaN marks unavailable values. Direction columns are components, not angles;
the deflections here are small. Read with `np.fromfile(path).reshape(-1,12)`.

Modes are described in the note. Default-cut `constant` omits above-cut
ionisation recoil; compare it only as a diagnostic. `constant_uncut` raises
the range cut, but the converted energy cut must be inspected. `constant_all` explicitly sets the electron energy cut to 10^9 MeV after
initializing the material couples, updates the table and rebuilds physics.
This covers all tested energy transfers. No mode names
alone establish that the electron-scattering coverage is complete. Every
process list and actual electron energy cut is printed in the log.

`acts.cpp` compares the actual material accumulator, mean-loss Sympy
trajectory, analytic endpoint-flow Jacobian, and finite differences.
`rates.cpp` compares initialized unrestricted stopping powers, substitutes
Geant4 density/I in the ACTS Bethe expression, and separately integrates a
G4-ionisation momentum history with the ACTS scattering accumulator.
`analyse.py` archives fitted core widths, block errors, quantile widths, RMS,
acceptance and path information. It intentionally skips incomplete outputs.

The 43 production samples occupy about 619 MB. Keep them in a
scratch output directory; only summaries, histograms, logs and plots belong
in the notes repository. The original before-threshold-fix table must be
kept distinct from output produced by the fixed implementation.

## Source after PR split

PR https://github.com/acts-project/acts/pull/6431 now contains only the
material derivatives. To reproduce the full stepper study, use the archived
complete ACTS patch or local branch `preserve-sympy-dense-stepper-fixes` at
`fe95eec2d9`. The current dev3 PR branch alone does not contain the dense
stepper fixes.

## Published draft stack

The complete study implementation is now published on upstream branch
`fix-sympy-dense-jacobian-transport` at `aeefb00ec9`, draft PR
https://github.com/acts-project/acts/pull/6433. Its parent error-control layer
is https://github.com/acts-project/acts/pull/6432 (also draft). The full tree
matches `fe95eec2d9`; use it or the archived complete patch to reproduce the
study. The material-only PR remains #6431.
