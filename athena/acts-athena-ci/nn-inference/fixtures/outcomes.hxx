#include "xAODTracking/TrackParticleContainer.h"
#include "xAODTruth/TruthParticleContainer.h"
#include "xAODTruth/TruthVertex.h"
#include "AthLinks/ElementLink.h"
#include "TruthUtils/HepMCHelpers.h"
#include "TruthUtils/MagicNumbers.h"
#include <fstream>
#include <map>
#include <set>
#include <cmath>
#include <iomanip>
struct FourwayOutcomes {
 std::ofstream out;
 double minPt;
 bool gun;
 FourwayOutcomes(const std::string& path,double threshold,bool single):out(path),minPt(threshold),gun(single){out<<std::setprecision(12);}
 static std::uint64_t key(const xAOD::TruthParticle& t){
  std::uint64_t h=14695981039346656037ULL;
  auto add=[&](auto v){const auto* b=reinterpret_cast<const unsigned char*>(&v);for(std::size_t i=0;i<sizeof(v);++i){h^=b[i];h*=1099511628211ULL;}};
  add(t.uid());add(t.pdgId());add(t.px());add(t.py());add(t.pz());add(t.e());
  if(t.hasProdVtx()){add(t.prodVtx()->x());add(t.prodVtx()->y());add(t.prodVtx()->z());}
  return h;
 }
 bool selected(const xAOD::TruthParticle& t)const{
  return t.pt()>minPt && std::abs(t.eta())<4 && !t.isNeutral() && MC::isStable(&t)
   && !HepMC::is_simulation_particle(&t) && (!t.hasProdVtx() || t.prodVtx()->perp()<300);
 }
 static int summary(const xAOD::TrackParticle& t,xAOD::SummaryType type){std::uint8_t v=0;return t.summaryValue(v,type)?v:-1;}
 void event(unsigned long long run,unsigned long long ev,const xAOD::TruthParticleContainer& truth,const xAOD::TrackParticleContainer& tracks){
  static const SG::ConstAccessor<float> probAcc("truthMatchProbability");
  static const SG::ConstAccessor<ElementLink<xAOD::TruthParticleContainer>> linkAcc("truthParticleLink");
  std::map<std::uint64_t,const xAOD::TruthParticle*> eligible;
  for(const auto* t:truth)if(selected(*t)){if(!eligible.emplace(key(*t),t).second)throw std::runtime_error("Duplicate physical truth key");}
  if(gun && eligible.size()!=1)throw std::runtime_error("Gun event does not have exactly one selected primary");
  std::map<std::uint64_t,unsigned> counts;
  unsigned total=0,fakes=0,half=0;
  for(std::size_t i=0;i<tracks.size();++i){
   const auto& tr=*tracks[i];
   const float prob=probAcc.isAvailable(tr)?probAcc(tr):std::nanf("");
   const xAOD::TruthParticle* tp=nullptr;
   if(linkAcc.isAvailable(tr)&&linkAcc(tr).isValid())tp=*linkAcc(tr);
   const auto id=tp?key(*tp):0;
   const bool sel=eligible.count(id);
   if(sel && std::isfinite(prob) && prob>.5)++counts[id];
   const bool inEta=std::abs(tr.eta())<4;
   const bool fake=!std::isfinite(prob)||prob<.5;
   total+=inEta;fakes+=inEta&&fake;half+=inEta&&prob==.5;
   out<<"R "<<run<<' '<<ev<<' '<<i<<' '<<id<<' '<<sel<<' '<<prob<<' '<<tr.pt()<<' '<<tr.eta()<<' '<<tr.phi()<<' '<<tr.d0()<<' '<<tr.z0()<<' '<<tr.chiSquared()<<' '<<tr.numberDoF();
   for(auto type:{xAOD::numberOfPixelHits,xAOD::numberOfSCTHits,xAOD::numberOfPixelHoles,xAOD::numberOfSCTHoles,xAOD::numberOfPixelOutliers,xAOD::numberOfSCTOutliers,xAOD::numberOfPixelSharedHits,xAOD::numberOfSCTSharedHits,xAOD::numberOfPixelSplitHits})out<<' '<<summary(tr,type);
   out<<' '<<(tp?tp->pdgId():0)<<' '<<(tp?tp->pt():0)<<' '<<(tp?tp->eta():0)<<'\n';
  }
  unsigned matched=0,duplicated=0;
  for(const auto& [id,tp]:eligible){
   const auto n=counts[id];matched+=n>0;duplicated+=n>1;
   const auto* pv=tp->hasProdVtx()?tp->prodVtx():nullptr;
   const auto* dv=tp->hasDecayVtx()?tp->decayVtx():nullptr;
   out<<"T "<<run<<' '<<ev<<' '<<id<<' '<<tp->pdgId()<<' '<<tp->pt()<<' '<<tp->eta()<<' '<<tp->phi()<<' '<<(pv?pv->x():0)<<' '<<(pv?pv->y():0)<<' '<<(pv?pv->z():0)<<' '<<(dv?dv->perp():-1)<<' '<<(dv?dv->z():0)<<' '<<(dv?dv->nOutgoingParticles():0)<<' '<<n<<' '<<tp->uid()<<'\n';
   if(dv)for(std::size_t j=0;j<dv->nOutgoingParticles();++j){
    const auto* c=dv->outgoingParticle(j);if(!c)continue;
    out<<"D "<<run<<' '<<ev<<' '<<id<<' '<<key(*c)<<' '<<c->pdgId()<<' '<<c->pt()<<' '<<c->eta()<<' '<<c->phi()<<'\n';
   }
  }
  out<<"E "<<run<<' '<<ev<<' '<<eligible.size()<<' '<<matched<<' '<<duplicated<<' '<<total<<' '<<fakes<<' '<<half<<'\n';
 }
 void close(){out.close();}
};
