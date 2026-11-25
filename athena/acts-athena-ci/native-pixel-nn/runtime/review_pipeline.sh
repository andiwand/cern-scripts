#!/usr/bin/env bash
# Run after building and validating the final review sources; no concurrent builds.
set -eo pipefail
review_scripts=/home/astefl/scripts/athena/acts-athena-ci/native-pixel-nn
review_results=/home/astefl/source/acts/acts-athena-ci/run/native-pixel-nn/mr-review
review_input=/home/astefl/source/acts/acts-athena-ci/run/edge-holes/input/RDO.39626672._000001.pool.root.1
set +e
source "$review_scripts/env.sh" > "$review_results/timing-env.log" 2>&1
source /home/astefl/source/acts/acts-athena-ci/athena-build-native-pixel-nn/x86_64-el9-gcc15-opt/setup.sh >> "$review_results/timing-env.log" 2>&1
set -euo pipefail
unset NATIVE_NN_STAGE NATIVE_NN_THRESHOLD
python3 "$review_scripts/runtime/review_time.py" > "$review_results/standalone/timing.log" 2>&1
bash "$review_scripts/run.sh" "$review_results/physics/Native" Native 100 "$review_input" 4
bash "$review_scripts/extract.sh" "$review_results/physics/Native" 100 > "$review_results/physics/Native/extract.log" 2>&1
for review_backend in OnnxRuntime Native; do
 taskset -c 16 bash "$review_scripts/run.sh" "$review_results/timing/c1/$review_backend" "$review_backend" 20 "$review_input" 0
done
python3 "$review_scripts/summarize.py" "$review_results" > "$review_results/analysis.log"
python3 "$review_scripts/compare_records.py" Native "$review_results" >> "$review_results/analysis.log"
