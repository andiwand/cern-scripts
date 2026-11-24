#!/usr/bin/env bash
# TARGET BACKEND PRESSURE_BYTES; same cases and library preloads as main study.
set -eo pipefail
nn_target=$1;nn_backend=$2;nn_pressure=$3
set +e
source /home/astefl/scripts/athena/acts-athena-ci/nn-inference/env.sh > /tmp/nn-vector-env.log 2>&1
set -e
nn_build="$NN_STUDY_ROOT/build"
if [[ "$nn_target" == v2 ]]; then nn_build="$NN_STUDY_ROOT/build-x86-v2"; fi
export LD_LIBRARY_PATH="$nn_build:$LD_LIBRARY_PATH"
source "$NN_STUDY_SCRIPTS/athena_preload.sh"
"$nn_build/bench" time "$nn_backend" "$NN_STUDY_ROOT/captured-inputs.bin" 30000 3 "$nn_pressure"
