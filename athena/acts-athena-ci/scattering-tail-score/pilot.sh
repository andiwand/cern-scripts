#!/bin/bash
# Short scoring-on/off pilot: OUT/<variant>_on and _off (run.sh SCORING=1/0), then audit_pilot.py
# (scoring must not change reconstruction; score dimensions/weights valid).
# usage: pilot.sh OUT [VARIANT...]   (default: tail5 core7)
# env: EVENTS (5), THREADS (4), ON_ONLY=1 (only scoring-on runs, no audit; e.g. LIB=onnx/native NN=1
#      backend pilots for compare_nn_backend.py), LIB, NN, INPUT (passed to run.sh)
S=$(cd "$(dirname "$0")" && pwd)
R=$1; shift
VARIANTS=${*:-tail5 core7}
set -e
mkdir "$R"
for v in $VARIANTS; do
  pids=()
  for state in on off; do
    [[ $state == off && ${ON_ONLY:-0} == 1 ]] && continue
    rec=1; [[ $state == off ]] && rec=0
    bash "$S/run.sh" "$R/${v}_$state" "$v" "${EVENTS:-5}" 0 "${THREADS:-4}" $rec > "$R/${v}_$state.driver.log" 2>&1 &
    pids+=($!)
  done
  for p in "${pids[@]}"; do wait "$p"; done
done
[[ ${ON_ONLY:-0} == 1 ]] && exit 0
source /home/astefl/scripts/athena/acts-athena-ci/scattering-tail/env.sh
python "$S/audit_pilot.py" "$R"
