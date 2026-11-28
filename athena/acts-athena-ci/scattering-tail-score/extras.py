#!/usr/bin/env python3
"""Read-only diagnostic export: hit summaries and 0.5–1 GeV truth acceptance."""
from pathlib import Path
import sys
import ROOT

ROOT.xAOD.Init().ignore()
ROOT.gInterpreter.Declare(
    Path(__file__).with_name("extract.hxx").read_text()
    + r"""
struct TailExtraWriter {
 std::ofstream out;
 TailExtraWriter(const std::string& path):out(path){out<<std::setprecision(17);}
 void event(unsigned long long run,unsigned long long ev,const xAOD::TruthParticleContainer& truth,const xAOD::TrackParticleContainer& tracks){
  for(const auto* p:truth)if(p->pt()>500 && p->pt()<=1000 && std::abs(p->eta())<4 && !p->isNeutral() && MC::isStable(p) && !HepMC::is_simulation_particle(p) && (!p->hasProdVtx() || p->prodVtx()->perp()<300))
   out<<"P "<<run<<' '<<ev<<' '<<TailScoreWriter::key(*p)<<' '<<p->pt()/1000<<' '<<p->eta()<<'\n';
  static const SG::ConstAccessor<ElementLink<xAOD::TruthParticleContainer>> link("truthParticleLink");
  for(std::size_t i=0;i<tracks.size();++i){
   const auto& t=*tracks[i];const xAOD::TruthParticle* p=nullptr;
   if(link.isAvailable(t)&&link(t).isValid())p=*link(t);
   out<<"R "<<run<<' '<<ev<<' '<<i<<' '<<(p?TailScoreWriter::key(*p):0)<<' '<<(p?p->pt()/1000:NAN)<<' '<<(p?p->eta():NAN);
   for(auto type:{xAOD::numberOfPixelHits,xAOD::numberOfSCTHits,xAOD::numberOfPixelHoles,xAOD::numberOfSCTHoles,xAOD::numberOfPixelOutliers,xAOD::numberOfSCTOutliers,xAOD::numberOfPixelSharedHits,xAOD::numberOfSCTSharedHits}){
    std::uint8_t v=0;out<<' '<<(t.summaryValue(v,type)?static_cast<int>(v):-1);
   }
   out<<'\n';
  }
 }
 void close(){out.close();}
};
"""
)
chain = ROOT.TChain("CollectionTree")
assert chain.Add(sys.argv[1])
tree = ROOT.xAOD.MakeTransientTree(chain)
ROOT.SetOwnership(chain, False)
ROOT.SetOwnership(tree, False)
out = Path(sys.argv[2])
assert not out.exists(), out
writer = ROOT.TailExtraWriter(str(out))
for i in range(tree.GetEntries()):
    tree.GetEntry(i)
    writer.event(
        tree.EventInfo.runNumber(),
        tree.EventInfo.eventNumber(),
        tree.TruthParticles,
        tree.InDetTrackParticles,
    )
writer.close()
print("Events:", tree.GetEntries())
