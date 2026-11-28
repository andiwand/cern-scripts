#!/bin/bash
source /home/astefl/scripts/athena/acts-athena-ci/scattering-tail/env.sh
source /home/astefl/source/acts/acts-athena-ci/athena-build-tail-score/x86_64-el9-gcc15-opt/setup.sh
set -e
R=/home/astefl/source/acts/acts-athena-ci/run/scattering-tail-score
S=/home/astefl/scripts/athena/acts-athena-ci/scattering-tail-score
python "$S/extras.py" "$R/nn/training/core7/myAOD.pool.root" "$R/nn/training/core7/backend-extras.tsv" > "$R/nn/training/core7/backend-extras.log" 2>&1 & p1=$!
python "$S/extras.py" "$R/nn-native/training/core7/myAOD.pool.root" "$R/nn-native/training/core7/backend-extras.tsv" > "$R/nn-native/training/core7/backend-extras.log" 2>&1 & p2=$!
wait "$p1"
wait "$p2"
python - "$R" <<'PY'
import hashlib,json,sys
from pathlib import Path
root=Path(sys.argv[1]); records={}; hashes={}
for backend in ['nn','nn-native']:
 p=root/backend/'training/core7/backend-extras.tsv'
 records[backend]=sorted(p.read_text().splitlines())
 hashes[backend]=hashlib.sha256(p.read_bytes()).hexdigest()
assert records['nn']==records['nn-native'], 'Full truth links or hit summaries differ'
result=dict(checks='Exact full truth links (including below 1 GeV), eight hit/hole/outlier/shared summaries, and 0.5–1 GeV truth records',records=len(records['nn']),events=200,sha256=hashes)
(root/'nn-native/backend-full-links.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
PY
