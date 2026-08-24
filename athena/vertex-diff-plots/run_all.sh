#!/bin/bash
# Paired vertex-diff plots for the ACTS 47.5.0 bump (athena!90327).
# Run on lxplus, after: setupATLAS && asetup Athena,main,latest && kinit
#
#   ./run_all.sh [workdir]           # default workdir: $PWD
#
# Reads the CI outputs saved on EOS by the frozen-Tier0 check and the matching
# references on cvmfs. No reco re-run needed.
set -u -o pipefail

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
  echo "Some inputs are unreadable. Do you have a Kerberos ticket (kinit)?"
  echo "If the EOS side is gone the area was cleaned - see section 7 of the runbook."
  exit 1
fi

for s in $SAMPLES; do
  echo "== $s"
  [ -f "$WORK/npz/${s}_ref.npz" ] || "$HERE/extract_pv.py" "${REFF[$s]}" "$WORK/npz/${s}_ref.npz" || exit 1
  [ -f "$WORK/npz/${s}_new.npz" ] || "$HERE/extract_pv.py" "${NEWF[$s]}" "$WORK/npz/${s}_new.npz" || exit 1
  "$HERE/compare_pv.py" "$WORK/npz/${s}_ref.npz" "$WORK/npz/${s}_new.npz" "$s" "$WORK/plots/$s" || exit 1
done

cat "$WORK"/plots/*/summary.md > "$WORK/plots/ALL_summary.md"
echo
echo "== done"
echo "   summary : $WORK/plots/ALL_summary.md"
echo "   headline: $WORK/plots/<sample>/fig02_delta_position_pull.png"
