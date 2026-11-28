#!/bin/bash
# Athena (legacy) vs ACTS tracking on one Run 4 sample: reco both sides, IDPVM both, DCube ACTS vs Athena.
# usage: athena_vs_acts.sh <mu1|mu10|mu100|ttbar200|RDO file> [nevents]
# Output: ~/cern/data/track_finding/run4_athena_vs_acts_<sample>/ (OUT overrides). A side whose AOD.<side>.root is
# already there is not re-run, so ART outputs can be dropped in instead, e.g.
#   https://atlas-art-data.web.cern.ch/atlas-art-data/grid-output/main/Athena/<platform>/<nightly>/InDetPhysValMonitoring/<test>/AOD.root
# env: SIDES (default "acts athena"), NT (threads, default 4), SKIP (events to skip: one event verbose = SKIP=<i> and nevents 1),
#      ACTS_FLAGS (ACTS preInclude, default ActsConfig.ActsCIFlags.actsWorkflowFlags),
#      ACTS_PRE / ACTS_POST (extra pre/postExec of the ACTS side; verbose CKF:
#        ACTS_PRE="flags.Common.MsgSuppression=False;" ACTS_POST="cfg.getEventAlgo('ActsTrackFindingAlg').OutputLevel=1"),
#      DCUBE_XML (default dcube_ART_IDPVMPlots_ITk.xml, looked up in $DATAPATH)
# Needs an Athena release (asetup) in the environment.
D=/cvmfs/atlas-nightlies.cern.ch/repo/data/data-art/PhaseIIUpgrade/RDO/ATLAS-P2-RUN4-03-00-00
S=$1; NEV=$2; pre=""; idpvm=()
case $S in
  mu1) rdo=$D/mc21_14TeV.900492.PG_single_muonpm_Pt1_etaFlatnp0_43.recon.RDO.e8481_s4149_r14697/RDO.33645151._000047.pool.root.1
       pre="flags.Detector.EnableHGTD=False;flags.Detector.GeometryHGTD=False;"; idpvm=(--truthMinPt 999);;
  mu10) rdo=$D/mc21_14TeV.900495.PG_single_muonpm_Pt10_etaFlatnp0_43.recon.RDO.e8481_s4149_r14697/RDO.33675641._000037.pool.root.1;;
  mu100) rdo=$D/mc21_14TeV.900498.PG_single_muonpm_Pt100_etaFlatnp0_43.recon.RDO.e8481_s4149_r14697/RDO.33675668._000016.pool.root.1;;
  ttbar200) rdo=$D/mc21_14TeV.601229.PhPy8EG_A14_ttbar_hdamp258p75_SingleLep.recon.RDO.e8481_s4149_r14700/RDO.33629020._000047.pool.root.1
       NEV=${NEV:-100};;
  *.root*) rdo=$(readlink -f $S); S=$(basename $S | cut -d. -f1-2);;
  *) sed -n '2,14p' $0; exit 1;;
esac
NEV=${NEV:-1000}
OUT=${OUT:-~/cern/data/track_finding/run4_athena_vs_acts_$S}
mkdir -p $OUT && cd $OUT || exit 1
xml=$(find -H ${DATAPATH//:/ } -mindepth 1 -maxdepth 1 -name ${DCUBE_XML:-dcube_ART_IDPVMPlots_ITk.xml} -print -quit 2>/dev/null)
ignore="Acts.+FindingAlg.+ERROR.+Propagation.+reached.+the.+step.+count.+limit,Acts.+FindingAlg.+ERROR.+Propagation.+failed:.+PropagatorError:3.+Propagation.+reached.+the.+configured.+maximum.+number.+of.+steps.+with.+the.+initial.+parameters,Acts.+FindingAlg.+ERROR.+Step.+size.+adjustment.+exceeds.+maximum.+trials,Acts.+FindingAlg.Acts.+ERROR.+CombinatorialKalmanFilter.+failed:.+CombinatorialKalmanFilterError:5.+Propagation.+reaches.+max.+steps.+before.+track.+finding.+is.+finished.+with.+the.+initial.+parameters,Acts.+FindingAlg.Acts.+ERROR.+SurfaceError:1,Acts.+FindingAlg.Acts.+ERROR.+failed.+to.+extrapolate.+track"
export ATHENA_CORE_NUMBER=${NT:-4}

for side in ${SIDES:-acts athena}; do
  if [ ! -f AOD.$side.root ]; then
    if [ $side = acts ]; then inc=",${ACTS_FLAGS:-ActsConfig.ActsCIFlags.actsWorkflowFlags}"; p="$pre${ACTS_PRE}"; post=(${ACTS_POST:+--postExec "$ACTS_POST"})
    else inc=""; p="$pre"; post=(); fi
    echo "== reco $side ($NEV events of $rdo)"
    Reco_tf.py --CA --steering doRAWtoALL \
      --preInclude "InDetConfig.ConfigurationHelpers.OnlyTrackingPreInclude$inc" \
      ${p:+--preExec "$p"} "${post[@]}" --ignorePatterns "$ignore" \
      --inputRDOFile $rdo --outputAODFile AOD.$side.root \
      --perfmon fullmonmt --maxEvents $NEV --skipEvents ${SKIP:-0} --multithreaded > reco.$side.log 2>&1 || { echo "reco $side failed, see $OUT/reco.$side.log"; exit 1; }
    mv log.RAWtoALL log.RAWtoALL.$side
  fi
  echo "== IDPVM $side"
  runIDPVM.py --filesInput AOD.$side.root --outputFile idpvm.$side.root --OnlyTrackingPreInclude \
    --doTightPrimary --doHitLevelPlots --HSFlag All --doExpertPlots "${idpvm[@]}" > idpvm.$side.log 2>&1 || echo "IDPVM $side failed"
done

if [ -f idpvm.acts.root ] && [ -f idpvm.athena.root ] && [ -n "$xml" ]; then
  $ATLAS_LOCAL_ROOT/dcube/current/DCubeClient/python/dcube.py -p -x dcube_acts_athena -c $xml \
    -r idpvm.athena.root -R athena -M acts idpvm.acts.root > dcube.log 2>&1
  echo "== DCube: $OUT/dcube_acts_athena"
fi
