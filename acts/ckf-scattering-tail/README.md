# CKF scattering tail

Benchmark of the CKF scattering tail modes on ODD ttbar with <μ> = 200.
The code is on the acts branch `proto-ckf-scattering-tail` (andiwand/acts).
The notes are in `cern-notes/acts/notebook/2026-10-23_ckf-scattering-tail-*`.

## Scripts

- `run.py`: the ODD chain (`full_chain_odd.py --ttbar`). `--mode` sets `ScatteringTailMode` (0 none, 1 retry, 2 retry + branch, 3 select only, 4 mixture). `--chi2` sets the measurement and outlier cuts. `--record-scatters` writes the Fatras scatters above 3× Highland.
- `run_all.sh OUT [N]`: the physics runs of the six main configurations.
- `run_scan.sh RUNS TIMING`: the intermediate baseline cuts 25/50 and 35/70, physics and timing.
- `timing.sh OUT [N] [ROUNDS]`: single-thread CKF timing, with the configurations interleaved.
- `fitmix.py`: the two-Gaussian fit to the Fatras semi-Gaussian model. It prints the table in `detail/ScatteringTail.hpp`.
- `analyze.py RUNS --timing T --pdf P --json J --export E`: efficiency, fakes, pulls, p-values and CPU.
- `make_report.py export.json content.html out.html`: the interactive report. `content.html` holds the prose (force-added, because `*.html` is ignored).
- `compare_stages.py`: per-event checksums of each stage between repeated runs.

## Traps

- The Pythia8 pile-up generator keeps state across events. With more than 1 thread, events 9 and 127 of the 200 differ between runs. Use `compare_stages.py` to find such events.
- The tail flag comes from the scatter CSVs of the first run only. All runs must use the same events.
- The dev3 build has forced assertions. Only the relative CPU numbers are meaningful.
