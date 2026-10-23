// Validation driver for the generic Runge-Kutta stepper (acts#6211).
//
// Compares SympyStepper, HelixStepper and GenericRungeKuttaStepper with the
// tableaus classicalRk4 (step doubling), dormandPrince54 and verner98
// (embedded) in vacuum, without a detector.
//
// Studies, written as JSON lines to stdout:
//   hom   constant 2 T field, residuals to the analytic helix (long double)
//   inh   smooth analytic field, residuals to a fixed-step Verner reference
//   map   RZ field map of the same field, residuals to a fixed-step reference
//   fb    forward-backward closure in the analytic field
//   jac   bound-to-free jacobian against central finite differences
//   prof  step sizes along one track
//   time  wall time per propagation (single thread)

#include "Acts/Definitions/Units.hpp"
#include "Acts/EventData/BoundTrackParameters.hpp"
#include "Acts/EventData/ParticleHypothesis.hpp"
#include "Acts/Geometry/GeometryContext.hpp"
#include "Acts/MagneticField/BFieldMapUtils.hpp"
#include "Acts/MagneticField/ConstantBField.hpp"
#include "Acts/MagneticField/MagneticFieldContext.hpp"
#include "Acts/MagneticField/MagneticFieldProvider.hpp"
#include "Acts/Propagator/ActorList.hpp"
#include "Acts/Propagator/ButcherTableau.hpp"
#include "Acts/Propagator/ConstrainedStep.hpp"
#include "Acts/Propagator/GenericRungeKuttaStepper.hpp"
#include "Acts/Propagator/HelixStepper.hpp"
#include "Acts/Propagator/Propagator.hpp"
#include "Acts/Propagator/SympyStepper.hpp"
#include "Acts/Propagator/VoidNavigator.hpp"
#include "Acts/Propagator/detail/SympyBoundToFreeScaling.hpp"
#include "Acts/Utilities/Logger.hpp"

#include <algorithm>
#include <atomic>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <functional>
#include <memory>
#include <mutex>
#include <random>
#include <string>
#include <thread>
#include <vector>

using namespace Acts;
using namespace Acts::UnitLiterals;

namespace {

// ---------------------------------------------------------------------------
// Fields

thread_local std::uint64_t g_lookups = 0;

// Counts the field lookups of the wrapped provider in this thread
class CountingField final : public MagneticFieldProvider {
 public:
  explicit CountingField(std::shared_ptr<const MagneticFieldProvider> inner)
      : m_inner(std::move(inner)) {}
  Cache makeCache(const MagneticFieldContext& mctx) const override {
    return m_inner->makeCache(mctx);
  }
  Result<Vector3> getField(const Vector3& position,
                           Cache& cache) const override {
    ++g_lookups;
    return m_inner->getField(position, cache);
  }

 private:
  std::shared_ptr<const MagneticFieldProvider> m_inner;
};

// Smooth axially symmetric field: a solenoid-like core with a periodic z
// modulation, which decays in r.
//   Bz = B0 (1 + a cos(z/L)) s(r),  Br = (r/2) B0 a sin(z/L)/L s(r),
//   s(r) = 1 / (1 + (r/R)^2)
// Without s(r) it is exactly divergence-free; s(r) breaks that by a term of
// order r/R^2. For a test of the integrators this does not matter.
struct AnalyticField {
  double b0 = 2_T;
  double a = 0.3;
  double l = 1.5_m;
  double rScale = 4_m;

  Vector2 rz(double r, double z) const {
    const double s = 1. / (1. + (r / rScale) * (r / rScale));
    const double bz = b0 * (1. + a * std::cos(z / l)) * s;
    const double br = 0.5 * r * b0 * a * std::sin(z / l) / l * s;
    return {br, bz};
  }
  Vector3 operator()(const Vector3& p) const {
    const double r = std::hypot(p.x(), p.y());
    const Vector2 f = rz(r, p.z());
    if (r == 0.) {
      return {0., 0., f[1]};
    }
    return {f[0] * p.x() / r, f[0] * p.y() / r, f[1]};
  }
};

class AnalyticFieldProvider final : public MagneticFieldProvider {
 public:
  struct Cache {};
  Acts::MagneticFieldProvider::Cache makeCache(
      const MagneticFieldContext& /*mctx*/) const override {
    return Acts::MagneticFieldProvider::Cache(std::in_place_type<Cache>);
  }
  Result<Vector3> getField(const Vector3& position,
                           Acts::MagneticFieldProvider::Cache& /*cache*/)
      const override {
    return Result<Vector3>::success(m_field(position));
  }

 private:
  AnalyticField m_field;
};

std::shared_ptr<const MagneticFieldProvider> makeFieldMap(double cell,
                                                          double extent) {
  AnalyticField f;
  std::vector<double> rPos;
  std::vector<double> zPos;
  const auto nR = static_cast<std::size_t>(std::lround(extent / cell)) + 1;
  const auto nZ = 2 * (nR - 1) + 1;
  for (std::size_t i = 0; i < nR; ++i) {
    rPos.push_back(static_cast<double>(i) * cell);
  }
  for (std::size_t j = 0; j < nZ; ++j) {
    zPos.push_back(-extent + static_cast<double>(j) * cell);
  }
  std::vector<Vector2> values(nR * nZ);
  for (std::size_t i = 0; i < nR; ++i) {
    for (std::size_t j = 0; j < nZ; ++j) {
      values[i * nZ + j] = f.rz(rPos[i], zPos[j]);
    }
  }
  auto bin = [](std::array<std::size_t, 2> b, std::array<std::size_t, 2> n) {
    return b[0] * n[1] + b[1];
  };
  // Positions and field are already in internal units
  return std::make_shared<decltype(fieldMapRZ(bin, rPos, zPos, values))>(
      fieldMapRZ(bin, rPos, zPos, values, 1., 1.));
}

// ---------------------------------------------------------------------------
// Analytic helix in a constant field, in long double

using LVec = std::array<long double, 3>;

struct HelixEnd {
  LVec pos;
  LVec dir;
  long double time;
};

// Free state after a path s, for a start (pos, dir) with |dir| = 1
HelixEnd analyticHelix(const LVec& pos, const LVec& dir, long double qop,
                       long double mass, long double bz, long double s) {
  // dT/ds = qop T x B with B = (0, 0, bz): rotation about z by -kappa s
  const long double kappa = qop * bz;
  const long double tz = dir[2];
  const long double tx = dir[0];
  const long double ty = dir[1];
  HelixEnd e;
  if (std::fabs(kappa * s) < 1e-12L) {
    for (int i = 0; i < 3; ++i) {
      e.pos[i] = pos[i] + s * dir[i];
      e.dir[i] = dir[i];
    }
  } else {
    const long double phi = kappa * s;
    const long double c = std::cos(phi);
    const long double sn = std::sin(phi);
    // T_perp rotates as (tx, ty) -> (tx c + ty s, -tx s + ty c)
    e.dir = {tx * c + ty * sn, -tx * sn + ty * c, tz};
    e.pos = {pos[0] + (tx * sn + ty * (1 - c)) / kappa,
             pos[1] + (-tx * (1 - c) + ty * sn) / kappa, pos[2] + tz * s};
  }
  const long double p = std::fabs(1.L / qop);
  e.time = s * std::sqrt(1.L + (mass / p) * (mass / p));
  return e;
}

// ---------------------------------------------------------------------------
// Checkpoint recorder

struct Record {
  bool ok = false;
  double s = 0;
  FreeVector pars = FreeVector::Zero();
  // Derivative of the free state by the start bound parameters
  BoundToFreeMatrix jac = BoundToFreeMatrix::Zero();
  std::uint64_t lookups = 0;
  std::size_t steps = 0;
};

struct StepRec {
  double s;
  double h;
};

const std::vector<double>* g_dummy = nullptr;
bool g_trace = false;

template <typename state_t>
BoundToFreeMatrix boundToFree(const state_t& st) {
  if constexpr (requires { st.jacTransport; }) {
    return st.jacTransport * st.jacToGlobal;
  } else {
    // The sympy stepper stores the q/p column scaled with q/p
    BoundToFreeMatrix j = st.jacToGlobal;
    detail::sympy::fromScaledBoundToFree(j, st.pars[eFreeQOverP]);
    return j;
  }
}

struct CheckpointRecorder {
  struct this_result {
    std::vector<Record> records;
    std::vector<StepRec> stepLog;
    std::size_t next = 0;
    double lastS = 0;
  };
  using result_type = this_result;

  const std::vector<double>* checkpoints = g_dummy;
  bool withJacobian = false;
  bool logSteps = false;

  template <typename propagator_state_t, typename stepper_t,
            typename navigator_t>
  Result<void> act(propagator_state_t& state, const stepper_t& stepper,
                   const navigator_t& /*navigator*/, result_type& result,
                   const Logger& /*logger*/) const {
    const double s = std::abs(stepper.pathLength(state.stepping));
    if (g_trace) {
      std::fprintf(stderr, "trace s=%.9g stepSize=%s next=%zu\n", s,
                   stepper.outputStepSize(state.stepping).c_str(), result.next);
    }
    if (logSteps && s != result.lastS) {
      result.stepLog.push_back({s, s - result.lastS});
      result.lastS = s;
    }
    while (result.next < checkpoints->size()) {
      const double target = (*checkpoints)[result.next];
      const double dist = target - s;
      if (std::abs(dist) < 1e-9 * std::max(1., target)) {
        Record r;
        r.ok = true;
        r.s = s;
        r.pars.segment<3>(eFreePos0) = stepper.position(state.stepping);
        r.pars[eFreeTime] = stepper.time(state.stepping);
        r.pars.segment<3>(eFreeDir0) = stepper.direction(state.stepping);
        r.pars[eFreeQOverP] = stepper.qOverP(state.stepping);
        if (withJacobian) {
          r.jac = boundToFree(state.stepping);
        }
        r.lookups = g_lookups;
        // The propagator increments the step count after the actors
        r.steps = state.steps + 1;
        result.records.push_back(r);
        ++result.next;
        continue;
      }
      // The stepper applies the propagation direction itself
      stepper.updateStepSize(state.stepping, dist,
                             ConstrainedStep::Type::Actor);
      break;
    }
    return Result<void>::success();
  }
};

// ---------------------------------------------------------------------------
// Stepper configurations

enum class Kind { Sympy, Helix, RK };

struct StepperCfg {
  std::string name;
  Kind kind;
  std::shared_ptr<const ButcherTableau> tableau;
  GenericRungeKuttaStepper::ErrorEstimation est =
      GenericRungeKuttaStepper::ErrorEstimation::Embedded;
  bool gradient = true;
  // Fixed step size, if > 0
  double fixedStep = 0;
};

StepperCfg sympyCfg() {
  return {"sympy", Kind::Sympy, nullptr};
}
StepperCfg helixCfg() {
  return {"helix", Kind::Helix, nullptr};
}
StepperCfg rk4Cfg() {
  return {"rk4", Kind::RK, ButcherTableau::classicalRk4(),
          GenericRungeKuttaStepper::ErrorEstimation::StepDoubling};
}
StepperCfg dp5Cfg() {
  return {"dp5", Kind::RK, ButcherTableau::dormandPrince54()};
}
StepperCfg vern9Cfg() {
  return {"vern9", Kind::RK, ButcherTableau::verner98()};
}
StepperCfg fixedCfg(const std::string& name,
                    std::shared_ptr<const ButcherTableau> t, double h) {
  StepperCfg c{name, Kind::RK, std::move(t),
               GenericRungeKuttaStepper::ErrorEstimation::None};
  c.fixedStep = h;
  return c;
}

struct Start {
  Vector3 pos = Vector3::Zero();
  double time = 0;
  double phi = 0;
  double theta = 0;
  double qop = 0;
};

Vector3 dirOf(double phi, double theta) {
  return {std::sin(theta) * std::cos(phi), std::sin(theta) * std::sin(phi),
          std::cos(theta)};
}

struct RunOut {
  std::vector<Record> records;
  std::vector<StepRec> stepLog;
  std::string error;
};

Logging::Level g_logLevel = Logging::FATAL;
// Maximum step size of the adaptive steppers, if > 0
double g_maxStep = 0;

template <typename stepper_t>
RunOut runWith(stepper_t stepper, const StepperCfg& cfg, const Start& start,
               const std::vector<double>& checkpoints, double tol,
               bool withJacobian, bool backward, bool logSteps) {
  using Prop = Propagator<stepper_t, VoidNavigator>;
  using Options = typename Prop::template Options<ActorList<CheckpointRecorder>>;

  static const GeometryContext gctx =
      GeometryContext::dangerouslyDefaultConstruct();
  static const MagneticFieldContext mctx;

  Prop prop(std::move(stepper), VoidNavigator{},
            getDefaultLogger("prop", g_logLevel));
  Options options(gctx, mctx);
  options.pathLimit = checkpoints.back();
  options.maxSteps = 20'000'000;
  options.loopProtection = false;
  options.surfaceTolerance = 1e-9 * std::max(1., checkpoints.back());
  options.direction = backward ? Direction::Backward() : Direction::Forward();
  options.stepping.stepTolerance = tol;
  options.stepping.maxRungeKuttaStepTrials = 100000;
  if constexpr (std::is_same_v<stepper_t, GenericRungeKuttaStepper>) {
    options.stepping.errorEstimation = cfg.est;
    options.stepping.includeFieldGradient = cfg.gradient;
  }
  if constexpr (std::is_same_v<stepper_t, SympyStepper>) {
    options.stepping.doDense = false;
  }
  if (cfg.fixedStep > 0) {
    options.stepping.initialStepSize = cfg.fixedStep;
    options.stepping.maxStepSize = cfg.fixedStep;
  } else if (g_maxStep > 0) {
    options.stepping.maxStepSize = g_maxStep;
  }
  auto& rec = options.actorList.template get<CheckpointRecorder>();
  rec.checkpoints = &checkpoints;
  rec.withJacobian = withJacobian;
  rec.logSteps = logSteps;

  std::optional<BoundMatrix> cov;
  if (withJacobian) {
    cov = BoundMatrix::Identity();
  }
  Vector4 pos4;
  pos4 << start.pos, start.time;
  auto pars = BoundTrackParameters::createCurvilinear(
      pos4, start.phi, start.theta, start.qop, cov, ParticleHypothesis::pion());

  auto state = prop.makeState(options);
  g_lookups = 0;
  auto init = prop.initialize(state, pars, nullptr);
  RunOut out0;
  if (init.ok()) {
    auto res = prop.propagate(state);
    if (!res.ok()) {
      out0.error = res.error().message();
    }
  } else {
    out0.error = init.error().message();
  }
  RunOut& out = out0;
  auto& r = state.template get<CheckpointRecorder::result_type>();
  out.records = r.records;
  out.records.resize(checkpoints.size());  // missing ones stay ok = false
  out.stepLog = r.stepLog;
  return out;
}

RunOut run(const StepperCfg& cfg,
           const std::shared_ptr<const MagneticFieldProvider>& field,
           const Start& start, const std::vector<double>& checkpoints,
           double tol, bool withJacobian, bool backward = false,
           bool logSteps = false) {
  switch (cfg.kind) {
    case Kind::Sympy:
      return runWith(SympyStepper(field), cfg, start, checkpoints, tol,
                     withJacobian, backward, logSteps);
    case Kind::Helix:
      return runWith(HelixStepper(field), cfg, start, checkpoints, tol,
                     withJacobian, backward, logSteps);
    case Kind::RK: {
      GenericRungeKuttaStepper::Config c;
      c.bField = field;
      c.tableau = cfg.tableau;
      return runWith(GenericRungeKuttaStepper(c), cfg, start, checkpoints, tol,
                     withJacobian, backward, logSteps);
    }
  }
  return {};
}

// ---------------------------------------------------------------------------
// Finite-difference jacobian of the free state at fixed path length

// Columns: loc0, loc1, phi, theta, q/p. The time column is trivial.
constexpr std::array<double, 5> kFdDelta = {0.1_mm, 0.1_mm, 1e-4, 1e-4,
                                            1e-4};  // q/p: relative

Start perturbed(const Start& s, std::size_t col, double d) {
  Start p = s;
  const double phi = s.phi;
  const double theta = s.theta;
  const Vector3 u(-std::sin(phi), std::cos(phi), 0.);
  const Vector3 v(-std::cos(theta) * std::cos(phi),
                  -std::cos(theta) * std::sin(phi), std::sin(theta));
  switch (col) {
    case 0:
      p.pos += d * u;
      break;
    case 1:
      p.pos += d * v;
      break;
    case 2:
      p.phi += d;
      break;
    case 3:
      p.theta += d;
      break;
    case 4:
      p.qop += d * s.qop;
      break;
  }
  return p;
}

double deltaOf(const Start& s, std::size_t col, double scale) {
  return col == 4 ? kFdDelta[col] * scale * s.qop : kFdDelta[col] * scale;
}

using EndFn = std::function<std::vector<FreeVector>(const Start&)>;

// Richardson-extrapolated central differences. Returns the jacobian and an
// error estimate per checkpoint.
std::pair<std::vector<BoundToFreeMatrix>, std::vector<BoundToFreeMatrix>>
fdJacobian(const Start& start, std::size_t nCheck, const EndFn& endFn) {
  std::vector<BoundToFreeMatrix> jac(nCheck, BoundToFreeMatrix::Zero());
  std::vector<BoundToFreeMatrix> err(nCheck, BoundToFreeMatrix::Zero());
  for (std::size_t col = 0; col < 5; ++col) {
    std::array<std::vector<FreeVector>, 2> d1;
    std::array<std::vector<FreeVector>, 2> d2;
    const double h1 = deltaOf(start, col, 1.);
    const double h2 = deltaOf(start, col, 0.5);
    d1[0] = endFn(perturbed(start, col, +h1 / (col == 4 ? start.qop : 1.)));
    d1[1] = endFn(perturbed(start, col, -h1 / (col == 4 ? start.qop : 1.)));
    d2[0] = endFn(perturbed(start, col, +h2 / (col == 4 ? start.qop : 1.)));
    d2[1] = endFn(perturbed(start, col, -h2 / (col == 4 ? start.qop : 1.)));
    for (std::size_t k = 0; k < nCheck; ++k) {
      const FreeVector c1 = (d1[0][k] - d1[1][k]) / (2 * h1);
      const FreeVector c2 = (d2[0][k] - d2[1][k]) / (2 * h2);
      const FreeVector r = (4 * c2 - c1) / 3;
      jac[k].col(col) = r;
      err[k].col(col) = (r - c2).cwiseAbs();
    }
  }
  return {jac, err};
}

// Relative error of the column groups loc (0,1), angles (2,3), q/p (4).
// Rows: position and time in mm, direction scaled with the path length.
std::array<double, 3> jacError(const BoundToFreeMatrix& j,
                               const BoundToFreeMatrix& ref, double s) {
  auto scaled = [s](BoundToFreeMatrix m) {
    m.block<3, 6>(eFreeDir0, 0) *= std::max(s, 1.);
    m.row(eFreeQOverP).setZero();
    m.col(5).setZero();
    return m;
  };
  const BoundToFreeMatrix a = scaled(j);
  const BoundToFreeMatrix b = scaled(ref);
  std::array<double, 3> e{};
  const std::array<std::pair<int, int>, 3> groups = {
      std::pair{0, 2}, std::pair{2, 2}, std::pair{4, 1}};
  for (std::size_t g = 0; g < 3; ++g) {
    const auto [c0, n] = groups[g];
    const double num = (a.middleCols(c0, n) - b.middleCols(c0, n)).norm();
    const double den = b.middleCols(c0, n).norm();
    e[g] = den > 0 ? num / den : num;
  }
  return e;
}

// ---------------------------------------------------------------------------
// Output

std::mutex g_out;

void emit(const std::string& line) {
  std::lock_guard lock(g_out);
  std::fputs(line.c_str(), stdout);
  std::fputc('\n', stdout);
}

std::string fmt(double v) {
  if (!std::isfinite(v)) {
    return "null";
  }
  char buf[32];
  std::snprintf(buf, sizeof(buf), "%.6e", v);
  return buf;
}

// ---------------------------------------------------------------------------
// Parallel loop

void parallelFor(std::size_t n, const std::function<void(std::size_t)>& f) {
  std::atomic<std::size_t> next{0};
  const unsigned nThreads = std::max(1u, std::thread::hardware_concurrency());
  std::vector<std::thread> threads;
  for (unsigned t = 0; t < nThreads; ++t) {
    threads.emplace_back([&] {
      for (std::size_t i = next++; i < n; i = next++) {
        f(i);
      }
    });
  }
  for (auto& t : threads) {
    t.join();
  }
}

}  // namespace

int main(int argc, char** argv) {
  const std::string only = argc > 1 ? argv[1] : "";
  auto want = [&](const char* s) { return only.empty() || only == s; };

  const double bz = 2_T;
  const auto homField = std::make_shared<CountingField>(
      std::make_shared<ConstantBField>(Vector3(0, 0, bz)));
  const auto inhField =
      std::make_shared<CountingField>(std::make_shared<AnalyticFieldProvider>());

  // 1 cm to 100 m, two points per decade
  std::vector<double> paths;
  for (int i = 0; i <= 8; ++i) {
    paths.push_back(10_mm * std::pow(10., 0.5 * i));
  }
  std::vector<double> pathsShort(paths.begin(), paths.begin() + 7);  // 10 m

  const std::vector<double> momenta = {0.1_GeV, 1_GeV, 10_GeV};
  std::vector<double> tols;
  for (int i = 2; i <= 26; ++i) {
    tols.push_back(std::pow(10., -0.5 * i));  // 1e-1 .. 1e-13
  }

  std::mt19937_64 rng(20261020);
  std::uniform_real_distribution<double> uPhi(-M_PI, M_PI);
  std::uniform_real_distribution<double> uTheta(50. * M_PI / 180.,
                                                130. * M_PI / 180.);
  std::vector<std::pair<double, double>> dirs;
  for (int i = 0; i < 8; ++i) {
    dirs.emplace_back(uPhi(rng), uTheta(rng));
  }
  auto makeStart = [&](double p, std::size_t d) {
    Start s;
    s.phi = dirs[d].first;
    s.theta = dirs[d].second;
    s.qop = 1. / p;
    return s;
  };

  std::vector<StepperCfg> scanned = {sympyCfg(), helixCfg(), rk4Cfg(),
                                     dp5Cfg(), vern9Cfg()};
  // Optional second argument: run only this stepper
  if (argc > 2 && only != "debug") {
    std::erase_if(scanned, [&](const StepperCfg& c) { return c.name != argv[2]; });
  }
  auto maxTolIndex = [&](const StepperCfg& c) {
    // The helix error control needs h ~ tol^(1/3): stop at 1e-10
    return c.kind == Kind::Helix ? std::size_t{19} : tols.size();
  };
  const double mass = ParticleHypothesis::pion().mass();

  // ---- hom: constant field, truth = analytic helix --------------------
  if (want("hom")) {
    struct Job {
      StepperCfg cfg;
      std::size_t ip, id, it;
      bool jac;
    };
    std::vector<Job> jobs;
    for (const auto& c : scanned) {
      const std::size_t nt = c.kind == Kind::Helix ? 1 : tols.size();
      for (std::size_t ip = 0; ip < momenta.size(); ++ip) {
        for (std::size_t id = 0; id < dirs.size(); ++id) {
          for (std::size_t it = 0; it < nt; ++it) {
            jobs.push_back({c, ip, id, it, false});
            jobs.push_back({c, ip, id, it, true});
          }
        }
      }
    }
    // Analytic reference jacobian per momentum and direction
    std::vector<std::vector<BoundToFreeMatrix>> refJac(momenta.size() *
                                                       dirs.size());
    std::vector<std::vector<BoundToFreeMatrix>> refJacErr(momenta.size() *
                                                          dirs.size());
    auto analyticEnds = [&](const Start& s) {
      std::vector<FreeVector> ends;
      const Vector3 d = dirOf(s.phi, s.theta);
      const LVec p0 = {s.pos.x(), s.pos.y(), s.pos.z()};
      const LVec d0 = {d.x(), d.y(), d.z()};
      for (double sp : paths) {
        const HelixEnd e = analyticHelix(p0, d0, s.qop, mass, bz, sp);
        FreeVector f;
        f << static_cast<double>(e.pos[0]), static_cast<double>(e.pos[1]),
            static_cast<double>(e.pos[2]), static_cast<double>(e.time),
            static_cast<double>(e.dir[0]), static_cast<double>(e.dir[1]),
            static_cast<double>(e.dir[2]), s.qop;
        ends.push_back(f);
      }
      return ends;
    };
    for (std::size_t ip = 0; ip < momenta.size(); ++ip) {
      for (std::size_t id = 0; id < dirs.size(); ++id) {
        auto [j, e] =
            fdJacobian(makeStart(momenta[ip], id), paths.size(), analyticEnds);
        refJac[ip * dirs.size() + id] = j;
        refJacErr[ip * dirs.size() + id] = e;
      }
    }
    parallelFor(jobs.size(), [&](std::size_t i) {
      const Job& job = jobs[i];
      const Start s = makeStart(momenta[job.ip], job.id);
      const double tol = tols[job.it];
      const RunOut out = run(job.cfg, homField, s, paths, tol, job.jac);
      const Vector3 d = dirOf(s.phi, s.theta);
      for (std::size_t k = 0; k < paths.size(); ++k) {
        const Record& r = out.records[k];
        std::string line = "{\"study\":\"hom\",\"stepper\":\"" + job.cfg.name +
                           "\",\"p\":" + fmt(momenta[job.ip]) +
                           ",\"dir\":" + std::to_string(job.id) +
                           ",\"tol\":" + fmt(tol) + ",\"s\":" + fmt(paths[k]) +
                           ",\"jacrun\":" + (job.jac ? "true" : "false") +
                           ",\"ok\":" + (r.ok ? "true" : "false");
        if (r.ok) {
          // Truth at the recorded path length
          const HelixEnd e =
              analyticHelix({0, 0, 0}, {d.x(), d.y(), d.z()}, s.qop, mass, bz,
                            static_cast<long double>(r.s));
          long double dr = 0;
          long double dt = 0;
          for (int c = 0; c < 3; ++c) {
            const long double a = r.pars[eFreePos0 + c] - e.pos[c];
            const long double b = r.pars[eFreeDir0 + c] - e.dir[c];
            dr += a * a;
            dt += b * b;
          }
          line += ",\"dpos\":" + fmt(static_cast<double>(std::sqrt(dr))) +
                  ",\"ddir\":" + fmt(static_cast<double>(std::sqrt(dt))) +
                  ",\"dtime\":" +
                  fmt(static_cast<double>(
                      std::fabs(r.pars[eFreeTime] - e.time))) +
                  ",\"lookups\":" + std::to_string(r.lookups) +
                  ",\"steps\":" + std::to_string(r.steps);
          if (job.jac) {
            const auto& ref = refJac[job.ip * dirs.size() + job.id][k];
            const auto je = jacError(r.jac, ref, paths[k]);
            line += ",\"jac\":[" + fmt(je[0]) + "," + fmt(je[1]) + "," +
                    fmt(je[2]) + "]";
          }
        }
        line += "}";
        emit(line);
      }
    });
    // Floor of the finite-difference reference itself
    for (std::size_t ip = 0; ip < momenta.size(); ++ip) {
      for (std::size_t id = 0; id < dirs.size(); ++id) {
        for (std::size_t k = 0; k < paths.size(); ++k) {
          const auto& ref = refJac[ip * dirs.size() + id][k];
          const auto& err = refJacErr[ip * dirs.size() + id][k];
          const auto je = jacError(ref + err, ref, paths[k]);
          emit("{\"study\":\"homfd\",\"p\":" + fmt(momenta[ip]) +
               ",\"dir\":" + std::to_string(id) + ",\"s\":" + fmt(paths[k]) +
               ",\"jac\":[" + fmt(je[0]) + "," + fmt(je[1]) + "," + fmt(je[2]) +
               "]}");
        }
      }
    }
  }

  // ---- inh / map: residuals to a fixed-step reference -----------------
  auto scanAgainstReference = [&](const std::string& study,
                                  const std::shared_ptr<const MagneticFieldProvider>&
                                      field,
                                  const std::vector<double>& checks,
                                  const StepperCfg& refCfg,
                                  const StepperCfg& checkCfg) {
    const std::size_t nRef = momenta.size() * dirs.size();
    std::vector<std::vector<Record>> ref(nRef);
    std::vector<std::vector<Record>> chk(nRef);
    parallelFor(2 * nRef, [&](std::size_t i) {
      const std::size_t j = i / 2;
      const Start s = makeStart(momenta[j / dirs.size()], j % dirs.size());
      if (i % 2 == 0) {
        ref[j] = run(refCfg, field, s, checks, 1., false).records;
      } else {
        chk[j] = run(checkCfg, field, s, checks, 1., false).records;
      }
    });
    // Reference uncertainty: two independent fixed-step integrations
    for (std::size_t j = 0; j < nRef; ++j) {
      for (std::size_t k = 0; k < checks.size(); ++k) {
        const Record& a = ref[j][k];
        const Record& b = chk[j][k];
        std::string line = "{\"study\":\"" + study + "ref\",\"p\":" +
                           fmt(momenta[j / dirs.size()]) +
                           ",\"dir\":" + std::to_string(j % dirs.size()) +
                           ",\"s\":" + fmt(checks[k]) +
                           ",\"ok\":" + (a.ok && b.ok ? "true" : "false");
        if (a.ok && b.ok) {
          line += ",\"dpos\":" +
                  fmt((a.pars.segment<3>(0) - b.pars.segment<3>(0)).norm()) +
                  ",\"ddir\":" +
                  fmt((a.pars.segment<3>(4) - b.pars.segment<3>(4)).norm()) +
                  ",\"rmax\":" + fmt(a.pars.segment<2>(0).norm()) +
                  ",\"zabs\":" + fmt(std::abs(a.pars[2]));
        }
        emit(line + "}");
      }
    }
    struct Job {
      StepperCfg cfg;
      std::size_t j, it;
    };
    std::vector<Job> jobs;
    for (const auto& c : scanned) {
      for (std::size_t j = 0; j < nRef; ++j) {
        for (std::size_t it = 0; it < maxTolIndex(c); ++it) {
          jobs.push_back({c, j, it});
        }
      }
    }
    parallelFor(jobs.size(), [&](std::size_t i) {
      const Job& job = jobs[i];
      const Start s =
          makeStart(momenta[job.j / dirs.size()], job.j % dirs.size());
      const double tol = tols[job.it];
      const RunOut out = run(job.cfg, field, s, checks, tol, false);
      for (std::size_t k = 0; k < checks.size(); ++k) {
        const Record& r = out.records[k];
        const Record& a = ref[job.j][k];
        std::string line =
            "{\"study\":\"" + study + "\",\"stepper\":\"" + job.cfg.name +
            "\",\"p\":" + fmt(momenta[job.j / dirs.size()]) +
            ",\"dir\":" + std::to_string(job.j % dirs.size()) +
            ",\"tol\":" + fmt(tol) + ",\"s\":" + fmt(checks[k]) +
            ",\"ok\":" + (r.ok && a.ok ? "true" : "false");
        if (r.ok && a.ok) {
          line += ",\"dpos\":" +
                  fmt((r.pars.segment<3>(0) - a.pars.segment<3>(0)).norm()) +
                  ",\"ddir\":" +
                  fmt((r.pars.segment<3>(4) - a.pars.segment<3>(4)).norm()) +
                  ",\"lookups\":" + std::to_string(r.lookups) +
                  ",\"steps\":" + std::to_string(r.steps);
        }
        emit(line + "}");
      }
    });
  };

  if (want("inh")) {
    scanAgainstReference("inh", inhField, paths,
                         fixedCfg("ref", ButcherTableau::verner98(), 2_mm),
                         fixedCfg("chk", ButcherTableau::dormandPrince54(),
                                  0.25_mm));
  }

  if (want("map")) {
    const auto mapField =
        std::make_shared<CountingField>(makeFieldMap(20_mm, 10.5_m));
    scanAgainstReference("map", mapField, pathsShort,
                         fixedCfg("ref", ButcherTableau::verner98(), 0.25_mm),
                         fixedCfg("chk", ButcherTableau::verner98(), 0.5_mm));
  }

  // Same as map, with the step size capped at the cell size of the map
  if (only == "mapcap") {
    const auto mapField =
        std::make_shared<CountingField>(makeFieldMap(20_mm, 10.5_m));
    g_maxStep = 20_mm;
    scanAgainstReference("mapcap", mapField, pathsShort,
                         fixedCfg("ref", ButcherTableau::verner98(), 0.25_mm),
                         fixedCfg("chk", ButcherTableau::verner98(), 0.5_mm));
    g_maxStep = 0;
  }

  // ---- fb: forward-backward closure ------------------------------------
  if (want("fb")) {
    struct Job {
      StepperCfg cfg;
      std::size_t j, it, ik;
    };
    std::vector<Job> jobs;
    const std::size_t nRef = momenta.size() * dirs.size();
    for (const auto& c : scanned) {
      for (std::size_t j = 0; j < nRef; ++j) {
        for (std::size_t it = 0; it < maxTolIndex(c); it += 2) {
          for (std::size_t ik = 0; ik < paths.size(); ++ik) {
            jobs.push_back({c, j, it, ik});
          }
        }
      }
    }
    parallelFor(jobs.size(), [&](std::size_t i) {
      const Job& job = jobs[i];
      const Start s =
          makeStart(momenta[job.j / dirs.size()], job.j % dirs.size());
      const double tol = tols[job.it];
      const std::vector<double> check = {paths[job.ik]};
      const RunOut fwd = run(job.cfg, inhField, s, check, tol, false);
      std::string line = "{\"study\":\"fb\",\"stepper\":\"" + job.cfg.name +
                         "\",\"p\":" + fmt(momenta[job.j / dirs.size()]) +
                         ",\"dir\":" + std::to_string(job.j % dirs.size()) +
                         ",\"tol\":" + fmt(tol) + ",\"s\":" + fmt(check[0]);
      bool ok = fwd.records[0].ok;
      if (ok) {
        const FreeVector& e = fwd.records[0].pars;
        Start b;
        b.pos = e.segment<3>(eFreePos0);
        b.time = e[eFreeTime];
        const Vector3 d = e.segment<3>(eFreeDir0).normalized();
        b.phi = std::atan2(d.y(), d.x());
        b.theta = std::acos(std::clamp(d.z(), -1., 1.));
        b.qop = e[eFreeQOverP];
        const RunOut bwd = run(job.cfg, inhField, b, check, tol, false, true);
        ok = bwd.records[0].ok;
        if (ok) {
          const FreeVector& f = bwd.records[0].pars;
          line += ",\"dpos\":" + fmt((f.segment<3>(0) - s.pos).norm()) +
                  ",\"ddir\":" +
                  fmt((f.segment<3>(4) - dirOf(s.phi, s.theta)).norm()) +
                  ",\"lookups\":" +
                  std::to_string(fwd.records[0].lookups +
                                 bwd.records[0].lookups);
        }
      }
      line += std::string(",\"ok\":") + (ok ? "true" : "false") + "}";
      emit(line);
    });
  }

  // ---- jac: jacobian against finite differences, analytic field --------
  if (want("jac")) {
    const StepperCfg fdCfg = fixedCfg("fd", ButcherTableau::verner98(), 2_mm);
    const std::size_t nRef = momenta.size() * dirs.size();
    std::vector<std::vector<BoundToFreeMatrix>> refJac(nRef);
    std::vector<std::vector<BoundToFreeMatrix>> refErr(nRef);
    parallelFor(nRef, [&](std::size_t j) {
      const Start s = makeStart(momenta[j / dirs.size()], j % dirs.size());
      auto ends = [&](const Start& st) {
        const RunOut o = run(fdCfg, inhField, st, paths, 1., false);
        std::vector<FreeVector> v;
        for (const auto& r : o.records) {
          v.push_back(r.ok ? r.pars
                           : FreeVector::Constant(
                                 std::numeric_limits<double>::quiet_NaN()));
        }
        return v;
      };
      auto [jac, err] = fdJacobian(s, paths.size(), ends);
      refJac[j] = jac;
      refErr[j] = err;
    });
    for (std::size_t j = 0; j < nRef; ++j) {
      for (std::size_t k = 0; k < paths.size(); ++k) {
        const auto je = jacError(refJac[j][k] + refErr[j][k], refJac[j][k],
                                 paths[k]);
        emit("{\"study\":\"jacfd\",\"p\":" + fmt(momenta[j / dirs.size()]) +
             ",\"dir\":" + std::to_string(j % dirs.size()) +
             ",\"s\":" + fmt(paths[k]) + ",\"jac\":[" + fmt(je[0]) + "," +
             fmt(je[1]) + "," + fmt(je[2]) + "]}");
      }
    }
    std::vector<StepperCfg> cfgs = scanned;
    StepperCfg noGrad = dp5Cfg();
    noGrad.name = "dp5-nograd";
    noGrad.gradient = false;
    cfgs.push_back(noGrad);
    StepperCfg vNoGrad = vern9Cfg();
    vNoGrad.name = "vern9-nograd";
    vNoGrad.gradient = false;
    cfgs.push_back(vNoGrad);
    struct Job {
      StepperCfg cfg;
      std::size_t j, it;
    };
    std::vector<Job> jobs;
    for (const auto& c : cfgs) {
      for (std::size_t j = 0; j < nRef; ++j) {
        for (std::size_t it = 0; it < maxTolIndex(c); it += 2) {
          jobs.push_back({c, j, it});
        }
      }
    }
    parallelFor(jobs.size(), [&](std::size_t i) {
      const Job& job = jobs[i];
      const Start s =
          makeStart(momenta[job.j / dirs.size()], job.j % dirs.size());
      const double tol = tols[job.it];
      const RunOut out = run(job.cfg, inhField, s, paths, tol, true);
      for (std::size_t k = 0; k < paths.size(); ++k) {
        const Record& r = out.records[k];
        std::string line =
            "{\"study\":\"jac\",\"stepper\":\"" + job.cfg.name +
            "\",\"p\":" + fmt(momenta[job.j / dirs.size()]) +
            ",\"dir\":" + std::to_string(job.j % dirs.size()) +
            ",\"tol\":" + fmt(tol) + ",\"s\":" + fmt(paths[k]) +
            ",\"ok\":" + (r.ok ? "true" : "false");
        if (r.ok) {
          const auto je = jacError(r.jac, refJac[job.j][k], paths[k]);
          line += ",\"jac\":[" + fmt(je[0]) + "," + fmt(je[1]) + "," +
                  fmt(je[2]) + "],\"lookups\":" + std::to_string(r.lookups);
        }
        emit(line + "}");
      }
    });
  }

  // ---- prof: step sizes along one track -------------------------------
  if (want("prof")) {
    const std::vector<double> check = {10_m};
    for (double p : {0.5_GeV, 2_GeV}) {
      for (const auto& c : scanned) {
        for (double tol : {1e-4, 1e-8}) {
          if (c.kind == Kind::Helix && tol < 1e-6) {
            continue;
          }
          const Start s = makeStart(p, 0);
          const RunOut out = run(c, inhField, s, check, tol, false, false, true);
          std::string line = "{\"study\":\"prof\",\"stepper\":\"" + c.name +
                             "\",\"p\":" + fmt(p) + ",\"tol\":" + fmt(tol) +
                             ",\"lookups\":" +
                             std::to_string(out.records[0].lookups) +
                             ",\"steps\":[";
          for (std::size_t i = 0; i < out.stepLog.size(); ++i) {
            line += (i ? "," : "") + std::string("[") +
                    fmt(out.stepLog[i].s) + "," + fmt(out.stepLog[i].h) + "]";
          }
          emit(line + "]}");
        }
      }
    }
  }

  // ---- time: wall time per propagation, single thread ------------------
  // ---- debug: one track with a verbose log ----------------------------
  if (only == "debug" && argc > 5) {
    // validate debug STEPPER P_GEV TOL PATH_MM
    const std::string name = argv[2];
    StepperCfg c = name == "helix"   ? helixCfg()
                   : name == "sympy" ? sympyCfg()
                   : name == "rk4"   ? rk4Cfg()
                   : name == "dp5"   ? dp5Cfg()
                                     : vern9Cfg();
    g_logLevel = Logging::VERBOSE;
    g_trace = true;
    std::vector<double> checks;
    for (double s : paths) {
      if (s <= std::stod(argv[5]) * 1.0001) {
        checks.push_back(s);
      }
    }
    const RunOut o = run(c, inhField, makeStart(std::stod(argv[3]), 0), checks,
                         std::stod(argv[4]), false);
    std::printf("ok %d error '%s'\n", o.records.back().ok, o.error.c_str());
    return 0;
  }

  // ---- mapdebug: end positions of one track in the field map ----------
  if (only == "mapdebug") {
    const auto mapField =
        std::make_shared<CountingField>(makeFieldMap(20_mm, 10.5_m));
    const std::vector<double> check = {1_m};
    const Start s = makeStart(1_GeV, 0);
    auto show = [&](const std::string& what, const StepperCfg& c, double tol,
                    double maxStep, const std::shared_ptr<const MagneticFieldProvider>& f) {
      g_maxStep = maxStep;
      const RunOut o = run(c, f, s, check, tol, false);
      g_maxStep = 0;
      const auto& r = o.records[0];
      std::printf("%-34s ok %d steps %7zu lookups %8llu pos %.12f %.12f %.12f\n",
                  what.c_str(), r.ok, r.steps,
                  static_cast<unsigned long long>(r.lookups), r.pars[0], r.pars[1],
                  r.pars[2]);
    };
    for (const auto& [name, f] :
         std::vector<std::pair<std::string, std::shared_ptr<const MagneticFieldProvider>>>{
             {"map", mapField}, {"analytic", inhField}}) {
      std::printf("== %s\n", name.c_str());
      show("vern9 fixed 0.25", fixedCfg("f", ButcherTableau::verner98(), 0.25_mm), 1, 0, f);
      show("vern9 fixed 0.5", fixedCfg("f", ButcherTableau::verner98(), 0.5_mm), 1, 0, f);
      show("dp5 fixed 0.25", fixedCfg("f", ButcherTableau::dormandPrince54(), 0.25_mm), 1, 0, f);
      show("rk4 fixed 0.25", fixedCfg("f", ButcherTableau::classicalRk4(), 0.25_mm), 1, 0, f);
      show("dp5 fixed 7", fixedCfg("f", ButcherTableau::dormandPrince54(), 7_mm), 1, 0, f);
      show("sympy tol 1e-10", sympyCfg(), 1e-10, 0, f);
      show("vern9 tol 1e-10", vern9Cfg(), 1e-10, 0, f);
      show("vern9 tol 1e-10 max 0.25", vern9Cfg(), 1e-10, 0.25_mm, f);
      show("dp5 tol 1e-10", dp5Cfg(), 1e-10, 0, f);
      StepperCfg sd = dp5Cfg();
      sd.est = GenericRungeKuttaStepper::ErrorEstimation::StepDoubling;
      show("dp5 doubling tol 1e-10", sd, 1e-10, 0, f);
    }
    return 0;
  }

  // timecov: with covariance, 1 GeV, the tolerance grid of the jac study
  if (want("time") || only == "timecov") {
    const bool cov = only == "timecov";
    const std::string study = cov ? "timecov" : "time";
    const std::vector<double> timeMomenta =
        cov ? std::vector<double>{1_GeV} : momenta;
    const std::vector<double> check = {10_m};
    for (const auto& c : scanned) {
      for (std::size_t it = 0; it < maxTolIndex(c); it += cov ? 2 : 1) {
        for (double p : timeMomenta) {
          const double tol = tols[it];
          std::vector<double> perRun;
          std::uint64_t lookups = 0;
          bool ok = true;
          for (std::size_t d = 0; d < dirs.size() && ok; ++d) {
            const Start s = makeStart(p, d);
            // Warm-up and repeat count
            auto t0 = std::chrono::steady_clock::now();
            RunOut o = run(c, inhField, s, check, tol, cov);
            auto t1 = std::chrono::steady_clock::now();
            ok = o.records[0].ok;
            lookups += o.records[0].lookups;
            const double once = std::chrono::duration<double>(t1 - t0).count();
            const int reps =
                std::clamp(static_cast<int>(0.02 / std::max(once, 1e-9)), 1,
                           2000);
            t0 = std::chrono::steady_clock::now();
            for (int r = 0; r < reps; ++r) {
              o = run(c, inhField, s, check, tol, cov);
            }
            t1 = std::chrono::steady_clock::now();
            perRun.push_back(std::chrono::duration<double>(t1 - t0).count() /
                             reps);
          }
          std::sort(perRun.begin(), perRun.end());
          emit("{\"study\":\"" + study + "\",\"stepper\":\"" + c.name +
               "\",\"p\":" + fmt(p) + ",\"tol\":" + fmt(tol) +
               ",\"ok\":" + (ok ? "true" : "false") + ",\"us\":" +
               fmt(ok ? 1e6 * perRun[perRun.size() / 2] : NAN) +
               ",\"lookups\":" + fmt(static_cast<double>(lookups) /
                                      static_cast<double>(dirs.size())) +
               "}");
        }
      }
    }
  }
  return 0;
}
