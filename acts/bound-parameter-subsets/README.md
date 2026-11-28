# Bound parameter subsets: Kalman kernel micro-benchmark, 14.11.2026

Companion note: `~/cern/notes/acts/notebook/2026-11-14_bound-parameter-subsets.md`.
Results live in the note's companion folder `2026-11-14_bound-parameter-subsets/`.

`bench.cpp` times the Kalman algebra in fixed-size Eigen (double) for 6 and 5
parameters, with and without use of the known structure, and with runtime
sizes. It is not ACTS code: the kernels copy the algebra of
`CovarianceEngine.cpp`, `GainMatrixUpdaterImpl.hpp`, `GainMatrixSmoother.cpp`
and `MbfSmootherImpl.hpp`.

## Run

```sh
EIGEN=~/cern/source/acts/ci-dependencies/.spack-env/._view/<hash>/include/eigen3
clang++ -std=c++20 -O3 -DNDEBUG -I$EIGEN bench.cpp -o bench
./bench > kernels.json
```

- stdout: JSON, ns per call, median of 31 repetitions over 1024 random inputs.
- stderr: self check (structured == dense, 5x5 == leading block of 6x6).
