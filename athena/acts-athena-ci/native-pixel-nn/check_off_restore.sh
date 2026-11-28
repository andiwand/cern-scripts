#!/usr/bin/env bash
# Build and test with SICLUSTERIZATION_NATIVE_NN_AVX2=OFF, restore the default ON
# build and check the restored libraries' loaded ELF sections match (build ID excluded).
#   check_off_restore.sh OUT
# Run only after all measurements on the current build have finished.
set -euo pipefail
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
(($# == 1)) || { sed -n '2,5p' "$0" >&2; exit 2; }
out=$(realpath -m "$1")
lib=/home/astefl/source/acts/acts-athena-ci/athena-build-native-pixel-nn/x86_64-el9-gcc15-opt/lib
libraries=("$lib/libSiClusterizationToolLib.so" "$lib/libActsTrackReconstruction.so")
mkdir -p "$out"
sha256sum "${libraries[@]}" > "$out/libraries-before-off.txt"
python3 "$here/elf_sections.py" snapshot "$out/libraries-before-off.json" "${libraries[@]}"
bash "$here/build.sh" -DSICLUSTERIZATION_NATIVE_NN_AVX2=OFF > "$out/final-off-build.log" 2>&1
bash "$here/tests.sh" > "$out/tests-final-off.log" 2>&1
bash "$here/build.sh" > "$out/final-on-restore.log" 2>&1
# Whole-file hashes can differ in nonfunctional metadata; loaded sections decide.
sha256sum -c "$out/libraries-before-off.txt" > "$out/on-restore-check.log" 2>&1 || true
python3 "$here/elf_sections.py" compare "$out/libraries-before-off.json" "$out/restore-equivalence.json"
