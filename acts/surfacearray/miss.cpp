// Probe: does the SurfaceArray neighbour lookup return every surface a straight
// ray actually crosses, as a function of inclination?
#include "Acts/Geometry/GeometryContext.hpp"
#include "Acts/Geometry/ProtoLayer.hpp"
#include "Acts/Geometry/SurfaceArrayCreator.hpp"
#include "Acts/Surfaces/CylinderSurface.hpp"
#include "Acts/Surfaces/PlaneSurface.hpp"
#include "Acts/Surfaces/RectangleBounds.hpp"
#include "Acts/Surfaces/SurfaceArray.hpp"
#include "Acts/Utilities/Helpers.hpp"

#include <cmath>
#include <cstdio>
#include <numbers>
#include <random>
#include <set>
#include <string>
#include <vector>

using namespace Acts;
using VectorHelpers::perp;
using VectorHelpers::phi;

struct Barrel {
  std::vector<std::shared_ptr<const Surface>> surfaces;
};

Barrel makeBarrel(double R, std::size_t nPhi, std::size_t nZ, double modHalfPhi,
                  double modHalfZ, double tilt, double stagger, double phi0,
                  double zOverlapFrac) {
  Barrel b;
  auto bounds = std::make_shared<RectangleBounds>(modHalfPhi, modHalfZ);
  const double zPitch = 2 * modHalfZ * (1 - zOverlapFrac);
  for (std::size_t ip = 0; ip < nPhi; ++ip) {
    const double ph = phi0 + 2 * std::numbers::pi * ip / nPhi;
    const double r = R + ((ip % 2 == 0) ? -stagger : stagger);
    for (std::size_t iz = 0; iz < nZ; ++iz) {
      const double z = (static_cast<double>(iz) - 0.5 * (nZ - 1)) * zPitch;
      Transform3 t = Transform3::Identity();
      t *= AngleAxis3(ph, Vector3::UnitZ());
      t *= Translation3(r, 0, z);
      t *= AngleAxis3(std::numbers::pi / 2., Vector3::UnitY());
      t *= AngleAxis3(std::numbers::pi / 2., Vector3::UnitZ());
      t *= AngleAxis3(tilt, Vector3::UnitY());
      b.surfaces.push_back(Surface::makeShared<PlaneSurface>(t, bounds));
    }
  }
  return b;
}

int main(int argc, char** argv) {
  const bool phiOpt = (argc > 1 && std::string(argv[1]) == "opt");
  const std::size_t maxNb = (argc > 2) ? std::stoul(argv[2]) : 1;
  const double binFactor = (argc > 3) ? std::stod(argv[3]) : 1.0;
  const double phi0 = (argc > 4) ? std::stod(argv[4]) : 0.137;

  GeometryContext gctx = GeometryContext::dangerouslyDefaultConstruct();

  const double R = 100.;
  const std::size_t nPhi = 20, nZ = 30;
  const double modHalfPhi = 1.15 * std::numbers::pi * R / nPhi;
  const double modHalfZ = 20.;
  Barrel b = makeBarrel(R, nPhi, nZ, modHalfPhi, modHalfZ, -0.35, 2.0, phi0, 0.10);

  SurfaceArrayCreator::Config cfg;
  cfg.doPhiBinningOptimization = phiOpt;
  SurfaceArrayCreator sac{cfg, getDefaultLogger("sac", Logging::WARNING)};

  ProtoLayer pl(gctx, unpackSmartPointers(b.surfaces));
  const double rMin = pl.min(AxisDirection::AxisR, false);
  const double rMax = pl.max(AxisDirection::AxisR, false);
  const double zMax = pl.max(AxisDirection::AxisZ, false);

  const std::size_t binsPhi = std::max<std::size_t>(1, std::llround(nPhi * binFactor));
  const std::size_t binsZ = std::max<std::size_t>(1, std::llround(nZ * binFactor));
  SurfaceArray sa = sac.surfaceArrayOnCylinder(gctx, b.surfaces, binsPhi, binsZ,
                                               pl, Transform3::Identity(),
                                               static_cast<std::uint8_t>(maxNb));

  printf("# phiOpt=%d maxNb=%zu bins=%zux%zu phi0=%.3f R=[%.2f,%.2f] |z|<%.1f  maxEta=%.2f\n",
         static_cast<int>(phiOpt), maxNb, binsPhi, binsZ, phi0, rMin, rMax, zMax,
         std::asinh(zMax / R));

  // entry cylinder of the "layer volume"
  auto entry = Surface::makeShared<CylinderSurface>(Transform3::Identity(),
                                                    rMin - 1.0, zMax + 50.);

  std::mt19937_64 rng(12345);
  std::uniform_real_distribution<double> uphi(-std::numbers::pi, std::numbers::pi);
  std::uniform_real_distribution<double> uz(-50., 50.);

  printf("%6s %8s %9s %8s %9s %9s %9s\n", "eta", "rays", "truthHit", "missed",
         "missFrac", "cand/ray", "emptyRet");
  for (double eta : {0.0, 0.5, 1.0, 1.5, 1.8, 2.0, 2.2, 2.4}) {
    const double theta = 2 * std::atan(std::exp(-eta));
    std::size_t nRays = 0, nTruth = 0, nMissed = 0, nCand = 0, nEmpty = 0;
    for (int i = 0; i < 20000; ++i) {
      const double p = uphi(rng);
      const double z0 = uz(rng);
      Vector3 origin(0, 0, z0);
      Vector3 dir(std::sin(theta) * std::cos(p), std::sin(theta) * std::sin(p),
                  std::cos(theta));
      std::set<const Surface*> truth;
      for (const auto& s : b.surfaces) {
        auto is = s->intersect(gctx, origin, dir, BoundaryTolerance::None()).closest();
        if (is.isValid() && is.pathLength() > 0) {
          truth.insert(s.get());
        }
      }
      if (truth.empty()) {
        continue;
      }
      // realistic query position: where the ray enters the layer volume
      auto ei = entry->intersect(gctx, origin, dir, BoundaryTolerance::None()).closestForward();
      Vector3 qpos = ei.isValid() && ei.pathLength() > 0 ? ei.position()
                                                         : origin;
      ++nRays;
      nTruth += truth.size();
      auto found = sa.neighbors(gctx, qpos, dir);
      nCand += found.size();
      if (found.empty()) {
        ++nEmpty;
      }
      std::set<const Surface*> fset(found.begin(), found.end());
      for (const Surface* t : truth) {
        if (!fset.contains(t)) {
          ++nMissed;
        }
      }
    }
    printf("%6.1f %8zu %9zu %8zu %8.3f%% %9.2f %9zu\n", eta, nRays, nTruth, nMissed,
           100. * nMissed / std::max<std::size_t>(1, nTruth),
           static_cast<double>(nCand) / std::max<std::size_t>(1, nRays), nEmpty);
  }
  return 0;
}
