# Activation and small-head tuning

Follow-up to the common-SSE-activation CxxUtils prototype. These are isolated
compute experiments; the selected kernel is now integrated and validated by
`../../runtime/`. No custom exponential: Eigen supplies exp.

The final kernel keeps one SIMD packet in an Eigen array whose type includes
the width (4 or 8 floats), then uses CxxUtils for the blend/division. Eigen 3.4.1's
Select evaluator is scalar: GCC sometimes vectorizes it again, while Clang left
scalar branches/divisions in a helper call. Explicit vector arithmetic removes
that compiler dependence. The selected variant also keeps small-head sums local.

Both ISA objects have hidden visibility. Array widths distinguish Eigen helpers
within the library; hidden symbols prevent interposition with other Athena code.
`audit.py` checks these properties and SSE/AVX instructions. `finalize.sh` tests
direct calls, forced fallback and reversed object link order against ONNX on
100k inputs, all four heads.

Run sequentially after the parent prototype has been built:

```bash
bash build.sh
python3 audit.py
NATIVE_VEC_CASES='packet unroll flat heads bias' bash run.sh screen
NATIVE_VEC_CASES='heads vector vector_bias vector_loop' bash run.sh screen
bash finalize.sh
bash run.sh final
bash build_clean.sh
python3 summarize.py
```

Archive the first screen before running the second; the recorded study keeps it
in `run/native-pixel-nn/cxxutils/tuning/eigen-select`. `NATIVE_VEC_CASES` also limits
which variants `build.sh` rebuilds. No build runs alongside a timing job.

The clean source removes experimental conditionals. SSE uses `vector_loop`,
AVX2 uses `vector` (activation unrolled four times); neither uses bias-first or
ATH_FLATTEN. Clean objects were checked to have identical executable/constant
sections and numerical output to the measured variants. Their code count is
152 lines for kernel, header, ISA wrappers and dispatch, versus 97 in the Eigen
candidate; conversion/validation is 113 versus 112. Those prototype counts exclude
production integration. The final integrated count is 488 net lines: conversion
116, inference/header/dispatch 157, glue 74, tests 141.

Production also forces Eigen's strong-inline helpers inline within each ISA
source to prevent helper merging in reduced-optimization builds.
`inline_check.sh` inspects this at -O2, -O1 with sanitizers and -O0;
`sanitize.sh` runs the selected kernel's unit tests under ASan/UBSan.

Results: `run/native-pixel-nn/cxxutils/tuning`. The updated overview is
`atlas/tsi/notebook/2026-11-24_native-pixel-nn-final-candidate.md` in
https://github.com/andiwand/cern-notes.
