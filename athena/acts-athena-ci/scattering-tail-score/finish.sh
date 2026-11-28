#!/bin/bash
# Continue the authorized study without an SSH connection.
SCORE_SCRIPTS=/home/astefl/scripts/athena/acts-athena-ci/scattering-tail-score
SCORE_RUN=/home/astefl/source/acts/acts-athena-ci/run/scattering-tail-score
while kill -0 2686099 2>/dev/null; do sleep 15; done
source /home/astefl/scripts/athena/acts-athena-ci/scattering-tail/env.sh
set -e
trap 'echo $? > "$SCORE_RUN/finish-exit-code"' EXIT
python "$SCORE_SCRIPTS/freeze.py" "$SCORE_RUN"
SCORE_VARIANTS=$(python -c 'import json,sys;d=json.load(open(sys.argv[1]));print(" ".join(d["validation_variants"]))' "$SCORE_RUN/frozen-plan.json")
python "$SCORE_SCRIPTS/batch.py" "$SCORE_RUN/validation" 800 200 $SCORE_VARIANTS --parallel 3
python "$SCORE_SCRIPTS/analyze.py" evaluate "$SCORE_RUN/validation" "$SCORE_RUN/validation.json" --plan "$SCORE_RUN/training.json" > "$SCORE_RUN/validation-analysis.log" 2>&1
python "$SCORE_SCRIPTS/diagnostics.py" "$SCORE_RUN/validation" "$SCORE_RUN/training.json" "$SCORE_RUN/diagnostics.json"
python -c 'import hashlib,json,sys;from pathlib import Path;p=Path(sys.argv[1]);d=json.loads((p/"frozen-plan.json").read_text());assert hashlib.sha256((p/"training.json").read_bytes()).hexdigest()==d["training_sha256"];print("Frozen plan unchanged; validation and diagnostics complete")' "$SCORE_RUN"
