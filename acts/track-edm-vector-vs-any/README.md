# Track EDM: vector vs Any, 31.10.2026

Companion note: `~/cern/notes/acts/notebook/2026-10-31_track-edm-vector-vs-any.md`
and its static HTML page. Raw results and logs belong in the note's companion folder.

This is a CKF boundary experiment. The vector branch also replaces erased access
inside the Kalman updater, gain-matrix smoother and MBF smoother. It does not claim
to remove the generic EDM from all ACTS interfaces.

Local ACTS commits:

- main: `b965a0d025`
- vector: `5b64772761`, branch `experiment/track-edm-vector-2026-10-31`
- Any: `5fce885bea`, branch `experiment/track-edm-any-2026-10-31`

The default experiment directory is `/private/tmp/acts-edm-2026-10-31`.
Set `ACTS_EDM_EXPERIMENT_ROOT` to relocate it. It contains worktrees `main`, `vector`,
`any`, build directories `build-main`, `build-vector`, `build-any`, and `results`.
Copy these scripts into that directory before running them. The setup uses the
existing local Spack view and Python environment under `~/cern/source/acts/ci-dependencies`.

## Build

On a fresh experiment directory, create worktrees from the recorded revisions
before configuring. These branches are local and are not available from the remote.
For example, from the ACTS repository, using a new `ACTS_EDM_EXPERIMENT_ROOT`:

```sh
git worktree add --detach "$ACTS_EDM_EXPERIMENT_ROOT/main" b965a0d025
git worktree add --detach "$ACTS_EDM_EXPERIMENT_ROOT/vector" 5b64772761
git worktree add --detach "$ACTS_EDM_EXPERIMENT_ROOT/any" 5fce885bea
```

`cache.cmake` records the common release configuration. It uses locally available
third-party sources, including the exact ODD v6.0.3 checkout under the dev3 build.
The `prebuilt` directory contains the unchanged generated code from the existing
dev2 build, copied according to `codegen/manifest.json`; checksums are recorded in
`provenance.json`. Recreate it with `prepare_codegen.py`.

```sh
export ACTS_EDM_EXPERIMENT_ROOT=/private/tmp/acts-edm-2026-10-31
python3 prepare_codegen.py
export ROOTSYS=$(~/cern/source/acts/ci-dependencies/.spack-env/view/bin/root-config --prefix)
export DYLD_LIBRARY_PATH="$ROOTSYS/lib/root:$HOME/cern/source/acts/ci-dependencies/.spack-env/view/lib"
for variant in main vector any; do
  cmake -S "$ACTS_EDM_EXPERIMENT_ROOT/$variant" \
    -B "$ACTS_EDM_EXPERIMENT_ROOT/build-$variant" -G Ninja -C cache.cmake
  cmake --build "$ACTS_EDM_EXPERIMENT_ROOT/build-$variant" -j 4
  bash test.sh "$variant"
done
```

For a relocated experiment, also adjust the prebuilt path in `cache.cmake`.
No source changes are required to work around ROOT setup: explicitly setting its
library directory avoids `thisroot.sh` shell detection under restricted process access.

## Validation

Run separate writer-enabled jobs before timing:

```sh
for variant in main vector any; do
  CKF_EVENTS=4 CKF_RUNS=1 CKF_RECORD_MATERIAL_STATES=0 EDM_VALIDATE=1 \
    bash run-one.sh "$variant" "$ACTS_EDM_EXPERIMENT_ROOT/results/validation/muons/$variant"
  CKF_EVENTS=2 CKF_RUNS=1 CKF_RECORD_MATERIAL_STATES=0 CKF_PILEUP=200 EDM_VALIDATE=1 \
    bash run-one.sh "$variant" "$ACTS_EDM_EXPERIMENT_ROOT/results/validation/ttbar-pu200/$variant" --ttbar
done
python compare_outputs.py "$ACTS_EDM_EXPERIMENT_ROOT/results/validation/muons"
python compare_outputs.py "$ACTS_EDM_EXPERIMENT_ROOT/results/validation/ttbar-pu200"
```

Use the Spack Python virtualenv, which supplies NumPy, pandas, uproot and awkward.
CSV files are compared byte-for-byte. ROOT comparison checks tree/branch structure
and all packed buffers; floating-point NaNs in identical positions compare equal.
The report records exact equality separately from a 64-machine-epsilon fallback.

## Measurements

With all builds and tests stopped, run `python benchmark.py`. It runs all six
variant orderings serially, for the muon and ttbar+200-pileup configurations.
`analyze_timings.py` discards the first round of each process, then reports each
process median and ratios paired by block. It does not count repeated events as
independent observations. `compile_benchmark.py` separately measures complete
compilation of two CKF application translation units, three times per variant,
without ccache. Never run it concurrently with runtime benchmarks.

Run `python analyze_compile.py` for the compiler summary and
`python measure_sizes.py` for handle/wrapper sizes. With matplotlib and NumPy
available, `python render_report.py /path/to/2026-10-31_track-edm-vector-vs-any.md`
regenerates the plot and self-contained static HTML beside the note. The note's
companion folder must already contain `timing-summary.json`.

`full_chain_perf.py` is the existing `acts/benchmark/ckf/full_chain_perf.py` plus
optional validation writers. `workflow.patch` and `workflow.json` in the note's
results record the original script hash and changes. Timed runs have no writers.
