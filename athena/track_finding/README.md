# Track finding: Athena vs ACTS

`athena_vs_acts.sh <mu1|mu10|mu100|ttbar200|RDO file> [nevents]` reconstructs
one Run 4 sample with the legacy Athena tracking and with ACTS, runs IDPVM on
both and a DCube comparison (ACTS vs Athena). Output goes to
`~/cern/data/track_finding/run4_athena_vs_acts_<sample>/`.

```bash
asetup Athena,main,latest
./athena_vs_acts.sh mu10                     # 1000 events
SIDES=acts ACTS_POST="cfg.getEventAlgo('ActsTrackFindingAlg').OutputLevel=1" ./athena_vs_acts.sh ttbar200 5
SIDES=acts SKIP=67 OUT=~/cern/data/track_finding/mu1_evt67 ACTS_PRE="flags.Acts.doPrintTrackStates=True;flags.Common.MsgSuppression=False;" ./athena_vs_acts.sh mu1 1
```

A side whose `AOD.<side>.root` is already in the output directory is not
re-run, so ART grid outputs (`AOD.root` of an ART test, downloaded from
atlas-art-data) can be compared the same way. The sample paths are the
`ATLAS-P2-RUN4-03-00-00` ART RDOs.
