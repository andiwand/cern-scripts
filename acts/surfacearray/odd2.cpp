// ODD Gen1: how the miss rate depends on the grid granularity and on maxNeighborDistance
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
#include "ActsExamples/DD4hepDetector/DD4hepDetector.hpp"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <numbers>
#include <random>
#include <set>
#include <string>
using namespace Acts;
using VectorHelpers::perp; using VectorHelpers::phi;

int main(int argc, char** argv){
  const std::string want = (argc>1)? argv[1] : "Pixels::PositiveEndcap";
  const int layerIdx = (argc>2)? std::stoi(argv[2]) : 1;
  const int nRays = (argc>3)? std::stoi(argv[3]) : 20000;
  GeometryContext gctx = GeometryContext::dangerouslyDefaultConstruct();
  const char* oddPath=std::getenv("ODD_PATH");
  ActsExamples::DD4hepDetectorBase::Config cfg;
  cfg.xmlFileNames={std::string(oddPath)+"/xml/OpenDataDetector.xml"};
  cfg.name="OpenDataDetector"; cfg.logLevel=Logging::WARNING; cfg.dd4hepLogLevel=Logging::ERROR;
  ActsExamples::DD4hepDetector det{ActsExamples::DD4hepDetector::Config{cfg}};
  auto tg=det.trackingGeometry();

  const Layer* target=nullptr;
  tg->visitVolumes([&](const TrackingVolume* v){
    if(v->volumeName()!=want||v->confinedLayers()==nullptr) return;
    int i=0;
    for(const auto& l: v->confinedLayers()->arrayObjects()){
      if(l->surfaceArray()!=nullptr && i==layerIdx) target=l.get();
      ++i;
    }
  });
  if(!target){ printf("layer not found\n"); return 1; }
  const bool isDisc = want.find("Endcap")!=std::string::npos;
  std::vector<std::shared_ptr<const Surface>> surfaces;
  for(const Surface* s: target->surfaceArray()->surfaces()) surfaces.push_back(s->getSharedPtr());
  ProtoLayer pl(gctx, unpackSmartPointers(surfaces));
  printf("%s/L%d: %zu surfaces  R=[%.2f,%.2f] Z=[%.2f,%.2f]\n", want.c_str(), layerIdx, surfaces.size(),
     pl.min(AxisDirection::AxisR,false),pl.max(AxisDirection::AxisR,false),
     pl.min(AxisDirection::AxisZ,false),pl.max(AxisDirection::AxisZ,false));
  { auto ax=target->surfaceArray()->getAxes();
    printf("  native axes: ");
    for(auto* a: ax) printf("[nbins=%zu %.3f..%.3f] ", a->getNBins(), a->getBinEdges().front(), a->getBinEdges().back());
    printf("\n"); }

  auto scan=[&](const SurfaceArray& sa, const char* tag, double eta){
    const double theta=2*std::atan(std::exp(-eta));
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
    printf("  eta=%.1f  %-30s truth=%6zu missed=%6zu (%7.3f%%)  cand/q=%5.2f\n",
      eta,tag,nT,nM,100.*nM/std::max<std::size_t>(1,nT),(double)nC/std::max<std::size_t>(1,nQ));
  };

  SurfaceArrayCreator::Config sc; SurfaceArrayCreator sac{sc,getDefaultLogger("s",Logging::WARNING)};
  auto nat = target->surfaceArray()->getAxes();
  const std::size_t n0=nat[0]->getNBins(), n1=nat[1]->getNBins();
  for(double eta : {0.0, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5}){
    for(std::size_t f : {1u,2u,3u,5u}){
      char b[96];
      if(isDisc){
        auto sa=sac.surfaceArrayOnDisc(gctx,surfaces,n0*f,n1*f,pl);
        std::snprintf(b,sizeof b,"factor=%zu  binsR=%zu binsPhi=%zu",f,n0*f,n1*f); scan(sa,b,eta);
      } else {
        auto sa=sac.surfaceArrayOnCylinder(gctx,surfaces,n0*f,n1*f,pl);
        std::snprintf(b,sizeof b,"factor=%zu  binsPhi=%zu binsZ=%zu",f,n0*f,n1*f); scan(sa,b,eta);
      }
    }
    printf("\n");
  }
  return 0;
}
