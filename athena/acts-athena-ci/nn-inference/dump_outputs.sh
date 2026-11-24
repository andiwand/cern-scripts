#!/usr/bin/env bash
# INPUTS OUTPUT_DIRECTORY MAX_INPUTS
set -eo pipefail
nn_inputs=$1;nn_output=$2;nn_count=${3:-10000}
set +e
source /home/astefl/scripts/athena/acts-athena-ci/nn-inference/env.sh > /tmp/nn-study-dump-env.log 2>&1
set -e
mkdir -p "$nn_output"
source "$NN_STUDY_SCRIPTS/athena_preload.sh"
for nn_backend in original ort_cached ort_simple direct direct_avx2 sofie sofie_gemv lwtnn lwtnn_double; do
 "$NN_STUDY_ROOT/build/bench" dump "$nn_backend" "$nn_inputs" "$nn_output/$nn_backend.bin" "$nn_count"
done
env -u PYTHONHOME -u PYTHONPATH -u LD_PRELOAD /tmp/nn-model-inspection/bin/python "$NN_STUDY_SCRIPTS/validate.py" "$nn_output"
