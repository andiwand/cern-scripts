#!/bin/bash
# usage: rzscan.sh <nevents>
# Vary one RZ cut at a time and read the finder's own finalize line: how many
# measurements it puts on a track, and whether the backward pass ran. Hit
# counts do not care about machine load, so these run in parallel.
source /home/astefl/scripts/athena/acts-athena-ci/rz-track-finder/rzrunenv.sh >/dev/null 2>&1
R=/home/astefl/source/acts/acts-athena-ci/run
NEV=${1:-20}
A=ActsTrackFindingRzAlg
cd $R

declare -A CFG=(
  [base]=""
  [loosechi2]="cfg.getEventAlgo('$A').chi2Cut=50.0;"
  [widewindow]="cfg.getEventAlgo('$A').windowSigmas=10.0; cfg.getEventAlgo('$A').windowMin=3.0;"
  [moreholes]="cfg.getEventAlgo('$A').maxHoles=10; cfg.getEventAlgo('$A').maxConsecutiveHoles=5;"
  [morepercell]="cfg.getEventAlgo('$A').maxMeasurementsPerLayer=4;"
  [fullback]="cfg.getEventAlgo('$A').backwardLayers=0;"
  [nomaterial]="cfg.getEventAlgo('$A').applyMaterial=False;"
  [nodedup]="cfg.getEventAlgo('$A').skipDuplicateSeeds=False;"
)

for name in "${!CFG[@]}"; do
  (
    d=scan_$name; rm -rf $d; mkdir -p $d; cd $d
    input_rdo=$(python -c "from AthenaConfiguration.TestDefaults import defaultTestFiles; print(defaultTestFiles.RDO_RUN4[0])")
    conditions=$(python -c "from AthenaConfiguration.TestDefaults import defaultConditionsTags; print(defaultConditionsTags.RUN4_MC)")
    export ATHENA_CORE_NUMBER=1
    Reco_tf.py \
      --maxEvents $NEV \
      --multithreaded 'False' \
      --conditionsTag "all:${conditions}" \
      --preInclude "InDetConfig.ConfigurationHelpers.OnlyTrackingPreInclude,ActsConfig.ActsCIFlags.actsProductionFlags" \
      --steering 'doRAWtoALL' \
      --preExec "flags.Exec.FPE=-1; from ActsConfig.ActsConfigFlags import TrackFindingStrategy; flags.Acts.TrackFindingStrategy=TrackFindingStrategy.Rz;" \
      --postExec "${CFG[$name]}" \
      --inputRDOFile ${input_rdo} \
      --outputAODFile 'myAOD.pool.root' > reco.log 2>&1
    echo "[$name rc=$?] $(grep -oE 'RZ track finding:.*' log.RAWtoALL 2>/dev/null | head -1)"
  ) &
done
wait
echo "RZSCAN_DONE"
