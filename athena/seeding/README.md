# ACTS FT

```
Reco_tf.py \
    --inputRDOFile /cvmfs/atlas-nightlies.cern.ch/repo/data/data-art/PhaseIIUpgrade/RDO/ATLAS-P2-RUN4-03-00-00/mc21_14TeV.601229.PhPy8EG_A14_ttbar_hdamp258p75_SingleLep.recon.RDO.e8481_s4149_r14700/RDO.33629020._000047.pool.root.1 \
    --outputAODFile AOD.acts.root \
    --preInclude "InDetConfig.ConfigurationHelpers.OnlyTrackingPreInclude,ActsConfig.ActsCIFlags.actsWorkflowFlags" \
    --preExec 'flags.Common.MsgSuppression=False; \
    flags.Tracking.doStoreSiSPSeededTracks=True; \
    flags.Tracking.doTruth=True; \
    flags.Tracking.doITkFastTracking=True; \
    flags.Tracking.ITkActsValidateTracksPass.storeSiSPSeededTracks=True; \
    flags.Tracking.writeExtendedSi_PRDInfo=True; \
    flags.Tracking.doStoreTrackSeeds=True; \
    flags.Tracking.ITkActsPass.storeTrackSeeds=True; \
    flags.Tracking.doPixelDigitalClustering=True;' \
    --postExec "cfg.getEventAlgo('ActsPixelSeedingAlg').OutputLevel=1" \
    --maxEvents 1 \
    --perfmon fullmonmt \
    --multithreaded False
```

# ACTS legacy

```
Reco_tf.py \
    --inputRDOFile /cvmfs/atlas-nightlies.cern.ch/repo/data/data-art/PhaseIIUpgrade/RDO/ATLAS-P2-RUN4-03-00-00/mc21_14TeV.601229.PhPy8EG_A14_ttbar_hdamp258p75_SingleLep.recon.RDO.e8481_s4149_r14700/RDO.33629020._000047.pool.root.1 \
    --outputAODFile AOD.acts.root \
    --preInclude "InDetConfig.ConfigurationHelpers.OnlyTrackingPreInclude,ActsConfig.ActsCIFlags.actsLegacyWorkflowFlags" \
    --preExec 'flags.Common.MsgSuppression=False; \
    flags.Tracking.doStoreSiSPSeededTracks=True; \
    flags.Tracking.doTruth=True; \
    flags.Tracking.ITkActsValidateTracksPass.storeSiSPSeededTracks=True; \
    flags.Tracking.writeExtendedSi_PRDInfo=True; \
    flags.Tracking.doStoreTrackSeeds=True; \
    flags.Tracking.ITkActsPass.storeTrackSeeds=True; \
    flags.Tracking.doPixelDigitalClustering=True;' \
    --postExec "cfg.getEventAlgo('ActsLegacyPixelSeedingAlg').OutputLevel=1;cfg.getEventAlgo('ActsLegacyStripSeedingAlg').OutputLevel=1" \
    --maxEvents 1 \
    --perfmon fullmonmt \
    --multithreaded False
```

# ACTS legacy - debug strip seeding

```
Reco_tf.py \
    --inputRDOFile /cvmfs/atlas-nightlies.cern.ch/repo/data/data-art/PhaseIIUpgrade/RDO/ATLAS-P2-RUN4-03-00-00/mc21_14TeV.601229.PhPy8EG_A14_ttbar_hdamp258p75_SingleLep.recon.RDO.e8481_s4149_r14700/RDO.33629020._000047.pool.root.1 \
    --outputAODFile AOD.acts.root \
    --preInclude "InDetConfig.ConfigurationHelpers.OnlyTrackingPreInclude,ActsConfig.ActsCIFlags.actsLegacyWorkflowFlags" \
    --preExec 'flags.Common.MsgSuppression=False; \
    flags.Tracking.doStoreSiSPSeededTracks=True; \
    flags.Tracking.doTruth=True; \
    flags.Tracking.ITkActsValidateTracksPass.storeSiSPSeededTracks=True; \
    flags.Tracking.writeExtendedSi_PRDInfo=True; \
    flags.Tracking.doStoreTrackSeeds=True; \
    flags.Tracking.ITkActsPass.storeTrackSeeds=True; \
    flags.Tracking.doPixelDigitalClustering=True;' \
    --postExec "cfg.getEventAlgo('ActsLegacyStripSeedingAlg').OutputLevel=1" \
    --maxEvents 1 \
    --perfmon fullmonmt \
    --multithreaded False
```
