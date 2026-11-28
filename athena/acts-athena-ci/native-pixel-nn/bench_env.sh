#!/usr/bin/env bash
# Standalone-bench environment: nn-inference study env plus the Athena build setup.
# Source it from a script (then set your own shell options), or prefix a command:
#   bash bench_env.sh python3 bench_time.py ...
# Exports NATIVE_NN_ROOT/SOURCE/BUILD/LIB; NATIVE_NN_ROOT may be overridden.
bench_env_args=("$@")
bench_env_root=${NATIVE_NN_ROOT:-/home/astefl/source/acts/acts-athena-ci}
set +e
source /home/astefl/scripts/athena/acts-athena-ci/nn-inference/env.sh > /tmp/native-pixel-nn-bench-env.log 2>&1
source "$bench_env_root/athena-build-native-pixel-nn/x86_64-el9-gcc15-opt/setup.sh" >> /tmp/native-pixel-nn-bench-env.log 2>&1
# The setup scripts can reset inherited variables, so set ours afterwards.
export NATIVE_NN_ROOT=$bench_env_root
export NATIVE_NN_SOURCE=$NATIVE_NN_ROOT/athena-native-pixel-nn
export NATIVE_NN_BUILD=$NATIVE_NN_ROOT/athena-build-native-pixel-nn
export NATIVE_NN_LIB=$NATIVE_NN_BUILD/x86_64-el9-gcc15-opt/lib
if [[ ${BASH_SOURCE[0]} == "$0" ]]; then
 set -e
 exec "${bench_env_args[@]}"
fi
