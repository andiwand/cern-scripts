#!/usr/bin/env bash
# Compile validate.cpp against an existing ACTS build tree, without CMake.
#
#   ./build.sh SOURCE BUILD OUT
#
# SOURCE  ACTS source tree with GenericRungeKuttaStepper (acts#6211)
# BUILD   matching build tree with lib/libActsCore.dylib
# OUT     output binary
set -euo pipefail

source_dir=$(cd "$1" && pwd)
build_dir=$(cd "$2" && pwd)
out=$3
here=$(cd "$(dirname "$0")" && pwd)

# Reuse the include paths of the Core library from the build tree
deps=$(grep -o -- '-isystem [^ ]*' "$build_dir/build.ninja" | sort -u | tr '\n' ' ')

clang++ -std=c++20 -O2 -g -DNDEBUG -arch arm64 \
  -isysroot "$(xcrun --show-sdk-path)" \
  -I"$build_dir/Core/include" -I"$source_dir/Core/include" $deps \
  "$here/validate.cpp" -o "$out" \
  -Wl,-rpath,"$build_dir/lib" "$build_dir/lib/libActsCore.dylib"
