# Generic Runge-Kutta stepper validation

Validation of `GenericRungeKuttaStepper` from
https://github.com/acts-project/acts/pull/6211 against `SympyStepper` and
`HelixStepper`, in vacuum and without a detector. Tested source: PR head
cf52fd0537 in the `stepper-state` worktree.

Note: `acts/notebook/2026-10-20_runge-kutta-validation.md` in the notes repo.

## Files

- `validate.cpp`: the driver. It writes one JSON line for each run and
  checkpoint. Studies: `hom`, `inh`, `map`, `mapcap`, `fb`, `jac`, `prof`,
  `time`, `timecov` (with covariance), `mapdebug` (one track in the map,
  several configurations), `debug STEPPER P TOL PATH` (verbose log).
  An optional second argument restricts a scan to one stepper.
- `content.html`: the hand-written body of the report.
- `build.sh`: compiles the driver against an existing build tree, without
  CMake.
- `helix-rejection-fix.diff`: the local fix of `HelixStepper.cpp` for the
  patched helix runs. Without it, a rejected step whose error estimate is
  within rounding of the tolerance repeats forever, because
  `cbrt(tol / err)` rounds to 1.
- `merge.py`: merges the first pass with the reruns.
- `plot.py`: the figures, light and dark, and `summary.json`.
- `make_report.py`: the single-file HTML page.

## Reproduce

```
S=~/cern/source/acts/acts/stepper-state
B=~/cern/build/acts/acts/stepper-state
W=<work dir>
./build.sh $S $B $W/validate
for s in hom inh map prof jac fb time; do $W/validate $s > $W/data/$s.jsonl; done

# patched helix: compile a copy of HelixStepper.cpp with the diff into the
# driver, as build.sh does, then run the helix-only studies and mapcap
cp $S/Core/src/Propagator/HelixStepper.cpp $W/dbg/ && patch $W/dbg/HelixStepper.cpp helix-rejection-fix.diff
# add $W/dbg/HelixStepper.cpp to the clang++ line of build.sh, output validate-hfix
for job in "hom sympy" "jac sympy" "inh helix" "map helix" "jac helix" \
           "prof helix" mapcap "time helix" fb timecov; do
  $W/validate-hfix $job > "$W/fix/${job// /-}.jsonl"
done

python3 merge.py $W $W/merged
uv run --with numpy --with matplotlib plot.py $W/merged $W/plots
uv run --with pillow make_report.py $W/plots content.html report.html
```

Run time on an M3 Pro (10 threads): `hom` 18 min, `jac` 22 min, `inh` 5 min,
`map` 2 min. `time` runs one thread and must run alone.

## Method

- Checkpoints at 1 cm to 100 m, two for each decade. An actor limits the
  step to the next checkpoint. At loose tolerance and high momentum, the
  checkpoints and not the error control set the number of steps.
- Constant field: the truth is the analytic helix in long double, evaluated
  at the path length that the stepper reached. `HelixStepper` agrees with it
  to about 1e-14 mm.
- Analytic field: Bz = B0 (1 + a cos(z/L)) s(r), Br = (r/2) B0 a sin(z/L)/L s(r),
  s(r) = 1/(1 + (r/R)^2), with B0 = 2 T, a = 0.3, L = 1.5 m, R = 4 m. The
  reference is Verner 9(8) with a fixed step of 2 mm. DP5 with a fixed step
  of 0.25 mm checks it.
- Field map: RZ map of the same field with 20 mm cells. The reference is
  Verner with a fixed step of 0.25 mm. Verner with 0.5 mm checks it.
- Jacobian: the bound-to-free jacobian at a fixed path length, compared with
  central finite differences with Richardson extrapolation. The finite
  differences use Verner with a fixed step of 2 mm (analytic field), or the
  analytic helix (constant field). The sympy stepper stores the q/p column
  scaled with q/p; the driver converts it with
  `detail::sympy::fromScaledBoundToFree`.
- Field lookups: a wrapper of the field provider counts them. With a
  covariance, the Runge-Kutta stepper also computes dB/dr with central
  differences, which costs 6 more lookups for each field evaluation.
- 8 directions, theta 50-130 degrees, seed 20261020; plots show the median.
