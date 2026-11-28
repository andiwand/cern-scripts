#!/usr/bin/env python3
"""Snapshot/compare the complete Gaudi tool configuration across the inline refactor."""
import argparse,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('mode',choices=['before','after','direct']);p.add_argument('snapshot');p.add_argument('--source');a=p.parse_args()
from AthenaConfiguration.AllConfigFlags import initConfigFlags
from AthenaConfiguration.DetectorConfigFlags import setupDetectorFlags
from AthenaConfiguration.TestDefaults import defaultConditionsTags
flags=initConfigFlags()
flags.Input.Files=['/home/astefl/source/acts/acts-athena-ci/run/gbts-seed-split/input/RDO.39626672._000001.pool.root.1']
flags.IOVDb.GlobalTag=defaultConditionsTags.RUN4_MC
setupDetectorFlags(flags,['ITkPixel','ITkStrip'],toggle_geometry=True)
flags.lock();flags=flags.cloneAndReplace('Tracking.ActiveConfig','Tracking.ITkActsPass')
if a.source:
 import importlib.util
 spec=importlib.util.spec_from_file_location('ActsSeedingConfigUnderTest',a.source)
 c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
else:
 from ActsConfig import ActsSeedingConfig as c

def props(factory,**kw):
 acc=factory(flags,name='ComparisonSeedTool',**kw);tool=acc.popPrivateTools()
 # Include defaults of the C++ component, not only explicitly configured values.
 result={}
 for name in sorted(tool._descriptors):
  try:result[name]=str(getattr(tool,name))
  except AttributeError:pass
 acc.wasMerged()
 return result
old=props(c.ActsStripGbtsSeedingToolCfg)
if a.mode=='before':
 result={'selected':props(c.ActsStripGbtsTunedSeedingToolCfg,workingPoint='relaxed'),
         'old_primary':old,'pixel':props(c.ActsPixelGbtsSeedingToolCfg),
         'lrt':props(c.ActsLargeRadiusStripGbtsSeedingToolCfg),
         'direct_lrt':props(c.ActsStripGbtsSeedingToolCfg,LRTmode=True),
         'custom_table':props(c.ActsStripGbtsSeedingToolCfg,connectorInputFile='custom.txt')}
 Path(a.snapshot).write_text(json.dumps(result,indent=2)+'\n')
 print('Saved full selected, old primary, pixel, LRT and custom-table configurations.')
elif a.mode=='after':
 before=json.loads(Path(a.snapshot).read_text())
 for label,now in [('selected',old),('pixel',props(c.ActsPixelGbtsSeedingToolCfg)),
   ('lrt',props(c.ActsLargeRadiusStripGbtsSeedingToolCfg)),
   ('direct_lrt',props(c.ActsStripGbtsSeedingToolCfg,LRTmode=True)),
   ('custom_table',props(c.ActsStripGbtsSeedingToolCfg,connectorInputFile='custom.txt'))]:
  differences={k:(before[label].get(k),now.get(k)) for k in before[label].keys()|now.keys() if before[label].get(k)!=now.get(k)}
  assert not differences,(label,differences)
 override=props(c.ActsStripGbtsSeedingToolCfg,maxDChi2X=7.,filterMaxZ0=123.,connectionTauCuts=[])
 assert float(override['maxDChi2X'])==7 and float(override['filterMaxZ0'])==123 and override['connectionTauCuts']=='[]'
 print('Full selected configuration identical; pixel, LRT, custom-table behavior and explicit overrides preserved.')

else:
 before=json.loads(Path(a.snapshot).read_text())
 for label,now in [('selected',old),('pixel',props(c.ActsPixelGbtsSeedingToolCfg)),
                   ('lrt',props(c.ActsLargeRadiusStripGbtsSeedingToolCfg))]:
  differences={k:(before[label].get(k),now.get(k)) for k in before[label].keys()|now.keys() if before[label].get(k)!=now.get(k)}
  assert not differences,(label,differences)
 override=props(c.ActsStripGbtsSeedingToolCfg,maxDChi2X=7.,filterMaxZ0=123.,connectionTauCuts=[])
 assert float(override['maxDChi2X'])==7 and float(override['filterMaxZ0'])==123 and override['connectionTauCuts']=='[]'
 lrt_override=props(c.ActsLargeRadiusStripGbtsSeedingToolCfg,maxDChi2X=9.,tauRatioCorrectionStrip=.01)
 assert float(lrt_override['maxDChi2X'])==9 and float(lrt_override['tauRatioCorrectionStrip'])==.01
 renamed=props(c.ActsStripGbtsSeedingToolCfg,connectorInputFile='renamed.txt')
 assert {k:v for k,v in renamed.items() if k!='connectorInputFile'}=={k:v for k,v in old.items() if k!='connectorInputFile'}
 print('Direct defaults equal the validated point; pixel/LRT preserved; explicit overrides work; no table-name conditional.')
