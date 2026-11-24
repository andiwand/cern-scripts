# SIMD selection prototypes (not part of the MR candidate)

`make_prototype.py` writes a shared inference body, two ISA translation units,
a once-per-model CPU check and a small dispatcher to `run/native-pixel-nn/dispatch`.
`build.sh` compiles this with GCC 15.2 and Clang 20.1.8.

The initial prototype is **not safe to ship**: Clang emits the same weak Eigen
`general_matrix_vector_product::run` symbol from both ISA objects. Link order can
select the SSE helper for both, or expose AVX instructions through the SSE path.
GCC currently specializes it away, but that is not a sound portability guarantee.
Overriding `EIGEN_STRONG_INLINE` does not fix the deliberately non-inlined GEMV.

GCC's target pragma changes `__AVX2__` while Eigen headers are parsed; Clang's GCC
pragma does not. Per-source target flags handle both compilers cleanly. A build
that opts into AVX2/FMA must run on a CPU supporting those instructions.

The candidate includes the compile-time option
`SICLUSTERIZATION_NATIVE_NN_AVX2` (default OFF). It sets AVX2/FMA for inference
and retains 16-byte Eigen alignment. All machines running that opt-in build must
support AVX2/FMA, including any other callers of a merged Eigen helper.
Runtime dispatch would additionally need reliable Eigen symbol isolation, e.g.
a separate private backend library, rather than relying on optimizer behavior.
