#!/usr/bin/env python3
"""Export IDPVM-style truth/matches, optional likelihoods and prompt residuals."""
from pathlib import Path
import sys
import ROOT

ROOT.xAOD.Init().ignore()
ROOT.gInterpreter.Declare((Path(__file__).with_name("extract.hxx")).read_text())
chain = ROOT.TChain("CollectionTree")
assert chain.Add(sys.argv[1])
tree = ROOT.xAOD.MakeTransientTree(chain)
ROOT.SetOwnership(chain, False)
ROOT.SetOwnership(tree, False)
output = Path(sys.argv[2])
assert not output.exists(), output
if len(sys.argv) > 3:
    assert tree.GetEntries() == int(sys.argv[3]), (tree.GetEntries(), sys.argv[3])
writer = ROOT.TailScoreWriter(str(output))
for i in range(tree.GetEntries()):
    tree.GetEntry(i)
    writer.event(
        tree.EventInfo.runNumber(),
        tree.EventInfo.eventNumber(),
        tree.TruthParticles,
        tree.TruthEvents,
        tree.InDetTrackParticles,
    )
writer.close()
print("Events:", tree.GetEntries())
