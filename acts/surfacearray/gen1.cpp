// Gen1: truth vs. Layer::compatibleSurfaces (which is SurfaceArray::neighbors)
#include "Acts/Geometry/GeometryContext.hpp"
#include "Acts/Geometry/Layer.hpp"
#include "Acts/Geometry/TrackingGeometry.hpp"
#include "Acts/Propagator/Navigator.hpp"
#include "Acts/Geometry/TrackingVolume.hpp"
#include "Acts/Surfaces/Surface.hpp"
#include "Acts/Surfaces/SurfaceArray.hpp"
#include "Acts/Utilities/Helpers.hpp"
#include "Acts/Utilities/IAxis.hpp"
#include "ActsExamples/GenericDetector/GenericDetector.hpp"

#include <cmath>
#include <cstdio>
#include <map>
#include <numbers>
#include <random>
#include <set>
#include <string>
#include <vector>

using namespace Acts;
using VectorHelpers::perp;
using VectorHelpers::phi;

int main(int argc, char** argv) {
  const int nRays = (argc > 1) ? std::stoi(argv[1]) : 5000;
  GeometryContext gctx = GeometryContext::dangerouslyDefaultConstruct();

  ActsExamples::GenericDetector::Config cfg;
  cfg.gen3 = false;
  cfg.logLevel = cfg.surfaceLogLevel = cfg.layerLogLevel = cfg.volumeLogLevel =
      Logging::WARNING;
  ActsExamples::GenericDetector det{cfg};
  auto tg = det.trackingGeometry();

  struct LayerInfo {
    const Layer* layer{};
    std::vector<const Surface*> sensitives;
    std::string name;
  };
  std::vector<LayerInfo> layers;
  tg->visitVolumes([&](const TrackingVolume* v) {
    if (v->confinedLayers() == nullptr) {
      return;
    }
    int idx = 0;
    for (const auto& l : v->confinedLayers()->arrayObjects()) {
      if (l->surfaceArray() == nullptr) {
        ++idx;
        continue;
      }
      LayerInfo li;
      li.layer = l.get();
      li.name = v->volumeName() + "/L" + std::to_string(idx++);
      for (const Surface* s : l->surfaceArray()->surfaces()) {
        li.sensitives.push_back(s);
      }
      layers.push_back(std::move(li));
    }
  });
  printf("# Gen1 layers with a surface array: %zu\n", layers.size());

  std::mt19937_64 rng(4242);
  std::uniform_real_distribution<double> uphi(-std::numbers::pi, std::numbers::pi);
  std::uniform_real_distribution<double> uz(-100., 100.);

  struct Acc { std::size_t truth{}, miss{}, cand{}, queries{}; };
  std::map<int, Acc> byEta;
  std::map<std::string, std::map<int, Acc>> byLayerEta;

  for (double eta : {0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5}) {
    const double theta = 2 * std::atan(std::exp(-eta));
    const int key = static_cast<int>(std::lround(eta * 10));
    for (int i = 0; i < nRays; ++i) {
      const double p = uphi(rng);
      Vector3 origin(0, 0, uz(rng));
      Vector3 dir(std::sin(theta) * std::cos(p), std::sin(theta) * std::sin(p),
                  std::cos(theta));
      for (const LayerInfo& li : layers) {
        std::set<const Surface*> truth;
        for (const Surface* s : li.sensitives) {
          auto is = s->intersect(gctx, origin, dir, BoundaryTolerance::None()).closest();
          if (is.isValid() && is.pathLength() > 0) {
            truth.insert(s);
          }
        }
        if (truth.empty()) {
          continue;
        }
        // Gen1 queries from the approach surface of the layer
        NavigationOptions<Layer> nopts;
        nopts.resolveSensitive = true;
        nopts.nearLimit = 0.;
        nopts.farLimit = std::numeric_limits<double>::max();
        auto approach = li.layer->surfaceOnApproach(gctx, origin, dir, nopts);
        Vector3 q = approach.isValid() ? origin + approach.pathLength() * dir
                                       : origin;
        auto found = li.layer->surfaceArray()->neighbors(gctx, q, dir);
        std::set<const Surface*> fs(found.begin(), found.end());
        Acc& a = byEta[key];
        Acc& b = byLayerEta[li.name][key];
        a.queries++; b.queries++;
        a.truth += truth.size(); b.truth += truth.size();
        a.cand += found.size(); b.cand += found.size();
        for (const Surface* t : truth) {
          if (!fs.contains(t)) { a.miss++; b.miss++; }
        }
      }
    }
  }

  printf("\n%8s %10s %10s %10s %10s %10s\n", "eta", "queries", "truth", "missed", "miss%", "cand/q");
  for (auto& [k, a] : byEta) {
    printf("%8.1f %10zu %10zu %10zu %9.3f%% %10.2f\n", k / 10., a.queries, a.truth,
           a.miss, 100. * a.miss / std::max<std::size_t>(1, a.truth),
           static_cast<double>(a.cand) / std::max<std::size_t>(1, a.queries));
  }
  printf("\nper layer (only layers with misses):\n%-24s %6s %10s %10s %9s %8s\n",
         "layer", "eta", "truth", "missed", "miss%", "cand/q");
  for (auto& [name, m] : byLayerEta) {
    std::size_t tot = 0;
    for (auto& [k, a] : m) tot += a.miss;
    if (tot == 0) continue;
    for (auto& [k, a] : m) {
      if (a.miss == 0) continue;
      printf("%-24s %6.1f %10zu %10zu %8.3f%% %8.2f\n", name.c_str(), k / 10., a.truth,
             a.miss, 100. * a.miss / std::max<std::size_t>(1, a.truth),
             static_cast<double>(a.cand) / std::max<std::size_t>(1, a.queries));
    }
  }
  return 0;
}
