#!/usr/bin/env bash
set +e
source /home/astefl/scripts/athena/acts-athena-ci/nn-inference/env.sh > /tmp/native-cxxutils-validation-env.log 2>&1
set -euo pipefail
vec_out=/home/astefl/source/acts/acts-athena-ci/run/native-pixel-nn/cxxutils
for vec_compiler in gcc clang; do
  vec_dir=$vec_out/$vec_compiler
  mkdir -p "$vec_dir/validation"
  cp "$NN_STUDY_ROOT/validation-real-athena/original.bin" "$vec_dir/validation/original.bin"
  for vec_variant in selected forced_sse direct_sse direct_avx2 eigen_sse eigen_avx2 shared_sse shared_avx2; do
    vec_binary=$vec_variant
    vec_env=()
    if [[ $vec_variant == forced_sse ]]; then vec_binary=selected; vec_env=(NATIVE_NN_FORCE_SSE=1); fi
    env "${vec_env[@]}" "$vec_dir/bench_$vec_binary" dump "$NN_STUDY_ROOT/captured-inputs.bin" 100000 "$vec_dir/validation/$vec_variant.bin"
  done
  cmp "$vec_dir/validation/selected.bin" "$vec_dir/validation/direct_avx2.bin"
  cmp "$vec_dir/validation/forced_sse.bin" "$vec_dir/validation/direct_sse.bin"
  python3 /home/astefl/scripts/athena/acts-athena-ci/nn-inference/validate.py "$vec_dir/validation" > "$vec_dir/validation/report.txt"
  python3 - "$vec_dir/validation/validation.json" <<'PY'
import json,sys
report=json.load(open(sys.argv[1]))
assert all(v['finite'] and v['argmax_changes']==0 and v['elements_outside_1e-5_plus_1e-4_relative']==0 for v in report['backends'].values())
print(sys.argv[1], ': all numerical comparisons passed')
PY
done
