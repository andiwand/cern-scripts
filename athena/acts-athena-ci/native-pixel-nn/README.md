# Native pixel NN integration

Candidate branch: `acts-native-pixel-nn` in
`~/source/acts/acts-athena-ci/athena-native-pixel-nn`, based on Athena main
`41da040949efeca5de0e5adbd84054868a5165c6` (2026-11-24).
Build: `../athena-build-native-pixel-nn`; results: `../run/native-pixel-nn`.

- `build.sh`, `tests.sh`: pinned Nov 23 gcc15 nightly; three-package overlay;
  no ACTS override, GPU or benchmark library in reconstruction.
  Plain `build.sh` includes a runtime-dispatched AVX2/FMA kernel alongside the
  portable baseline. `build.sh -DSICLUSTERIZATION_NATIVE_NN_AVX2=OFF` omits it.
- `run.sh OUT Native|OnnxRuntime EVENTS RDO THREADS`: primary-pass NN post
  calibration on every cluster by default; main's seed policy and cuts.
  `NATIVE_NN_STAGE=pre` and `NATIVE_NN_THRESHOLD=15000` cover the other paths.
- `pipeline.sh`: two 100-event, four-thread physics runs; three alternating
  20-event serial timing pairs on CPU 16; pre/default-threshold smoke checks.
- `extract.sh`, `summarize.py [RESULT_ROOT]`: existing truth definitions, complete per-event
  outcome comparison and control-normalized timing. Repeated timing events are
  not pooled into the physics denominator. `compare_records.py Native [RESULT_ROOT]`
  separates discrete tracking quantities from fitted floating-point differences.
- `fingerprint_probe.cxx`: feasibility experiment for graph signatures with
  learned values externalized through public ORT APIs; not shipped in Athena.
- `eigen_compare.sh`, `time_eigen.sh`: paired Eigen/intrinsics standalone
  comparison. `.cxx` and assembly snapshots are kept with the results.
- `validate.sh`, `isa_check.sh`: 100k real-input comparison to ONNX, all four
  models; SSE2 and scalar variants. `mutate_models.py` and
  `validate_mutations.sh`: changed-weight acceptance and incompatible-model
  rejection. Python ONNX is only used to construct independent test inputs.
- `make_variants.py`, `build_variants.sh`, `validate_variants.sh`,
  `time_variants.sh`: additional Eigen/AVX2/activation experiments, separate
  from the production candidate. Time only when reconstruction is finished.
- `count_loc.py`: auditable per-file conversion/inference/glue/test count;
  includes declarations and build/config code, excludes comments/blank lines.

Standalone validation reuses the frozen capture and reference outputs in
`../run/nn-inference` and helpers in `../nn-inference`; those are not part of
or dependencies of the production implementation.

Final implementation: runtime layer counts/dimensions, CxxUtils GEMV/blend/division, Eigen exp,
and runtime SSE/AVX2 dispatch. The following retain the earlier Eigen experiments:
- `make_general_variants.py`, `build_general_variants.sh`,
  `validate_general_variants.sh`, `time_general_variants.sh`: final fixed/dynamic
  dimension and SSE/AVX2 comparison.
- `build_clang.sh`, `check_clang.sh`: Clang 20 comparison and numerical checks.
- `production_bench.sh [OUTPUT_SUBDIR]`: validates the actual Athena library.
- `dispatch/`: rejected Eigen GEMV runtime prototype and symbol audit; the final
  CxxUtils kernel avoids its common Eigen GEMV helper symbols.
- `roofline/`: empirical per-core arithmetic and cache-bandwidth bounds, plus
  sampled inference profiles. No profiling instrumentation in production code.
- `package_report.py`, `render_note.py`: archive compact evidence and produce
  the standalone HTML note.
- `read_elf_section.py`: reads ELF sections without rewriting the inspected file.

Do not rebuild or rewrite a shared library while reconstruction is running.
Do not edit a running shell script. Retained harness incident reports are under
`run/native-pixel-nn/physics/OnnxRuntime/wrapper-recovery.json` and
`run/native-pixel-nn/smoke-default-threshold/OnnxRuntime-inspection-failure/`;
completed physics records and accepted timing runs are unaffected.

Follow-up note: `atlas/tsi/notebook/2026-11-24_native-pixel-nn.md` in
https://github.com/andiwand/cern-notes.

Final review replaces graph fingerprints with required-tensor validation and a
64-input startup comparison against ONNX. `validate_layout.sh` exercises changed
weights/metadata, extra unused tensors and deliberate semantic mismatches through
the actual Athena library. `mutate_models.py` constructs these offline fixtures.
No OpenSSL linkage is needed by the final loader. Older fingerprint/dispatch
probes remain as study history, outside the production candidate.

Final implementation overview:
`atlas/tsi/notebook/2026-11-24_native-pixel-nn-final-candidate.md` in the notes repo.

Final SIMD tuning and validation:

- `cxxutils/`: initial shared-SSE-activation prototype; `cxxutils/tune/` explores
  packet widths, unrolling, local head sums and explicit SIMD SiLU selection.
  These generators use frozen study sources under `run/native-pixel-nn/cxxutils`;
  old Eigen generators require the historical Eigen candidate, not current main.
- `cxxutils/tune/clean.py`, `build_clean.sh`, `sanitize.sh`, `inline_check.sh`:
  reduce the selected variants to one kernel, verify unchanged outputs/code,
  check ASan/UBSan and inspect Eigen helper isolation at different optimization levels.
- `runtime/standalone.sh`: actual Athena GCC library and a Clang build of the
  same source; all four models on 100k captured inputs, automatic and forced SSE.
- `runtime/pipeline.sh`: six alternating isolated timing cycles, then fresh
  100-event physics, three serial timing pairs and pre/default-threshold smoke
  runs. Results live in `run/native-pixel-nn/runtime-mr`, preserving earlier data.
  Run only after `runtime/standalone.sh` and after the build/tests have finished.
- Analyze with `summarize.py /absolute/path/to/runtime-mr` and
  `compare_records.py Native /absolute/path/to/runtime-mr`.
- `runtime/analyze.py` checks the frozen measured libraries, all jobs and smoke
  counters. `ort_baseline.sh` refreshes the original ONNX call-path comparison
  after reconstruction. `audit.py` and `debug_audit.sh` inspect release/debug ISA
  boundaries, including scalar C++ helpers. `release_equivalence.py` records
  loaded sections before/after the final debug-wrapper fix; `package_report.py`
  archives this evidence alongside the updated note.
- `runtime/final_pipeline.sh`: repeat final native physics and both timing sides
  after the scalar debug-wrapper fix changed GCC's release instruction layout.
  Results live in `runtime-final`; unchanged ONNX physics/smoke jobs are explicit
  references to `runtime-mr`. Both SIMD paths pass fresh numerical/config tests.
  `prepare_final.py` records the directory/client/reference setup and refuses
  overwrites. After all measurements, `check_off_restore.sh` tests the OFF build,
  restores ON and verifies exact library hashes before report packaging.

Runtime-sized follow-up (2026-11-25):

- `runtime/generic_compile.sh`: GCC/Clang builds of the runtime-sized kernel and
  common model interface; 10k captured inputs, all four heads, auto/SSE/ONNX.
- `runtime/generic_time.py`: three alternating 50k-input × three-repeat cycles
  against the frozen aligned fixed-size candidate; comparison to ONNX outputs.
- `runtime/generic_baseline.sh` records that older baseline; do not regenerate it
  from the current headers. `interface_bench.cxx` exercises virtual inference and
  the native-preferred/explicit-ONNX factory, with a forced-baseline test path.
- Results default to `run/native-pixel-nn/generic/final`; override with
  `NATIVE_NN_RUN_ROOT`. Earlier `runtime/standalone.sh` assumes bit identity with
  the specialized kernel and is historical; GCC AVX2 now differs within tolerance.
- The unit test adds shallow/deep/wide/decoder-only models, concurrent ONNX/native
  calls and fallback. `runtime/generic_full.sh` performs a fresh full campaign in
  `generic/full`: 100k captured inputs through the actual Athena library; two
  100-event physics runs; three serial 20-event timing pairs; pre/default-threshold
  and automatic-fallback smoke jobs; AVX2-OFF tests and ON restoration.
  `generic_analyze.py` checks fresh-job provenance, shared library hashes and results.
