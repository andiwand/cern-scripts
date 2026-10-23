// Isolate the endcap-disc miss mechanism on a real Gen1 layer.
#include "Acts/Geometry/GeometryContext.hpp"
#include "Acts/Geometry/Layer.hpp"
#include "Acts/Geometry/ProtoLayer.hpp"
#include "Acts/Geometry/SurfaceArrayCreator.hpp"
#include "Acts/Geometry/TrackingGeometry.hpp"
#include "Acts/Geometry/TrackingVolume.hpp"
#include "Acts/Propagator/Navigator.hpp"
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
using namespace Acts;
using VectorHelpers::perp; using VectorHelpers::phi;

int main(int argc, char** argv){
  const int layerIdx = (argc>1)? std::stoi(argv[1]) : 1;
  const int nRays = (argc>2)? std::stoi(argv[2]) : 20000;
  GeometryContext gctx = GeometryContext::dangerouslyDefaultConstruct();
  ActsExamples::GenericDetector::Config cfg; cfg.gen3=false;
  cfg.logLevel=cfg.surfaceLogLevel=cfg.layerLogLevel=cfg.volumeLogLevel=Logging::WARNING;
  ActsExamples::GenericDetector det{cfg};
  auto tg = det.trackingGeometry();

  const Layer* target=nullptr;
  tg->visitVolumes([&](const TrackingVolume* v){
    if(v->volumeName()!="Pixel::PositiveEndcap"||v->confinedLayers()==nullptr) return;
    int i=0;
    for(const auto& l: v->confinedLayers()->arrayObjects()){
      if(l->surfaceArray()!=nullptr && i==layerIdx) target=l.get();
      ++i;
    }
  });
  if(!target){ printf("layer not found\n"); return 1; }
  std::vector<std::shared_ptr<const Surface>> surfaces;
  for(const Surface* s: target->surfaceArray()->surfaces()) surfaces.push_back(s->getSharedPtr());
  printf("layer with %zu surfaces\n", surfaces.size());
  {
    auto ax=target->surfaceArray()->getAxes();
    for(auto [i,a]: enumerate(ax))
      printf("  native axis %zu: nbins=%zu [%.3f,%.3f]\n", i, a->getNBins(), a->getBinEdges().front(), a->getBinEdges().back());
  }
  ProtoLayer pl(gctx, unpackSmartPointers(surfaces));
  printf("  protolayer R=[%.2f,%.2f] Z=[%.2f,%.2f]\n",
    pl.min(AxisDirection::AxisR,false),pl.max(AxisDirection::AxisR,false),
    pl.min(AxisDirection::AxisZ,false),pl.max(AxisDirection::AxisZ,false));

  const double eta=3.5, theta=2*std::atan(std::exp(-eta));
  auto scan=[&](const SurfaceArray& sa, const char* tag){
    std::mt19937_64 rng(11);
    std::uniform_real_distribution<double> uphi(-std::numbers::pi,std::numbers::pi);
    std::uniform_real_distribution<double> uz(-100.,100.);
    std::size_t nT=0,nM=0,nC=0,nQ=0;
    for(int i=0;i<nRays;++i){
      double p=uphi(rng); Vector3 origin(0,0,uz(rng));
      Vector3 dir(std::sin(theta)*std::cos(p),std::sin(theta)*std::sin(p),std::cos(theta));
      std::set<const Surface*> truth;
      for(auto& s: surfaces){ auto is=s->intersect(gctx,origin,dir,BoundaryTolerance::None()).closest();
        if(is.isValid()&&is.pathLength()>0) truth.insert(s.get()); }
      if(truth.empty()) continue;
      NavigationOptions<Layer> nopts; nopts.resolveSensitive=true; nopts.nearLimit=0.;
      nopts.farLimit=std::numeric_limits<double>::max();
      auto ap=target->surfaceOnApproach(gctx,origin,dir,nopts);
      Vector3 q= ap.isValid()? origin+ap.pathLength()*dir : origin;
      auto found=sa.neighbors(gctx,q,dir);
      std::set<const Surface*> fs(found.begin(),found.end());
      ++nQ; nT+=truth.size(); nC+=found.size();
      for(const Surface* t: truth) if(!fs.contains(t)) ++nM;
    }
    printf("%-34s truth=%6zu missed=%6zu (%7.3f%%)  cand/q=%.2f\n",tag,nT,nM,100.*nM/std::max<std::size_t>(1,nT),(double)nC/std::max<std::size_t>(1,nQ));
  };
  scan(*target->surfaceArray(), "native (Gen1 LayerCreator)");

  SurfaceArrayCreator::Config sc; SurfaceArrayCreator sac{sc,getDefaultLogger("s",Logging::WARNING)};
  for(std::size_t bR : {2u,4u,8u,16u,32u,64u}){
    auto sa=sac.surfaceArrayOnDisc(gctx,surfaces,bR,92,pl);
    char buf[80]; std::snprintf(buf,sizeof buf,"binsR=%zu binsPhi=92 maxNb=1",bR);
    scan(sa,buf);
  }
  for(std::uint8_t nb : {1u,2u,3u,4u}){
    auto sa=sac.surfaceArrayOnDisc(gctx,surfaces,2,92,pl,Transform3::Identity(),nb);
    char buf[80]; std::snprintf(buf,sizeof buf,"binsR=2 binsPhi=92 maxNb=%u",nb);
    scan(sa,buf);
  }
  return 0;
}
