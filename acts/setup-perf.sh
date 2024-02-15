#!/bin/zsh

script=$(readlink -f "$0")
script_dir=$(dirname "$script")

. "$script_dir/setup-dev.sh"

cmake -S "$source" -B "$build" \
  -DCMAKE_BUILD_TYPE=Release \
  -DACTS_FORCE_ASSERTIONS=OFF
