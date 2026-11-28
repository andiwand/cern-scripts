#!/bin/bash
# Continue after explicit review of the single native/ONNX track-count difference.
SCORE_SCRIPTS=/home/astefl/scripts/athena/acts-athena-ci/scattering-tail-score
SCORE_RUN=/home/astefl/source/acts/acts-athena-ci/run/scattering-tail-score
source /home/astefl/scripts/athena/acts-athena-ci/scattering-tail/env.sh
set -e
[[ -s "$SCORE_RUN/nn-native/backend-review-core7.json" ]]
[[ -s "$SCORE_RUN/nn-native/backend-core4.json" && -s "$SCORE_RUN/nn-native/backend-core5.json" ]]
cp "$SCORE_RUN/nn-native/finish-exit-code" "$SCORE_RUN/nn-native/strict-backend-stop-code"
trap 'echo $? > "$SCORE_RUN/nn-native/finish-exit-code"' EXIT
python "$SCORE_SCRIPTS/nn_analyze.py" tune "$SCORE_RUN/nn-native/training" "$SCORE_RUN/nn-native/training.json" --reference-plan "$SCORE_RUN/training.json" > "$SCORE_RUN/nn-native/tuning.log" 2>&1
python "$SCORE_SCRIPTS/freeze.py" "$SCORE_RUN/nn-native"
SCORE_VARIANTS=$(python -c 'import json,sys;print(" ".join(json.load(open(sys.argv[1]))["validation_variants"]))' "$SCORE_RUN/nn-native/frozen-plan.json")
SCORE_PARALLEL=$(python - "$SCORE_RUN/nn-native" <<'PYCODE'
from pathlib import Path
import json,os,shutil,sys
root=Path(sys.argv[1]);n=len(json.loads((root/"frozen-plan.json").read_text())["validation_variants"])
free=shutil.disk_usage(root).free
assert free > (3*n+10)*2**30, "Reserve 3 GiB per validation output plus 10 GiB free"
mem=int(next(line.split()[1] for line in Path("/proc/meminfo").read_text().splitlines() if line.startswith("MemAvailable:")))*1024
parallel=max(1,min(n,6,(os.cpu_count()-8)//8,int((mem/2**30-16)//14)))
(root/"validation-resources.json").write_text(json.dumps(dict(variants=n,parallel=parallel,threads_per_job=8,free_bytes=free,available_memory_bytes=mem),indent=2)+"\n")
print(parallel)
PYCODE
)
python "$SCORE_SCRIPTS/nn_native_batch.py" "$SCORE_RUN/nn-native/validation" 800 200 $SCORE_VARIANTS --parallel "$SCORE_PARALLEL"
python "$SCORE_SCRIPTS/nn_analyze.py" evaluate "$SCORE_RUN/nn-native/validation" "$SCORE_RUN/nn-native/validation.json" --plan "$SCORE_RUN/nn-native/training.json" > "$SCORE_RUN/nn-native/validation-analysis.log" 2>&1
python "$SCORE_SCRIPTS/diagnostics.py" "$SCORE_RUN/nn-native/validation" "$SCORE_RUN/nn-native/training.json" "$SCORE_RUN/nn-native/diagnostics.json"
python -c 'import hashlib,json,sys;from pathlib import Path;p=Path(sys.argv[1]);assert hashlib.sha256((p/"training.json").read_bytes()).hexdigest()==json.loads((p/"frozen-plan.json").read_text())["training_sha256"];print("NN follow-up completed; frozen choices unchanged")' "$SCORE_RUN/nn-native"
