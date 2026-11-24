#!/usr/bin/env bash
# Run only after the final measurement pipeline has finished.
set -euo pipefail
restore_root=/home/astefl/source/acts/acts-athena-ci
restore_scripts=/home/astefl/scripts/athena/acts-athena-ci/native-pixel-nn
restore_out=$restore_root/run/native-pixel-nn/runtime-final
restore_lib=$restore_root/athena-build-native-pixel-nn/x86_64-el9-gcc15-opt/lib
sha256sum "$restore_lib/libSiClusterizationToolLib.so" "$restore_lib/libActsTrackReconstruction.so" > "$restore_out/libraries-before-off.txt"
bash "$restore_scripts/build.sh" -DSICLUSTERIZATION_NATIVE_NN_AVX2=OFF > "$restore_out/final-off-build.log" 2>&1
bash "$restore_scripts/tests.sh" > "$restore_out/tests-final-off.log" 2>&1
bash "$restore_scripts/build.sh" > "$restore_out/final-on-restore.log" 2>&1
sha256sum -c "$restore_out/libraries-before-off.txt" > "$restore_out/on-restore-check.log"
