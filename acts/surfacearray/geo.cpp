// Truth-vs-navigation-lookup scan over a real Gen3 tracking geometry.
#include "Acts/Geometry/GeometryContext.hpp"
#include "Acts/Geometry/TrackingGeometry.hpp"
#include "Acts/Geometry/TrackingVolume.hpp"
#include "Acts/Navigation/INavigationPolicy.hpp"
#include "Acts/Navigation/NavigationDelegate.hpp"
#include "Acts/Navigation/NavigationStream.hpp"
#include "Acts/Surfaces/Surface.hpp"
#include "Acts/Utilities/Helpers.hpp"
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
  const int nRays = (argc > 1) ? std::stoi(argv[1]) : 20000;
  GeometryContext gctx = GeometryContext::dangerouslyDefaultConstruct();

  ActsExamples::GenericDetector::Config cfg;
  cfg.gen3 = true;
  cfg.logLevel = Logging::WARNING;
  cfg.surfaceLogLevel = Logging::WARNING;
  cfg.layerLogLevel = Logging::WARNING;
  cfg.volumeLogLevel = Logging::WARNING;
  ActsExamples::GenericDetector det{cfg};
  auto tg = det.trackingGeometry();

  // collect layer volumes that carry sensitive surfaces
  struct VolInfo {
    const TrackingVolume* vol{};
    std::vector<const Surface*> sensitives;
  };
  std::vector<VolInfo> vols;
  tg->visitVolumes([&](const TrackingVolume* v) {
    VolInfo vi;
    vi.vol = v;
    for (const auto& s : v->surfaces()) {
      if (s.isSensitive()) {
        vi.sensitives.push_back(&s);
      }
    }
    if (!vi.sensitives.empty()) {
      vols.push_back(std::move(vi));
    }
  });
  printf("# volumes with sensitive surfaces: %zu\n", vols.size());

  std::mt19937_64 rng(4242);
  std::uniform_real_distribution<double> uphi(-std::numbers::pi, std::numbers::pi);
  std::uniform_real_distribution<double> uz(-100., 100.);

  struct Acc { std::size_t truth{}, miss{}, cand{}, queries{}; };
  std::map<int, Acc> byEta;                    // eta bin -> accumulator
  std::map<std::string, Acc> byVol;

  auto etaList = {0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5};
  for (double eta : etaList) {
    const double theta = 2 * std::atan(std::exp(-eta));
    const int key = static_cast<int>(std::lround(eta * 10));
    for (int i = 0; i < nRays; ++i) {
      const double p = uphi(rng);
      Vector3 origin(0, 0, uz(rng));
      Vector3 dir(std::sin(theta) * std::cos(p), std::sin(theta) * std::sin(p),
                  std::cos(theta));
      for (const VolInfo& vi : vols) {
        std::set<const Surface*> truth;
        double sMin = std::numeric_limits<double>::max();
        for (const Surface* s : vi.sensitives) {
          auto is = s->intersect(gctx, origin, dir, BoundaryTolerance::None()).closest();
          if (is.isValid() && is.pathLength() > 0) {
            truth.insert(s);
            sMin = std::min(sMin, is.pathLength());
          }
        }
        if (truth.empty()) {
          continue;
        }
        // query position: enter the volume (bisection on TrackingVolume::inside)
        double lo = 0., hi = sMin;
        if (!vi.vol->inside(gctx, origin + hi * dir, 0.)) {
          continue;  // should not happen
        }
        for (int it = 0; it < 60; ++it) {
          double mid = 0.5 * (lo + hi);
          if (vi.vol->inside(gctx, origin + mid * dir, 0.)) { hi = mid; } else { lo = mid; }
        }
        Vector3 q = origin + hi * dir;

        NavigationStream stream;
        AppendOnlyNavigationStream appendOnly{stream};
        NavigationPolicyStateManager mgr;
        const INavigationPolicy* pol = vi.vol->navigationPolicy();
        if (pol == nullptr) { continue; }
        NavigationArguments args{.position = q, .direction = dir};
        if (!pol->isStateless()) {
          pol->createState(gctx, args, mgr, getDummyLogger());
        }
        auto st = mgr.currentState();
        vi.vol->initializeNavigationCandidates(gctx, args, st, appendOnly,
                                               getDummyLogger());
        std::set<const Surface*> found;
        for (const auto& c : stream.candidates()) {
          if (c.isSurfaceTarget() && c.surface().isSensitive()) {
            found.insert(&c.surface());
          }
        }
        Acc& a = byEta[key];
        Acc& b = byVol[vi.vol->volumeName()];
        a.queries++; b.queries++;
        a.truth += truth.size(); b.truth += truth.size();
        a.cand += found.size(); b.cand += found.size();
        for (const Surface* t : truth) {
          if (!found.contains(t)) { a.miss++; b.miss++; }
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
  printf("\n%-28s %10s %10s %10s %10s\n", "volume", "truth", "missed", "miss%", "cand/q");
  for (auto& [k, a] : byVol) {
    if (a.miss == 0) continue;
    printf("%-28s %10zu %10zu %9.3f%% %10.2f\n", k.c_str(), a.truth, a.miss,
           100. * a.miss / std::max<std::size_t>(1, a.truth),
           static_cast<double>(a.cand) / std::max<std::size_t>(1, a.queries));
  }
  return 0;
}
