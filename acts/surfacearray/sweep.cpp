// CSV sweep over ODD Gen1 layers: bin factor x eta -> miss rate, candidates
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
  const int nRays = (argc>1)? std::stoi(argv[1]) : 8000;
  GeometryContext gctx = GeometryContext::dangerouslyDefaultConstruct();
  const char* oddPath=std::getenv("ODD_PATH");
  ActsExamples::DD4hepDetectorBase::Config cfg;
  cfg.xmlFileNames={std::string(oddPath)+"/xml/OpenDataDetector.xml"};
  cfg.name="OpenDataDetector"; cfg.logLevel=Logging::WARNING; cfg.dd4hepLogLevel=Logging::ERROR;
  ActsExamples::DD4hepDetector det{ActsExamples::DD4hepDetector::Config{cfg}};
  auto tg=det.trackingGeometry();

  struct L { const Layer* layer; std::string name; bool disc; std::vector<std::shared_ptr<const Surface>> surf; };
  std::vector<L> layers;
  tg->visitVolumes([&](const TrackingVolume* v){
    if(v->confinedLayers()==nullptr) return;
    int i=0;
    for(const auto& l: v->confinedLayers()->arrayObjects()){
      int idx=i++;
      if(l->surfaceArray()==nullptr) continue;
      L e; e.layer=l.get(); e.name=v->volumeName()+"/L"+std::to_string(idx);
      e.disc = v->volumeName().find("Endcap")!=std::string::npos;
      for(const Surface* s: l->surfaceArray()->surfaces()) e.surf.push_back(s->getSharedPtr());
      layers.push_back(std::move(e));
    }
  });

  SurfaceArrayCreator::Config sc; SurfaceArrayCreator sac{sc,getDefaultLogger("s",Logging::WARNING)};
  printf("layer,kind,factor,nbins0,nbins1,eta,truth,missed,missfrac,candperquery\n");
  for(const L& e : layers){
    ProtoLayer pl(gctx, unpackSmartPointers(e.surf));
    auto nat=e.layer->surfaceArray()->getAxes();
    const std::size_t n0=nat[0]->getNBins(), n1=nat[1]->getNBins();
    for(std::size_t f : {1u,2u,3u,4u,5u,6u}){
      SurfaceArray sa = e.disc
        ? sac.surfaceArrayOnDisc(gctx,e.surf,n0*f,n1*f,pl)
        : sac.surfaceArrayOnCylinder(gctx,e.surf,n0*f,n1*f,pl);
      for(double eta : {0.0,0.5,1.0,1.5,2.0,2.5,3.0,3.25,3.5,3.75,4.0}){
        const double theta=2*std::atan(std::exp(-eta));
        std::mt19937_64 rng(11);
        std::uniform_real_distribution<double> uphi(-std::numbers::pi,std::numbers::pi);
        std::uniform_real_distribution<double> uz(-100.,100.);
        std::size_t nT=0,nM=0,nC=0,nQ=0;
        for(int i=0;i<nRays;++i){
          double p=uphi(rng); Vector3 origin(0,0,uz(rng));
          Vector3 dir(std::sin(theta)*std::cos(p),std::sin(theta)*std::sin(p),std::cos(theta));
          std::set<const Surface*> truth;
          for(auto& s: e.surf){ auto is=s->intersect(gctx,origin,dir,BoundaryTolerance::None()).closest();
            if(is.isValid()&&is.pathLength()>0) truth.insert(s.get()); }
          if(truth.empty()) continue;
          NavigationOptions<Layer> nopts; nopts.resolveSensitive=true; nopts.nearLimit=0.;
          nopts.farLimit=std::numeric_limits<double>::max();
          auto ap=e.layer->surfaceOnApproach(gctx,origin,dir,nopts);
          Vector3 q= ap.isValid()? origin+ap.pathLength()*dir : origin;
          auto found=sa.neighbors(gctx,q,dir);
          std::set<const Surface*> fs(found.begin(),found.end());
          ++nQ; nT+=truth.size(); nC+=found.size();
          for(const Surface* t: truth) if(!fs.contains(t)) ++nM;
        }
        if(nT==0) continue;
        printf("%s,%s,%zu,%zu,%zu,%.2f,%zu,%zu,%.6f,%.3f\n", e.name.c_str(), e.disc?"disc":"cylinder",
          f, n0*f, n1*f, eta, nT, nM, (double)nM/nT, (double)nC/std::max<std::size_t>(1,nQ));
      }
    }
    fflush(stdout);
  }
  return 0;
}
