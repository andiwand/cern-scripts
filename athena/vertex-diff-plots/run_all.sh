#!/bin/bash
# Paired vertex-diff plots for the ACTS 47.5.0 bump (athena!90327).
#
#   ./run_all.sh [workdir]              # default workdir: $PWD
#   SAMPLES="q454 q449" ./run_all.sh    # restrict the set
#
# Reads the CI outputs saved on EOS by the frozen-Tier0 check and the matching
# references on cvmfs.  No reco re-run needed.
#
# Needs a Kerberos ticket for the EOS side:  kinit $USER@CERN.CH
# The realm must be UPPERCASE -- `kinit user@cern.ch` fails pre-authentication,
# because only CERN.CH is defined in /etc/krb5.conf.d/cern-realm-cernch.conf.
#
# The two stages set up their own environments (see setup_env.sh), so this runs
# on a bare CERN box with cvmfs -- no asetup needed beforehand.
#
# Deliberately no `set -e` / `set -u`: sourcing atlasLocalSetup or an LCG view
# under either one kills the shell silently, with an empty log and exit 0.
set -o pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK="${1:-$PWD}"
mkdir -p "$WORK/npz" "$WORK/plots"

EOS=/eos/atlas/atlascerngroupdisk/proj-ascig/gitlabci/MR90327_39b6a18ac8b5f4c87c88b10b285298eae939f267
REF=/cvmfs/atlas-nightlies.cern.ch/repo/data/data-art/WorkflowReferences/main

declare -A NEWF=( [q442]=$EOS/RecoRun2Data/myAOD.pool.root
                  [q452]=$EOS/RecoRun2MC/myAOD.pool.root
                  [q449]=$EOS/RecoRun3Data_Checks/myAOD.pool.root
                  [q454]=$EOS/RecoRun3MC/myAOD.pool.root
                  [q447]=$EOS/RecoRun4MC/myAOD.pool.root )
declare -A REFF=( [q442]=$REF/q442/v123/myAOD.pool.root
                  [q452]=$REF/q452/v88/myAOD.pool.root
                  [q449]=$REF/q449/v184/myAOD.pool.root
                  [q454]=$REF/q454/v112/myAOD.pool.root
                  [q447]=$REF/q447/v11/myAOD.pool.root )

SAMPLES="${SAMPLES:-q442 q452 q449 q454 q447}"

echo "== checking inputs"
missing=0
for s in $SAMPLES; do
  for f in "${REFF[$s]}" "${NEWF[$s]}"; do
    if [ -r "$f" ]; then printf '  ok      %s\n' "$f"
    else                 printf '  MISSING %s\n' "$f"; missing=1; fi
  done
done
if [ "$missing" -ne 0 ]; then
  echo
  echo "Some inputs are unreadable."
  echo "  EOS side missing  -> no Kerberos ticket (kinit \$USER@CERN.CH, uppercase realm),"
  echo "                       or the CI scratch area was cleaned; see section 7 of the runbook."
  echo "  cvmfs side missing -> check the reference version directories still exist."
  exit 1
fi

# ---- stage 1: xAOD -> npz, needs AnalysisBase ------------------------------
echo "== extracting"
(
  source "$HERE/setup_env.sh" extract
  for s in $SAMPLES; do
    for side in ref new; do
      out="$WORK/npz/${s}_${side}.npz"
      [ -f "$out" ] && { echo "  have ${s}_${side}"; continue; }
      case $side in ref) in="${REFF[$s]}";; new) in="${NEWF[$s]}";; esac
      echo "  == ${s}_${side}"
      python "$HERE/extract_pv.py" "$in" "$out" || exit 1
    done
  done
) || exit 1

# ---- stage 2: npz -> figures, needs numpy + matplotlib ---------------------
echo "== comparing"
(
  source "$HERE/setup_env.sh" compare
  for s in $SAMPLES; do
    echo "  == $s"
    python "$HERE/compare_pv.py" "$WORK/npz/${s}_ref.npz" "$WORK/npz/${s}_new.npz" \
           "$s" "$WORK/plots/$s" || exit 1
  done
  python "$HERE/affected_fraction.py" "$WORK/npz" | tee "$WORK/plots/affected_fraction.txt"
) || exit 1

cat "$WORK"/plots/*/summary.md > "$WORK/plots/ALL_summary.md"
echo
echo "== done"
echo "   summary : $WORK/plots/ALL_summary.md"
echo "   headline: $WORK/plots/<sample>/fig02_delta_position_pull.png"
