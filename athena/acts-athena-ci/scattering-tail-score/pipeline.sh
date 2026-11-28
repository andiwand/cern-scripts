#!/bin/bash
# Train -> tune -> freeze -> validate -> evaluate -> diagnostics -> check, for one study directory.
# usage: pipeline.sh RUN [--from STEP]     (steps: train tune freeze validate evaluate diagnostics check)
# env: LIB, NN                 run.sh library / NN calibration (default: raw measurements, default library)
#      VARIANTS                training pool (default "core4 core5 core7 core10 tail4 tail5 tail7")
#      REF=RAW/training.json   tune against this plan's events and match targets (e.g. NN vs raw study)
#      PARENT=DIR              extend DIR: link its training/validation outputs, train only VARIANTS,
#                              freeze.py --extends DIR (choices of families without a new variant must not change)
#      ALSO (core7)            always validate these;  PARALLEL (3) concurrent run.sh jobs
#      TRAIN_EVENTS (200), VAL_EVENTS (800), VAL_SKIP (200; training uses skip 0)
# Writes RUN/{training,validation}/, training.json, frozen-plan.json, validation.json, diagnostics.json,
# main-point-check.json, logs and RUN/pipeline-exit-code.
S=$(cd "$(dirname "$0")" && pwd)
R=$(realpath -m "$1"); shift
FROM=train; [[ "$1" == --from ]] && FROM=$2
STEPS=(train tune freeze validate evaluate diagnostics check)
[[ " ${STEPS[*]} " == *" $FROM "* ]] || { echo "Unknown step $FROM"; exit 2; }
VARIANTS=${VARIANTS:-core4 core5 core7 core10 tail4 tail5 tail7}
ALSO=${ALSO-core7}
BATCH=(--parallel "${PARALLEL:-3}" --env "LIB=${LIB:-default}" --env "NN=${NN:-0}")
source /home/astefl/scripts/athena/acts-athena-ci/scattering-tail/env.sh
set -e
mkdir -p "$R"
trap 'echo $? > "$R/pipeline-exit-code"' EXIT

link() {  # link PARENT/$1/<v> for the given variants that exist there
  local stage=$1; shift
  mkdir -p "$R/$stage"
  for v in "$@"; do
    [[ -d "$PARENT/$stage/$v" && ! -e "$R/$stage/$v" ]] && ln -s "$(realpath "$PARENT/$stage/$v")" "$R/$stage/$v"
  done
  return 0
}

step_train() {
  local todo=$VARIANTS
  if [[ -n "$PARENT" ]]; then
    link training $(cd "$PARENT/training" && ls -d */ | tr -d /)
    todo=$(for v in $VARIANTS; do [[ -e "$R/training/$v" ]] || echo "$v"; done)
  fi
  [[ -z "$todo" ]] || python "$S/batch.py" "$R/training" "${TRAIN_EVENTS:-200}" 0 $todo "${BATCH[@]}"
}
step_tune() {
  python "$S/analyze.py" tune "$R/training" "$R/training.json" ${REF:+--reference-plan "$REF"} > "$R/tuning.log" 2>&1
}
step_freeze() {
  python "$S/freeze.py" "$R" --also $ALSO ${PARENT:+--extends "$PARENT"} \
    --validation-events "${VAL_EVENTS:-800}" --validation-skip "${VAL_SKIP:-200}"
}
step_validate() {
  local selected todo
  selected=$(python -c 'import json,sys;print(" ".join(json.load(open(sys.argv[1]))["validation_variants"]))' "$R/frozen-plan.json")
  [[ -n "$PARENT" ]] && link validation $selected
  todo=$(for v in $selected; do [[ -e "$R/validation/$v" ]] || echo "$v"; done)
  [[ -z "$todo" ]] || python "$S/batch.py" "$R/validation" "${VAL_EVENTS:-800}" "${VAL_SKIP:-200}" $todo "${BATCH[@]}"
}
step_evaluate() {
  python "$S/analyze.py" evaluate "$R/validation" "$R/validation.json" --plan "$R/training.json" > "$R/validation-analysis.log" 2>&1
}
step_diagnostics() {
  python "$S/diagnostics.py" "$R/validation" "$R/training.json" "$R/diagnostics.json"
}
step_check() {
  python -c 'import hashlib,json,sys;from pathlib import Path;p=Path(sys.argv[1]);d=json.loads((p/"frozen-plan.json").read_text());assert hashlib.sha256((p/"training.json").read_bytes()).hexdigest()==d["training_sha256"];print("Frozen plan unchanged")' "$R"
  python "$S/check_main_point.py" "$R"
}

run=0
for s in "${STEPS[@]}"; do
  [[ $s == "$FROM" ]] && run=1
  (( run )) || continue
  echo "=== $s $(date +%T)"
  "step_$s"
done
