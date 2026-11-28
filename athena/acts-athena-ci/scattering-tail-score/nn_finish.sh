#!/bin/bash
# All-charge NN follow-up; original study and build remain immutable.
SCORE_SCRIPTS=/home/astefl/scripts/athena/acts-athena-ci/scattering-tail-score
SCORE_RUN=/home/astefl/source/acts/acts-athena-ci/run/scattering-tail-score
source /home/astefl/scripts/athena/acts-athena-ci/scattering-tail/env.sh
set -e
mkdir "$SCORE_RUN/nn"
trap 'echo $? > "$SCORE_RUN/nn/finish-exit-code"' EXIT
python "$SCORE_SCRIPTS/nn_pilot_audit.py" "$SCORE_RUN"
cp "$SCORE_SCRIPTS/run_nn.sh" "$SCORE_SCRIPTS/nn_config.py" "$SCORE_SCRIPTS/nn_analyze.py" "$SCORE_RUN/nn/"
python "$SCORE_SCRIPTS/nn_batch.py" "$SCORE_RUN/nn/training" 200 0 core4 core5 core7 core10 tail4 tail5 tail7 --parallel 3
python "$SCORE_SCRIPTS/nn_analyze.py" tune "$SCORE_RUN/nn/training" "$SCORE_RUN/nn/training.json" --reference-plan "$SCORE_RUN/training.json" > "$SCORE_RUN/nn/tuning.log" 2>&1
python "$SCORE_SCRIPTS/freeze.py" "$SCORE_RUN/nn"
SCORE_VARIANTS=$(python -c 'import json,sys;print(" ".join(json.load(open(sys.argv[1]))["validation_variants"]))' "$SCORE_RUN/nn/frozen-plan.json")
python "$SCORE_SCRIPTS/nn_batch.py" "$SCORE_RUN/nn/validation" 800 200 $SCORE_VARIANTS --parallel 3
python "$SCORE_SCRIPTS/nn_analyze.py" evaluate "$SCORE_RUN/nn/validation" "$SCORE_RUN/nn/validation.json" --plan "$SCORE_RUN/nn/training.json" > "$SCORE_RUN/nn/validation-analysis.log" 2>&1
python "$SCORE_SCRIPTS/diagnostics.py" "$SCORE_RUN/nn/validation" "$SCORE_RUN/nn/training.json" "$SCORE_RUN/nn/diagnostics.json"
python -c 'import hashlib,json,sys;from pathlib import Path;p=Path(sys.argv[1]);assert hashlib.sha256((p/"training.json").read_bytes()).hexdigest()==json.loads((p/"frozen-plan.json").read_text())["training_sha256"];print("NN follow-up completed; frozen choices unchanged")' "$SCORE_RUN/nn"
