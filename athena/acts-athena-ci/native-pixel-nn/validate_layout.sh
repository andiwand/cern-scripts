#!/usr/bin/env bash
# Changed-model acceptance/rejection through a bench binary (e.g. bench_build.sh OUT athena).
#   validate_layout.sh BENCH MUTATIONS OUT [--count 1000]
# MUTATIONS is mutate_models.py output. Accepted cases (weights, metadata, extra) must
# load natively and agree with ONNX on the same models (validate_outputs.sh). Rejected
# cases must fail native construction; semantic mismatches must report the startup
# disagreement with ONNX.
set -eo pipefail
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
usage() { sed -n '2,7p' "$0" >&2; exit 2; }
(($# >= 3)) || usage
bench=$(realpath "$1") mutations=$(realpath "$2") out=$(realpath -m "$3"); shift 3
count=1000
while (($#)); do
 case $1 in
  --count) count=$2; shift 2;;
  *) usage;;
 esac
done
mkdir -p "$out"
for case in weights metadata extra; do
 mkdir -p "$out/$case"
 bash "$here/validate_outputs.sh" "$out/$case" --count "$count" --models "$mutations/$case" \
  native="$bench" onnx="$bench:NATIVE_NN_FORCE_ONNX=1" > "$out/$case/check.log" 2>&1
 echo "Accepted and checked $case"
done
inputs=${NATIVE_NN_INPUTS:-}
source "$here/bench_env.sh"
set -euo pipefail
inputs=${inputs:-$NN_STUDY_ROOT/captured-inputs.bin}
for case in nonfinite normalization activation shape missing dtype precision output_order; do
 log=$out/reject-$case.log
 if env -u NATIVE_NN_FORCE_SSE -u NATIVE_NN_FORCE_ONNX -u LD_PRELOAD "$bench" dump "$inputs" 1 "$out/unused.bin" "$mutations/$case" > "$log" 2>&1; then
  echo "Incorrectly accepted $case"; exit 1
 fi
 if [[ $case =~ ^(normalization|activation|precision|output_order)$ ]]; then
  grep -q 'Native pixel NN disagrees with ONNX' "$log"
 fi
 echo "Rejected $case"
done
