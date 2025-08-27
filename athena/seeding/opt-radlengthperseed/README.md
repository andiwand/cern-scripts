# Reference run

```
Reco_tf.py \
    --inputRDOFile /cvmfs/atlas-nightlies.cern.ch/repo/data/data-art/PhaseIIUpgrade/RDO/ATLAS-P2-RUN4-03-00-00/mc21_14TeV.601229.PhPy8EG_A14_ttbar_hdamp258p75_SingleLep.recon.RDO.e8481_s4149_r14700/RDO.33629020._000047.pool.root.1 \
    --outputAODFile AOD.main.root \
    --preInclude "InDetConfig.ConfigurationHelpers.OnlyTrackingPreInclude,ActsConfig.ActsCIFlags.actsWorkflowFlags" \
    --preExec 'flags.Common.MsgSuppression=False; \
    flags.Tracking.doStoreSiSPSeededTracks=True; \
    flags.Tracking.doTruth=True; \
    flags.Tracking.doITkFastTracking=True; \
    flags.Tracking.ITkActsValidateTracksPass.storeSiSPSeededTracks=True; \
    flags.Tracking.writeExtendedSi_PRDInfo=True; \
    flags.Tracking.doStoreTrackSeeds=True; \
    flags.Tracking.ITkActsPass.storeTrackSeeds=True; \
    flags.Tracking.doPixelDigitalClustering=True; \
    flags.Acts.doAnalysis=True; \
    flags.Acts.doAnalysisNtuples=False; \
    flags.DQ.useTrigger=False; \
    flags.Output.HISTFileName="HIST.main.root";' \
    --maxEvents 100 \
    --perfmon fullmonmt \
    --multithreaded False
```

# Changed

```
Reco_tf.py \
    --inputRDOFile /cvmfs/atlas-nightlies.cern.ch/repo/data/data-art/PhaseIIUpgrade/RDO/ATLAS-P2-RUN4-03-00-00/mc21_14TeV.601229.PhPy8EG_A14_ttbar_hdamp258p75_SingleLep.recon.RDO.e8481_s4149_r14700/RDO.33629020._000047.pool.root.1 \
    --outputAODFile AOD.changed.0.05.root \
    --preInclude "InDetConfig.ConfigurationHelpers.OnlyTrackingPreInclude,ActsConfig.ActsCIFlags.actsWorkflowFlags" \
    --preExec 'flags.Common.MsgSuppression=False; \
    flags.Tracking.doStoreSiSPSeededTracks=True; \
    flags.Tracking.doTruth=True; \
    flags.Tracking.doITkFastTracking=True; \
    flags.Tracking.ITkActsValidateTracksPass.storeSiSPSeededTracks=True; \
    flags.Tracking.writeExtendedSi_PRDInfo=True; \
    flags.Tracking.doStoreTrackSeeds=True; \
    flags.Tracking.ITkActsPass.storeTrackSeeds=True; \
    flags.Tracking.doPixelDigitalClustering=True; \
    flags.Acts.doAnalysis=True; \
    flags.Acts.doAnalysisNtuples=False; \
    flags.DQ.useTrigger=False; \
    flags.Output.HISTFileName="HIST.changed.0.05.root";' \
    --postExec "cfg.getEventAlgo('ActsPixelSeedingAlg').SeedTool.radLengthPerSeed=0.05" \
    --maxEvents 100 \
    --perfmon fullmonmt \
    --multithreaded False
```

# IDPVM for efficiency

```
runIDPVM.py \
    --filesInput AOD.main.root \
    --outputFile idpvm.main.root \
    --OnlyTrackingPreInclude \
    --doHitLevelPlots \
    --HSFlag All \
    --doExpertPlots \
    --validateExtraTrackCollections "SiSPSeedSegmentsActsPixelTrackParticles" \
    --doTechnicalEfficiency

runIDPVM.py \
    --filesInput AOD.changed.root \
    --outputFile idpvm.changed.root \
    --OnlyTrackingPreInclude \
    --doHitLevelPlots \
    --HSFlag All \
    --doExpertPlots \
    --validateExtraTrackCollections "SiSPSeedSegmentsActsPixelTrackParticles" \
    --doTechnicalEfficiency

runIDPVM.py \
    --filesInput AOD.changed.0.05.root \
    --outputFile idpvm.changed.0.05.root \
    --OnlyTrackingPreInclude \
    --doHitLevelPlots \
    --HSFlag All \
    --doExpertPlots \
    --validateExtraTrackCollections "SiSPSeedSegmentsActsPixelTrackParticles" \
    --doTechnicalEfficiency
```
