// Diagnose the missed hits in the pixel endcap discs of the Gen3 generic detector
#include "Acts/Geometry/GeometryContext.hpp"
#include "Acts/Geometry/TrackingGeometry.hpp"
#include "Acts/Geometry/TrackingVolume.hpp"
#include "Acts/Navigation/INavigationPolicy.hpp"
#include "Acts/Navigation/NavigationDelegate.hpp"
#include "Acts/Navigation/NavigationStream.hpp"
#include "Acts/Navigation/SurfaceArrayNavigationPolicy.hpp"
#include "Acts/Surfaces/Surface.hpp"
#include "Acts/Surfaces/SurfaceArray.hpp"
#include "Acts/Utilities/Helpers.hpp"
#include "Acts/Utilities/IAxis.hpp"
#include "ActsExamples/GenericDetector/GenericDetector.hpp"
#include <cmath>
#include <cstdio>
#include <numbers>
#include <random>
#include <set>
#include <string>
using namespace Acts;
using VectorHelpers::perp; using VectorHelpers::phi;

int main(int argc, char** argv){
  const std::string want = (argc>1)? argv[1] : "Pixel_pEC_L0";
  const double eta = (argc>2)? std::stod(argv[2]) : 3.5;
  const int nRays = (argc>3)? std::stoi(argv[3]) : 20000;
  GeometryContext gctx = GeometryContext::dangerouslyDefaultConstruct();
  ActsExamples::GenericDetector::Config cfg; cfg.gen3=true;
  cfg.logLevel=cfg.surfaceLogLevel=cfg.layerLogLevel=cfg.volumeLogLevel=Logging::WARNING;
  ActsExamples::GenericDetector det{cfg};
  auto tg = det.trackingGeometry();

  const TrackingVolume* vol=nullptr;
  tg->visitVolumes([&](const TrackingVolume* v){ if(v->volumeName()==want) vol=v; });
  if(!vol){ printf("volume not found\n"); return 1; }
  std::vector<const Surface*> sens;
  for(const auto& s: vol->surfaces()) if(s.isSensitive()) sens.push_back(&s);
  printf("volume %s: %zu sensitive surfaces\n", want.c_str(), sens.size());

  // reach into the policy to get the surface array
  // rebuild the same policy standalone so we can inspect its grid
  const bool isDisc = want.find("EC")!=std::string::npos;
  SurfaceArrayNavigationPolicy probePolicy(
      gctx, *vol, *getDefaultLogger("p",Logging::WARNING),
      SurfaceArrayNavigationPolicy::Config{
          .layerType = isDisc ? SurfaceArrayNavigationPolicy::LayerType::Disc
                              : SurfaceArrayNavigationPolicy::LayerType::Cylinder,
          .bins = {0,0}});
  const SurfaceArray* sa=&probePolicy.surfaceArray();
  if(sa){
    auto axes=sa->getAxes();
    for(auto [i,a]: enumerate(axes))
      printf("  axis %zu: nbins=%zu [%.4f, %.4f] width=%.4f\n", i, a->getNBins(),
             a->getBinEdges().front(), a->getBinEdges().back(),
             (a->getBinEdges().back()-a->getBinEdges().front())/a->getNBins());
    const Surface* rep=sa->surfaceRepresentation();
    printf("  representative: %s at z=%.3f\n", rep->name().data(),
           (rep->localToGlobalTransform(gctx)*Vector3(0,0,0)).z());
    printf("  maxNeighborDistance=%u  gridsize=%zu\n", sa->maxNeighborDistance(), sa->size());
  } else {
    printf("  (could not reach the SurfaceArray directly; policy is a chain)\n");
  }

  const double theta=2*std::atan(std::exp(-eta));
  std::mt19937_64 rng(11); std::uniform_real_distribution<double> uphi(-std::numbers::pi,std::numbers::pi);
  std::uniform_real_distribution<double> uz(-100.,100.);
  std::size_t nT=0,nM=0,nQ=0,shown=0;
  for(int i=0;i<nRays;++i){
    double p=uphi(rng); Vector3 origin(0,0,uz(rng));
    Vector3 dir(std::sin(theta)*std::cos(p),std::sin(theta)*std::sin(p),std::cos(theta));
    std::set<const Surface*> truth; double sMin=1e30;
    for(const Surface* s: sens){ auto is=s->intersect(gctx,origin,dir,BoundaryTolerance::None()).closest();
      if(is.isValid()&&is.pathLength()>0){ truth.insert(s); sMin=std::min(sMin,is.pathLength()); } }
    if(truth.empty()) continue;
    double lo=0., hi=sMin;
    if(!vol->inside(gctx,origin+hi*dir,0.)) continue;
    for(int it=0;it<60;++it){ double mid=0.5*(lo+hi); if(vol->inside(gctx,origin+mid*dir,0.)) hi=mid; else lo=mid; }
    Vector3 q=origin+hi*dir;
    NavigationStream stream; AppendOnlyNavigationStream ap{stream};
    NavigationPolicyStateManager mgr; const INavigationPolicy* pol=vol->navigationPolicy();
    NavigationArguments args{.position=q,.direction=dir};
    if(!pol->isStateless()) pol->createState(gctx,args,mgr,getDummyLogger());
    auto st=mgr.currentState();
    vol->initializeNavigationCandidates(gctx,args,st,ap,getDummyLogger());
    std::set<const Surface*> found;
    for(const auto& c: stream.candidates()) if(c.isSurfaceTarget()&&c.surface().isSensitive()) found.insert(&c.surface());
    ++nQ; nT+=truth.size();
    for(const Surface* t: truth) if(!found.contains(t)){
      ++nM;
      if(shown<8 && sa){
        const Surface* rep=sa->surfaceRepresentation();
        auto ri=rep->intersect(gctx,q,dir,BoundaryTolerance::Infinite()).closest();
        auto is=t->intersect(gctx,origin,dir,BoundaryTolerance::None()).closest();
        printf("  MISS: query r=%.2f phi=%+.4f z=%.2f | repProj r=%.2f phi=%+.4f z=%.2f (path=%.2f) | truth xing r=%.2f phi=%+.4f z=%.2f | module centre r=%.2f phi=%+.4f z=%.2f\n",
          perp(q),phi(q),q.z(), perp(ri.position()),phi(ri.position()),ri.position().z(), ri.pathLength(),
          perp(is.position()),phi(is.position()),is.position().z(),
          perp(t->center(gctx)),phi(t->center(gctx)),t->center(gctx).z());
        ++shown;
      }
    }
  }
  printf("eta=%.1f queries=%zu truth=%zu missed=%zu (%.3f%%)\n",eta,nQ,nT,nM,100.*nM/std::max<std::size_t>(1,nT));
  return 0;
}
