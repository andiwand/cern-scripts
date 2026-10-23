// scan of module-centre-to-bin-centre offset vs the detector's phi origin
#include "Acts/Geometry/GeometryContext.hpp"
#include "Acts/Geometry/ProtoLayer.hpp"
#include "Acts/Geometry/SurfaceArrayCreator.hpp"
#include "Acts/Surfaces/PlaneSurface.hpp"
#include "Acts/Surfaces/RectangleBounds.hpp"
#include "Acts/Surfaces/SurfaceArray.hpp"
#include "Acts/Utilities/Helpers.hpp"
#include "Acts/Utilities/IAxis.hpp"
#include <cmath>
#include <cstdio>
#include <numbers>
using namespace Acts;
using VectorHelpers::phi;
int main(){
  GeometryContext gctx=GeometryContext::dangerouslyDefaultConstruct();
  const double R=100; const std::size_t nPhi=20, nZ=3;
  const double hPhi=R*std::numbers::pi/nPhi*0.9, hZ=30;
  auto bounds=std::make_shared<RectangleBounds>(hPhi,hZ);
  const double step=2*std::numbers::pi/nPhi;
  printf("phi0_over_step,offset_bins\n");
  for(int i=0;i<=100;++i){
    const double phi0=step*i/100.;
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
    auto sa=sac.surfaceArrayOnCylinder(gctx,v,nPhi,nZ,pl);
    auto ax=sa.getAxes();
    const double lo=ax[0]->getBinEdges().front();
    const double bw=(ax[0]->getBinEdges().back()-lo)/ax[0]->getNBins();
    const Transform3 inv=sa.surfaceRepresentation()->localToGlobalTransform(gctx).inverse();
    double worst=0;
    for(std::size_t ip=0;ip<nPhi;++ip){
      double lp=phi(inv*v[ip*nZ]->center(gctx));
      double u=(lp-lo)/bw; double f=u-std::floor(u);
      worst=std::max(worst,std::abs(f-0.5));
    }
    printf("%.4f,%.5f\n", phi0/step, worst);
  }
  return 0;
}
