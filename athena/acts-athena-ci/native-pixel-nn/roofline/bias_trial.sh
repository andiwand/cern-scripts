#!/usr/bin/env bash
# Test initializing GEMV from the bias, without changing production sources.
set +e
source /home/astefl/scripts/athena/acts-athena-ci/nn-inference/env.sh > /tmp/native-bias-env.log 2>&1
set -e
native_root=/home/astefl/source/acts/acts-athena-ci
native_out=$native_root/run/native-pixel-nn/roofline/bias
native_pkg=$native_root/athena-native-pixel-nn/InnerDetector/InDetRecTools/SiClusterizationTool
mkdir -p "$native_out"
if [[ ${1:-build} == build ]]; then
 python3 - "$native_pkg/src/NativePixelClusterNN.cxx" "$native_out" <<'PY'
import sys
from pathlib import Path
source=Path(sys.argv[1]).read_text()
before='''  result.noalias() = weights * Eigen::Map<const Eigen::Matrix<float, In, 1>>(input);
  result += Eigen::Map<const Eigen::Matrix<float, Out, 1>>(layer.bias.data());'''
after='''  result = Eigen::Map<const Eigen::Matrix<float, Out, 1>>(layer.bias.data());
  result.noalias() += weights * Eigen::Map<const Eigen::Matrix<float, In, 1>>(input);'''
assert before in source
for name,body in [('reference',source),('bias',source.replace(before,after))]:
 (Path(sys.argv[2])/(name+'.cxx')).write_text(body)
PY
 native_crypto=$(sed -n 's|^OPENSSL_CRYPTO_LIBRARY:FILEPATH=||p' "$native_root/athena-build-native-pixel-nn/CMakeCache.txt")
 for native_isa in sse avx2; do
  native_flags='-march=x86-64-v2'
  if [[ $native_isa == avx2 ]]; then native_flags="$native_flags -mavx2 -mfma -DEIGEN_MAX_ALIGN_BYTES=16"; fi
  for native_case in reference bias; do
   native_name=${native_case}_${native_isa}
   g++ -O2 -DNDEBUG -std=c++23 -fPIC $native_flags -I"$native_pkg" -I"$NN_STUDY_LCG/eigen/3.4.1/x86_64-el9-gcc15-opt/include/eigen3" -c "$native_out/$native_case.cxx" -o "$native_out/$native_name.o"
   g++ -shared "$native_out/../../loader.o" "$native_out/$native_name.o" -L"$NN_STUDY_EXTERNALS/lib" -lonnxruntime "$native_crypto" -Wl,-rpath,"$NN_STUDY_EXTERNALS/lib" -o "$native_out/libNative_$native_name.so"
   g++ "$native_out/../../bench.o" -L"$native_out" -lNative_$native_name -L"$NN_STUDY_EXTERNALS/lib" -lonnxruntime -Wl,-rpath,"$native_out:$NN_STUDY_EXTERNALS/lib" -o "$native_out/bench_$native_name"
  done
 done
else
 : > "$native_out/timing.jsonl"
 for native_cycle in {1..6}; do
  native_order='reference_sse bias_sse reference_avx2 bias_avx2'
  if ((native_cycle%2==0)); then native_order='bias_avx2 reference_avx2 bias_sse reference_sse'; fi
  for native_case in $native_order; do
   native_result=$(taskset -c 16 "$native_out/bench_$native_case" time "$NN_STUDY_ROOT/captured-inputs.bin" 100000 unused)
   printf '{"cycle":%s,"backend":"%s","result":%s}\n' "$native_cycle" "$native_case" "$native_result" >> "$native_out/timing.jsonl"
  done
 done
fi
