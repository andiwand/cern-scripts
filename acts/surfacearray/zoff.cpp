// Probe: cylinder array whose layer is not centred at z=0 (as the Gen3
// SurfaceArrayNavigationPolicy always builds it: transform = Translation3(0,0,layerZ))
#include "Acts/Geometry/GeometryContext.hpp"
#include "Acts/Geometry/ProtoLayer.hpp"
#include "Acts/Geometry/SurfaceArrayCreator.hpp"
#include "Acts/Surfaces/CylinderSurface.hpp"
#include "Acts/Surfaces/PlaneSurface.hpp"
#include "Acts/Surfaces/RectangleBounds.hpp"
#include "Acts/Surfaces/SurfaceArray.hpp"
#include "Acts/Utilities/Helpers.hpp"
#include <cstdio>
#include <numbers>
#include <random>
#include <set>
using namespace Acts;
using VectorHelpers::perp; using VectorHelpers::phi;

int main(int argc, char** argv){
  const double zShift = (argc>1)? std::stod(argv[1]) : 0.0;
  GeometryContext gctx = GeometryContext::dangerouslyDefaultConstruct();
  const double R=100.; const std::size_t nPhi=20,nZ=20;
  const double modHalfPhi=1.15*std::numbers::pi*R/nPhi, modHalfZ=20., tilt=-0.35, stagger=2., phi0=0.137;
  auto bounds=std::make_shared<RectangleBounds>(modHalfPhi,modHalfZ);
  std::vector<std::shared_ptr<const Surface>> v;
  const double zPitch=2*modHalfZ*0.9;
  for(std::size_t ip=0;ip<nPhi;++ip){
    double ph=phi0+2*std::numbers::pi*ip/nPhi; double r=R+((ip%2==0)?-stagger:stagger);
    for(std::size_t iz=0;iz<nZ;++iz){
      double z=zShift+(static_cast<double>(iz)-0.5*(nZ-1))*zPitch;
      Transform3 t=Transform3::Identity();
      t*=AngleAxis3(ph,Vector3::UnitZ()); t*=Translation3(r,0,z);
      t*=AngleAxis3(std::numbers::pi/2.,Vector3::UnitY()); t*=AngleAxis3(std::numbers::pi/2.,Vector3::UnitZ());
      t*=AngleAxis3(tilt,Vector3::UnitY());
      v.push_back(Surface::makeShared<PlaneSurface>(t,bounds));
    }
  }
  SurfaceArrayCreator::Config cfg; cfg.doPhiBinningOptimization=false;
  SurfaceArrayCreator sac{cfg,getDefaultLogger("sac",Logging::WARNING)};
  ProtoLayer pl(gctx,unpackSmartPointers(v));
  double layerZ = pl.medium(AxisDirection::AxisZ);
  Transform3 layerTransform{Translation3(0,0,layerZ)};   // exactly what the policy does
  auto sa=sac.surfaceArrayOnCylinder(gctx,v,nPhi,nZ,pl,layerTransform,1);
  auto axes=sa.getAxes();
  printf("zShift=%.1f  layerZ(medium)=%.3f  z-axis=[%.3f,%.3f]  protoLayer z=[%.3f,%.3f]\n",
     zShift, layerZ, axes[1]->getBinEdges().front(), axes[1]->getBinEdges().back(),
     pl.min(AxisDirection::AxisZ,false), pl.max(AxisDirection::AxisZ,false));
  const Surface* rep=sa.surfaceRepresentation();
  printf("representative centre z = %.3f\n", (rep->localToGlobalTransform(gctx)*Vector3(0,0,0)).z());

  // ray scan
  auto entry=Surface::makeShared<CylinderSurface>(Transform3::Identity(), pl.min(AxisDirection::AxisR,false)-1.0, 1e5);
  std::mt19937_64 rng(7); std::uniform_real_distribution<double> uphi(-std::numbers::pi,std::numbers::pi);
  std::uniform_real_distribution<double> uzz(pl.min(AxisDirection::AxisZ,false), pl.max(AxisDirection::AxisZ,false));
  std::size_t nT=0,nM=0,nE=0,nR=0,nC=0;
  for(int i=0;i<50000;++i){
    double p=uphi(rng); double zt=uzz(rng);
    Vector3 origin(0,0,zt-1e-9); Vector3 dir(std::cos(p),std::sin(p),0.0); // pure radial, normal incidence
    std::set<const Surface*> truth;
    for(auto& s: v){ auto is=s->intersect(gctx,origin,dir,BoundaryTolerance::None()).closest();
      if(is.isValid()&&is.pathLength()>0) truth.insert(s.get()); }
    if(truth.empty()) continue;
    auto ei=entry->intersect(gctx,origin,dir,BoundaryTolerance::None()).closestForward();
    Vector3 q=ei.isValid()?ei.position():origin;
    ++nR; nT+=truth.size();
    auto found=sa.neighbors(gctx,q,dir);
    if(found.empty()) ++nE; nC+=found.size();
    std::set<const Surface*> fs(found.begin(),found.end());
    for(const Surface* t: truth) if(!fs.contains(t)) ++nM;
  }
  {
    Vector3 origin(0,0,layerZ); Vector3 dir(1,0,0);
    auto ri=rep->intersect(gctx,origin,dir,BoundaryTolerance::Infinite()).closest();
    auto lp = rep->globalToLocal(gctx, ri.position(), dir);
    printf("probe: global z=%.3f -> local (%.3f, %.3f)\n", ri.position().z(), lp.value()[0], lp.value()[1]);
  }
  printf("normal-incidence rays=%zu truth=%zu missed=%zu (%.3f%%) emptyReturns=%zu cand/ray=%.2f\n",
     nR,nT,nM,100.*nM/std::max<std::size_t>(1,nT),nE,(double)nC/std::max<std::size_t>(1,nR));
  return 0;
}
