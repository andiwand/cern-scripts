// Gen1 path: LayerCreator::cylinderLayer with an identity transform on a barrel
// that is not centred at z = 0.
#include "Acts/Geometry/GeometryContext.hpp"
#include "Acts/Geometry/LayerCreator.hpp"
#include "Acts/Geometry/CylinderLayer.hpp"
#include "Acts/Geometry/ProtoLayer.hpp"
#include "Acts/Geometry/SurfaceArrayCreator.hpp"
#include "Acts/Propagator/Navigator.hpp"
#include "Acts/Surfaces/CylinderSurface.hpp"
#include "Acts/Surfaces/PlaneSurface.hpp"
#include "Acts/Surfaces/RectangleBounds.hpp"
#include "Acts/Surfaces/SurfaceArray.hpp"
#include "Acts/Utilities/Helpers.hpp"
#include "Acts/Utilities/IAxis.hpp"
#include <cstdio>
#include <numbers>
#include <random>
#include <set>
using namespace Acts;
using VectorHelpers::perp; using VectorHelpers::phi;
int main(int argc,char** argv){
  const double zShift=(argc>1)?std::stod(argv[1]):0.;
  GeometryContext gctx=GeometryContext::dangerouslyDefaultConstruct();
  const double R=100.; const std::size_t nPhi=20,nZ=20;
  const double hPhi=1.15*std::numbers::pi*R/nPhi, hZ=20., tilt=-0.35, stagger=2., phi0=0.137;
  auto bounds=std::make_shared<RectangleBounds>(hPhi,hZ);
  std::vector<std::shared_ptr<const Surface>> v;
  const double zPitch=2*hZ*0.9;
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
  ProtoLayer pl(gctx,unpackSmartPointers(v));
  LayerCreator::Config lc;
  lc.surfaceArrayCreator=std::make_shared<SurfaceArrayCreator>(
      SurfaceArrayCreator::Config{}, getDefaultLogger("s",Logging::WARNING));
  LayerCreator creator{lc,getDefaultLogger("lc",Logging::WARNING)};
  auto layer=creator.cylinderLayer(gctx,v,nPhi,nZ,pl);   // identity transform
  const SurfaceArray* sa=layer->surfaceArray();
  auto ax=sa->getAxes();
  printf("zShift=%6.1f  layer z centre=%8.3f  z-axis=[%9.3f,%9.3f]  ",
    zShift,(sa->surfaceRepresentation()->localToGlobalTransform(gctx)*Vector3(0,0,0)).z(),
    ax[1]->getBinEdges().front(),ax[1]->getBinEdges().back());
  // scan at normal incidence
  auto entry=Surface::makeShared<CylinderSurface>(Transform3::Identity(), pl.min(AxisDirection::AxisR,false)-1.0, 1e5);
  std::mt19937_64 rng(7);
  std::uniform_real_distribution<double> uphi(-std::numbers::pi,std::numbers::pi);
  std::uniform_real_distribution<double> uzz(pl.min(AxisDirection::AxisZ,false),pl.max(AxisDirection::AxisZ,false));
  std::size_t nT=0,nM=0,nC=0,nQ=0;
  for(int i=0;i<30000;++i){
    double p=uphi(rng); double zt=uzz(rng);
    Vector3 origin(0,0,zt); Vector3 dir(std::cos(p),std::sin(p),0.);
    std::set<const Surface*> truth;
    for(auto& s: v){ auto is=s->intersect(gctx,origin,dir,BoundaryTolerance::None()).closest();
      if(is.isValid()&&is.pathLength()>0) truth.insert(s.get()); }
    if(truth.empty()) continue;
    auto ei=entry->intersect(gctx,origin,dir,BoundaryTolerance::None()).closestForward();
    Vector3 q=ei.isValid()?ei.position():origin;
    auto found=sa->neighbors(gctx,q,dir);
    ++nQ; nT+=truth.size(); nC+=found.size();
    std::set<const Surface*> fs(found.begin(),found.end());
    for(const Surface* t: truth) if(!fs.contains(t)) ++nM;
  }
  printf("missed=%zu/%zu  cand/query=%.2f\n",nM,nT,(double)nC/std::max<std::size_t>(1,nQ));
  return 0;
}
