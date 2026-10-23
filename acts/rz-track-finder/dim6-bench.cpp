// Does a two-variable direction shrink the RZ Jacobian enough to pay?
// State (x, y, z, phi, theta, q/p), Cartesian direction kept as a cache.
// Validated against the 7-dim transport through the chart Jacobian, then timed
// on the same chain of stops.
#include "Acts/TrackFinding/Rz/RzTransport.hpp"

#include <Eigen/Eigenvalues>

#include <chrono>
#include <cmath>
#include <cstdio>
#include <random>
#include <vector>

using namespace Acts;
using namespace Acts::Experimental;

namespace {

constexpr double kBz = 2. * 0.000299792458;

enum Idx6 : unsigned { eX = 0, eY, eZ, ePhi, eTheta, eQop, eSize6 };
using Vec6 = Eigen::Matrix<double, 6, 1>;
using Mat6 = Eigen::Matrix<double, 6, 6>;

// -------------------------------------------------------- 6-dim transport

/// The direction and its two chart derivatives, from the cached unit vector
struct Dir {
  Vector3 d;
  double sT{}, cT{};
  Vector3 dPhi;   // d(d)/d(phi) = sT * ephi
  Vector3 dTheta; // d(d)/d(theta), unit
};

Dir dirOf(double phi, double theta) {
  Dir r;
  const double sp = std::sin(phi), cp = std::cos(phi);
  r.sT = std::sin(theta);
  r.cT = std::cos(theta);
  r.d = Vector3(r.sT * cp, r.sT * sp, r.cT);
  r.dPhi = Vector3(-r.sT * sp, r.sT * cp, 0.);
  r.dTheta = Vector3(r.cT * cp, r.cT * sp, -r.sT);
  return r;
}

/// Chart Jacobian d(x,y,z,dx,dy,dz,qop)/d(x,y,z,phi,theta,qop)
Eigen::Matrix<double, 7, 6> chart(const Dir& u) {
  Eigen::Matrix<double, 7, 6> g = Eigen::Matrix<double, 7, 6>::Zero();
  g(eRzPos0, eX) = g(eRzPos1, eY) = g(eRzPos2, eZ) = 1.;
  g.block<3, 1>(eRzDir0, ePhi) = u.dPhi;
  g.block<3, 1>(eRzDir0, eTheta) = u.dTheta;
  g(eRzQOverP, eQop) = 1.;
  return g;
}

/// The step Jacobian in the chart, constrained to end on a surface. Two rows
/// are the identity, so they never enter the apply.
struct StepJac6 {
  double dxdphi{}, dxdth{}, a1{};
  double dydphi{}, dydth{}, a2{};
  double dzdth{};
  double dphidqop{};
  Vec6 d{Vec6::Zero()};      // derivative of the end state
  Vec6 dsdv{Vec6::Zero()};   // ds/d(start)

  void applyLeft(const double* x, double* y) const {
    const double w = dsdv[eX] * x[eX] + dsdv[eY] * x[eY] + dsdv[eZ] * x[eZ] +
                     dsdv[ePhi] * x[ePhi] + dsdv[eTheta] * x[eTheta] +
                     dsdv[eQop] * x[eQop];
    y[eX] = x[eX] + dxdphi * x[ePhi] + dxdth * x[eTheta] + a1 * x[eQop] +
            d[eX] * w;
    y[eY] = x[eY] + dydphi * x[ePhi] + dydth * x[eTheta] + a2 * x[eQop] +
            d[eY] * w;
    y[eZ] = x[eZ] + dzdth * x[eTheta] + d[eZ] * w;
    y[ePhi] = x[ePhi] + dphidqop * x[eQop] + d[ePhi] * w;
    y[eTheta] = x[eTheta];
    y[eQop] = x[eQop];
  }
  Mat6 applyLeft(const Mat6& x) const {
    Mat6 y;
    for (unsigned c = 0; c < eSize6; ++c) {
      applyLeft(x.col(c).data(), y.col(c).data());
    }
    return y;
  }
  Mat6 transport(const Mat6& c) const {
    const Mat6 jc = applyLeft(c);
    const Mat6 x = jc.transpose();
    double w[eSize6];
    for (unsigned col = 0; col < eSize6; ++col) {
      w[col] = dsdv.dot(x.col(col));
    }
    Mat6 y;
    auto row = [&](unsigned r, auto&& entry) {
      for (unsigned col = 0; col <= r; ++col) {
        y(r, col) = entry(col) + d[r] * w[col];
      }
    };
    row(eX, [&](unsigned c) {
      return x(eX, c) + dxdphi * x(ePhi, c) + dxdth * x(eTheta, c) +
             a1 * x(eQop, c);
    });
    row(eY, [&](unsigned c) {
      return x(eY, c) + dydphi * x(ePhi, c) + dydth * x(eTheta, c) +
             a2 * x(eQop, c);
    });
    row(eZ, [&](unsigned c) { return x(eZ, c) + dzdth * x(eTheta, c); });
    row(ePhi, [&](unsigned c) { return x(ePhi, c) + dphidqop * x(eQop, c); });
    for (unsigned c = 0; c <= eTheta; ++c) {
      y(eTheta, c) = x(eTheta, c);
    }
    for (unsigned c = 0; c < eSize6; ++c) {
      y(eQop, c) = x(eQop, c);
    }
    for (unsigned r = 0; r < eSize6; ++r) {
      for (unsigned c = r + 1; c < eSize6; ++c) {
        y(r, c) = y(c, r);
      }
    }
    return y;
  }
  Eigen::Matrix<double, 3, 6> positionRows() const {
    Eigen::Matrix<double, 3, 6> r = Eigen::Matrix<double, 3, 6>::Zero();
    r(0, eX) = 1.;
    r(0, ePhi) = dxdphi;
    r(0, eTheta) = dxdth;
    r(0, eQop) = a1;
    r(1, eY) = 1.;
    r(1, ePhi) = dydphi;
    r(1, eTheta) = dydth;
    r(1, eQop) = a2;
    r(2, eZ) = 1.;
    r(2, eTheta) = dzdth;
    for (unsigned i = 0; i < 3; ++i) {
      r.row(i) += d[eX + i] * dsdv.transpose();
    }
    return r;
  }
  Mat6 dense() const {
    Mat6 j = Mat6::Identity();
    j.block<3, 6>(eX, 0) = positionRows();
    j(ePhi, eQop) = dphidqop;
    j.row(ePhi) += d[ePhi] * dsdv.transpose();
    return j;
  }
};

/// Step the 6-dim state, returning the new cached direction
Dir step6(Vec6& v, const Dir& u, double s, double& dx0, double& dy0) {
  const double k = v[eQop] * kBz;
  const detail::StepTrig t = detail::stepTrig(k * s);
  const double f1 = s * t.sinc;
  const double f2 = s * t.versc;
  dx0 = u.d.x();
  dy0 = u.d.y();
  v[eX] += dx0 * f1 + dy0 * f2;
  v[eY] += -dx0 * f2 + dy0 * f1;
  v[eZ] += u.d.z() * s;
  v[ePhi] -= k * s;
  // the direction cache rotates with the step; no trigonometry of its own
  Dir r = u;
  r.d.x() = dx0 * t.cs + dy0 * t.sn;
  r.d.y() = -dx0 * t.sn + dy0 * t.cs;
  r.dPhi = Vector3(-r.d.y(), r.d.x(), 0.);
  r.dTheta = Vector3(r.cT * r.d.x() / r.sT, r.cT * r.d.y() / r.sT, -r.sT);
  return r;
}

/// The constrained step Jacobian, from the deltas the step already produced
StepJac6 stepJac6(const Vec6& v0, const Dir& u0, double s, const Dir& uEnd,
                  double dxEnd, double dyEnd, double dzEnd, double dX,
                  double dY, const Vector3& normal) {
  const double k = v0[eQop] * kBz;
  const detail::StepTrig t = detail::stepTrig(k * s);
  const double g1 = s * s * t.dsinc;
  const double g2 = s * s * t.dversc;
  const double ctst = u0.cT / u0.sT;
  StepJac6 j;
  j.dxdphi = -dY;
  j.dydphi = dX;
  j.dxdth = ctst * dX;
  j.dydth = ctst * dY;
  j.dzdth = -u0.sT * s;
  j.a1 = kBz * (u0.d.x() * g1 + u0.d.y() * g2);
  j.a2 = kBz * (-u0.d.x() * g2 + u0.d.y() * g1);
  j.dphidqop = -kBz * s;
  j.d[eX] = dxEnd;
  j.d[eY] = dyEnd;
  j.d[eZ] = dzEnd;
  j.d[ePhi] = -k;
  const double along = normal.dot(Vector3(dxEnd, dyEnd, dzEnd));
  const double n0 = normal.x(), n1 = normal.y(), n2 = normal.z();
  j.dsdv[eX] = n0;
  j.dsdv[eY] = n1;
  j.dsdv[eZ] = n2;
  j.dsdv[ePhi] = n0 * j.dxdphi + n1 * j.dydphi;
  j.dsdv[eTheta] = n0 * j.dxdth + n1 * j.dydth + n2 * j.dzdth;
  j.dsdv[eQop] = n0 * j.a1 + n1 * j.a2;
  j.dsdv *= -1. / along;
  return j;
}

}  // namespace

int main() {
  const RzHelix helix{kBz};

  // ------------------------------------------------- validate against 7-dim
  {
    const double phi0 = 0.37, theta0 = 1.12;
    Vec6 v6;
    v6 << 3., -2., 11., phi0, theta0, 1. / 2000.;
    Dir u0 = dirOf(phi0, theta0);
    RzVector v7;
    v7.segment<3>(eRzPos0) = Vector3(v6[eX], v6[eY], v6[eZ]);
    v7.segment<3>(eRzDir0) = u0.d;
    v7[eRzQOverP] = v6[eQop];

    Mat6 c6 = Mat6::Zero();
    c6.diagonal() << 0.4, 0.3, 0.9, 1e-4, 2e-4, 1e-9;
    c6(eX, ePhi) = c6(ePhi, eX) = 3e-3;
    c6(eZ, eTheta) = c6(eTheta, eZ) = 5e-3;
    c6(ePhi, eQop) = c6(eQop, ePhi) = 2e-7;
    const RzMatrix c7 = chart(u0) * c6 * chart(u0).transpose();

    const double radius = 250.;
    const std::optional<double> s = helix.pathToCylinder(v7, radius);
    RzVector w7 = v7;
    helix.step(w7, *s);
    const Vector3 pEnd = w7.segment<3>(eRzPos0);
    const Vector3 normal = Vector3(pEnd.x(), pEnd.y(), 0.).normalized();

    const RzMatrix t7 =
        helix.stepJacobianOnto(v7, *s, w7, normal).transport(c7);

    Vec6 w6 = v6;
    double dx0 = 0., dy0 = 0.;
    const Vec6 before = w6;
    const Dir uEnd = step6(w6, u0, *s, dx0, dy0);
    const StepJac6 j6 =
        stepJac6(v6, u0, *s, uEnd, uEnd.d.x(), uEnd.d.y(), uEnd.d.z(),
                 w6[eX] - before[eX], w6[eY] - before[eY], normal);
    const Mat6 t6 = j6.transport(c6);
    const RzMatrix lifted = chart(uEnd) * t6 * chart(uEnd).transpose();

    std::printf("state  : 7-dim end pos (%.6f %.6f %.6f)\n", w7[eRzPos0],
                w7[eRzPos1], w7[eRzPos2]);
    std::printf("         6-dim end pos (%.6f %.6f %.6f)\n", w6[eX], w6[eY],
                w6[eZ]);
    std::printf("         6-dim end dir vs 7-dim: %.3e\n",
                (uEnd.d - w7.segment<3>(eRzDir0)).cwiseAbs().maxCoeff());
    std::printf("cov    : max |G C6 G^T - C7| after transport = %.3e"
                "  (|C| ~ %.3e)\n",
                (lifted - t7).cwiseAbs().maxCoeff(),
                t7.cwiseAbs().maxCoeff());
    // sanity: the dense forms agree through the chart too
    const Eigen::Matrix<double, 7, 6> gEnd = chart(uEnd);
    const RzMatrix jd = helix.stepJacobianOnto(v7, *s, w7, normal).dense();
    std::printf("jac    : max |J7 G0 - Gend J6| = %.3e\n",
                (jd * chart(u0) - gEnd * j6.dense()).cwiseAbs().maxCoeff());
  }

  // ------------------------------------------------------------ timing
  std::mt19937_64 rng(42);
  std::normal_distribution<double> gauss(0., 1.);

  struct Stop {
    double radius{};
    Vector3 normal{}, u{}, v{}, position{};
    double cov00{}, cov11{};
  };
  const double phi0 = 0.3, theta0 = 1.19;
  RzVector v0;
  {
    const Dir u = dirOf(phi0, theta0);
    v0.segment<3>(eRzPos0) = Vector3::Zero();
    v0.segment<3>(eRzDir0) = u.d;
    v0[eRzQOverP] = 1. / 2000.;
  }
  std::vector<Stop> stops;
  {
    RzVector w = v0;
    for (int i = 0; i < 20; ++i) {
      Stop st;
      st.radius = 33. + i * 50.;
      const std::optional<double> s = helix.pathToCylinder(w, st.radius);
      if (!s.has_value()) {
        std::printf("track does not reach r = %g\n", st.radius);
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
      st.position = p + 0.05 * gauss(rng) * st.u + 0.3 * gauss(rng) * st.v;
      stops.push_back(st);
    }
  }

  RzMatrix c07 = RzMatrix::Zero();
  c07.block<3, 3>(eRzPos0, eRzPos0) = 1. * SquareMatrix3::Identity();
  c07.block<3, 3>(eRzDir0, eRzDir0) = 1e-4 * SquareMatrix3::Identity();
  c07(eRzQOverP, eRzQOverP) = 1e-9;
  Mat6 c06 = Mat6::Zero();
  c06.diagonal() << 1., 1., 1., 1e-4, 1e-4, 1e-9;

  volatile double sink = 0.;
  const int kReps = 300000;

  // ---- 7-dim: transport, material, evaluate, update, per stop
  auto t0 = std::chrono::steady_clock::now();
  for (int rep = 0; rep < kReps; ++rep) {
    RzVector v = v0;
    RzMatrix c = c07;
    for (const Stop& st : stops) {
      const std::optional<double> s = helix.pathToCylinder(v, st.radius);
      RzVector w = v;
      helix.step(w, *s);
      const RzHelix::StepJacobian j =
          helix.stepJacobianOnto(v, *s, w, st.normal);
      c = j.transport(c);
      v = w;
      // material: scattering and straggling, projected on the surface
      {
        const Vector3 d = v.segment<3>(eRzDir0);
        const SquareMatrix3 tr = SquareMatrix3::Identity() - d * d.transpose();
        c.block<3, 3>(eRzDir0, eRzDir0) += 1e-8 * tr;
        c.block<3, 3>(eRzPos0, eRzPos0) += 1e-6 * tr;
        c.block<3, 3>(eRzPos0, eRzDir0) += 1e-7 * tr;
        c.block<3, 3>(eRzDir0, eRzPos0) += 1e-7 * tr;
        c(eRzQOverP, eRzQOverP) += 1e-12;
        const SquareMatrix3 pr = SquareMatrix3::Identity() -
                                 d * st.normal.transpose() / st.normal.dot(d);
        c.block<3, eRzSize>(eRzPos0, 0) = pr * c.block<3, eRzSize>(eRzPos0, 0);
        c.block<eRzSize, 3>(0, eRzPos0) =
            c.block<eRzSize, 3>(0, eRzPos0) * pr.transpose();
      }
      // evaluate on the module, update at the stop
      {
        const Eigen::Matrix<double, 3, eRzSize> jp = j.positionRows();
        const Eigen::Matrix<double, 1, eRzSize> hu = st.u.transpose() * jp;
        const Eigen::Matrix<double, 1, eRzSize> hv = st.v.transpose() * jp;
        Eigen::Matrix<double, eRzSize, 2> ch;
        ch.col(0) = c * hu.transpose();
        ch.col(1) = c * hv.transpose();
        const double s00 = hu.dot(ch.col(0)) + st.cov00;
        const double s01 = hv.dot(ch.col(0));
        const double s11 = hv.dot(ch.col(1)) + st.cov11;
        const double det = s00 * s11 - s01 * s01;
        Eigen::Matrix<double, 2, 2> si;
        si << s11 / det, -s01 / det, -s01 / det, s00 / det;
        const Vector3 dd = st.position - v.segment<3>(eRzPos0);
        Eigen::Matrix<double, 2, 1> res;
        res << st.u.dot(dd), st.v.dot(dd);
        const Eigen::Matrix<double, eRzSize, 2> k = ch * si;
        v += k * res;
        v.segment<3>(eRzDir0).normalize();
        c -= k * ch.transpose();
        c = 0.5 * (c + c.transpose()).eval();
      }
    }
    sink = sink + v[eRzQOverP] + c(0, 0);
  }
  auto t1 = std::chrono::steady_clock::now();

  // ---- 6-dim: the same, in the chart
  auto t2 = std::chrono::steady_clock::now();
  for (int rep = 0; rep < kReps; ++rep) {
    Vec6 v;
    v << 0., 0., 0., phi0, theta0, 1. / 2000.;
    Dir u = dirOf(phi0, theta0);
    Mat6 c = c06;
    for (const Stop& st : stops) {
      RzVector lift;
      lift.segment<3>(eRzPos0) = Vector3(v[eX], v[eY], v[eZ]);
      lift.segment<3>(eRzDir0) = u.d;
      lift[eRzQOverP] = v[eQop];
      const std::optional<double> s = helix.pathToCylinder(lift, st.radius);
      const Vec6 before = v;
      double dx0 = 0., dy0 = 0.;
      const Dir uEnd = step6(v, u, *s, dx0, dy0);
      const StepJac6 j =
          stepJac6(before, u, *s, uEnd, uEnd.d.x(), uEnd.d.y(), uEnd.d.z(),
                   v[eX] - before[eX], v[eY] - before[eY], st.normal);
      c = j.transport(c);
      u = uEnd;
      // material: two scalars for the angles, the position block as before
      {
        c(ePhi, ePhi) += 1e-8 / (u.sT * u.sT);
        c(eTheta, eTheta) += 1e-8;
        c(eQop, eQop) += 1e-12;
        const SquareMatrix3 tr =
            SquareMatrix3::Identity() - u.d * u.d.transpose();
        c.block<3, 3>(eX, eX) += 1e-6 * tr;
        const Vector3 ePhiHat = u.dPhi / u.sT;
        c.block<3, 1>(eX, ePhi) += 1e-7 * ePhiHat;
        c.block<3, 1>(eX, eTheta) += 1e-7 * u.dTheta;
        c.block<1, 3>(ePhi, eX) = c.block<3, 1>(eX, ePhi).transpose();
        c.block<1, 3>(eTheta, eX) = c.block<3, 1>(eX, eTheta).transpose();
        const SquareMatrix3 pr = SquareMatrix3::Identity() -
                                 u.d * st.normal.transpose() /
                                     st.normal.dot(u.d);
        c.block<3, 6>(eX, 0) = pr * c.block<3, 6>(eX, 0);
        c.block<6, 3>(0, eX) = c.block<6, 3>(0, eX) * pr.transpose();
      }
      {
        const Eigen::Matrix<double, 3, 6> jp = j.positionRows();
        const Eigen::Matrix<double, 1, 6> hu = st.u.transpose() * jp;
        const Eigen::Matrix<double, 1, 6> hv = st.v.transpose() * jp;
        Eigen::Matrix<double, 6, 2> ch;
        ch.col(0) = c * hu.transpose();
        ch.col(1) = c * hv.transpose();
        const double s00 = hu.dot(ch.col(0)) + st.cov00;
        const double s01 = hv.dot(ch.col(0));
        const double s11 = hv.dot(ch.col(1)) + st.cov11;
        const double det = s00 * s11 - s01 * s01;
        Eigen::Matrix<double, 2, 2> si;
        si << s11 / det, -s01 / det, -s01 / det, s00 / det;
        const Vector3 dd = st.position - Vector3(v[eX], v[eY], v[eZ]);
        Eigen::Matrix<double, 2, 1> res;
        res << st.u.dot(dd), st.v.dot(dd);
        const Eigen::Matrix<double, 6, 2> k = ch * si;
        v += k * res;
        // the chart needs no normalisation; the cache costs two sincos
        u = dirOf(v[ePhi], v[eTheta]);
        c -= k * ch.transpose();
        c = 0.5 * (c + c.transpose()).eval();
      }
    }
    sink = sink + v[eQop] + c(0, 0);
  }
  auto t3 = std::chrono::steady_clock::now();


  // ---- 6-dim covariance, Cartesian parameters: the chart is only ever the
  // basis the covariance lives in, so nothing needs a sine or a cosine
  auto t4 = std::chrono::steady_clock::now();
  for (int rep = 0; rep < kReps; ++rep) {
    RzVector v = v0;
    Mat6 c = c06;
    for (const Stop& st : stops) {
      const std::optional<double> s = helix.pathToCylinder(v, st.radius);
      const Vector3 p0 = v.segment<3>(eRzPos0);
      Dir u;
      u.d = v.segment<3>(eRzDir0);
      u.cT = u.d.z();
      u.sT = std::sqrt(1. - u.cT * u.cT);
      u.dPhi = Vector3(-u.d.y(), u.d.x(), 0.);
      u.dTheta = Vector3(u.cT * u.d.x() / u.sT, u.cT * u.d.y() / u.sT, -u.sT);
      RzVector w = v;
      helix.step(w, *s);
      Vec6 lift;
      lift << p0.x(), p0.y(), p0.z(), 0., 0., v[eRzQOverP];
      Dir uEnd;
      uEnd.d = w.segment<3>(eRzDir0);
      uEnd.cT = u.cT;
      uEnd.sT = u.sT;
      uEnd.dPhi = Vector3(-uEnd.d.y(), uEnd.d.x(), 0.);
      uEnd.dTheta = Vector3(uEnd.cT * uEnd.d.x() / uEnd.sT,
                            uEnd.cT * uEnd.d.y() / uEnd.sT, -uEnd.sT);
      const StepJac6 j =
          stepJac6(lift, u, *s, uEnd, uEnd.d.x(), uEnd.d.y(), uEnd.d.z(),
                   w[eRzPos0] - p0.x(), w[eRzPos1] - p0.y(), st.normal);
      c = j.transport(c);
      v = w;
      {
        c(ePhi, ePhi) += 1e-8 / (uEnd.sT * uEnd.sT);
        c(eTheta, eTheta) += 1e-8;
        c(eQop, eQop) += 1e-12;
        const SquareMatrix3 tr =
            SquareMatrix3::Identity() - uEnd.d * uEnd.d.transpose();
        c.block<3, 3>(eX, eX) += 1e-6 * tr;
        const Vector3 ePhiHat = uEnd.dPhi / uEnd.sT;
        c.block<3, 1>(eX, ePhi) += 1e-7 * ePhiHat;
        c.block<3, 1>(eX, eTheta) += 1e-7 * uEnd.dTheta;
        c.block<1, 3>(ePhi, eX) = c.block<3, 1>(eX, ePhi).transpose();
        c.block<1, 3>(eTheta, eX) = c.block<3, 1>(eX, eTheta).transpose();
        const SquareMatrix3 pr = SquareMatrix3::Identity() -
                                 uEnd.d * st.normal.transpose() /
                                     st.normal.dot(uEnd.d);
        c.block<3, 6>(eX, 0) = pr * c.block<3, 6>(eX, 0);
        c.block<6, 3>(0, eX) = c.block<6, 3>(0, eX) * pr.transpose();
      }
      {
        const Eigen::Matrix<double, 3, 6> jp = j.positionRows();
        const Eigen::Matrix<double, 1, 6> hu = st.u.transpose() * jp;
        const Eigen::Matrix<double, 1, 6> hv = st.v.transpose() * jp;
        Eigen::Matrix<double, 6, 2> ch;
        ch.col(0) = c * hu.transpose();
        ch.col(1) = c * hv.transpose();
        const double s00 = hu.dot(ch.col(0)) + st.cov00;
        const double s01 = hv.dot(ch.col(0));
        const double s11 = hv.dot(ch.col(1)) + st.cov11;
        const double det = s00 * s11 - s01 * s01;
        Eigen::Matrix<double, 2, 2> si;
        si << s11 / det, -s01 / det, -s01 / det, s00 / det;
        const Vector3 dd = st.position - v.segment<3>(eRzPos0);
        Eigen::Matrix<double, 2, 1> res;
        res << st.u.dot(dd), st.v.dot(dd);
        const Eigen::Matrix<double, 6, 2> k = ch * si;
        const Vec6 delta = k * res;
        v[eRzPos0] += delta[eX];
        v[eRzPos1] += delta[eY];
        v[eRzPos2] += delta[eZ];
        v[eRzQOverP] += delta[eQop];
        v.segment<3>(eRzDir0) +=
            delta[ePhi] * uEnd.dPhi / uEnd.sT + delta[eTheta] * uEnd.dTheta;
        v.segment<3>(eRzDir0).normalize();
        c -= k * ch.transpose();
        c = 0.5 * (c + c.transpose()).eval();
      }
    }
    sink = sink + v[eRzQOverP] + c(0, 0);
  }
  auto t5 = std::chrono::steady_clock::now();
  const double cc = std::chrono::duration<double>(t5 - t4).count();

  // ---- what the pure covariance transport costs on its own, 7 against 6
  auto t6 = std::chrono::steady_clock::now();
  for (int rep = 0; rep < kReps; ++rep) {
    RzMatrix c = c07;
    RzVector v = v0;
    for (const Stop& st : stops) {
      const std::optional<double> s = helix.pathToCylinder(v, st.radius);
      RzVector w = v;
      helix.step(w, *s);
      c = helix.stepJacobianOnto(v, *s, w, st.normal).transport(c);
      v = w;
    }
    sink = sink + c(0, 0);
  }
  auto t7 = std::chrono::steady_clock::now();
  auto t8 = std::chrono::steady_clock::now();
  for (int rep = 0; rep < kReps; ++rep) {
    Mat6 c = c06;
    RzVector v = v0;
    for (const Stop& st : stops) {
      const std::optional<double> s = helix.pathToCylinder(v, st.radius);
      const Vector3 p0 = v.segment<3>(eRzPos0);
      Dir u;
      u.d = v.segment<3>(eRzDir0);
      u.cT = u.d.z();
      u.sT = std::sqrt(1. - u.cT * u.cT);
      RzVector w = v;
      helix.step(w, *s);
      Dir uEnd = u;
      uEnd.d = w.segment<3>(eRzDir0);
      Vec6 lift;
      lift << p0.x(), p0.y(), p0.z(), 0., 0., v[eRzQOverP];
      c = stepJac6(lift, u, *s, uEnd, uEnd.d.x(), uEnd.d.y(), uEnd.d.z(),
                   w[eRzPos0] - p0.x(), w[eRzPos1] - p0.y(), st.normal)
              .transport(c);
      v = w;
    }
    sink = sink + c(0, 0);
  }
  auto t9 = std::chrono::steady_clock::now();
  // ---- geometry only, to subtract: the solve and the step carry no covariance
  auto ta = std::chrono::steady_clock::now();
  for (int rep = 0; rep < kReps; ++rep) {
    RzVector v = v0;
    for (const Stop& st : stops) {
      const std::optional<double> s = helix.pathToCylinder(v, st.radius);
      helix.step(v, *s);
    }
    sink = sink + v[eRzPos0];
  }
  auto tb = std::chrono::steady_clock::now();
  const double geo = std::chrono::duration<double>(tb - ta).count();

  const double tr7 = std::chrono::duration<double>(t7 - t6).count();
  const double tr6 = std::chrono::duration<double>(t9 - t8).count();

  const double a = std::chrono::duration<double>(t1 - t0).count();
  const double b = std::chrono::duration<double>(t3 - t2).count();
  std::printf("\nstops %zu, reps %d\n", stops.size(), kReps);
  std::printf("7-dim (dir as 3 vector) : %7.1f ns/track  %6.1f ns/stop\n",
              a / kReps * 1e9, a / kReps / stops.size() * 1e9);
  std::printf("6-dim (phi, theta)      : %7.1f ns/track  %6.1f ns/stop\n",
              b / kReps * 1e9, b / kReps / stops.size() * 1e9);
  std::printf("6-dim cov, cartesian par: %7.1f ns/track  %6.1f ns/stop\n",
              cc / kReps * 1e9, cc / kReps / stops.size() * 1e9);
  std::printf("6 / 7 (phi,theta state) : %7.3f\n", b / a);
  std::printf("6 / 7 (cartesian param) : %7.3f\n", cc / a);
  std::printf("\ntransport + geometry solve only:\n");
  std::printf("  7-dim %7.1f ns/track   6-dim %7.1f ns/track   ratio %.3f\n",
              tr7 / kReps * 1e9, tr6 / kReps * 1e9, tr6 / tr7);
  const double g = geo / kReps * 1e9;
  std::printf("\ngeometry solve alone (common to both): %.1f ns/track\n", g);
  std::printf("covariance algebra alone:\n");
  std::printf("  transport      7-dim %7.1f   6-dim %7.1f   ratio %.3f\n",
              tr7 / kReps * 1e9 - g, tr6 / kReps * 1e9 - g,
              (tr6 / kReps * 1e9 - g) / (tr7 / kReps * 1e9 - g));
  std::printf("  whole stop     7-dim %7.1f   6-dim %7.1f   ratio %.3f\n",
              a / kReps * 1e9 - g, cc / kReps * 1e9 - g,
              (cc / kReps * 1e9 - g) / (a / kReps * 1e9 - g));
  // ---- conditioning: the rank the two parametrisations carry
  {
    RzVector v = v0;
    RzMatrix c7f = c07;
    Mat6 c6f = c06;
    for (const Stop& st : stops) {
      const std::optional<double> ss = helix.pathToCylinder(v, st.radius);
      const Vector3 p0 = v.segment<3>(eRzPos0);
      Dir u;
      u.d = v.segment<3>(eRzDir0);
      u.cT = u.d.z();
      u.sT = std::sqrt(1. - u.cT * u.cT);
      RzVector w = v;
      helix.step(w, *ss);
      Dir uEnd = u;
      uEnd.d = w.segment<3>(eRzDir0);
      Vec6 lift;
      lift << p0.x(), p0.y(), p0.z(), 0., 0., v[eRzQOverP];
      c7f = helix.stepJacobianOnto(v, *ss, w, st.normal).transport(c7f);
      c6f = stepJac6(lift, u, *ss, uEnd, uEnd.d.x(), uEnd.d.y(), uEnd.d.z(),
                     w[eRzPos0] - p0.x(), w[eRzPos1] - p0.y(), st.normal)
                .transport(c6f);
      v = w;
    }
    const Eigen::SelfAdjointEigenSolver<RzMatrix> e7(c7f);
    const Eigen::SelfAdjointEigenSolver<Mat6> e6(c6f);
    std::printf("\nconditioning after 20 transports, no updates:\n");
    std::printf("  7-dim eigenvalues:");
    for (int i = 0; i < 7; ++i) {
      std::printf(" %.2e", e7.eigenvalues()[i]);
    }
    std::printf("\n  6-dim eigenvalues:");
    for (int i = 0; i < 6; ++i) {
      std::printf(" %.2e", e6.eigenvalues()[i]);
    }
    std::printf("\n  condition number 7-dim %.2e, 6-dim %.2e\n",
                e7.eigenvalues()[6] / std::abs(e7.eigenvalues()[0]),
                e6.eigenvalues()[5] / std::abs(e6.eigenvalues()[0]));
  }
  std::printf("sink %g\n", static_cast<double>(sink));
  return 0;
}
