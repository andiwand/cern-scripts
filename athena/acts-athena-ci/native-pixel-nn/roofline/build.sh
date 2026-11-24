#!/bin/bash
set +e
source /home/astefl/scripts/athena/acts-athena-ci/nn-inference/env.sh > /tmp/native-roofline-env.log 2>&1
set -e
roof_scripts=/home/astefl/scripts/athena/acts-athena-ci/native-pixel-nn/roofline
roof_out=/home/astefl/source/acts/acts-athena-ci/run/native-pixel-nn/roofline
mkdir -p "$roof_out"
for roof_isa in sse avx2; do
 roof_flags='-march=x86-64-v2'
 if [[ $roof_isa == avx2 ]]; then roof_flags="$roof_flags -mavx2 -mfma"; fi
 g++ -O2 -DNDEBUG -std=c++23 $roof_flags -I"$NN_STUDY_LCG/eigen/3.4.1/x86_64-el9-gcc15-opt/include/eigen3" "$roof_scripts/roofline.cxx" -o "$roof_out/$roof_isa"
 objdump -Cd "$roof_out/$roof_isa" > "$roof_out/$roof_isa.asm"
done
