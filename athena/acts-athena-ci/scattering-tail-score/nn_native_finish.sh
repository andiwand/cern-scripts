#!/bin/bash
# All-charge NN follow-up; original study and build remain immutable.
SCORE_SCRIPTS=/home/astefl/scripts/athena/acts-athena-ci/scattering-tail-score
SCORE_RUN=/home/astefl/source/acts/acts-athena-ci/run/scattering-tail-score
source /home/astefl/scripts/athena/acts-athena-ci/scattering-tail/env.sh
set -e
mkdir "$SCORE_RUN/nn-native"
trap 'echo $? > "$SCORE_RUN/nn-native/finish-exit-code"' EXIT
for v in core7 tail5; do
  python "$SCORE_SCRIPTS/compare_nn_backend.py" "$SCORE_RUN/nn-pilot/$v" "$SCORE_RUN/nn-native-pilot/$v" "$SCORE_RUN/nn-native/pilot-$v.json"
done
cp "$SCORE_SCRIPTS/run_nn_native.sh" "$SCORE_SCRIPTS/nn_native_config.py" "$SCORE_SCRIPTS/nn_analyze.py" "$SCORE_RUN/nn-native/"
python "$SCORE_SCRIPTS/nn_native_batch.py" "$SCORE_RUN/nn-native/training" 200 0 core4 core5 core7 core10 tail4 tail5 tail7 --parallel 3
for v in core4 core5 core7; do
  while [[ ! -f "$SCORE_RUN/nn/training/$v/exit-code" ]]; do sleep 15; done
  [[ $(cat "$SCORE_RUN/nn/training/$v/exit-code") == 0 ]]
  python "$SCORE_SCRIPTS/compare_nn_backend.py" "$SCORE_RUN/nn/training/$v" "$SCORE_RUN/nn-native/training/$v" "$SCORE_RUN/nn-native/backend-$v.json"
done
python "$SCORE_SCRIPTS/nn_analyze.py" tune "$SCORE_RUN/nn-native/training" "$SCORE_RUN/nn-native/training.json" --reference-plan "$SCORE_RUN/training.json" > "$SCORE_RUN/nn-native/tuning.log" 2>&1
python "$SCORE_SCRIPTS/freeze.py" "$SCORE_RUN/nn-native"
SCORE_VARIANTS=$(python -c 'import json,sys;print(" ".join(json.load(open(sys.argv[1]))["validation_variants"]))' "$SCORE_RUN/nn-native/frozen-plan.json")
python "$SCORE_SCRIPTS/nn_native_batch.py" "$SCORE_RUN/nn-native/validation" 800 200 $SCORE_VARIANTS --parallel 3
python "$SCORE_SCRIPTS/nn_analyze.py" evaluate "$SCORE_RUN/nn-native/validation" "$SCORE_RUN/nn-native/validation.json" --plan "$SCORE_RUN/nn-native/training.json" > "$SCORE_RUN/nn-native/validation-analysis.log" 2>&1
python "$SCORE_SCRIPTS/diagnostics.py" "$SCORE_RUN/nn-native/validation" "$SCORE_RUN/nn-native/training.json" "$SCORE_RUN/nn-native/diagnostics.json"
python -c 'import hashlib,json,sys;from pathlib import Path;p=Path(sys.argv[1]);assert hashlib.sha256((p/"training.json").read_bytes()).hexdigest()==json.loads((p/"frozen-plan.json").read_text())["training_sha256"];print("NN follow-up completed; frozen choices unchanged")' "$SCORE_RUN/nn-native"
