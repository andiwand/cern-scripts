# Native pixel NN integration

Candidate branch: `acts-native-pixel-nn` in
`~/source/acts/acts-athena-ci/athena-native-pixel-nn`, based on Athena main
`41da040949efeca5de0e5adbd84054868a5165c6` (2026-11-24).
Build: `../athena-build-native-pixel-nn`; results: `../run/native-pixel-nn`.

- `build.sh`, `tests.sh`: pinned Nov 23 gcc15 nightly; three-package overlay;
  no ACTS override, GPU or benchmark library in reconstruction.
  `build.sh -DSICLUSTERIZATION_NATIVE_NN_AVX2=ON` opts into AVX2/FMA hardware;
  plain `build.sh` restores the default SSE build.
- `run.sh OUT Native|OnnxRuntime EVENTS RDO THREADS`: primary-pass NN post
  calibration on every cluster by default; main's seed policy and cuts.
  `NATIVE_NN_STAGE=pre` and `NATIVE_NN_THRESHOLD=15000` cover the other paths.
- `pipeline.sh`: two 100-event, four-thread physics runs; three alternating
  20-event serial timing pairs on CPU 16; pre/default-threshold smoke checks.
- `extract.sh`, `summarize.py`: existing truth definitions, complete per-event
  outcome comparison and control-normalized timing. Repeated timing events are
  not pooled into the physics denominator.
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

Final implementation: fixed dimensions, ordinary Eigen GEMV and full-array SiLU.
- `make_general_variants.py`, `build_general_variants.sh`,
  `validate_general_variants.sh`, `time_general_variants.sh`: final fixed/dynamic
  dimension and SSE/AVX2 comparison.
- `build_clang.sh`, `check_clang.sh`: Clang 20 comparison and numerical checks.
- `production_bench.sh [OUTPUT_SUBDIR]`: validates the actual Athena library.
- `dispatch/`: rejected two-symbol runtime prototype and symbol audit; explains
  why the candidate uses a compile-time option.
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
