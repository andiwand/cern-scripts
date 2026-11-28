#!/usr/bin/env bash
# Build the standalone bench (bench.cxx) into OUT/KIND/bench.
#   bench_build.sh OUT KIND... [--src DIR]
# KIND: athena  link the built Athena libSiClusterizationToolLib
#       gcc     compile the package sources with g++ into OUT/gcc/libNNGeneric.so
#       clang   same with clang++ (NATIVE_NN_CLANG, default /usr/bin/clang++)
# --src DIR replaces the package src/ directory (e.g. an edited copy for a kernel A/B).
set -eo pipefail
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
usage() { sed -n '2,8p' "$0" >&2; exit 2; }
(($# >= 2)) || usage
out=$(realpath -m "$1"); shift
kinds=() src=
while (($#)); do
 case $1 in
  --src) src=$(realpath "$2"); shift 2;;
  athena|gcc|clang) kinds+=("$1"); shift;;
  *) usage;;
 esac
done
((${#kinds[@]})) || usage
clang=${NATIVE_NN_CLANG:-/usr/bin/clang++}
source "$here/bench_env.sh"
set -euo pipefail
pkg=$NATIVE_NN_SOURCE/InnerDetector/InDetRecTools/SiClusterizationTool
src=${src:-$pkg/src}
includes=(-I"$pkg" -I"$NN_STUDY_EXTERNALS/include" -I"$NATIVE_NN_SOURCE/Control/CxxUtils" -I"$NN_STUDY_LCG/eigen/3.4.1/x86_64-el9-gcc15-opt/include/eigen3" -I"$NN_STUDY_LCG/Boost/1.91.0/x86_64-el9-gcc15-opt/include")
flags=(-O2 -DNDEBUG -std=c++23 -march=x86-64-v2)
for kind in "${kinds[@]}"; do
 dir=$out/$kind
 mkdir -p "$dir"
 if [[ $kind == athena ]]; then
  g++ "${flags[@]}" "${includes[@]}" "$here/bench.cxx" -L"$NATIVE_NN_LIB" -lSiClusterizationToolLib -L"$NN_STUDY_EXTERNALS/lib" -lonnxruntime -Wl,-rpath,"$NATIVE_NN_LIB:$NN_STUDY_EXTERNALS/lib" -o "$dir/bench"
  continue
 fi
 cxx=g++
 if [[ $kind == clang ]]; then cxx=$clang; fi
 for name in NativePixelClusterNN NativePixelClusterNNBaseline NativePixelClusterNNAvx2 PixelClusterNNFactory; do
  extra=(-DSICLUSTERIZATION_NATIVE_NN_HAVE_AVX2)
  if [[ $name == *Baseline || $name == *Avx2 ]]; then extra+=(-fvisibility=hidden -fvisibility-inlines-hidden '-DEIGEN_STRONG_INLINE=inline __attribute__((always_inline))'); fi
  if [[ $name == *Avx2 ]]; then extra+=(-mavx2 -mfma -DEIGEN_MAX_ALIGN_BYTES=16); fi
  "$cxx" "${flags[@]}" -fPIC "${extra[@]}" "${includes[@]}" -c "$src/$name.cxx" -o "$dir/$name.o"
 done
 "$cxx" -shared "$dir/"*.o -L"$NN_STUDY_EXTERNALS/lib" -lonnxruntime -Wl,-rpath,"$NN_STUDY_EXTERNALS/lib" -o "$dir/libNNGeneric.so"
 "$cxx" "${flags[@]}" "${includes[@]}" "$here/bench.cxx" -L"$dir" -lNNGeneric -L"$NN_STUDY_EXTERNALS/lib" -lonnxruntime -Wl,-rpath,"$dir:$NN_STUDY_EXTERNALS/lib" -o "$dir/bench"
done
