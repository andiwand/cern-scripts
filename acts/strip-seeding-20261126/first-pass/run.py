#!/usr/bin/env python3
"""Strip-only seed comparison, no pixel seeds or track finding; serial Athena."""
import argparse,json,sys
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument('--events',type=int,default=20)
p.add_argument('--skip',type=int,default=0)
p.add_argument('--input',default='/home/astefl/source/acts/acts-athena-ci/run/gbts-seed-split/input/RDO.39626672._000001.pool.root.1')
p.add_argument('--variants',help='JSON object: GBTS name -> tool property overrides')
p.add_argument('--no-legacy',action='store_true')
p.add_argument('--no-grid',action='store_true')
args=p.parse_args()
from AthenaConfiguration.AllConfigFlags import initConfigFlags
from AthenaConfiguration.DetectorConfigFlags import setupDetectorFlags
from AthenaConfiguration.TestDefaults import defaultConditionsTags
flags=initConfigFlags()
flags.Input.Files=args.input.split(',')
flags.IOVDb.GlobalTag=defaultConditionsTags.RUN4_MC
setupDetectorFlags(flags,['ITkPixel','ITkStrip'],toggle_geometry=True)
flags.Concurrency.NumThreads=0
flags.Exec.MaxEvents=args.events
flags.Exec.SkipEvents=args.skip
flags.Exec.FPE=-1
flags.Tracking.doITkFastTracking=False
flags.Acts.useCache=False
flags.PerfMon.doFullMonMT=True
flags.lock()
af=flags.cloneAndReplace('Tracking.ActiveConfig','Tracking.ITkActsPass')
lf=flags.cloneAndReplace('Tracking.ActiveConfig','Tracking.ITkMainPass')
from AthenaConfiguration.MainServicesConfig import MainServicesCfg
from AthenaPoolCnvSvc.PoolReadConfig import PoolReadCfg
from AthenaConfiguration.ComponentFactory import CompFactory
cfg=MainServicesCfg(flags)
cfg.merge(PoolReadCfg(flags))
from PixelGeoModelXml.ITkPixelGeoModelConfig import ITkPixelReadoutGeometryCfg
# The shared GBTS layer tool requires both geometry managers even for strip-only seeding.
cfg.merge(ITkPixelReadoutGeometryCfg(flags))
from xAODTruthCnv.xAODTruthCnvConfig import GEN_AOD2xAODCfg
cfg.merge(GEN_AOD2xAODCfg(flags,WriteInTimePileUpTruth=True))
from ActsConfig.ActsRegionsOfInterestConfig import ActsMainRegionsOfInterestCreatorAlgCfg
cfg.merge(ActsMainRegionsOfInterestCreatorAlgCfg(af))
from ActsConfig.ActsClusterizationConfig import ActsStripClusterizationAlgCfg
cfg.merge(ActsStripClusterizationAlgCfg(af))
from ActsConfig.ActsSpacePointFormationConfig import ActsStripSpacePointFormationAlgCfg
cfg.merge(ActsStripSpacePointFormationAlgCfg(af))
from ActsConfig.ActsTruthConfig import ActsStripClusterToTruthAssociationAlgCfg
cfg.merge(ActsStripClusterToTruthAssociationAlgCfg(af))
from ActsConfig.ActsSeedingConfig import ActsStripSeedingAlgCfg,ActsStripGbtsSeedingToolCfg,ActsStripGbtsTunedSeedingToolCfg,ActsStripGridTripletSeedingToolCfg,ActsGbtsLayerToolCfg
variants=json.loads(Path(args.variants).read_text()) if args.variants else {'gbts':{}}
keys=[]
for name,overrides in variants.items():
    factory=ActsStripGbtsTunedSeedingToolCfg if 'workingPoint' in overrides else ActsStripGbtsSeedingToolCfg
    tool=cfg.popToolsAndMerge(factory(af,name='Gbts_'+name,**overrides))
    cfg.merge(ActsStripSeedingAlgCfg(af,name='Seed_'+name,SeedTool=tool,OutputSeeds=name))
    keys.append(name)
if not args.no_grid:
    tool=cfg.popToolsAndMerge(ActsStripGridTripletSeedingToolCfg(af))
    cfg.merge(ActsStripSeedingAlgCfg(af,name='Seed_grid',SeedTool=tool,OutputSeeds='grid'))
    keys.append('grid')
legacy={}
if not args.no_legacy:
    from InDetConfig.InDetPrepRawDataFormationConfig import ITkXAODToInDetClusterConversionCfg
    cfg.merge(ITkXAODToInDetClusterConversionCfg(flags,ProcessPixel=False))
    from InDetConfig.SiSpacePointFormationConfig import ITkStripSiTrackerSpacePointFinderCfg
    cfg.merge(ITkStripSiTrackerSpacePointFinderCfg(flags,SpacePointsSCTName='LegacyStripSpacePoints',SpacePointsOverlapName='LegacyOverlapSpacePoints'))
    from InDetConfig.SiSpacePointsSeedToolConfig import ITkSiSpacePointsSeedMakerCfg
    legacy['LegacyTool']=cfg.popToolsAndMerge(ITkSiSpacePointsSeedMakerCfg(lf,usePixel=False,useStrip=True,useFastTracking=False,SpacePointsStripName='LegacyStripSpacePoints',SpacePointsOverlapName='LegacyOverlapSpacePoints'))
layer_tool=cfg.popToolsAndMerge(ActsGbtsLayerToolCfg(af,name='StudyGbtsLayers',dumpGbtsGeometry=True,geometryDump='gbts-geometry.txt'))
cfg.addEventAlgo(CompFactory.StripSeedStudy(Seeds=keys,RunLegacy=not args.no_legacy,LayerTool=layer_tool,**legacy))
cfg.printConfig(withDetails=True,summariseProps=True)
cfg.store(open('config.pkl','wb'))
Path('variants.json').write_text(json.dumps(variants,indent=2)+'\n')
sys.exit(not cfg.run().isSuccess())
