#!/bin/bash
# Validate the doSecondPassBranchStopper default of MR 92380 (MR build, 20 events serial, default RDO, properties from flags only)
A=/home/astefl/source/acts/acts-athena-ci; R=$A/run/stay-on-seed/stopper-check; mkdir -p $R
PRIM="a=cfg.getEventAlgo('ActsTrackFindingAlg'); a.useTopSpRZboundary=[0.,0.]; a.twoWaySmoothing=True;"
LRT="cfg.getEventAlgo('ActsLargeRadiusTrackFindingAlg').twoWaySmoothing=True;"
SHOW="print('STOPPER primary',cfg.getEventAlgo('ActsTrackFindingAlg').doSecondPassBranchStopper,'lrt',cfg.getEventAlgo('ActsLargeRadiusTrackFindingAlg').doSecondPassBranchStopper);"
run() { local n=$1 pre=$2 post=$3; rm -rf $R/$n; mkdir -p $R/$n
  ( cd $R/$n && source ~/scripts/athena/acts-athena-ci/mr92381/env.sh && source $A/athena-build-mr92380/x86_64-el9-gcc15-opt/setup.sh && \
    EXTRA_PRE="$pre" EXTRA_POST="$post$SHOW" bash ~/scripts/athena/acts-athena-ci/mr92381/spotjob.sh 1 20 serial | sed "s/^/$n /" ) & }
run default "pass" ""
run primrev "flags.Tracking.ITkActsPass.autoReverseSearch=True;" "$PRIM"
run lrtrev "flags.Tracking.ITkActsLargeRadiusPass.autoReverseSearch=True;" "$LRT"
run lrtrev-stop "flags.Tracking.ITkActsLargeRadiusPass.autoReverseSearch=True;" "${LRT}cfg.getEventAlgo('ActsLargeRadiusTrackFindingAlg').doSecondPassBranchStopper=True;"
wait; echo STOPPER_CHECK_DONE
