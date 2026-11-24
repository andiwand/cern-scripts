#!/bin/bash
set +e
source /home/astefl/scripts/athena/acts-athena-ci/nn-inference/env.sh > /tmp/native-nn-inline-env.log 2>&1
set -e
native_inline_root=/home/astefl/source/acts/acts-athena-ci
native_inline_clean=$native_inline_root/run/native-pixel-nn/cxxutils/tuning/clean
native_inline_out=$native_inline_root/run/native-pixel-nn/cxxutils/tuning/inline-review
mkdir -p "$native_inline_out"
for native_inline_mode in release sanitize debug; do
 native_inline_flags=(-O2 -DNDEBUG)
 if [[ $native_inline_mode == sanitize ]]; then native_inline_flags=(-O1 -fsanitize=address,undefined); fi
 if [[ $native_inline_mode == debug ]]; then native_inline_flags=(-O0); fi
 g++ "${native_inline_flags[@]}" -std=c++23 -fPIC -march=x86-64-v2 -mavx2 -mfma -DEIGEN_MAX_ALIGN_BYTES=16 '-DEIGEN_STRONG_INLINE=inline __attribute__((always_inline))' -fvisibility=hidden -fvisibility-inlines-hidden -I"$native_inline_clean" -I"$native_inline_root/athena-native-pixel-nn/Control/CxxUtils" -I"$NN_STUDY_LCG/eigen/3.4.1/x86_64-el9-gcc15-opt/include/eigen3" -c "$native_inline_clean/Avx2.cxx" -o "$native_inline_out/$native_inline_mode.o"
 nm -gC --defined-only "$native_inline_out/$native_inline_mode.o" | rg 'Eigen::' > "$native_inline_out/$native_inline_mode-eigen.txt" || true
 wc -l "$native_inline_out/$native_inline_mode-eigen.txt"
done
