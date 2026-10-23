// createVariableAxis phi branch: are the variable bin edges in the frame of the
// representative surface?
#include "Acts/Geometry/GeometryContext.hpp"
#include "Acts/Geometry/ProtoLayer.hpp"
#include "Acts/Geometry/SurfaceArrayCreator.hpp"
#include "Acts/Surfaces/PlaneSurface.hpp"
#include "Acts/Surfaces/RectangleBounds.hpp"
#include "Acts/Surfaces/SurfaceArray.hpp"
#include "Acts/Utilities/Helpers.hpp"
#include "Acts/Utilities/IAxis.hpp"
#include <cstdio>
#include <numbers>
using namespace Acts;
using VectorHelpers::phi;
int main(){
  GeometryContext gctx=GeometryContext::dangerouslyDefaultConstruct();
  double R=100; std::size_t nPhi=12, nZ=3;
  double hPhi=R*std::numbers::pi/nPhi*0.9, hZ=30;
  auto bounds=std::make_shared<RectangleBounds>(hPhi,hZ);
  for(double phi0 : {0.0, 0.3}){
    std::vector<std::shared_ptr<const Surface>> v;
    for(std::size_t ip=0;ip<nPhi;++ip){
      double ph=phi0+2*std::numbers::pi*ip/nPhi;
      for(std::size_t iz=0;iz<nZ;++iz){
        double z=(static_cast<double>(iz)-1.)*2*hZ;
        Transform3 t=Transform3::Identity();
        t*=AngleAxis3(ph,Vector3::UnitZ()); t*=Translation3(R,0,z);
        t*=AngleAxis3(std::numbers::pi/2.,Vector3::UnitY()); t*=AngleAxis3(std::numbers::pi/2.,Vector3::UnitZ());
        v.push_back(Surface::makeShared<PlaneSurface>(t,bounds));
      }
    }
    ProtoLayer pl(gctx,unpackSmartPointers(v));
    pl.envelope[AxisDirection::AxisR]={2.,2.};
    SurfaceArrayCreator::Config c; SurfaceArrayCreator sac{c,getDefaultLogger("s",Logging::WARNING)};
    auto sa=sac.surfaceArrayOnCylinder(gctx,v,arbitrary,equidistant,pl);
    auto ax=sa.getAxes();
    const Transform3 inv=sa.surfaceRepresentation()->localToGlobalTransform(gctx).inverse();
    printf("phi0=%.2f  variable phi axis nbins=%zu edges:",phi0,ax[0]->getNBins());
    for(double e: ax[0]->getBinEdges()) printf(" %+.3f",e);
    printf("\n   module local phis:");
    for(std::size_t ip=0;ip<nPhi;++ip) printf(" %+.3f", phi(inv*v[ip*nZ]->center(gctx)));
    printf("\n");
    // is every module centre strictly inside a bin (i.e. no edge cuts a module centre)?
    double worst=1e9;
    for(std::size_t ip=0;ip<nPhi;++ip){
      double lp=phi(inv*v[ip*nZ]->center(gctx));
      double d=1e9;
      for(double e: ax[0]->getBinEdges()) d=std::min(d,std::abs(lp-e));
      worst=std::min(worst,d);
    }
    printf("   closest distance from any module centre to a bin edge: %.4f rad (module half width ~%.4f)\n\n",
           worst, hPhi/R);
  }
  return 0;
}
