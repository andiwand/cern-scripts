#!/usr/bin/env bash
# Dump all four heads for captured inputs and compare them.
#   validate_outputs.sh OUTDIR [--count N] [--ref LABEL] [--identical A=B]... [--models DIR] LABEL=BINARY[:ENV=V[,ENV=V]]...
# Each case runs `BINARY dump INPUTS N OUTDIR/LABEL.bin [DIR]` with NATIVE_NN_FORCE_SSE,
# NATIVE_NN_FORCE_ONNX and LD_PRELOAD cleared, then ENV applied. Every label is
# checked against LABEL=ref (default onnx; a pre-existing OUTDIR/REF.bin also works)
# by check_outputs.py: no element outside 1e-5+1e-4|ref| and no multiplicity change.
# --identical A=B additionally requires bit-identical dumps. Defaults: N=100000,
# INPUTS=$NATIVE_NN_INPUTS or $NN_STUDY_ROOT/captured-inputs.bin.
set -eo pipefail
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
usage() { sed -n '2,9p' "$0" >&2; exit 2; }
(($# >= 2)) || usage
out=$(realpath -m "$1"); shift
count=100000 ref=onnx models= checks=() cases=() labels=()
while (($#)); do
 case $1 in
  --count) count=$2; shift 2;;
  --ref) ref=$2; shift 2;;
  --identical) checks+=(--identical "$2"); shift 2;;
  --models) models=$(realpath "$2"); shift 2;;
  -*) usage;;
  *=*) cases+=("$1"); shift;;
  *) usage;;
 esac
done
inputs=${NATIVE_NN_INPUTS:-}
source "$here/bench_env.sh"
set -euo pipefail
inputs=${inputs:-$NN_STUDY_ROOT/captured-inputs.bin}
mkdir -p "$out"
for case in "${cases[@]}"; do
 label=${case%%=*} spec=${case#*=} envs=()
 binary=${spec%%:*}
 if [[ $spec == *:* ]]; then IFS=, read -ra envs <<< "${spec#*:}"; fi
 env -u NATIVE_NN_FORCE_SSE -u NATIVE_NN_FORCE_ONNX -u LD_PRELOAD "${envs[@]}" \
  "$binary" dump "$inputs" "$count" "$out/$label.bin" ${models:+"$models"}
 if [[ $label != "$ref" ]]; then labels+=("$label"); fi
done
python3 "$here/check_outputs.py" "$out" --ref "$ref" "${checks[@]}" "${labels[@]}"
