#!/bin/bash
# usage: rz2_job.sh <old|new> <ckf|rz> <ttbar|pt10|pt100> <nevents> <dir> [idpvm] [postExec]
# One reconstruction job, old = athena-build-rz (nightly 2026-09-04, rz-on-v47.6.1),
# new = athena-build-rz2 (nightly 2026-09-15, feat-rz-track-finder on v47.7.0).
# newgrid = the new build with GridTriplet pixel seeding on both ACTS passes,
# which is what the old nightly ran; new runs the new default, GBTS.
# The environment is sourced here so that one caller can alternate the builds.
SIDE=$1; V=$2; SAMPLE=$3; NEV=$4; DIR=$5; IDPVM=${6:-0}; EXTRA=${7:-}
ACI=/home/astefl/source/acts/acts-athena-ci
R=$ACI/run
case $SIDE in
  old) source /home/astefl/scripts/athena/acts-athena-ci/rz-track-finder/rzrunenv.sh >/dev/null 2>&1 ;;
  new) source /home/astefl/scripts/athena/acts-athena-ci/rz-track-finder/rz2runenv.sh >/dev/null 2>&1 ;;
  newgrid) source /home/astefl/scripts/athena/acts-athena-ci/rz-track-finder/rz2runenv.sh >/dev/null 2>&1
    SEEDPRE='from ActsConfig.ActsConfigFlags import SeedingStrategy; flags.Tracking.ITkActsPass.PixelSeedingStrategy=SeedingStrategy.GridTriplet; flags.Tracking.ITkActsLargeRadiusPass.PixelSeedingStrategy=SeedingStrategy.GridTriplet;' ;;
  *) echo "unknown side $SIDE"; exit 1 ;;
esac
case $V in
  ckf) STRAT='TrackFindingStrategy.Ckf' ;;
  rz)  STRAT='TrackFindingStrategy.Rz' ;;
  *) echo "unknown variant $V"; exit 1 ;;
esac
conditions=$(python -c "from AthenaConfiguration.TestDefaults import defaultConditionsTags; print(defaultConditionsTags.RUN4_MC)")
PRE="InDetConfig.ConfigurationHelpers.OnlyTrackingPreInclude,ActsConfig.ActsCIFlags.actsProductionFlags"
case $SAMPLE in
  ttbar) input=$(python -c "from AthenaConfiguration.TestDefaults import defaultTestFiles; print(defaultTestFiles.RDO_RUN4[0])") ;;
  pt10|pt100) input=$R/mu_${SAMPLE}/RDO.pool.root; PRE="Campaigns.MC23PhaseIINoPileUp,$PRE" ;;
  *) echo "unknown sample $SAMPLE"; exit 1 ;;
esac
rm -rf $DIR; mkdir -p $DIR; cd $DIR
echo "$SIDE $V $SAMPLE $NEV $(date +%T) load=$(cut -d' ' -f1 /proc/loadavg) $AtlasBuildStamp" > job.txt
export ATHENA_CORE_NUMBER=1
Reco_tf.py --maxEvents $NEV --perfmon 'fullmonmt' --multithreaded 'False' \
  --conditionsTag "all:${conditions}" \
  --preInclude "$PRE" \
  --steering 'doRAWtoALL' \
  --preExec "flags.Exec.FPE=-1; from ActsConfig.ActsConfigFlags import TrackFindingStrategy; flags.Acts.TrackFindingStrategy=${STRAT}; ${SEEDPRE:-}" \
  --postExec "${EXTRA}" \
  --inputRDOFile ${input} --outputAODFile 'myAOD.pool.root' > reco.log 2>&1
echo "RECO RC=$?"
echo "done $(date +%T) load=$(cut -d' ' -f1 /proc/loadavg)" >> job.txt
[ "$IDPVM" = 1 ] || exit 0
[ -f myAOD.pool.root ] || { echo "no AOD"; exit 1; }
runIDPVM.py --filesInput myAOD.pool.root --outputFile idpvm.root \
            --doTightPrimary --doExpertPlots --HSFlag All > idpvm.log 2>&1
echo "IDPVM RC=$?"
