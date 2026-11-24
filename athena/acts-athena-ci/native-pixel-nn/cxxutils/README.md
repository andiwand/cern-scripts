# CxxUtils pixel NN compute prototype

Standalone follow-up to the Eigen candidate; no Athena source changes or physics
jobs. Models, loader checks, captured inputs and output transforms are unchanged.
Results: `run/native-pixel-nn/cxxutils` in the acts-athena-ci workspace.

`Dense.icc` uses width-templated `CxxUtils::vec`, column-major weights and up to
eight independent output accumulators. The two `GCC unroll` hints keep those
accumulators in registers under GCC 15; Clang 20 accepts them too. The generated
SSE/AVX2 inference objects contain no Eigen. One common Eigen/SSE object handles
SiLU, so this prototype does not need mixed-ISA Eigen templates or its own exp.

The loader detects AVX2 **and** FMA once per model. Inference dispatches through
a predictable branch. `NATIVE_NN_FORCE_SSE=1` forces the baseline in the harness.
Direct-entry control libraries measure the same kernels without that branch.

Run sequentially, on an idle machine:

```bash
bash build.sh
bash run.sh screen
bash build_selected.sh
bash validate.sh
python3 audit.py
bash run.sh final
python3 summarize.py
```

- `make_prototype.py` generates model/loader copies and inference wrappers outside
  the candidate tree. `build.sh kernels` rebuilds only the vector kernels.
- Screening tests 1/2/4/8 output accumulators; final timings use six alternating
  cycles, CPU 16, 100k captured inputs and five repeats. Both NNs are included.
- Eigen controls are rebuilt with matching flags/compiler. `shared_*` uses Eigen
  GEMV with the same common SSE activation, separating GEMV and activation costs.
- Validation compares all four heads on 100k inputs with ONNX and checks direct
  and dispatched paths bit-for-bit. This is numerical, not physics validation.
- `audit.py` checks no AVX in baseline objects, YMM/FMA in AVX2 kernels, and no
  Eigen symbols in either CxxUtils ISA object. No non-AVX machine was available.

The initial screen without unrolling is retained under `initial/` in the results.
The historical generated `Kernel.icc` there records that version.

Do not rebuild or edit a running script during timing. The report is
`atlas/tsi/notebook/2026-11-24_native-pixel-nn-cxxutils.md` in
https://github.com/andiwand/cern-notes.
