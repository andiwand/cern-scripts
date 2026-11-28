# ACTS benchmarks

## Full chain A/B timing

`full_chain_perf.py` runs the ODD chain single-threaded in rounds and writes
the per-event time of one stage to `OUT/times.csv`. `--stage` picks what is
reconstructed and timed: `ckf` (default), `seeding`, `kf`, `gsf`. Input is a
particle gun, `--ttbar` (Pythia8, `--pileup`, default 200) or `--geant4 DIR`.
`--write` (CKF) writes track summaries and states for comparing outputs
between builds; leave it off for timing.

`ab.sh` interleaves two clones round by round, so drifts of the machine hit
both sides equally:

```sh
# clones ~/cern/source/acts/acts/{perf1,perf2}, builds of the same name
./ab.sh perf1 perf2                                 # CKF, ttbar, 8 x 3 events
./ab.sh perf1 perf2 --stage kf                      # Kalman fitter, muon gun
ROUNDS=6 OUT=/tmp/ab ./ab.sh perf1 perf2 --stage seeding --ttbar
./compare_ab.py ~/cern/data/benchmark/ab_perf1_perf2
```

Output goes to `~/cern/data/benchmark/ab_<BASE>_<CHANGED>` unless `OUT` is set.
A single side runs directly in an activated environment:
`./full_chain_perf.py OUT --stage gsf`.

## Navigation micro-benchmark

`navigation/`: drop-in benchmark for `Tests/Benchmarks/`, see its README.
