#!/bin/bash
S=/home/astefl/scripts/athena/acts-athena-ci/scattering-tail-score
R=/home/astefl/source/acts/acts-athena-ci/run/scattering-tail-score
source /home/astefl/scripts/athena/acts-athena-ci/scattering-tail/env.sh
set -e
mkdir "$R/nn-extended"
trap 'echo $? > "$R/nn-extended/exit-code"' EXIT
python - "$R" <<'PY'
from pathlib import Path
import shutil,sys
r=Path(sys.argv[1]);assert shutil.disk_usage(r).free>16*2**30
(r/'nn-extended/training').mkdir()
for p in (r/'nn-native/training').iterdir():
 if p.is_dir():(r/'nn-extended/training'/p.name).symlink_to(p,target_is_directory=True)
PY
bash "$S/run_nn_wide.sh" "$R/nn-extended/training/core14" core14 200 0 4
python "$S/nn_analyze.py" tune "$R/nn-extended/training" "$R/nn-extended/training.json" --reference-plan "$R/training.json" > "$R/nn-extended/tuning.log" 2>&1
python "$S/extend_nn_nominal.py" "$R"
python - "$R" <<'PY'
from pathlib import Path
import json,shutil,sys
r=Path(sys.argv[1]);assert shutil.disk_usage(r).free>14*2**30
(r/'nn-extended/validation').mkdir()
for p in (r/'nn-native/validation').iterdir():
 if p.is_dir():(r/'nn-extended/validation'/p.name).symlink_to(p,target_is_directory=True)
# Later queued tail5/tail7 directories may not exist yet.
for v in json.loads((r/'nn-native/frozen-plan.json').read_text())['validation_variants']:
 p=r/'nn-extended/validation'/v
 if not p.is_symlink():p.symlink_to(r/'nn-native/validation'/v,target_is_directory=True)
PY
bash "$S/run_nn_wide.sh" "$R/nn-extended/validation/core14" core14 800 200 8
