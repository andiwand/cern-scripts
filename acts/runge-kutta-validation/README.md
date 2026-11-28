# Stepper validation in vacuum

Accuracy, Jacobian and cost of `SympyStepper`, `HelixStepper` and
`GenericRungeKuttaStepper` (RK4, DP5, Verner 9; acts#6211) against analytic
and high-order references, without a detector. Note:
`acts/notebook/2026-10-20_runge-kutta-validation.md` in the notes repo.

- `validate.cpp`: the driver; one JSON line per run and checkpoint.
  Studies: `hom`, `inh`, `map`, `mapcap`, `fb`, `jac`, `prof`, `time`,
  `timecov` (with covariance), `mapdebug` (one track in the map, several
  configurations), `debug STEPPER P TOL PATH` (verbose log). An optional
  second argument restricts a scan to one stepper.
- `build.sh SOURCE BUILD OUT`: compiles the driver against an existing build
  tree, without CMake.
- `plot.py DATA OUT`: figures (light and dark) and `summary.json` from
  `DATA/<study>.jsonl`.

```sh
S=~/cern/source/acts/acts/<clone>
B=~/cern/build/acts/acts/<clone>
W=~/cern/data/runge-kutta-validation
./build.sh $S $B $W/validate
for s in hom inh map prof jac fb time; do $W/validate $s > $W/data/$s.jsonl; done
uv run --with numpy --with matplotlib plot.py $W/data $W/plots
```

Run time on an M3 Pro (10 threads): `hom` 18 min, `jac` 22 min, `inh` 5 min,
`map` 2 min. `time` runs one thread and must run alone.

## Method

- Checkpoints at 1 cm to 100 m, two per decade. An actor limits the step to
  the next checkpoint, so at loose tolerance and high momentum the checkpoints
  and not the error control set the number of steps.
- Constant field: the truth is the analytic helix in long double at the path
  length the stepper reached.
- Analytic field: Bz = B0 (1 + a cos(z/L)) s(r), Br = (r/2) B0 a sin(z/L)/L s(r),
  s(r) = 1/(1 + (r/R)^2), B0 = 2 T, a = 0.3, L = 1.5 m, R = 4 m. Reference:
  Verner 9(8) with a fixed 2 mm step, checked by DP5 with 0.25 mm.
- Field map: RZ map of the same field with 20 mm cells. Reference: Verner with
  0.25 mm, checked with 0.5 mm.
- Jacobian: bound-to-free at a fixed path length against central finite
  differences with Richardson extrapolation. The sympy stepper stores the q/p
  column scaled with q/p; the driver converts it with
  `detail::sympy::fromScaledBoundToFree`.
- Field lookups are counted by a wrapper of the field provider. With a
  covariance the Runge-Kutta stepper also computes dB/dr by central
  differences, 6 more lookups per field evaluation.
- 8 directions, theta 50-130 degrees, seed 20261020; plots show the median.
- `HelixStepper` can loop forever on a rejected step whose error estimate is
  within rounding of the tolerance (`cbrt(tol / err)` rounds to 1); the study
  ran it with the scaling capped at 0.9 (see git history for the diff).
