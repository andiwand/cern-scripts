#!/bin/bash
set -o pipefail
source /home/astefl/scripts/athena/acts-athena-ci/native-pixel-nn/env.sh > /tmp/native-roofline-run-env.log 2>&1
set -e
roof_out=/home/astefl/source/acts/acts-athena-ci/run/native-pixel-nn/roofline
for roof_isa in sse avx2; do
 taskset -c 16 "$roof_out/$roof_isa" .543 > "$roof_out/$roof_isa.jsonl" 2> "$roof_out/$roof_isa.log"
done
