# Athena

## MacOS

The default docker setup of Athena on MacOS is very slow. Better to use a properly virtualized alma9 directly like described here https://atlassoftwaredocs.web.cern.ch/athena/lima/.

## Some recent performance scripts

```bash
# run acts

ATHENA_CORE_NUMBER=20 Reco_tf.py \
    --conditionsTag "default:OFLCOND-MC21-SDR-RUN4-05" \
    --preInclude "InDetConfig.ConfigurationHelpers.OnlyTrackingRecoPreInclude,ActsConfig.ActsCIFlags.actsWorkflowFlags" \
    --preExec "flags.Tracking.writeExtendedSi_PRDInfo=True; \
    	       flags.Acts.doLargeRadius=True;" \
    --inputRDOFile /cvmfs/atlas-nightlies.cern.ch/repo/data/data-art/PhaseIIUpgrade/RDO/ATLAS-P2-RUN4-04-00-00/mc21_14TeV.601229.PhPy8EG_A14_ttbar_hdamp258p75_SingleLep.recon.RDO.e8481_s4494_r16635/RDO.46493535.100evt.pool.root \
    --outputAODFile AOD.root \
    --maxEvents 1000 \
    --multithreaded

# run IDPVM

runIDPVM.py \
    --filesInput AOD.root \
    --outputFile idpvm.root \
    --HSFlag All \
    --doTechnicalEfficiency \
    --doExpertPlots \
    --OnlyTrackingPreInclude

# run dcube

$ATLAS_LOCAL_ROOT/dcube/current/DCubeClient/python/dcube.py \
    -p -x tmp-decube-main-changed \
    -c /home/astefl/source/acts/acts-athena-ci/athena/InnerDetector/InDetValidation/InDetPhysValMonitoring/share/dcube_ART_IDPVMPlots_ITk.xml \
    -r tmp-main/idpvm.root \
    -R "acts-main" \
    -M "acts-changed" \
    tmp-changed/idpvm.root
```
