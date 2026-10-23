#include "Acts/Propagator/detail/NavigationHelpers.hpp"
#include "Acts/Surfaces/CylinderSurface.hpp"
#include "Acts/Surfaces/PlaneSurface.hpp"
#include "Acts/Surfaces/RectangleBounds.hpp"
#include "spatial-index.hpp"
#include <iostream>
#include <random>

int main() {
  using namespace Acts;
  auto gctx = GeometryContext::dangerouslyDefaultConstruct();
  std::mt19937 rng(42);
  std::uniform_real_distribution<double> coord(-30., 30.);
  std::vector<std::shared_ptr<Surface>> surfaces;
  std::vector<detail::NavigationObjectCandidate> candidates;
  for (int i = 0; i < 128; ++i) {
    Transform3 tr = Transform3::Identity();
    tr.translate(Vector3(coord(rng), coord(rng), coord(rng)));
    tr.rotate(AngleAxis3(coord(rng), Vector3(1, 2, 3).normalized()));
    surfaces.push_back(Surface::makeShared<PlaneSurface>(
        tr, std::make_shared<RectangleBounds>(4., 7.)));
    candidates.emplace_back(*surfaces.back(),
                            i % 8 == 0 ? BoundaryTolerance::Infinite()
                                       : BoundaryTolerance::None());
  }
  surfaces.push_back(
      Surface::makeShared<CylinderSurface>(Transform3::Identity(), 20., 50.));
  candidates.emplace_back(*surfaces.back(), BoundaryTolerance::None());
  CandidateIndex first(candidates, gctx, true), second(candidates, gctx, true);
  CandidateIndex::QueryCache cache;
  std::vector<std::size_t> indexed, cached;
  for (int i = 0; i < 20000; ++i) {
    const auto &index = i % 101 == 0 ? second : first;
    Vector3 position(coord(rng), coord(rng), coord(rng));
    Vector3 direction =
        Vector3(coord(rng), coord(rng), coord(rng)).normalized();
    double near = i % 2 == 0 ? -5. : 1e-4;
    double far = i % 2 == 0 ? 0. : 5.;
    if (i % 97 == 0)
      far = std::numeric_limits<double>::infinity();
    index.candidates(position, direction, near, far, 1e-4, indexed);
    index.candidates(position, direction, near, far, 1e-4, cached, cache);
    if (indexed != cached)
      throw std::runtime_error("Cached candidate set changed");
    for (std::size_t j = 0; j < candidates.size(); ++j) {
      for (const auto &intersection :
           candidates[j].intersect(gctx, position, direction, 1e-4)) {
        if (intersection.isValid() &&
            detail::checkPathLength(intersection.pathLength(), near, far)) {
          if (!std::binary_search(cached.begin(), cached.end(), j))
            throw std::runtime_error("Index omitted a valid intersection");
        }
      }
    }
  }
  std::cout << "20000 forward/backward/owner-change queries match the uncached "
               "index and retain every brute-force intersection\n";
}
