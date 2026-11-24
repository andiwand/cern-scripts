#!/usr/bin/env bash
set -eo pipefail
set +e
source /home/astefl/scripts/athena/acts-athena-ci/nn-inference/env.sh > /tmp/nn-kernels-env.log 2>&1
set -e
source "$NN_STUDY_SCRIPTS/athena_preload.sh"
"$NN_STUDY_ROOT/vectorization/kernels"
