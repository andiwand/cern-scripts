#include "Acts/Definitions/Units.hpp"
#include "Acts/EventData/BoundTrackParameters.hpp"
#include "Acts/Geometry/GeometryContext.hpp"
#include "Acts/MagneticField/ConstantBField.hpp"
#include "Acts/Material/HomogeneousVolumeMaterial.hpp"
#include "Acts/Material/Interactions.hpp"
#include "Acts/Propagator/SympyStepper.hpp"
#include "Acts/Propagator/detail/MaterialEffectsAccumulator.hpp"
#include "ActsTests/CommonHelpers/PredefinedMaterials.hpp"
#include <fstream>
#include <iomanip>
#include <iostream>
using namespace Acts;
using namespace Acts::UnitLiterals;
int main(int argc, char **argv) {
  const std::string output = argc > 1 ? argv[1] : ".";
  const auto geo = GeometryContext::dangerouslyDefaultConstruct();
  const MagneticFieldContext mag;
  const auto particle = ParticleHypothesis::muon();
  double mass = particle.mass();
  SympyStepper stepper(std::make_shared<ConstantBField>(Vector3::Zero()));
  auto run = [&](const Material &mat, double p, double L, double h) {
    SympyStepper::Options opt(geo, mag);
    opt.initialStepSize = h;
    opt.maxStepSize = h;
    opt.stepTolerance = 1e-10;
    auto st = stepper.makeState(opt);
    stepper.initialize(st, BoundTrackParameters::createCurvilinear(
                               Vector4::Zero(), Vector3::UnitX(), -1 / p,
                               BoundMatrix::Identity() * 1e-20, particle));
    HomogeneousVolumeMaterial volume(mat);
    while (st.pathAccumulated < L - 1e-9) {
      st.stepSize.setUser(std::min(h, L - st.pathAccumulated));
      auto r = stepper.step(st, Direction::Forward(), &volume);
      if (!r.ok())
        throw std::runtime_error(r.error().message());
    }
    return st;
  };
  std::ofstream out(output + "/acts.csv");
  out << std::setprecision(15)
      << "material,p,L,mode,pout,angle_sigma,exit_sigma,cov_y_angle,screen_"
         "sigma\n";
  for (auto [name, mat] : std::vector<std::pair<std::string, Material>>{
           {"Fe", ActsTests::makeIron()},
           {"lAr", ActsTests::makeLiquidArgon()}}) {
    for (double p : {4., 10., 100.})
      for (double L : {10., 100., 1000.})
        for (bool constant : {false, true}) {
          FreeMatrix cov;
          double pout = p;
          if (constant) {
            detail::MaterialEffectsAccumulator acc;
            acc.initialize(.01, particle, p);
            acc.accumulate(mat, L, -1 / p, -1 / p);
            cov = acc.computeAdditionalFreeCovariance(Vector3::UnitX()).value();
          } else {
            auto st = run(mat, p, L, 1.);
            pout = stepper.absoluteMomentum(st);
            cov = st.materialEffectsAccumulator
                      .computeAdditionalFreeCovariance(Vector3::UnitX())
                      .value();
          }
          double drift = 1500 - L / 2;
          double sv = cov(eFreePos1, eFreePos1) +
                      2 * drift * cov(eFreePos1, eFreeDir1) +
                      drift * drift * cov(eFreeDir1, eFreeDir1);
          out << name << ',' << p << ',' << L << ','
              << (constant ? "constant" : "mean") << ',' << pout << ','
              << std::sqrt(cov(eFreeDir1, eFreeDir1)) << ','
              << std::sqrt(cov(eFreePos1, eFreePos1)) << ','
              << cov(eFreePos1, eFreeDir1) << ',' << std::sqrt(sv) << '\n';
        }
  }
  auto mat = ActsTests::makeIron();
  MaterialSlab slab(mat, 1_mm);
  auto f = [&](double q) {
    double p = std::abs(1 / q);
    return q * std::hypot(p, mass) / (p * p) *
           computeEnergyLossMean(slab, eMuon, mass, q, 1);
  };
  std::ofstream jac(output + "/threshold.csv");
  jac << std::setprecision(15) << "p,L,h,epsilon,pout,jac,fd,exact,saltation\n";
  for (auto [p, L, threshold] : std::vector<std::array<double, 3>>{
           {2., 1000., 10 * mass},
           {8.5, 1000., std::sqrt(64 - mass * mass)},
           {1005., 1000., std::sqrt(1e6 - mass * mass)}}) {
    for (double h : {1., .1}) {
      auto st = run(mat, p, L, h);
      double q0 = -1 / p, qf = stepper.qOverP(st), qth = -1 / threshold;
      double salt = f(qth * (1 + 1e-6)) / f(qth * (1 - 1e-6));
      for (double relative : {1e-3, 3e-4, 1e-4}) {
        double eps = std::abs(q0) * relative;
        auto plus = run(mat, -1 / (q0 + eps), L, h),
             minus = run(mat, -1 / (q0 - eps), L, h);
        double fd = (stepper.qOverP(plus) - stepper.qOverP(minus)) / (2 * eps);
        jac << p << ',' << L << ',' << h << ',' << relative << ','
            << stepper.absoluteMomentum(st) << ','
            << st.jacToGlobal(eFreeQOverP, eBoundQOverP) << ',' << fd << ','
            << f(qf) / f(q0) << ',' << salt << '\n';
      }
    }
  }
}
