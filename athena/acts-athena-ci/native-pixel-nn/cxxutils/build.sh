#!/usr/bin/env bash
set +e
source /home/astefl/scripts/athena/acts-athena-ci/nn-inference/env.sh > /tmp/native-cxxutils-build-env.log 2>&1
set -euo pipefail
vec_root=/home/astefl/source/acts/acts-athena-ci
vec_out=$vec_root/run/native-pixel-nn/cxxutils
vec_here=/home/astefl/scripts/athena/acts-athena-ci/native-pixel-nn/cxxutils
vec_pkg=$vec_root/athena-native-pixel-nn/InnerDetector/InDetRecTools/SiClusterizationTool
python3 "$vec_here/make_prototype.py"
for vec_compiler in gcc clang; do
  vec_cxx=g++
  if [[ $vec_compiler == clang ]]; then vec_cxx=/usr/bin/clang++; fi
  vec_dir=$vec_out/$vec_compiler
  mkdir -p "$vec_dir"
  vec_flags=(-O2 -DNDEBUG -std=c++23 -fPIC -march=x86-64-v2)
  vec_include=(-I"$vec_out" -I"$vec_root/athena-native-pixel-nn/Control/CxxUtils" -I"$NN_STUDY_EXTERNALS/include" -I"$NN_STUDY_LCG/eigen/3.4.1/x86_64-el9-gcc15-opt/include/eigen3")
  vec_link=(-L"$NN_STUDY_EXTERNALS/lib" -lonnxruntime -Wl,-rpath,"$NN_STUDY_EXTERNALS/lib:$vec_dir")
  "$vec_cxx" --version > "$vec_dir/compiler.txt"
  if [[ ${1:-all} != kernels ]]; then
    for vec_file in Loader Activation Dispatch bench; do
      "$vec_cxx" "${vec_flags[@]}" "${vec_include[@]}" -c "$vec_out/$vec_file.cxx" -o "$vec_dir/$vec_file.o"
    done
  fi
  for vec_blocks in 1 2 4 8; do
    for vec_isa in Sse Avx2; do
      vec_extra=()
      if [[ $vec_isa == Avx2 ]]; then vec_extra=(-mavx2 -mfma); fi
      "$vec_cxx" "${vec_flags[@]}" "${vec_include[@]}" "${vec_extra[@]}" -DNN_BLOCKS="$vec_blocks" -c "$vec_out/$vec_isa.cxx" -o "$vec_dir/${vec_isa}_b$vec_blocks.o"
    done
    "$vec_cxx" -shared "$vec_dir/"{Loader,Activation,Dispatch}.o "$vec_dir/"{Sse,Avx2}_b"$vec_blocks".o "${vec_link[@]}" -o "$vec_dir/libVec_b$vec_blocks.so"
    "$vec_cxx" "$vec_dir/bench.o" -L"$vec_dir" -lVec_b"$vec_blocks" "${vec_link[@]}" -o "$vec_dir/bench_b$vec_blocks"
  done
  if [[ ${1:-all} == kernels ]]; then continue; fi
  # Compile current Eigen baselines afresh with matching compiler/flags.
  "$vec_cxx" "${vec_flags[@]}" -I"$vec_pkg" "${vec_include[@]}" -c "$vec_pkg/src/NativePixelClusterNNFromOnnx.cxx" -o "$vec_dir/EigenLoader.o"
  "$vec_cxx" "${vec_flags[@]}" -I"$vec_pkg" "${vec_include[@]}" -c "$vec_here/../bench.cxx" -o "$vec_dir/EigenBench.o"
  for vec_isa in sse avx2; do
    vec_extra=()
    if [[ $vec_isa == avx2 ]]; then vec_extra=(-mavx2 -mfma -DEIGEN_MAX_ALIGN_BYTES=16); fi
    for vec_kind in eigen shared; do
      vec_source=$vec_pkg/src/NativePixelClusterNN.cxx
      vec_objects=()
      if [[ $vec_kind == shared ]]; then vec_source=$vec_out/EigenSharedActivation.cxx; vec_objects=("$vec_dir/Activation.o"); fi
      "$vec_cxx" "${vec_flags[@]}" -I"$vec_pkg" "${vec_include[@]}" "${vec_extra[@]}" -c "$vec_source" -o "$vec_dir/${vec_kind}_${vec_isa}.o"
      "$vec_cxx" -shared "$vec_dir/EigenLoader.o" "$vec_dir/${vec_kind}_${vec_isa}.o" "${vec_objects[@]}" "${vec_link[@]}" -o "$vec_dir/lib${vec_kind}_${vec_isa}.so"
      "$vec_cxx" "$vec_dir/EigenBench.o" -L"$vec_dir" -l"${vec_kind}_${vec_isa}" "${vec_link[@]}" -o "$vec_dir/bench_${vec_kind}_${vec_isa}"
    done
  done
done
