#!/usr/bin/env bash
set +e
source /home/astefl/scripts/athena/acts-athena-ci/nn-inference/env.sh > /tmp/native-cxxutils-sanitize-env.log 2>&1
set -euo pipefail
san_root=/home/astefl/source/acts/acts-athena-ci
san_clean=$san_root/run/native-pixel-nn/cxxutils/tuning/clean
san_out=$san_root/run/native-pixel-nn/cxxutils/tuning/sanitizer
mkdir -p "$san_out"
python3 - "$san_root" "$san_out" <<'PY'
from pathlib import Path
import subprocess,sys
r=Path(sys.argv[1]);o=Path(sys.argv[2])
s=subprocess.check_output(['git','-C',str(r/'athena-native-pixel-nn'),'show',
 'fd1750c6d06:InnerDetector/InDetRecTools/SiClusterizationTool/test/NativePixelClusterNN_test.cxx'],text=True)
s=s.replace('#include "PathResolver/PathResolver.h"','''std::string PathResolverFindCalibFile(const std::string& path) {
  return "/cvmfs/atlas.cern.ch/repo/sw/database/GroupData/" + path;
}''')
s=s.replace('int main() {','int main(int argc, char**) {\n  const bool allowAvx2 = argc == 1;')
for call in ['native(env, path, model)','wrong(env, path, (model + 1) % 4)',
             'wrong(env, path, 4)','wrong(env, changedPath, model)',
             'metadataChanged(env, changedPath, model)',
             'missing(env, "nonexistent-native-nn.onnx", 0)']:
 assert call in s
 s=s.replace(call,call[:-1]+', allowAvx2)')
(o/'test.cxx').write_text(s)
PY
san_flags=(-O1 -g -std=c++23 -fPIC -march=x86-64-v2 -fsanitize=address,undefined -fno-omit-frame-pointer)
san_includes=(-I"$san_clean" -I"$san_root/athena-native-pixel-nn/Control/CxxUtils" -I"$NN_STUDY_EXTERNALS/include" -I"$NN_STUDY_LCG/eigen/3.4.1/x86_64-el9-gcc15-opt/include/eigen3")
for san_file in Loader Dispatch Sse Avx2; do
 san_extra=()
 if [[ $san_file == Sse || $san_file == Avx2 ]]; then san_extra+=(-fvisibility=hidden -fvisibility-inlines-hidden); fi
 if [[ $san_file == Avx2 ]]; then san_extra+=(-mavx2 -mfma -DEIGEN_MAX_ALIGN_BYTES=16); fi
 g++ "${san_flags[@]}" "${san_includes[@]}" "${san_extra[@]}" -c "$san_clean/$san_file.cxx" -o "$san_out/$san_file.o"
done
g++ "${san_flags[@]}" "${san_includes[@]}" "$san_out/test.cxx" "$san_out/"{Loader,Dispatch,Sse,Avx2}.o -pthread -L"$NN_STUDY_EXTERNALS/lib" -lonnxruntime -Wl,-rpath,"$NN_STUDY_EXTERNALS/lib" -o "$san_out/test"
for san_mode in auto sse; do
 mkdir -p "$san_out/$san_mode"
 (
  cd "$san_out/$san_mode"
  san_args=()
  if [[ $san_mode == sse ]]; then san_args=(force-sse); fi
  ASAN_OPTIONS=detect_leaks=1:halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1 "$san_out/test" "${san_args[@]}" > test.log 2>&1
 )
done
