#!/usr/bin/env python3
"""Physical truth identity survives differing AOD thinning; job is part of the key."""
import argparse,gzip,shutil
from pathlib import Path
import ROOT
p=argparse.ArgumentParser();p.add_argument('output',type=Path);p.add_argument('input');p.add_argument('--gun',action='store_true');p.add_argument('--events',type=int);a=p.parse_args()
assert not a.output.exists(),a.output
a.output.parent.mkdir(parents=True,exist_ok=True)
ROOT.xAOD.Init().ignore()
ROOT.gInterpreter.Declare(Path(__file__).with_suffix('.hxx').read_text())
chain=ROOT.TChain('CollectionTree');chain.Add(a.input)
tree=ROOT.xAOD.MakeTransientTree(chain)
ROOT.SetOwnership(chain,False);ROOT.SetOwnership(tree,False)
n=tree.GetEntries()
if a.events is not None:assert n==a.events,(n,a.events)
tmp=a.output.with_suffix('.partial')
writer=ROOT.FourwayOutcomes(str(tmp),500 if a.gun else 1000,a.gun)
for i in range(n):
 tree.GetEntry(i)
 writer.event(tree.EventInfo.runNumber(),tree.EventInfo.eventNumber(),tree.TruthParticles,tree.InDetTrackParticles)
writer.close()
compressed=a.output.with_name(a.output.name+'.partial')
with tmp.open('rb') as src,gzip.open(compressed,'wb',compresslevel=3) as dst:shutil.copyfileobj(src,dst)
compressed.replace(a.output);tmp.unlink()
print(a.output,n,'events')
