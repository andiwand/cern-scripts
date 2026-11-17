#!/bin/zsh
B=~/cern/build/acts/acts/gbts-barrel/bin
tag=$1; shift
for s in $(seq 1 20); do
  $B/ActsBenchmarkGbtsSeeding --layout itk --seed $s --runs 0 "$@" 2>&1 | grep -E "^\[gbts\]|efficiency=" | sed "s/^/$tag s$s /"
done
