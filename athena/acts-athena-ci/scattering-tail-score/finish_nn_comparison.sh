#!/bin/bash
# Final expanded nominal control; preserve both earlier frozen studies.
S=/home/astefl/scripts/athena/acts-athena-ci/scattering-tail-score
R=/home/astefl/source/acts/acts-athena-ci/run/scattering-tail-score
source /home/astefl/scripts/athena/acts-athena-ci/scattering-tail/env.sh
set -e
trap 'echo $? > "$R/nn-extended/comparison-exit-code"' EXIT
# Wait for immutable reconstruction outputs; the two analyses may run together.
# Atomic cache publication makes their shared input caches safe.
while true; do
  SCORE_READY=1
  for v in core10 core5 core7 tail4 tail5 tail7; do
    [[ $(cat "$R/nn-native/validation/$v/exit-code" 2>/dev/null) == 0 ]] || SCORE_READY=0
  done
  [[ $SCORE_READY == 1 ]] && break
  kill -0 3417061 2>/dev/null || exit 1
  sleep 30
done
while [[ ! -f "$R/nn-extended/exit-code" ]] && kill -0 3494107 2>/dev/null; do sleep 30; done
[[ $(cat "$R/nn-extended/exit-code") == 0 ]]
python - "$R/nn-extended" <<'PY'
from pathlib import Path
import hashlib,json,sys
r=Path(sys.argv[1]);plan=json.loads((r/'frozen-plan.json').read_text())
assert hashlib.sha256((r/'training.json').read_bytes()).hexdigest()==plan['training_sha256']
for p in (r/'validation').iterdir():
 assert (p/'exit-code').read_text().strip()=='0',p
print('All reconstructions and frozen plan pass',flush=True)
PY
python "$S/nn_analyze.py" evaluate "$R/nn-extended/validation" "$R/nn-extended/validation.json" --plan "$R/nn-extended/training.json" > "$R/nn-extended/validation-analysis.log" 2>&1
python "$S/diagnostics.py" "$R/nn-extended/validation" "$R/nn-extended/training.json" "$R/nn-extended/diagnostics.json"
python "$S/check_main_point.py" "$R/nn-extended"
python "$S/cross_nn.py" "$R" nn-extended > "$R/nn-extended/cross-calibration.log" 2>&1
while [[ $(cat "$R/nn-native/finish-exit-code" 2>/dev/null) != 0 ]] && kill -0 3417061 2>/dev/null; do sleep 30; done
[[ $(cat "$R/nn-native/finish-exit-code") == 0 ]]
printf 'Final expanded NN comparison completed\n' 
