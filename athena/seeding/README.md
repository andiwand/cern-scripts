# Seeding

`check_counts.sh <fast|legacy> [Default|GridTriplet|ModuleTriplet]` runs the
ActsCheckObjectCounts CI recipe on ttbar mu=200 with one pixel seeding
strategy and prints the ACTS object counts (`ParseActsStatDump.py`), in the
current directory.

```bash
./check_counts.sh legacy GridTriplet                          # 5 events, perfmon
DEBUG=ActsPixelSeedingAlg ./check_counts.sh fast ModuleTriplet  # 1 event, VERBOSE seeding, counts.txt
DEBUG=ActsLegacyStripSeedingAlg MT=1 ./check_counts.sh legacy
```

To look at the seeds themselves, add to the `--preExec` of a reco:
`flags.Tracking.doStoreTrackSeeds=True; flags.Tracking.ITkActsPass.storeTrackSeeds=True;`
and validate them with `runIDPVM.py ... --validateExtraTrackCollections SiSPSeedSegmentsActsPixelTrackParticles --doTechnicalEfficiency`.
