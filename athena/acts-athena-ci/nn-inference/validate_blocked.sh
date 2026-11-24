#!/usr/bin/env bash
set -eo pipefail
set +e
source /home/astefl/scripts/athena/acts-athena-ci/nn-inference/env.sh > /tmp/nn-blocked-validation-env.log 2>&1
set -e
export LD_LIBRARY_PATH="$NN_STUDY_ROOT/build-blocked:$LD_LIBRARY_PATH"
source "$NN_STUDY_SCRIPTS/athena_preload.sh"
nn_out="$NN_STUDY_ROOT/blocked/validation"
mkdir -p "$nn_out"
cp "$NN_STUDY_ROOT/validation-real-athena/original.bin" "$nn_out/original.bin"
"$NN_STUDY_ROOT/build-blocked/bench" dump direct_blocked "$NN_STUDY_ROOT/captured-inputs.bin" "$nn_out/direct_blocked.bin" 100000
cmp "$nn_out/direct_blocked.bin" "$NN_STUDY_ROOT/validation-real-athena/direct.bin"
env -u PYTHONHOME -u PYTHONPATH -u LD_PRELOAD /tmp/nn-model-inspection/bin/python "$NN_STUDY_SCRIPTS/validate.py" "$nn_out"
