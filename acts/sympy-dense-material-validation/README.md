# Sympy dense-material / Geant4 validation

Note: `acts/notebook/2026-10-31_sympy-dense-material-geant4.md` in
https://github.com/andiwand/cern-notes (local `~/cern/notes`).

The note's companion directory contains results, figures, patches and logs.
No historical simulation files are modified.

## Files

- `audit.cpp`: independent scalar energy integration, actual Sympy stepping,
  q/p finite differences, screen covariance, and initialized Geant4 stopping powers.
- `CMakeLists.txt`: baseline executable against the existing ACTS library;
  patched executable and tests compile the changed sources directly.
- `reanalyse.py`: reanalyse the saved thesis samples at matched initial momenta.
- `legacy_common.py`: frozen pre-fix fitter used only for the before/after study.
- `test_comparison.py`: regression checks for the corrected thesis helpers.
- `make_report.py`: plots, dated Markdown and self-contained static HTML.

## Reproduce locally

Dependencies are the ACTS ci-dependencies view and Geant4 11.3.2. The
generator needs Sympy/NumPy; the analysis needs NumPy, SciPy >= 1.15,
uproot, awkward, pandas, Matplotlib and markdown-it-py. The local
`~/cern/venv/bin/python` has the generator packages and
`~/cern/source/acts/ci-dependencies/.python-env/bin/python` has the analysis
packages. The CMake defaults point at the dev3 worktree/build.

```sh
study=$HOME/cern/scripts/acts/sympy-dense-material-validation
source_dir=$HOME/cern/source/acts/acts/dev3
work=/tmp/sympy-dense-validation
mkdir -p "$work/generated/codegen" "$work/patched-results"
PYTHONPATH="$source_dir/codegen/src" "$HOME/cern/venv/bin/python" \
  "$source_dir/Core/src/Propagator/generate_sympy_stepper.py" \
  "$work/generated/codegen/sympy_stepper_math.hpp"
cmake -S "$study" -B "$work/build" -G Ninja \
  -DPATCHED_CODEGEN="$work/generated"
cmake --build "$work/build" -j 4
"$work/build/test-unit" --report_level=short
"$work/build/test-material" --report_level=short
"$work/build/test-integration" --report_level=short
source "$HOME/cern/data/geant4/11.3/env.sh"
"$work/build/audit-patched" "$work/patched-results"
```

The baseline `audit` target is meaningful only while the linked ACTS build
still contains the pre-fix code at `5bbaa63f5d332b24627a44eb76f23bb6f2e53f67`.
Once rebuilt, use the archived baseline CSVs rather than labelling a second
patched execution as baseline. Numerical reference integration is independent
of the Sympy q/p equations. The follow-up in `followup/` fixes momentum derivatives crossing the
discontinuous loss-model boundaries and isolates the remaining Geant4
scattering, production-cut and step-size differences. See the appended note.

`reanalyse.py` currently uses the original thesis data paths. It writes its
figures/CSV beside the script; run a copy in a scratch directory to keep the
scripts checkout clean. The frozen fitter preserves the historical curve
after installing the thesis fixes. `make_report.py DATA OUTPUT` expects the
evidence filenames in the archived companion directory and writes the dated
note and assets under OUTPUT. Its HTML embeds the two figures and needs no
JavaScript or network connection.

```sh
analysis_python=$HOME/cern/source/acts/ci-dependencies/.python-env/bin/python
"$analysis_python" "$study/test_comparison.py"
```

## Follow-up

`followup/` contains the 6.45-million-primary controlled Geant4 comparison,
threshold-Jacobian validation, and report appendix. Its standalone CMake
harness reproduces all four deterministic numerical tables exactly.

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
