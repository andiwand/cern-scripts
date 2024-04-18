#!/usr/bin/env bash

script=$(readlink -f "$0")
script_dir=$(dirname "$script")

. "$script_dir/setup-dev.sh"

cmake -S "$source" -B "$build" \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CXX_FLAGS_RELEASE="-O3 -DNDEBUG -fno-omit-frame-pointer -mno-omit-leaf-frame-pointer" \
  -DACTS_FORCE_ASSERTIONS=OFF
