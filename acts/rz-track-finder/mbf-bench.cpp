// Microbenchmark: the RZ backward refilter kernel against an mBF smoother
// kernel, on the same chain of stops. Arithmetic only; no measurement search.
#include "Acts/TrackFinding/Rz/RzTransport.hpp"

#include <chrono>
#include <cmath>
#include <cstdio>
#include <random>
#include <vector>

using namespace Acts;
using namespace Acts::Experimental;

namespace {

long gBackIters = 0, gBackCalls = 0, gPlaneIters = 0, gPlaneCalls = 0;
double gBackTol = 1e-9;

constexpr double kBz = 2. * 0.000299792458;  // 2 T in native units

struct Stop {
  double radius{};      // cylinder radius of the stop
  bool measurement{};   // whether a hit sits on it
  Vector3 normal{};     // module normal
  Vector3 u{}, v{};     // module frame axes
  Vector3 position{};   // module centre
  double cov00{}, cov01{}, cov11{};
  int dim{};
};

// ---------------------------------------------------------------- kernel A
// The backward refilter, as RzTrackFinder::backwardPass runs it.

struct Pending {
  double varAngle{}, varPosition{}, covAnglePosition{}, varQOverP{};
  bool empty() const { return varAngle == 0. && varQOverP == 0.; }
  void advance(double s) {
    varPosition += 2. * covAnglePosition * s + varAngle * s * s;
    covAnglePosition += varAngle * s;
  }
};

struct State {
  RzVector v;
  RzMatrix c;
  Pending pending;
  RzVector anchor;
  double pathSince{};
};

// RzTrackFinder::pathBackward, cylinder branch
double pathBackward(const RzHelix& helix, const RzVector& v, double radius,
                    double guess) {
  double s = guess;
  ++gBackCalls;
  for (int i = 0; i < 6; ++i) {
    ++gBackIters;
    RzVector w = v;
    helix.step(w, s);
    const double f =
        w[eRzPos0] * w[eRzPos0] + w[eRzPos1] * w[eRzPos1] - radius * radius;
    const double df = 2. * (w[eRzPos0] * w[eRzDir0] + w[eRzPos1] * w[eRzDir1]);
    if (df == 0.) {
      break;
    }
    const double ds = f / df;
    s -= ds;
    if (std::abs(ds) < gBackTol) {
      return s;
    }
  }
  return s;
}

// RzTrackFinder::materialise
void materialise(State& state, const Vector3& normal) {
  Pending& p = state.pending;
  if (p.empty()) {
    return;
  }
  const Vector3 d = state.v.segment<3>(eRzDir0);
  const SquareMatrix3 transverse = SquareMatrix3::Identity() - d * d.transpose();
  state.c.block<3, 3>(eRzDir0, eRzDir0) += p.varAngle * transverse;
  state.c.block<3, 3>(eRzPos0, eRzPos0) += p.varPosition * transverse;
  state.c.block<3, 3>(eRzPos0, eRzDir0) += p.covAnglePosition * transverse;
  state.c.block<3, 3>(eRzDir0, eRzPos0) += p.covAnglePosition * transverse;
  state.c(eRzQOverP, eRzQOverP) += p.varQOverP;
  const SquareMatrix3 project =
      SquareMatrix3::Identity() - d * normal.transpose() / normal.dot(d);
  state.c.block<3, eRzSize>(eRzPos0, 0) =
      project * state.c.block<3, eRzSize>(eRzPos0, 0);
  state.c.block<eRzSize, 3>(0, eRzPos0) =
      state.c.block<eRzSize, 3>(0, eRzPos0) * project.transpose();
  p = Pending{};
}

// RzTrackFinder::evaluate, gate off, plus RzTrackFinder::update
void evaluateAndUpdate(const RzHelix& helix, State& state, const Stop& m) {
  const Vector3 p0 = state.v.segment<3>(eRzPos0);
  const Vector3 d0 = state.v.segment<3>(eRzDir0);
  const double along = m.normal.dot(d0);
  double s = m.normal.dot(m.position - p0) / along;
  // pathToPlane: Newton from the straight line
  ++gPlaneCalls;
  for (int i = 0; i < 4; ++i) {
    ++gPlaneIters;
    RzVector w = state.v;
    helix.step(w, s);
    const double f = m.normal.dot(w.segment<3>(eRzPos0) - m.position);
    const double df = m.normal.dot(w.segment<3>(eRzDir0));
    const double ds = f / df;
    s -= ds;
    if (std::abs(ds) < 1e-9) {
      break;
    }
  }
  RzVector w = state.v;
  helix.step(w, s);
  const Vector3 d = m.position - w.segment<3>(eRzPos0);
  const double ru = m.u.dot(d);
  const double rv = m.v.dot(d);

  Eigen::Matrix<double, eRzSize, 2> ch;
  Eigen::Matrix<double, 2, 2> sInv = Eigen::Matrix<double, 2, 2>::Zero();
  const Eigen::Matrix<double, 3, eRzSize> jPos =
      helix.stepJacobianOnto(state.v, s, w, m.normal).positionRows();
  const Eigen::Matrix<double, 1, eRzSize> hu = m.u.transpose() * jPos;
  ch.col(0) = state.c * hu.transpose();
  const double s00 = hu.dot(ch.col(0)) + m.cov00;
  if (m.dim == 1) {
    ch.col(1).setZero();
    sInv(0, 0) = 1. / s00;
  } else {
    const Eigen::Matrix<double, 1, eRzSize> hv = m.v.transpose() * jPos;
    ch.col(1) = state.c * hv.transpose();
    const double s01 = hv.dot(ch.col(0)) + m.cov01;
    const double s11 = hv.dot(ch.col(1)) + m.cov11;
    const double det = s00 * s11 - s01 * s01;
    sInv(0, 0) = s11 / det;
    sInv(0, 1) = -s01 / det;
    sInv(1, 0) = sInv(0, 1);
    sInv(1, 1) = s00 / det;
  }
  Eigen::Matrix<double, 2, 1> residual;
  residual << ru, rv;

  const Eigen::Matrix<double, eRzSize, 2> k = ch * sInv;
  state.v += k * residual;
  state.v.segment<3>(eRzDir0).normalize();
  state.anchor = state.v;
  state.c -= k * ch.transpose();
  state.c = 0.5 * (state.c + state.c.transpose()).eval();
}

// ---------------------------------------------------------------- kernel B
// mBF: the adjoint recursion over the same stops.

// F^T x, with the same sparsity RzHelix::StepJacobian::applyLeft uses
void applyLeftT(const RzHelix::StepJacobian& j, const double* x, double* y) {
  const double z = j.d[eRzPos0] * x[eRzPos0] + j.d[eRzPos1] * x[eRzPos1] +
                   j.d[eRzPos2] * x[eRzPos2] + j.d[eRzDir0] * x[eRzDir0] +
                   j.d[eRzDir1] * x[eRzDir1];
  y[eRzPos0] = x[eRzPos0] + j.dsdv[eRzPos0] * z;
  y[eRzPos1] = x[eRzPos1] + j.dsdv[eRzPos1] * z;
  y[eRzPos2] = x[eRzPos2] + j.dsdv[eRzPos2] * z;
  y[eRzDir0] = j.f1 * x[eRzPos0] - j.f2 * x[eRzPos1] + j.cs * x[eRzDir0] -
               j.sn * x[eRzDir1] + j.dsdv[eRzDir0] * z;
  y[eRzDir1] = j.f2 * x[eRzPos0] + j.f1 * x[eRzPos1] + j.sn * x[eRzDir0] +
               j.cs * x[eRzDir1] + j.dsdv[eRzDir1] * z;
  y[eRzDir2] = j.s * x[eRzPos2] + x[eRzDir2] + j.dsdv[eRzDir2] * z;
  y[eRzQOverP] = j.a1 * x[eRzPos0] + j.a2 * x[eRzPos1] + j.b1 * x[eRzDir0] +
                 j.b2 * x[eRzDir1] + x[eRzQOverP] + j.dsdv[eRzQOverP] * z;
}

RzMatrix applyLeftTMat(const RzHelix::StepJacobian& j, const RzMatrix& x) {
  RzMatrix y;
  for (unsigned int c = 0; c < eRzSize; ++c) {
    applyLeftT(j, x.col(c).data(), y.col(c).data());
  }
  return y;
}

// F^T L F for symmetric L, through the sparse form
RzMatrix sandwich(const RzHelix::StepJacobian& j, const RzMatrix& l) {
  const RzMatrix m1 = applyLeftTMat(j, l);       // F^T L
  return applyLeftTMat(j, m1.transpose());       // (F^T (F^T L)^T)  = F^T L F
}


// ------------------------------------------------------- mBF correctness
// A linear-Gaussian chain with no process noise: the mBF smoothed state at
// the inner end must equal the brute-force posterior from the normal
// equations.
static void checkMbf(const std::vector<Stop>& stops,
                     const std::vector<RzHelix::StepJacobian>& jacs,
                     const RzVector& x0, const RzMatrix& c0) {
  const std::size_t n = stops.size();
  // dense F per step, and the running product G_i = F_{i-1} ... F_0
  std::vector<RzMatrix> f(n), g(n);
  for (std::size_t i = 0; i < n; ++i) {
    f[i] = jacs[i].dense();
    g[i] = (i == 0) ? f[0] : (f[i] * g[i - 1]).eval();
  }
  // truth and simulated measurements at each state (state i is after step i)
  std::vector<Eigen::Matrix<double, 2, eRzSize>> h(n);
  std::vector<Eigen::Matrix<double, 2, 2>> r(n);
  std::vector<Eigen::Matrix<double, 2, 1>> meas(n);
  std::mt19937_64 rng(7);
  std::normal_distribution<double> gauss(0., 1.);
  const RzVector xTruth = x0 + 0.001 * RzVector::Ones();
  for (std::size_t i = 0; i < n; ++i) {
    const Eigen::Matrix<double, 3, eRzSize> jPos = jacs[i].positionRows();
    h[i].row(0) = stops[i].u.transpose() * jPos;
    h[i].row(1) = stops[i].v.transpose() * jPos;
    r[i] = Eigen::Matrix<double, 2, 2>::Zero();
    r[i](0, 0) = stops[i].cov00;
    r[i](1, 1) = stops[i].cov11;
    // the measurement of the truth state carried to stop i, plus noise
    const RzVector xi = (i == 0) ? xTruth : RzVector(g[i - 1] * xTruth);
    meas[i] = h[i] * xi;
    meas[i](0) += std::sqrt(r[i](0, 0)) * gauss(rng);
    meas[i](1) += std::sqrt(r[i](1, 1)) * gauss(rng);
  }

  // brute force: information form of the posterior at state 0 (before step 0)
  RzMatrix info = c0.inverse();
  RzVector rhs = info * x0;
  for (std::size_t i = 0; i < n; ++i) {
    const RzMatrix gi = (i == 0) ? RzMatrix::Identity() : g[i - 1];
    const Eigen::Matrix<double, 2, eRzSize> hg = h[i] * gi;
    info += hg.transpose() * r[i].inverse() * hg;
    rhs += hg.transpose() * r[i].inverse() * meas[i];
  }
  const RzVector xRef = info.inverse() * rhs;
  const RzMatrix cRef = info.inverse();

  // the mBF recursion, exactly as kernel B runs it, over the same chain
  // running the filter forward first to get K, S^-1 and the residual
  RzVector xf = x0;
  RzMatrix cf = c0;
  std::vector<Eigen::Matrix<double, eRzSize, 2>> kk(n);
  std::vector<Eigen::Matrix<double, 2, 2>> si(n);
  std::vector<Eigen::Matrix<double, 2, 1>> yy(n);
  std::vector<Eigen::Matrix<double, 2, eRzSize>> hh(n);
  for (std::size_t i = 0; i < n; ++i) {
    // the filter here updates at the state before the step, with H F folded
    // in, which is what the RZ finder does
    hh[i] = h[i];
    const Eigen::Matrix<double, 2, 2> s =
        hh[i] * cf * hh[i].transpose() + r[i];
    si[i] = s.inverse();
    kk[i] = cf * hh[i].transpose() * si[i];
    yy[i] = meas[i] - hh[i] * xf;
    xf += kk[i] * yy[i];
    cf -= kk[i] * hh[i] * cf;
    // carry to the next state
    xf = f[i] * xf;
    cf = (f[i] * cf * f[i].transpose()).eval();
  }

  RzMatrix bigLambda = RzMatrix::Zero();
  RzVector smallLambda = RzVector::Zero();
  for (int i = static_cast<int>(n) - 1; i >= 0; --i) {
    const Eigen::Matrix<double, eRzSize, 2> lk = bigLambda * kk[i];
    const RzMatrix lkh = lk * hh[i];
    const Eigen::Matrix<double, 2, 2> klk = kk[i].transpose() * lk;
    const RzMatrix chatLchat =
        bigLambda - lkh - lkh.transpose() + hh[i].transpose() * klk * hh[i];
    bigLambda = hh[i].transpose() * si[i] * hh[i] + chatLchat;
    const Eigen::Matrix<double, 2, 1> kl = kk[i].transpose() * smallLambda;
    smallLambda = smallLambda - hh[i].transpose() * kl -
                  hh[i].transpose() * (si[i] * yy[i]);
    if (i > 0) {
      bigLambda = (f[i - 1].transpose() * bigLambda * f[i - 1]).eval();
      smallLambda = (f[i - 1].transpose() * smallLambda).eval();
    }
  }
  const RzVector xMbf = x0 - c0 * smallLambda;
  const RzMatrix cMbf = c0 - c0 * bigLambda * c0;

  std::printf("mBF check: max |x_mbf - x_ref| = %.3e (|x| ~ %.3e)\n",
              (xMbf - xRef).cwiseAbs().maxCoeff(), xRef.cwiseAbs().maxCoeff());
  std::printf("mBF check: max |C_mbf - C_ref| = %.3e (|C| ~ %.3e)\n",
              (cMbf - cRef).cwiseAbs().maxCoeff(), cRef.cwiseAbs().maxCoeff());
}

}  // namespace

int main() {
  std::mt19937_64 rng(42);
  std::uniform_real_distribution<double> uni(0., 1.);

  // A chain of 20 stops out to r = 1 m, a measurement on every other one.
  // The modules sit on the true trajectory, smeared by their resolution, so
  // that the filter sees realistic residuals and the Newton solves converge
  // the way they do in the finder.
  const RzHelix helix{kBz};
  RzVector v0;
  v0 << 0., 0., 0., std::cos(0.3), std::sin(0.3), 0.4, 1. / 2000.;
  v0.segment<3>(eRzDir0).normalize();

  std::normal_distribution<double> gauss(0., 1.);
  std::vector<Stop> stops;
  {
    RzVector w = v0;
    for (int i = 0; i < 20; ++i) {
      Stop st;
      st.radius = 33. + i * 50.;
      st.measurement = (i % 2) == 0;
      const std::optional<double> s = helix.pathToCylinder(w, st.radius);
      if (!s.has_value()) {
        std::printf("truth track does not reach r = %g\n", st.radius);
        return 1;
      }
      helix.step(w, *s);
      const Vector3 p = w.segment<3>(eRzPos0);
      const double phi = std::atan2(p.y(), p.x());
      st.normal = Vector3(std::cos(phi), std::sin(phi), 0.);
      st.u = Vector3(-std::sin(phi), std::cos(phi), 0.);
      st.v = Vector3(0., 0., 1.);
      st.cov00 = 0.05 * 0.05;
      st.cov11 = 0.3 * 0.3;
      st.cov01 = 0.;
      st.dim = 2;
      st.position = p + 0.05 * gauss(rng) * st.u + 0.3 * gauss(rng) * st.v;
      stops.push_back(st);
    }
  }

  // The forward reference trajectory and the Jacobians mBF would have stored
  std::vector<RzVector> states;
  std::vector<double> paths;
  std::vector<RzHelix::StepJacobian> jacs;
  {
    RzVector v = v0;
    for (const Stop& st : stops) {
      const std::optional<double> s = helix.pathToCylinder(v, st.radius);
      RzVector w = v;
      helix.step(w, *s);
      jacs.push_back(helix.stepJacobianOnto(v, *s, w, st.normal));
      paths.push_back(*s);
      v = w;
      states.push_back(v);
    }
  }

  RzMatrix c0 = RzMatrix::Zero();
  c0.block<3, 3>(eRzPos0, eRzPos0) = 1. * SquareMatrix3::Identity();
  c0.block<3, 3>(eRzDir0, eRzDir0) = 1e-4 * SquareMatrix3::Identity();
  c0(eRzQOverP, eRzQOverP) = 1e-9;

  {
    RzMatrix cCheck = RzMatrix::Identity();
    cCheck.block<3,3>(eRzPos0,eRzPos0) *= 1.;
    cCheck.block<3,3>(eRzDir0,eRzDir0) *= 1e-4;
    cCheck(eRzQOverP,eRzQOverP) = 1e-9;
    checkMbf(stops, jacs, v0, cCheck);
  }

  volatile double sink = 0.;
  const int kReps = 200000;

  // ------------------------------------------------------------- time A
  auto t0 = std::chrono::steady_clock::now();
  for (int rep = 0; rep < kReps; ++rep) {
    State state;
    state.v = states.back();
    state.anchor = state.v;
    state.c = c0;
    state.pathSince = 0.;
    for (int i = static_cast<int>(stops.size()) - 2; i >= 0; --i) {
      const Stop& st = stops[i];
      const double s = pathBackward(helix, state.v, st.radius, -paths[i + 1]);
      helix.step(state.v, s);
      state.pathSince += s;
      state.pending.varAngle += 1e-8;
      state.pending.varQOverP += 1e-12;
      state.pending.advance(-s);
      // moveCovariance
      state.c = helix.stepJacobianOnto(state.anchor, state.pathSince, state.v,
                                       st.normal)
                    .transport(state.c);
      state.anchor = state.v;
      state.pathSince = 0.;
      materialise(state, st.normal);
      if (st.measurement) {
        evaluateAndUpdate(helix, state, st);
      }
    }
    sink = sink + state.v[eRzQOverP] + state.c(0, 0);
  }
  auto t1 = std::chrono::steady_clock::now();

  // ------------------------------------------------------------- time B
  // Precomputed by the forward pass in this scheme: HJ, K, S^-1, residual
  std::vector<Eigen::Matrix<double, 2, eRzSize>> hj(stops.size());
  std::vector<Eigen::Matrix<double, eRzSize, 2>> kk(stops.size());
  std::vector<Eigen::Matrix<double, 2, 2>> si(stops.size());
  std::vector<Eigen::Matrix<double, 2, 1>> yy(stops.size());
  for (std::size_t i = 0; i < stops.size(); ++i) {
    const Eigen::Matrix<double, 3, eRzSize> jPos = jacs[i].positionRows();
    hj[i].row(0) = stops[i].u.transpose() * jPos;
    hj[i].row(1) = stops[i].v.transpose() * jPos;
    Eigen::Matrix<double, 2, 2> s = hj[i] * c0 * hj[i].transpose();
    s(0, 0) += stops[i].cov00;
    s(1, 1) += stops[i].cov11;
    si[i] = s.inverse();
    kk[i] = c0 * hj[i].transpose() * si[i];
    yy[i] << 0.01, 0.02;
  }

  auto t2 = std::chrono::steady_clock::now();
  for (int rep = 0; rep < kReps; ++rep) {
    RzMatrix bigLambda = RzMatrix::Zero();
    RzVector smallLambda = RzVector::Zero();
    for (int i = static_cast<int>(stops.size()) - 1; i >= 0; --i) {
      if (stops[i].measurement) {
        // CHat^T L CHat with CHat = I - K H, kept rank 2
        const Eigen::Matrix<double, eRzSize, 2> lk = bigLambda * kk[i];
        const RzMatrix lkh = lk * hj[i];
        const Eigen::Matrix<double, 2, 2> klk = kk[i].transpose() * lk;
        const RzMatrix chatLchat = bigLambda - lkh - lkh.transpose() +
                                   hj[i].transpose() * klk * hj[i];
        bigLambda = hj[i].transpose() * si[i] * hj[i] + chatLchat;
        // CHat^T l - H^T S^-1 y
        const Eigen::Matrix<double, 2, 1> kl = kk[i].transpose() * smallLambda;
        smallLambda = smallLambda - hj[i].transpose() * kl -
                      hj[i].transpose() * (si[i] * yy[i]);
      }
      // through the transport to the stop before
      bigLambda = sandwich(jacs[i], bigLambda);
      RzVector next;
      applyLeftT(jacs[i], smallLambda.data(), next.data());
      smallLambda = next;
    }
    // the one smoothed state the finder needs, at the inner end
    const RzVector smoothed = states.front() - c0 * smallLambda;
    const RzMatrix smoothedCov = c0 - c0 * bigLambda * c0;
    sink = sink + smoothed[eRzQOverP] + smoothedCov(0, 0);
  }
  auto t3 = std::chrono::steady_clock::now();

  const double a = std::chrono::duration<double>(t1 - t0).count();
  const double b = std::chrono::duration<double>(t3 - t2).count();
  std::printf("stops %zu, measurements %d, reps %d\n", stops.size(), 10, kReps);
  std::printf("A backward refilter : %8.3f s  %8.1f ns/track  %6.1f ns/stop\n",
              a, a / kReps * 1e9, a / kReps / stops.size() * 1e9);
  std::printf("B mBF smoother      : %8.3f s  %8.1f ns/track  %6.1f ns/stop\n",
              b, b / kReps * 1e9, b / kReps / stops.size() * 1e9);
  std::printf("B / A               : %8.3f\n", b / a);
  std::printf("newton iters: pathBackward %.3f/call, pathToPlane %.3f/call\n",
              double(gBackIters) / double(gBackCalls),
              double(gPlaneIters) / double(gPlaneCalls));

  // --------------------------------------------- cost of the mBF tape
  // What the forward pass must store for mBF that it does not store now:
  // the step Jacobian per stop, and (HJ, K, S^-1, y) per measurement.
  struct Tape {
    std::vector<RzHelix::StepJacobian> f;
    std::vector<Eigen::Matrix<double, 2, eRzSize>> h;
    std::vector<Eigen::Matrix<double, eRzSize, 2>> k;
    std::vector<Eigen::Matrix<double, 2, 2>> s;
    std::vector<Eigen::Matrix<double, 2, 1>> y;
    void clear() { f.clear(); h.clear(); k.clear(); s.clear(); y.clear(); }
  };
  Tape tape;
  tape.f.reserve(32); tape.h.reserve(16); tape.k.reserve(16);
  tape.s.reserve(16); tape.y.reserve(16);
  auto t4 = std::chrono::steady_clock::now();
  for (int rep = 0; rep < kReps; ++rep) {
    tape.clear();
    for (std::size_t i = 0; i < stops.size(); ++i) {
      tape.f.push_back(jacs[i]);
      if (stops[i].measurement) {
        tape.h.push_back(hj[i]);
        tape.k.push_back(kk[i]);
        tape.s.push_back(si[i]);
        tape.y.push_back(yy[i]);
      }
    }
    sink = sink + tape.f.back().f1 + tape.h.back()(0, 0);
  }
  auto t5 = std::chrono::steady_clock::now();
  const double tp = std::chrono::duration<double>(t5 - t4).count();
  std::printf("tape write          : %8.3f s  %8.1f ns/track  (%zu doubles)\n",
              tp, tp / kReps * 1e9,
              stops.size() * 23 + 10 * (14 + 14 + 4 + 2));

  // ------------------------- A with a looser pathBackward tolerance
  gBackIters = gBackCalls = 0;
  gBackTol = 1e-6;
  auto t6 = std::chrono::steady_clock::now();
  for (int rep = 0; rep < kReps; ++rep) {
    State state;
    state.v = states.back();
    state.anchor = state.v;
    state.c = c0;
    state.pathSince = 0.;
    for (int i = static_cast<int>(stops.size()) - 2; i >= 0; --i) {
      const Stop& st = stops[i];
      const double s = pathBackward(helix, state.v, st.radius, -paths[i + 1]);
      helix.step(state.v, s);
      state.pathSince += s;
      state.pending.varAngle += 1e-8;
      state.pending.varQOverP += 1e-12;
      state.pending.advance(-s);
      state.c = helix.stepJacobianOnto(state.anchor, state.pathSince, state.v,
                                       st.normal)
                    .transport(state.c);
      state.anchor = state.v;
      state.pathSince = 0.;
      materialise(state, st.normal);
      if (st.measurement) {
        evaluateAndUpdate(helix, state, st);
      }
    }
    sink = sink + state.v[eRzQOverP] + state.c(0, 0);
  }
  auto t7 = std::chrono::steady_clock::now();
  const double aLoose = std::chrono::duration<double>(t7 - t6).count();
  std::printf("A, pathBackward tol 1e-6 : %8.1f ns/track  (%.3f iters/call)\n",
              aLoose / kReps * 1e9, double(gBackIters) / double(gBackCalls));
  std::printf("sink %g\n", static_cast<double>(sink));
  return 0;
}
