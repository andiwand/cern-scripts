# intersection count: Gen1 vs Gen3

Counts every `Surface::intersect` call per track on an ITk-like toy built the
Gen1 way and several Gen3 ways, with the Athena recipes. Written for
`~/cern/notes/acts/notebook/2026-10-19_gen3-intersection-count.md`.

Files:

- `core-intersect-counter.patch`: the counter. Adds `g_intersectCount[10]` and
  `g_intersectPhase` to `Core/src/Surfaces/Surface.cpp`, increments in the six
  `intersect` implementations, phase guards in `Layer::compatibleSurfaces` (5),
  `TrackingVolume::compatibleLayers` (4) and `compatibleBoundaries` (6), and in
  `NavigationStream::initialize` (7 portal, 8 surface, 9 other) and `update` (9).
  Phases 0-3 come from the test's forwarding navigator: 0 stepper, 1 nextTarget
  outside the guards, 2 initialize, 3 handleSurfaceReached.
- `IntersectionCountTests.cpp`: the toy and the drive. Drop into
  `Tests/UnitTests/Core/Propagator/` and add
  `add_unittest(IntersectionCount IntersectionCountTests.cpp)`.
- `analyze.py`: summary tables and `<out>.summary.json`. Run with `python3 -I`.

Environment:

- `ACTS_ICOUNT_OUT` csv path (default `intersection-count.csv`), also writes
  `<out>.modules.csv` with one line per module.
- `ACTS_ICOUNT_TRACKS` number of tracks (default 2000).
- `ACTS_ICOUNT_VARIANTS` comma list of
  `gen1,gen1-2ap,gen3-abut,gen3-sandwich,gen3-tryall,gen3-window,gen3-floor1`.
- `ACTS_ICOUNT_BFIELD` solenoid field in tesla (default 2).

Built against ACTS main @ `c8cafbbb95` on 19.10.2026. The dev1 build tree
refused to re-run CMake (Homebrew Python moved), so the test was compiled with
the compile and link lines of `ActsUnitTestNavigator` from
`ninja -t commands`, and the patched Core objects the same way.
