#!/bin/bash
# Full truth links, hit summaries and 0.5-1 GeV truth from retained validation AODs (extras.py, in parallel),
# then why.py: frozen-point gains/losses -> RUN/why.json.
# usage: extras.sh RUN [VARIANT...]   (default: the variants chosen at the 0.995 point; needs their myAOD.pool.root)
S=$(cd "$(dirname "$0")" && pwd)
R=$1; shift
source /home/astefl/scripts/athena/acts-athena-ci/scattering-tail/env.sh
source /home/astefl/source/acts/acts-athena-ci/athena-build-tail-score/x86_64-el9-gcc15-opt/setup.sh
set -e
trap 'echo $? > "$R/extras-exit-code"' EXIT
VARIANTS=${*:-$(python -c 'import json,sys;print(" ".join(sorted({c["variant"] for c in json.load(open(sys.argv[1]))["choices"]["0.995"]["groups"].values()})))' "$R/training.json")}
pids=()
for v in $VARIANTS; do
  python "$S/extras.py" "$R/validation/$v/myAOD.pool.root" "$R/validation/$v/extras.tsv" > "$R/validation/$v/extras.log" 2>&1 &
  pids+=($!)
done
for p in "${pids[@]}"; do wait "$p"; done
python "$S/why.py" "$R" > "$R/why.log" 2>&1
