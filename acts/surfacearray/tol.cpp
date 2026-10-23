#include "Acts/Geometry/GeometryContext.hpp"
#include "Acts/Geometry/ProtoLayer.hpp"
#include "Acts/Surfaces/PlaneSurface.hpp"
#include "Acts/Surfaces/RectangleBounds.hpp"
#include "Acts/Utilities/Helpers.hpp"
#include <cstdio>
#include <numbers>
using namespace Acts;
int main(){
  GeometryContext gctx=GeometryContext::dangerouslyDefaultConstruct();
  double R=100; std::size_t nPhi=12; double hPhi=R*std::numbers::pi/nPhi*0.98, hZ=30;
  auto bounds=std::make_shared<RectangleBounds>(hPhi,hZ);
  std::vector<std::shared_ptr<const Surface>> v;
  for(std::size_t ip=0;ip<nPhi;++ip){
    double ph=2*std::numbers::pi*ip/nPhi;
    Transform3 t=Transform3::Identity();
    t*=AngleAxis3(ph,Vector3::UnitZ()); t*=Translation3(R,0,0);
    t*=AngleAxis3(std::numbers::pi/2.,Vector3::UnitY()); t*=AngleAxis3(std::numbers::pi/2.,Vector3::UnitZ());
    v.push_back(Surface::makeShared<PlaneSurface>(t,bounds));
  }
  ProtoLayer pl(gctx,unpackSmartPointers(v));
  double rep=pl.medium(AxisDirection::AxisR,true);
  double tol=pl.range(AxisDirection::AxisR)*0.5;
  double dist=rep-R;
  printf("representative R = %.17g\n  tolerance      = %.17g\n  |centre - rep| = %.17g\n  difference     = %.3g  -> surface %s the grid\n",
    rep,tol,dist,dist-tol,(dist>tol)?"DROPPED from":"kept in");
  return 0;
}
