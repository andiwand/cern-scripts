# Pixel NN inference latency — 2026-11-24

Note: `~/notes/atlas/tsi/notebook/2026-11-24_nn-inference-latency.{md,html}`.
Data/build: `~/source/acts/acts-athena-ci/run/nn-inference/`.
Athena worktree/build: `athena-nn-inference` / `athena-build-nn-inference`.
Base commit: `5b4a3634984fd3062ae816c63c65c95020313681` (NN repairs and SeedOnly policy).

Paths are specific to this local checkout. `fixtures/` preserves byte-identical
copies of the reconstruction configuration, package filter and truth-outcome
extractor used for the runs; scripts now reference these copies. The earlier
SeedOnly outcome file used by `compare_outcomes.py` remains a local reference.

This is a private performance prototype, not a production backend API.
Every backend evaluates the deployed `nn-01-01-01` model function; no retraining,
quantization, approximate-angle cache, or tracking cut changes. Strips and LRT
remain as in the preceding primary-only post-calibration study.

## Reproduce

1. In an isolated Python environment with `onnx`, `numpy` and `markdown`, run
   `export_models.py`. It writes the ONNX reference, a batch-one graph, LWTNN
   JSON and binary weights. Do not run that Python environment with Athena's
   `PYTHONHOME` or `PYTHONPATH` set.
2. Source `env.sh` with `errexit` temporarily disabled for `asetup`, then run
   `generate_sofie.py`. ROOT 6.40.02 needs the two recorded declaration/syntax
   repairs and a stable sigmoid to avoid exponential overflow. A separate
   generated-header variant replaces batch-one GEMM by GEMV.
3. Run `build_backends.sh`, `integrate.py` once in a clean worktree, and
   `build_athena.sh`. All backend code uses release gcc15, `-O2 -DNDEBUG`, no
   fast-math; only direct AVX2 kernels carry an explicit CPU target. SOFIE uses
   its allocation-free generated `doInfer` entry point and release OpenBLAS.
4. Run `run.sh OUTPUT original 5 INPUT_RDO` with `NN_STUDY_CAPTURE` pointing to
   an unused binary output path. Records are 67 float32 inputs. This diagnostic
   is excluded from performance results.
5. `dump_outputs.sh INPUTS OUTPUT 100000` and `validate.py OUTPUT` compare all
   four networks, not just the selected position network. Validation tolerance
   is diagnostic; reconstruction output is checked independently. The executable
   rejects invalid/divide-by-zero/overflow flags during output validation. Both output
   validation and isolated timing source `athena_preload.sh` to match Athena's
   tcmalloc and Intel math libraries. Unset `LD_PRELOAD` for the analysis venv.
6. Run `vectorization.py --standalone`, then `blocked.py --standalone`, without
   other study jobs running. They build, validate and benchmark the compiler
   targets, individual layers and additional SSE register-blocked backend; the
   latter also runs its 100-event reconstruction check. They retain their own libraries
   and executables: the benchmark has DT_RPATH, so LD_LIBRARY_PATH alone cannot
   select a different library. The Athena plugin instead selects it at runtime.
7. `cycles.py isolated --cycles 3 --cpu 16`: two-network latency on 30,000
   evenly spaced real inputs, three inner repetitions per process, alternating
   backend order across three cycles. Compare warm inference and a 1 MiB cache
   sweep before each call, excluding the sweep itself from timing. Pressure
   results include per-call timer overhead; warm results time the whole loop.
8. `cycles.py integrated --cycles 3 --events 20 --cpu 16`: sequential serial
   Athena runs, first event excluded by PerfMon, physics extraction after each.
   `cycles.py physics --events 100`: independent 100-event, four-thread physics
   comparisons (three jobs concurrently), excluded from timing. Do not run these
   alongside either isolated or integrated timing.
9. `summarize.py`, `kernel_summary.py`, `plot.py`, `kernel_plot.py` in the release
   environment, then `count_loc.py`, `update_note.py` and `render_note.py`
   in the isolated Python environment. `provenance.py` records code/model hashes
   and compiler/BLAS settings; source `athena_preload.sh` before it as well.
   `finalize_report.sh` performs these collection/rendering steps together;
   `audit.py` checks the 40 backend reconstruction jobs, six raw/NN reference
   jobs and 60 isolated processes.
   Copy compact results/plots, not trained weights,
   into the note's companion directory.

`count_loc.py` adds the local implementation-size comparison before rendering
(also called by `finalize_report.sh`). It attributes frozen source ranges to
each backend, counting shared inference helpers once per backend and conversion
code alongside C++. SOFIE-generated headers are separate. It excludes common
benchmark/build/test machinery and library internals; hashes guard the line
ranges against source changes. Counts are physical lines, not complexity or
production-diff estimates. The audit is saved as `loc-counts.json` with the note.

All jobs keep AODs, logs, library hashes and outcome records. Output directories
are never silently overwritten. `v1/` retains preliminary scalar-direct timing
exploration; final comparisons use the vectorized implementation and must not
mix those data. `system-libraries/` retains the initial standalone runs without
Athena's preloads; reported comparisons use the matched libraries. Background
host load is recorded and limits close comparisons. `v2-before-stable-sigmoid/`
retains runs before removing sigmoid overflow. `profile.sh` runs separate
five-event diagnostics with per-calibration stage timers; these do not enter
the performance table. Stages are input preparation, multiplicity inference,
position inference, then subcluster selection and cleanup.

`uncalibrated_reference.py` adds three serial raw/blocked-SSE pairs using the
same SeedOnly build, cuts and events, after all backend runs and their first
report refresh. `run_reference.sh` changes only the primary calibration mode;
`summarize_uncalibrated.py` verifies the logged tool configuration and computes
the remaining CPU overhead against raw cluster positions/errors. Run
`finalize_report.sh` again after this additional reference finishes.

Two late backend runs and the initial raw reference encountered load 30–40 and
are retained in `high-load-runs/`, excluded from accepted timing. The exclusions
are recorded in `timing-exclusions.json`. `recover_quiet.py` first runs the raw
reference, then replaces the two backend runs. `wait_quiet.py` requires a sustained
lower-load window; `run_quiet_job.py` monitors load throughout reconstruction and
retains/retries runs reaching 20. No other users' jobs are modified.

`vectorization.py` adds a separate `-march=x86-64-v2` shared library, without
replacing the main study binaries. After the first reconstruction cycle, the
physics driver waits while this check builds, validates and alternates the
SSE2 and x86-64-v2 builds. `kernels.cxx` then separates dense-layer and activation
costs for the multiplicity/pos1 pair, using 512 real inputs. Its blocked SSE
kernel motivated the additional `direct_blocked` backend. `blocked.py` validates
it, runs 100-event physics, and measures it alongside direct SSE and SOFIE/GEMV.
It is then included in the remaining serial reconstruction cycles. Per-layer
timings have a different cache history from whole-network timings.

The orchestration uses completion barriers: physics waits for
`vectorization/complete.txt`; later serial cycles wait for
`blocked/isolated-complete.txt`. These markers record completed checks, not user
approvals. `finish_study.py` resumes the remaining cycles after a launch-only
failure; it is specific to this run. All successful results are retained.

SOFIE serializes 17 subnormal parameters in the pos1 probability head as zero.
That head feeds a one-element softmax and is identically one for finite inputs;
positions, precisions and all other parameters are unaffected. The compact audit
is in the note; raw values remain only in the working data.
