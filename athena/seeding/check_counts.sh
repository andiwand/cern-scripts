#!/bin/bash
# ActsCheckObjectCounts-style reco of ttbar mu=200 with one seeding strategy, then ParseActsStatDump.py.
# usage: check_counts.sh <fast|legacy> [Default|GridTriplet|ModuleTriplet]
#   fast:   ActsCIFlags.actsWorkflowFlags
#   legacy: ActsCIFlags.actsLegacyWorkflowFlags, with calo, LRT and low-pT passes
# env: DEBUG=<alg> (e.g. ActsPixelSeedingAlg, ActsLegacyStripSeedingAlg): VERBOSE output of that algorithm,
#        no message suppression, 1 event, counts into counts.txt; otherwise 5 events with perfmon, counts to stdout
#      NEV, INPUT_RDO, MT=1 (--multithreaded, log into reco.log)
WF=$1; STRAT=${2:-Default}
input_rdo=${INPUT_RDO:-/cvmfs/atlas-nightlies.cern.ch/repo/data/data-art/PhaseIIUpgrade/RDO/ATLAS-P2-RUN4-03-00-00/mc21_14TeV.601229.PhPy8EG_A14_ttbar_hdamp258p75_SingleLep.recon.RDO.e8481_s4149_r14700/RDO.33629020._000047.pool.root.1}
log_file="reco.log"
ignore_pattern="ActsLowPtTrackFindingAlg.+ERROR.+Propagation.+reached.+the.+step.+count.+limit,ActsLowPtTrackFindingAlg.+ERROR.+Propagation.+failed:.+PropagatorError:..+Propagation.+reached.+the.+configured.+maximum.+number.+of.+steps.+with.+the.+initial.+parameters"

pre="flags.Exec.FPE=-1; flags.Acts.doITkConversion=True; flags.Tracking.doTruth=False; flags.Tracking.doITkConversion=False; flags.Detector.EnableCalo=True;"
case $WF in
  fast) flags=actsWorkflowFlags;;
  legacy) flags=actsLegacyWorkflowFlags
    pre="$pre flags.Detector.GeometryCalo=True; flags.Detector.EnableLAr=True; flags.Detector.EnableTile=True; flags.Detector.EnableMuon=False; flags.Acts.doLargeRadius=True; flags.Acts.doLowPt=True;";;
  *) echo "usage: check_counts.sh <fast|legacy> [Default|GridTriplet|ModuleTriplet]"; exit 1;;
esac
pre="$pre from ActsConfig.ActsConfigFlags import SeedingStrategy;flags.Acts.SeedingStrategy=SeedingStrategy.$STRAT;"
opts=()
if [ -n "$DEBUG" ]; then
  pre="flags.Common.MsgSuppression=False; $pre"
  opts+=(--postExec "cfg.getEventAlgo('$DEBUG').OutputLevel=1")
  n_events=${NEV:-1}
else
  opts+=(--perfmon fullmonmt)
  n_events=${NEV:-5}
fi

export ATHENA_CORE_NUMBER=1
if [ "${MT:-0}" = 1 ]; then
  Reco_tf.py --preExec "$pre" \
    --preInclude "InDetConfig.ConfigurationHelpers.OnlyTrackingPreInclude,ActsConfig.ActsCIFlags.$flags" \
    "${opts[@]}" --ignorePatterns "${ignore_pattern}" --inputRDOFile ${input_rdo} --outputAODFile AOD.pool.root \
    --maxEvents ${n_events} --multithreaded > ${log_file} 2>&1
else
  Reco_tf.py --preExec "$pre" \
    --preInclude "InDetConfig.ConfigurationHelpers.OnlyTrackingPreInclude,ActsConfig.ActsCIFlags.$flags" \
    "${opts[@]}" --ignorePatterns "${ignore_pattern}" --inputRDOFile ${input_rdo} --outputAODFile AOD.pool.root \
    --maxEvents ${n_events}
fi

rc=$?
if [ $rc != 0 ]; then
    echo ">>>>>>>>>>>>>>>> Reconstruction step just failed:"
    cat ${log_file}
    echo ">>>>>>>>>>>>>>>> here is the full log (log.RAWtoALL):"
    cat log.RAWtoALL
    exit $rc
fi

if [ -n "$DEBUG" ]; then ParseActsStatDump.py --inputFile log.RAWtoALL > counts.txt
else ParseActsStatDump.py --inputFile log.RAWtoALL; fi
