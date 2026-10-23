// Probe: phi rotation alignment of the equidistant phi axis
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
#include <vector>

using namespace Acts;
using VectorHelpers::phi;
using VectorHelpers::perp;

// build a barrel of nPhi x nZ planar modules tangential to cylinder R
std::vector<std::shared_ptr<const Surface>> makeBarrel(double R, std::size_t nPhi,
                                                       std::size_t nZ,
                                                       double moduleHalfPhiLen,
                                                       double moduleHalfZ,
                                                       double phi0 = 0.) {
  std::vector<std::shared_ptr<const Surface>> out;
  auto bounds = std::make_shared<RectangleBounds>(moduleHalfPhiLen, moduleHalfZ);
  for (std::size_t iz = 0; iz < nZ; ++iz) {
    double z = (static_cast<double>(iz) - 0.5 * (nZ - 1)) * 2 * moduleHalfZ;
    for (std::size_t ip = 0; ip < nPhi; ++ip) {
      double ph = phi0 + 2 * std::numbers::pi * ip / nPhi;
      Transform3 t = Transform3::Identity();
      t *= AngleAxis3(ph, Vector3::UnitZ());
      t *= Translation3(R, 0, z);
      // local x -> global phi dir, local y -> global z, normal -> radial
      t *= AngleAxis3(std::numbers::pi / 2., Vector3::UnitY());
      t *= AngleAxis3(std::numbers::pi / 2., Vector3::UnitZ());
      out.push_back(Surface::makeShared<PlaneSurface>(t, bounds));
    }
  }
  return out;
}

int main() {
  GeometryContext gctx = GeometryContext::dangerouslyDefaultConstruct();
  const double R = 100.;
  const std::size_t nPhi = 12, nZ = 4;
  const double hPhi = R * std::numbers::pi / nPhi * 0.98;
  const double hZ = 30.;

  for (double phi0 : {0.0, 0.13, 0.5}) {
    auto surfaces = makeBarrel(R, nPhi, nZ, hPhi, hZ, phi0);
    SurfaceArrayCreator::Config cfg;  // doPhiBinningOptimization = true
    SurfaceArrayCreator sac{cfg, getDefaultLogger("sac", Logging::WARNING)};
    ProtoLayer pl(gctx, unpackSmartPointers(surfaces));
    pl.envelope[AxisDirection::AxisR] = {1., 1.};
    auto sa = sac.surfaceArrayOnCylinder(gctx, surfaces, nPhi, nZ, pl);

    const Surface* rep = sa.surfaceRepresentation();
    double repRot = phi(rep->localToGlobalTransform(gctx).rotation() * Vector3::UnitX());
    auto axes = sa.getAxes();
    const IAxis& axPhi = *axes[0];
    double lo = axPhi.getBinEdges().front(), hi = axPhi.getBinEdges().back();
    double step = (hi - lo) / axPhi.getNBins();

    printf("=== phi0=%.3f nPhi=%zu : rep rotation=%+.6f  axis[%.4f,%.4f] nbins=%zu step=%.6f\n",
           phi0, nPhi, repRot, lo, hi, axPhi.getNBins(), step);
    // local phi of each module center in the representative frame
    double worst = 0;
    for (std::size_t ip = 0; ip < nPhi; ++ip) {
      const Surface& s = *surfaces[ip];
      Vector3 c = s.center(gctx);
      Vector3 lc = rep->localToGlobalTransform(gctx).inverse() * c;
      double lphi = phi(lc);
      // distance from nearest bin center
      double u = (lphi - lo) / step;
      double frac = u - std::floor(u);  // 0.5 == bin center
      double d = std::abs(frac - 0.5);
      worst = std::max(worst, d);
      if (ip < 4) {
        printf("   module %2zu: globalphi=%+.6f localphi=%+.6f  binfrac=%.4f (0.5=center)\n",
               ip, phi(c), lphi, frac);
      }
    }
    printf("   worst |binfrac-0.5| over modules = %.4f  (0 = perfectly centred, 0.5 = on the edge)\n", worst);
  }
  return 0;
}
