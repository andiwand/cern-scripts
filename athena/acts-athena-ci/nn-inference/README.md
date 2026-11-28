# nn-inference

What is left of the pixel NN inference latency study
(`atlas/tsi/notebook/2026-11-24_nn-inference-latency.md`): the pieces
`../native-pixel-nn` uses. Data, captured inputs and reference outputs stay in
`$ACI_BASE/run/nn-inference`.

| file | usage |
|---|---|
| `env.sh` | nightly 2026-11-23T2100, `NN_STUDY_ROOT`, release BLAS and ONNX externals; source with `errexit` off |
| `validate.py <dir>` | compare every `<backend>.bin` in `<dir>` to `original.bin` (all four networks, 33 float32 outputs per input) |
| `fixtures/outcomes.py <out> <AOD glob> [--gun] [--events N]` | per-particle truth outcome records of an AOD (`outcomes.hxx` is its C++ writer) |
