# Direct hadronics through the ACTS scheduler

Production implementation: ACTS `ca045e1435` on `feat/fatras-threaded-hadronic`.
Use an MT-enabled Geant4 build and its standard datasets. No custom event library,
Geant4 run manager, or Geant4 event scheduler is required. Registered model graphs
remain toolkit-owned; contexts are reused per OS thread in a stable worker pool.
Do not configure a separate full Geant4 simulation in the same process.

`scan.py` runs `../run.py` sequentially at 1/2/4/8 ACTS workers, reverses run order
on alternate repeats, and compares every event CSV hash. The first full output
corpus is retained; later duplicate CSVs are removed after recording hashes.
`plot.py runs.json --output DIR` produces the PDF and median timing table.

For the recorded scan, five unfiltered ttbar + fixed PU200 inputs were repeated
four times with unique event indices and simulation seeds. These are 20 workload
events, not 20 independent generator events. All 40 CSVs agree across all 12 runs.

| ACTS workers | Wall s / 20 events | CPU s / 20 events | Peak MiB |
| ---: | ---: | ---: | ---: |
| 1 | 27.33 | 27.26 | 611.7 |
| 2 | 14.39 | 28.40 | 707.2 |
| 4 | 7.87 | 30.32 | 869.0 |
| 8 | 6.51 | 44.85 | 1279.8 |

Medians of three runs, Apple M3 Pro / 12 CPU cores / 18 GiB. Full ACTS sequencer,
including worker initialization and CSV I/O; setup imports/geometry are separate.
Four workers give 3.47x wall speedup for 11% more CPU; eight give 4.20x for 65% more
CPU. Memory includes concurrent full events and output buffers, not just models.

A separate matched five-event run succeeds under OS-level denial of access to
the 561 MiB custom table and matches the multithreaded CSVs exactly. The inclusive
result is 15312 secondary pixel hits/event versus replay 15466, paired difference
-154 +/-188 (SEM). Single-worker CPU/event is 1.36 s; archived main 0.79 s and
strict-ID default Geant4 40.06 s. Small diagnostic sample, no physics-closure claim.

Unit tests cover conservation bookkeeping, repeated seeds/handles, caller RNG
isolation and concurrent worker teardown. Address/ThreadSanitizer wrapper builds
pass; installed Geant4 libraries are uninstrumented. The changed Geant4 manager
source compiles. The scheduler test uses the pinned validation bridge, not a
clean rebuild of the complete ACTS project; normal CI remains required.

Results, plots and exact original commands:
`../results/2026-10-15/threaded-integration/`.
