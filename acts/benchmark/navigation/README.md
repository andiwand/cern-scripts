# navigation benchmark

Drop `NavigationBenchmark.cpp` into `Tests/Benchmarks/` and add

    add_benchmark(Navigation NavigationBenchmark.cpp)

to its `CMakeLists.txt`. Needs `-DACTS_BUILD_BENCHMARKS=ON`.

Drives the navigator over `CylindricalTrackingGeometry`, which has real surface
arrays so the grid lookup is exercised. Two measurements: a straight-line
propagation through the whole geometry, and `Layer::compatibleSurfaces` on its
own. Per-run precision ~0.2%, which the full chain cannot reach — its floor is
~1.5% on the CKF and navigation is a sixth of that, so anything under ~10% of
navigation is invisible there.

`ACTS_BENCH_GEN3=1` builds the Gen3 geometry instead, for a Gen1/Gen3
comparison.

It prints the number of successful propagations and the step count next to the
timing, and that is not decoration: without the `EndOfWorldReached` aborter every
propagation ran to the step limit and returned an error, and the benchmark
produced a confident, entirely bogus -10%.

See `~/cern/notes/acts/notebook/2026-08-21_navigation-operation-budget.md`.
