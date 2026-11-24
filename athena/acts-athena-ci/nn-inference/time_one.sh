#!/usr/bin/env bash
set -eo pipefail
nn_backend=$1;nn_pressure=$2
set +e
source /home/astefl/scripts/athena/acts-athena-ci/nn-inference/env.sh > /tmp/nn-study-time-env.log 2>&1
set -e
source "$NN_STUDY_SCRIPTS/athena_preload.sh"
nn_build="$NN_STUDY_ROOT/build"
if [[ "$nn_backend" == direct_blocked ]]; then nn_build="$NN_STUDY_ROOT/build-blocked"; fi
export LD_LIBRARY_PATH="$nn_build:$LD_LIBRARY_PATH"
"$nn_build/bench" time "$nn_backend" "$NN_STUDY_ROOT/captured-inputs.bin" 30000 3 "$nn_pressure"
