# Environment bootstrap for the vertex-diff plots.  Source it, do not run it.
#
#   source setup_env.sh extract    # AnalysisBase: ROOT + xAOD, for extract_pv.py
#   source setup_env.sh compare    # LCG view: numpy + matplotlib, for compare_pv.py
#
# Two stages, two environments, because no single one has both:
#   - AnalysisBase reads the xAOD but ships no matplotlib.
#   - The LCG view has numpy/matplotlib but no xAOD dictionaries.
# A full Athena release has both, but AnalysisBase is a far smaller download and
# is all extract_pv.py needs -- it only reads the transient tree.
#
# NOTE: never `set -e` or `set -u` around this.  atlasLocalSetup and asetup both
# return non-zero and dereference unset variables, which silently kills the
# calling shell with no output at all.

ANALYSIS_BASE_VERSION="${ANALYSIS_BASE_VERSION:-25.2.107}"
LCG_VIEW="${LCG_VIEW:-/cvmfs/sft.cern.ch/lcg/views/LCG_109/x86_64-el9-gcc13-opt}"

case "${1:-extract}" in
  extract)
    export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase
    source "$ATLAS_LOCAL_ROOT_BASE/user/atlasLocalSetup.sh" --quiet >/dev/null 2>&1
    asetup "AnalysisBase,$ANALYSIS_BASE_VERSION" >/dev/null 2>&1
    ;;
  compare)
    source "$LCG_VIEW/setup.sh" >/dev/null 2>&1
    ;;
  *)
    echo "usage: source setup_env.sh {extract|compare}" >&2
    ;;
esac
