// Classify misses: which axis is the lookup bin off in?
#include "Acts/Geometry/GeometryContext.hpp"
#include "Acts/Geometry/ProtoLayer.hpp"
#include "Acts/Geometry/SurfaceArrayCreator.hpp"
#include "Acts/Surfaces/CylinderSurface.hpp"
#include "Acts/Surfaces/PlaneSurface.hpp"
#include "Acts/Surfaces/RectangleBounds.hpp"
#include "Acts/Surfaces/SurfaceArray.hpp"
#include "Acts/Utilities/Helpers.hpp"
#include <cmath>
#include <cstdio>
#include <map>
#include <numbers>
#include <random>
#include <set>
#include <string>
using namespace Acts;
using VectorHelpers::perp; using VectorHelpers::phi;

int main(int argc, char** argv) {
  const bool phiOpt = (argc > 1 && std::string(argv[1]) == "opt");
  const std::size_t maxNb = (argc > 2) ? std::stoul(argv[2]) : 1;
  const double binFactor = (argc > 3) ? std::stod(argv[3]) : 1.0;
  const double etaSel = (argc > 4) ? std::stod(argv[4]) : 0.0;

  GeometryContext gctx = GeometryContext::dangerouslyDefaultConstruct();
  const double R=100.; const std::size_t nPhi=20,nZ=30;
  const double modHalfPhi=1.15*std::numbers::pi*R/nPhi, modHalfZ=20., tilt=-0.35, stagger=2., phi0=0.137;
  auto bounds=std::make_shared<RectangleBounds>(modHalfPhi,modHalfZ);
  std::vector<std::shared_ptr<const Surface>> v;
  const double zPitch=2*modHalfZ*0.9;
  for(std::size_t ip=0;ip<nPhi;++ip){
    double ph=phi0+2*std::numbers::pi*ip/nPhi; double r=R+((ip%2==0)?-stagger:stagger);
    for(std::size_t iz=0;iz<nZ;++iz){
      double z=(static_cast<double>(iz)-0.5*(nZ-1))*zPitch;
      Transform3 t=Transform3::Identity();
      t*=AngleAxis3(ph,Vector3::UnitZ()); t*=Translation3(r,0,z);
      t*=AngleAxis3(std::numbers::pi/2.,Vector3::UnitY()); t*=AngleAxis3(std::numbers::pi/2.,Vector3::UnitZ());
      t*=AngleAxis3(tilt,Vector3::UnitY());
      v.push_back(Surface::makeShared<PlaneSurface>(t,bounds));
    }
  }
  SurfaceArrayCreator::Config cfg; cfg.doPhiBinningOptimization=phiOpt;
  SurfaceArrayCreator sac{cfg,getDefaultLogger("sac",Logging::WARNING)};
  ProtoLayer pl(gctx,unpackSmartPointers(v));
  const std::size_t bp=std::max<std::size_t>(1,std::llround(nPhi*binFactor));
  const std::size_t bz=std::max<std::size_t>(1,std::llround(nZ*binFactor));
  auto sa=sac.surfaceArrayOnCylinder(gctx,v,bp,bz,pl,Transform3::Identity(),static_cast<std::uint8_t>(maxNb));
  const Surface* rep=sa.surfaceRepresentation();
  auto axes=sa.getAxes();
  double plo=axes[0]->getBinEdges().front(), phi_hi=axes[0]->getBinEdges().back();
  double zlo=axes[1]->getBinEdges().front(), zhi=axes[1]->getBinEdges().back();
  double pstep=(phi_hi-plo)/axes[0]->getNBins(), zstep=(zhi-zlo)/axes[1]->getNBins();
  printf("# phiOpt=%d maxNb=%zu bins=%zux%zu eta=%.1f  phiaxis=[%.4f,%.4f] (2pi would be %.4f, gap=%.4f = %.2f bins)\n",
    (int)phiOpt,maxNb,bp,bz,etaSel,plo,phi_hi,2*std::numbers::pi,2*std::numbers::pi-(phi_hi-plo),(2*std::numbers::pi-(phi_hi-plo))/pstep);

  auto entry=Surface::makeShared<CylinderSurface>(Transform3::Identity(), pl.min(AxisDirection::AxisR,false)-1.0, pl.max(AxisDirection::AxisZ,false)+50.);
  const Transform3 repInv = rep->localToGlobalTransform(gctx).inverse();
  auto binOf=[&](const Vector3& g)->std::pair<long,long>{
    Vector3 l=repInv*g;
    double lp=phi(l);
    // emulate closed-axis wrap
    double span=phi_hi-plo;
    double u=std::fmod(lp-plo, span); if(u<0) u+=span;
    long ip=static_cast<long>(std::floor(u/pstep));
    long iz=static_cast<long>(std::floor((l.z()-zlo)/zstep));
    return {ip,iz};
  };

  std::mt19937_64 rng(999);
  std::uniform_real_distribution<double> uphi(-std::numbers::pi,std::numbers::pi);
  std::uniform_real_distribution<double> uz(-50.,50.);
  double theta=2*std::atan(std::exp(-etaSel));
  std::map<std::pair<long,long>,long> hist;
  std::size_t nTruth=0,nMiss=0;
  for(int i=0;i<50000;++i){
    double p=uphi(rng), z0=uz(rng);
    Vector3 origin(0,0,z0);
    Vector3 dir(std::sin(theta)*std::cos(p),std::sin(theta)*std::sin(p),std::cos(theta));
    std::set<const Surface*> truth;
    for(auto& s: v){ auto is=s->intersect(gctx,origin,dir,BoundaryTolerance::None()).closest();
      if(is.isValid()&&is.pathLength()>0) truth.insert(s.get()); }
    if(truth.empty()) continue;
    auto ei=entry->intersect(gctx,origin,dir,BoundaryTolerance::None()).closestForward();
    if(!ei.isValid()) continue;
    Vector3 q=ei.position();
    auto found=sa.neighbors(gctx,q,dir);
    std::set<const Surface*> fs(found.begin(),found.end());
    // lookup bin used
    auto ri=rep->intersect(gctx,q,dir,BoundaryTolerance::Infinite()).closest();
    auto qb=binOf(ri.position());
    nTruth+=truth.size();
    for(const Surface* t: truth){
      if(fs.contains(t)) continue;
      ++nMiss;
      // where the truth intersection actually is
      auto is=t->intersect(gctx,origin,dir,BoundaryTolerance::None()).closest();
      auto tb=binOf(is.position());
      long dp=tb.first-qb.first;
      long span=static_cast<long>(bp);
      if(dp>span/2) dp-=span; if(dp<-span/2) dp+=span;
      hist[{dp,tb.second-qb.second}]++;
    }
  }
  printf("truth=%zu missed=%zu (%.3f%%)\n",nTruth,nMiss,100.*nMiss/std::max<std::size_t>(1,nTruth));
  printf("miss distribution (dPhiBin, dZBin) -> count:\n");
  for(auto& [k,c]: hist) printf("   (%+3ld,%+4ld) : %ld\n",k.first,k.second,c);
  return 0;
}
