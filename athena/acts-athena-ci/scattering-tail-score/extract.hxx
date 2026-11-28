#include "xAODTracking/TrackParticleContainer.h"
#include "xAODTruth/TruthParticleContainer.h"
#include "xAODTruth/TruthEventContainer.h"
#include "xAODTruth/TruthVertex.h"
#include "AthLinks/ElementLink.h"
#include "TruthUtils/HepMCHelpers.h"
#include "TruthUtils/MagicNumbers.h"
#include <fstream>
#include <set>
#include <cmath>
#include <iomanip>
#include <stdexcept>

struct TailScoreWriter {
  std::ofstream out;
  TailScoreWriter(const std::string& path):out(path) { out<<std::setprecision(17); }
  static std::uint64_t key(const xAOD::TruthParticle& t) {
    // Stable across AOD thinning; uid alone is not unique in pileup.
    std::uint64_t h=14695981039346656037ULL;
    auto add=[&](auto value) { const auto* bytes=reinterpret_cast<const unsigned char*>(&value);
      for(std::size_t i=0;i<sizeof(value);++i){h^=bytes[i];h*=1099511628211ULL;} };
    add(t.uid());add(t.pdgId());add(t.px());add(t.py());add(t.pz());add(t.e());
    if(t.hasProdVtx()){add(t.prodVtx()->x());add(t.prodVtx()->y());add(t.prodVtx()->z());}
    return h;
  }
  static bool selected(const xAOD::TruthParticle& t) {
    return t.pt()>1000 && std::abs(t.eta())<4 && !t.isNeutral() && MC::isStable(&t)
      && !HepMC::is_simulation_particle(&t)
      && (!t.hasProdVtx() || t.prodVtx()->perp()<300);
  }
  void event(unsigned long long run,unsigned long long ev,
             const xAOD::TruthParticleContainer& truth,const xAOD::TruthEventContainer& hard,
             const xAOD::TrackParticleContainer& tracks) {
    static const SG::ConstAccessor<float> probAcc("truthMatchProbability");
    static const SG::ConstAccessor<ElementLink<xAOD::TruthParticleContainer>> linkAcc("truthParticleLink");
    static const SG::ConstAccessor<double> score("scatteringTailScore"), dim("scatteringTailDimensions"),
      weight("scatteringTailWeight"), logl("scatteringTailLogLikelihood");
    std::set<std::uint64_t> hs, ids;
    if(!hard.empty())for(std::size_t i=0;i<hard[0]->nTruthParticles();++i){
      const auto* p=hard[0]->truthParticle(i);if(p)hs.insert(key(*p));
    }
    for(const auto* p:truth)if(selected(*p)){
      const auto id=key(*p);
      if(!ids.insert(id).second)throw std::runtime_error("Duplicate truth fingerprint");
      out<<"P "<<run<<' '<<ev<<' '<<id<<' '<<p->pt()/1000<<' '<<p->eta()<<' '
         <<hs.count(id)<<' '<<(p->hasProdVtx()?p->prodVtx()->perp():-1)<<'\n';
    }
    for(std::size_t i=0;i<tracks.size();++i){
      const auto& tr=*tracks[i];
      const double prob=probAcc.isAvailable(tr)?probAcc(tr):NAN;
      const xAOD::TruthParticle* p=nullptr;
      if(linkAcc.isAvailable(tr) && linkAcc(tr).isValid())p=*linkAcc(tr);
      const auto id=p && selected(*p)?key(*p):0;
      double d0=NAN,z0=NAN,qpt=NAN;
      // Straight-line truth reference, restricted to r_prod < 0.1 mm so the
      // neglected helix correction is negligible at pT > 1 GeV.
      if(id && p->hasProdVtx() && p->prodVtx()->perp()<.1){
        const auto& v=*p->prodVtx();
        const double x=v.x()-tr.vx(), y=v.y()-tr.vy(), phi=p->phi();
        const double theta=2*std::atan(std::exp(-p->eta()));
        d0=tr.d0()-(-x*std::sin(phi)+y*std::cos(phi));
        z0=tr.z0()-(v.z()-tr.vz()-(x*std::cos(phi)+y*std::sin(phi))/std::tan(theta));
        const double trueQpt=p->charge()/p->pt();
        qpt=(tr.qOverP()/std::sin(tr.theta())-trueQpt)/std::abs(trueQpt);
      }
      const bool scored=score.isAvailable(tr);
      if(scored && (!std::isfinite(score(tr)) || !(dim(tr)>0)))throw std::runtime_error("Invalid score");
      out<<"R "<<run<<' '<<ev<<' '<<i<<' '<<id<<' '<<prob<<' '<<tr.pt()/1000<<' '<<tr.eta()
         <<' '<<tr.chiSquared()<<' '<<tr.numberDoF()<<' '<<(scored?score(tr):NAN)
         <<' '<<(scored?dim(tr):NAN)<<' '<<(scored?weight(tr):NAN)<<' '<<(scored?logl(tr):NAN)
         <<' '<<d0<<' '<<z0<<' '<<qpt<<' '<<tr.phi0()<<' '<<tr.d0()<<' '<<tr.z0()
         <<' '<<tr.qOverP()<<' '<<tr.theta()<<'\n';
    }
    out<<"E "<<run<<' '<<ev<<' '<<ids.size()<<' '<<tracks.size()<<'\n';
  }
  void close(){out.close();}
};
