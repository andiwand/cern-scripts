#!/bin/bash
# usage: rzstop.sh <nevents>  -- branch stopper scan, parallel
source /home/astefl/scripts/athena/acts-athena-ci/rz-track-finder/rzrunenv.sh >/dev/null 2>&1
R=/home/astefl/source/acts/acts-athena-ci/run
NEV=${1:-20}
A=ActsTrackFindingRzAlg
cd $R
declare -A CFG=(
  [off]=""
  [pt400]="cfg.getEventAlgo('$A').ptMin=400.0;"
  [pt700]="cfg.getEventAlgo('$A').ptMin=700.0;"
  [pt900]="cfg.getEventAlgo('$A').ptMin=900.0;"
  [layers]="cfg.getEventAlgo('$A').minMeasurementsAtLayer=3; cfg.getEventAlgo('$A').layersForMinMeasurements=5;"
  [both]="cfg.getEventAlgo('$A').ptMin=700.0; cfg.getEventAlgo('$A').minMeasurementsAtLayer=3; cfg.getEventAlgo('$A').layersForMinMeasurements=5;"
)
for name in "${!CFG[@]}"; do
  (
    d=stop_$name; rm -rf $d; mkdir -p $d; cd $d
    input_rdo=$(python -c "from AthenaConfiguration.TestDefaults import defaultTestFiles; print(defaultTestFiles.RDO_RUN4[0])")
    conditions=$(python -c "from AthenaConfiguration.TestDefaults import defaultConditionsTags; print(defaultConditionsTags.RUN4_MC)")
    export ATHENA_CORE_NUMBER=1
    Reco_tf.py --maxEvents $NEV --multithreaded 'False' \
      --conditionsTag "all:${conditions}" \
      --preInclude "InDetConfig.ConfigurationHelpers.OnlyTrackingPreInclude,ActsConfig.ActsCIFlags.actsProductionFlags" \
      --steering 'doRAWtoALL' \
      --preExec "flags.Exec.FPE=-1; from ActsConfig.ActsConfigFlags import TrackFindingStrategy; flags.Acts.TrackFindingStrategy=TrackFindingStrategy.Rz;" \
      --postExec "${CFG[$name]}" \
      --inputRDOFile ${input_rdo} --outputAODFile 'myAOD.pool.root' > reco.log 2>&1
    echo "[$name rc=$?]"
  ) &
done
wait
echo "RZSTOP_DONE"
