#!/usr/bin/env bash
set -eo pipefail
variant=$1
out=$2
shift 2
base=${ACTS_EDM_EXPERIMENT_ROOT:-/private/tmp/acts-edm-2026-10-31}
. /Users/andreas/cern/source/acts/ci-dependencies/.python-env/bin/activate
edm_view=/Users/andreas/cern/source/acts/ci-dependencies/.spack-env/view
export ROOTSYS=$("$edm_view/bin/root-config" --prefix)
export DYLD_LIBRARY_PATH="$ROOTSYS/lib/root:$edm_view/lib"
export LD_LIBRARY_PATH="$DYLD_LIBRARY_PATH"
export DD4HEP_LIBRARY_PATH="$edm_view/lib"
export DD4hepINSTALL="$edm_view"
export PYTHONPATH="$ROOTSYS/lib/root"
export ROOT_INCLUDE_PATH="$edm_view/include:$edm_view/include/root"
export LC_ALL=C
. "$base/build-$variant/this_acts.sh" >/dev/null
export PYTHONPATH="$base/$variant/Examples/Scripts/Python:$PYTHONPATH"
python3 - "$base/build-$variant/python" <<'PYCODE'
import sys
from pathlib import Path
import acts
print("acts from", acts.__file__)
assert Path(acts.__file__).resolve().is_relative_to(Path(sys.argv[1]).resolve())
PYCODE
python3 -u "$base/full_chain_perf.py" "$out" "$@"
