#!/usr/bin/env bash
# setup-dev.sh <name>, then reconfigure as Release with frame pointers and
# without forced assertions, for timing and profiling. DEPS as in setup-dev.sh.

script=$(readlink -f "$0")
script_dir=$(dirname "$script")

. "$script_dir/setup-dev.sh"

cmake -S "$source" -B "$build" \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CXX_FLAGS_RELEASE="-O3 -DNDEBUG -fno-omit-frame-pointer -mno-omit-leaf-frame-pointer" \
  -DACTS_FORCE_ASSERTIONS=OFF
