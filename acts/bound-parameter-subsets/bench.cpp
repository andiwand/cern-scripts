// Kernel micro-benchmark: what do the time slot and the dense covariance cost
// in the Kalman algebra? Fixed-size Eigen in double, as ACTS uses it.
//
// Not ACTS code. The kernels copy the algebra of
//   Core/src/Propagator/detail/CovarianceEngine.cpp   (J C J^T)
//   Core/include/Acts/TrackFitting/detail/GainMatrixUpdaterImpl.hpp
//   Core/src/TrackFitting/GainMatrixSmoother.cpp
// and add structured variants of the same maths.

#include <Eigen/Dense>

#include <algorithm>
#include <chrono>
#include <cstdio>
#include <functional>
#include <random>
#include <string>
#include <vector>

#define NOINLINE __attribute__((noinline))

template <int N>
using Vec = Eigen::Matrix<double, N, 1>;
template <int R, int C = R>
using Mat = Eigen::Matrix<double, R, C>;
using MatX = Eigen::MatrixXd;
using VecX = Eigen::VectorXd;
// runtime size, storage on the stack with a compile-time maximum of 6
using MatM = Eigen::Matrix<double, Eigen::Dynamic, Eigen::Dynamic, 0, 6, 6>;
using VecM = Eigen::Matrix<double, Eigen::Dynamic, 1, 0, 6, 1>;

// ---------------------------------------------------------------- transport

template <int N>
NOINLINE void transportDense(const Mat<N>& C, const Mat<N>& J, Mat<N>& out) {
  out = J * C * J.transpose();
}

// J = [[A, 0], [b^T, 1]]: nothing depends on the last parameter (time), the
// last parameter depends on the others. Full 6x6 result, 5x5 sandwich inside.
NOINLINE void transportTimeStructured(const Mat<6>& C, const Mat<6>& J,
                                      Mat<6>& out) {
  const auto A = J.topLeftCorner<5, 5>();
  const Vec<5> b = J.row(5).head<5>().transpose();
  const auto C55 = C.topLeftCorner<5, 5>();
  const Vec<5> c = C.col(5).head<5>();
  out.topLeftCorner<5, 5>() = A * C55 * A.transpose();
  const Vec<5> v = C55 * b + c;
  const Vec<5> av = A * v;
  out.col(5).head<5>() = av;
  out.row(5).head<5>() = av.transpose();
  out(5, 5) = b.dot(v) + b.dot(c) + C(5, 5);
}

// 6x6 storage, only the leading 5x5 is active. n is a runtime value.
NOINLINE void transportPrefixSwitch(int n, const Mat<6>& C, const Mat<6>& J,
                                    Mat<6>& out) {
  switch (n) {
    case 5:
      out.topLeftCorner<5, 5>() = J.topLeftCorner<5, 5>() *
                                  C.topLeftCorner<5, 5>() *
                                  J.topLeftCorner<5, 5>().transpose();
      break;
    default:
      out = J * C * J.transpose();
  }
}

// block-diagonal covariance: (loc0, phi, q/p) and (loc1, theta)
NOINLINE void transportBlock32(const Mat<3>& C3, const Mat<3>& J3,
                               const Mat<2>& C2, const Mat<2>& J2,
                               Mat<3>& out3, Mat<2>& out2) {
  out3 = J3 * C3 * J3.transpose();
  out2 = J2 * C2 * J2.transpose();
}

NOINLINE void transportHeap(const MatX& C, const MatX& J, MatX& out) {
  out = J * C * J.transpose();
}

NOINLINE void transportMax6(const MatM& C, const MatM& J, MatM& out) {
  out = J * C * J.transpose();
}

// ------------------------------------------------------------------- update

// as GainMatrixUpdaterImpl.hpp: dense projector H
template <int N, int M>
NOINLINE void updateActs(const Vec<N>& x, const Mat<N>& C, const Mat<M, N>& H,
                         const Vec<M>& m, const Mat<M>& V, Vec<N>& xOut,
                         Mat<N>& cOut) {
  const Mat<N, M> K =
      (C * H.transpose() * (H * C * H.transpose() + V).inverse()).eval();
  xOut = x + K * (m - H * x);
  const Mat<N> tmp = (Mat<N>::Identity() - K * H).eval();
  cOut = tmp * C;
}

// same maths, H is "the first M parameters": no projector products
template <int N, int M>
NOINLINE void updateStructured(const Vec<N>& x, const Mat<N>& C,
                               const Vec<M>& m, const Mat<M>& V, Vec<N>& xOut,
                               Mat<N>& cOut) {
  const Mat<M> S = C.template topLeftCorner<M, M>() + V;
  const Mat<N, M> K = C.template leftCols<M>() * S.inverse();
  xOut = x + K * (m - x.template head<M>());
  cOut = C - K * C.template topRows<M>();
}

// 6x6 storage, leading 5 active, runtime n
NOINLINE void updatePrefixSwitch(int n, const Vec<6>& x, const Mat<6>& C,
                                 const Vec<2>& m, const Mat<2>& V,
                                 Vec<6>& xOut, Mat<6>& cOut) {
  const Mat<2> Sinv = (C.topLeftCorner<2, 2>() + V).inverse();
  switch (n) {
    case 5: {
      const Mat<5, 2> K = C.topLeftCorner<5, 2>() * Sinv;
      xOut.head<5>() = x.head<5>() + K * (m - x.head<2>());
      cOut.topLeftCorner<5, 5>() =
          C.topLeftCorner<5, 5>() - K * C.topLeftCorner<2, 5>();
      break;
    }
    default: {
      const Mat<6, 2> K = C.leftCols<2>() * Sinv;
      xOut = x + K * (m - x.head<2>());
      cOut = C - K * C.topRows<2>();
    }
  }
}

// block-diagonal: two independent 1D updates, 3x3 and 2x2
NOINLINE void updateBlock32(const Vec<3>& x3, const Mat<3>& C3, double m0,
                            double v0, const Vec<2>& x2, const Mat<2>& C2,
                            double m1, double v1, Vec<3>& x3Out, Mat<3>& c3Out,
                            Vec<2>& x2Out, Mat<2>& c2Out) {
  const Vec<3> K3 = C3.col(0) / (C3(0, 0) + v0);
  x3Out = x3 + K3 * (m0 - x3[0]);
  c3Out = C3 - K3 * C3.row(0);
  const Vec<2> K2 = C2.col(0) / (C2(0, 0) + v1);
  x2Out = x2 + K2 * (m1 - x2[0]);
  c2Out = C2 - K2 * C2.row(0);
}

NOINLINE void updateHeap(const VecX& x, const MatX& C, const MatX& H,
                         const VecX& m, const MatX& V, VecX& xOut, MatX& cOut) {
  const MatX K =
      (C * H.transpose() * (H * C * H.transpose() + V).inverse()).eval();
  xOut = x + K * (m - H * x);
  const MatX tmp = (MatX::Identity(C.rows(), C.rows()) - K * H).eval();
  cOut = tmp * C;
}

// ----------------------------------------------------------------- smoother

// RTS step as GainMatrixSmoother.cpp
template <int N>
NOINLINE void rtsStep(const Vec<N>& xf, const Mat<N>& Cf, const Mat<N>& J,
                      const Vec<N>& xp, const Mat<N>& Cp, const Vec<N>& xs1,
                      const Mat<N>& Cs1, Vec<N>& xs, Mat<N>& Cs) {
  const Mat<N> G = Cf * J.transpose() * Cp.inverse();
  xs = xf + G * (xs1 - xp);
  Cs = Cf + G * (Cs1 - Cp) * G.transpose();
}

// MBF step, algebra of MbfSmootherImpl.hpp with H = first M parameters dense
template <int N, int M>
NOINLINE void mbfStep(const Mat<N>& C, const Mat<M, N>& H, const Mat<M>& V,
                      const Vec<M>& res, const Mat<N>& F, Mat<N>& bigLambda,
                      Vec<N>& smallLambda) {
  const Mat<M> Sinv = (H * C * H.transpose() + V).inverse();
  const Mat<N, M> K = C * H.transpose() * Sinv;
  const Mat<N> CHat = Mat<N>::Identity() - K * H;
  const Mat<N> bigTilde =
      H.transpose() * Sinv * H + CHat.transpose() * bigLambda * CHat;
  const Vec<N> smallTilde =
      CHat.transpose() * smallLambda - H.transpose() * Sinv * res;
  bigLambda = F.transpose() * bigTilde * F;
  smallLambda = F.transpose() * smallTilde;
}

// ------------------------------------------------------------------ harness

constexpr int kSamples = 1024;
static std::mt19937_64 rng(42);

template <int N>
Mat<N> randomSpd() {
  std::normal_distribution<double> g(0, 1);
  Mat<N> a;
  for (int i = 0; i < N * N; ++i) a.data()[i] = g(rng);
  return a * a.transpose() + Mat<N>::Identity() * N;
}

// transport jacobian with the ACTS structure: time column is a unit vector
Mat<6> randomJacobian() {
  std::normal_distribution<double> g(0, 0.3);
  Mat<6> j = Mat<6>::Identity();
  for (int r = 0; r < 6; ++r)
    for (int c = 0; c < 5; ++c) j(r, c) += g(rng);
  return j;
}

struct Row {
  std::string group, name;
  double ns;
};
static std::vector<Row> rows;
static double sink = 0;

template <typename F>
void bench(const std::string& group, const std::string& name, F&& f) {
  using clock = std::chrono::steady_clock;
  const int inner = 200;
  std::vector<double> t;
  for (int rep = 0; rep < 31; ++rep) {
    const auto t0 = clock::now();
    for (int k = 0; k < inner; ++k)
      for (int i = 0; i < kSamples; ++i) f(i);
    const auto t1 = clock::now();
    t.push_back(std::chrono::duration<double, std::nano>(t1 - t0).count() /
                (double(inner) * kSamples));
  }
  std::sort(t.begin(), t.end());
  rows.push_back({group, name, t[t.size() / 2]});
}

int main() {
  std::vector<Mat<6>> C6(kSamples), J6(kSamples), Cp6(kSamples), Cs6(kSamples);
  std::vector<Vec<6>> x6(kSamples), xp6(kSamples), xs6(kSamples);
  std::vector<Mat<2>> V2(kSamples);
  std::vector<Vec<2>> m2(kSamples);
  std::normal_distribution<double> g(0, 1);
  for (int i = 0; i < kSamples; ++i) {
    C6[i] = randomSpd<6>();
    Cp6[i] = randomSpd<6>();
    Cs6[i] = randomSpd<6>();
    J6[i] = randomJacobian();
    for (int k = 0; k < 6; ++k) {
      x6[i][k] = g(rng);
      xp6[i][k] = g(rng);
      xs6[i][k] = g(rng);
    }
    V2[i] = randomSpd<2>();
    m2[i] = Vec<2>(g(rng), g(rng));
  }
  // 5-parameter copies: the leading 5x5
  std::vector<Mat<5>> C5(kSamples), J5(kSamples), Cp5(kSamples), Cs5(kSamples);
  std::vector<Vec<5>> x5(kSamples), xp5(kSamples), xs5(kSamples);
  // block copies: (0,2,4) and (1,3)
  std::vector<Mat<3>> C3(kSamples), J3(kSamples);
  std::vector<Mat<2>> C2(kSamples), J2(kSamples);
  std::vector<Vec<3>> x3(kSamples);
  std::vector<Vec<2>> x2(kSamples);
  std::vector<MatX> CX6, JX6, CX5, JX5, VX;
  std::vector<VecX> xX6, xX5, mX;
  std::vector<MatM> CM6, JM6, CM5, JM5;
  const int i3[3] = {0, 2, 4}, i2[2] = {1, 3};
  for (int i = 0; i < kSamples; ++i) {
    C5[i] = C6[i].topLeftCorner<5, 5>();
    J5[i] = J6[i].topLeftCorner<5, 5>();
    Cp5[i] = Cp6[i].topLeftCorner<5, 5>();
    Cs5[i] = Cs6[i].topLeftCorner<5, 5>();
    x5[i] = x6[i].head<5>();
    xp5[i] = xp6[i].head<5>();
    xs5[i] = xs6[i].head<5>();
    for (int r = 0; r < 3; ++r) {
      x3[i][r] = x6[i][i3[r]];
      for (int c = 0; c < 3; ++c) {
        C3[i](r, c) = C6[i](i3[r], i3[c]);
        J3[i](r, c) = J6[i](i3[r], i3[c]);
      }
    }
    for (int r = 0; r < 2; ++r) {
      x2[i][r] = x6[i][i2[r]];
      for (int c = 0; c < 2; ++c) {
        C2[i](r, c) = C6[i](i2[r], i2[c]);
        J2[i](r, c) = J6[i](i2[r], i2[c]);
      }
    }
    CX6.emplace_back(C6[i]);
    JX6.emplace_back(J6[i]);
    CX5.emplace_back(C5[i]);
    JX5.emplace_back(J5[i]);
    VX.emplace_back(V2[i]);
    xX6.emplace_back(x6[i]);
    xX5.emplace_back(x5[i]);
    mX.emplace_back(m2[i]);
    CM6.emplace_back(C6[i]);
    JM6.emplace_back(J6[i]);
    CM5.emplace_back(C5[i]);
    JM5.emplace_back(J5[i]);
  }
  Mat<2, 6> H26 = Mat<2, 6>::Zero();
  H26(0, 0) = H26(1, 1) = 1;
  Mat<2, 5> H25 = Mat<2, 5>::Zero();
  H25(0, 0) = H25(1, 1) = 1;
  Mat<1, 6> H16 = Mat<1, 6>::Zero();
  H16(0, 0) = 1;
  Mat<1, 5> H15 = Mat<1, 5>::Zero();
  H15(0, 0) = 1;
  const MatX HX6 = H26, HX5 = H25;
  // volatile: the kernels must not see the projector or n as constants
  volatile int n5 = 5, n6 = 6;

  // ---- self check: structured == dense
  {
    Mat<6> a, b;
    transportDense<6>(C6[0], J6[0], a);
    transportTimeStructured(C6[0], J6[0], b);
    Vec<6> xa, xb;
    Mat<6> ca, cb;
    updateActs<6, 2>(x6[0], C6[0], H26, m2[0], V2[0], xa, ca);
    updateStructured<6, 2>(x6[0], C6[0], m2[0], V2[0], xb, cb);
    Mat<5> t5;
    transportDense<5>(C5[0], J5[0], t5);
    Vec<5> x5o;
    Mat<5> c5o;
    updateActs<5, 2>(x5[0], C5[0], H25, m2[0], V2[0], x5o, c5o);
    std::fprintf(stderr,
                 "check transport structured-dense %.2e, update "
                 "structured-dense %.2e, 5x5 == leading block of 6x6: "
                 "transport %.2e update %.2e\n",
                 (a - b).norm(), (ca - cb).norm() + (xa - xb).norm(),
                 (t5 - a.topLeftCorner<5, 5>()).norm(),
                 (c5o - ca.topLeftCorner<5, 5>()).norm() +
                     (x5o - xa.head<5>()).norm());
  }

  Mat<6> o6;
  Mat<5> o5;
  Mat<3> o3;
  Mat<2> o2;
  Vec<6> v6;
  Vec<5> v5;
  Vec<3> v3;
  Vec<2> v2;
  MatX oX6(6, 6), oX5(5, 5);
  VecX vX6(6), vX5(5);
  MatM oM;

  const std::string T = "transport J C J^T";
  bench(T, "6 dense (ACTS today)", [&](int i) { transportDense<6>(C6[i], J6[i], o6); sink += o6(1, 1); });
  bench(T, "6, time structure used", [&](int i) { transportTimeStructured(C6[i], J6[i], o6); sink += o6(1, 1); });
  bench(T, "5 dense (no time)", [&](int i) { transportDense<5>(C5[i], J5[i], o5); sink += o5(1, 1); });
  bench(T, "6 stored, leading 5 active, runtime switch", [&](int i) { transportPrefixSwitch(n5, C6[i], J6[i], o6); sink += o6(1, 1); });
  bench(T, "3+2 block diagonal", [&](int i) { transportBlock32(C3[i], J3[i], C2[i], J2[i], o3, o2); sink += o3(1, 1); });
  bench(T, "runtime size 6, max-size storage", [&](int i) { transportMax6(CM6[i], JM6[i], oM); sink += oM(1, 1); });
  bench(T, "runtime size 5, max-size storage", [&](int i) { transportMax6(CM5[i], JM5[i], oM); sink += oM(1, 1); });
  bench(T, "runtime size 6, heap", [&](int i) { transportHeap(CX6[i], JX6[i], oX6); sink += oX6(1, 1); });
  bench(T, "runtime size 5, heap", [&](int i) { transportHeap(CX5[i], JX5[i], oX5); sink += oX5(1, 1); });

  const std::string U = "update, 2D measurement";
  bench(U, "6 dense H (ACTS today)", [&](int i) { updateActs<6, 2>(x6[i], C6[i], H26, m2[i], V2[i], v6, o6); sink += o6(1, 1); });
  bench(U, "6, H as index subset", [&](int i) { updateStructured<6, 2>(x6[i], C6[i], m2[i], V2[i], v6, o6); sink += o6(1, 1); });
  bench(U, "5 dense H (no time)", [&](int i) { updateActs<5, 2>(x5[i], C5[i], H25, m2[i], V2[i], v5, o5); sink += o5(1, 1); });
  bench(U, "5, H as index subset", [&](int i) { updateStructured<5, 2>(x5[i], C5[i], m2[i], V2[i], v5, o5); sink += o5(1, 1); });
  bench(U, "6 stored, leading 5 active, runtime switch", [&](int i) { updatePrefixSwitch(n5, x6[i], C6[i], m2[i], V2[i], v6, o6); sink += o6(1, 1); });
  bench(U, "3+2 block diagonal, two 1D updates", [&](int i) { updateBlock32(x3[i], C3[i], m2[i][0], V2[i](0, 0), x2[i], C2[i], m2[i][1], V2[i](1, 1), v3, o3, v2, o2); sink += o3(1, 1); });
  bench(U, "runtime size 6, heap", [&](int i) { updateHeap(xX6[i], CX6[i], HX6, mX[i], VX[i], vX6, oX6); sink += oX6(1, 1); });
  bench(U, "runtime size 5, heap", [&](int i) { updateHeap(xX5[i], CX5[i], HX5, mX[i], VX[i], vX5, oX5); sink += oX5(1, 1); });

  const std::string U1 = "update, 1D measurement";
  std::vector<Mat<1>> V1(kSamples);
  std::vector<Vec<1>> m1(kSamples);
  for (int i = 0; i < kSamples; ++i) {
    V1[i](0, 0) = V2[i](0, 0);
    m1[i][0] = m2[i][0];
  }
  bench(U1, "6 dense H (ACTS today)", [&](int i) { updateActs<6, 1>(x6[i], C6[i], H16, m1[i], V1[i], v6, o6); sink += o6(1, 1); });
  bench(U1, "6, H as index subset", [&](int i) { updateStructured<6, 1>(x6[i], C6[i], m1[i], V1[i], v6, o6); sink += o6(1, 1); });
  bench(U1, "5 dense H (no time)", [&](int i) { updateActs<5, 1>(x5[i], C5[i], H15, m1[i], V1[i], v5, o5); sink += o5(1, 1); });
  bench(U1, "5, H as index subset", [&](int i) { updateStructured<5, 1>(x5[i], C5[i], m1[i], V1[i], v5, o5); sink += o5(1, 1); });

  const std::string S = "smoother step";
  bench(S, "RTS 6 (6x6 inverse)", [&](int i) { rtsStep<6>(x6[i], C6[i], J6[i], xp6[i], Cp6[i], xs6[i], Cs6[i], v6, o6); sink += o6(1, 1); });
  bench(S, "RTS 5 (5x5 inverse)", [&](int i) { rtsStep<5>(x5[i], C5[i], J5[i], xp5[i], Cp5[i], xs5[i], Cs5[i], v5, o5); sink += o5(1, 1); });
  {
    Mat<6> L6 = Mat<6>::Zero();
    Vec<6> l6 = Vec<6>::Zero();
    Mat<5> L5 = Mat<5>::Zero();
    Vec<5> l5 = Vec<5>::Zero();
    bench(S, "MBF 6, 2D measurement", [&](int i) { L6.setZero(); l6.setZero(); mbfStep<6, 2>(C6[i], H26, V2[i], m2[i], J6[i], L6, l6); sink += L6(1, 1); });
    bench(S, "MBF 5, 2D measurement", [&](int i) { L5.setZero(); l5.setZero(); mbfStep<5, 2>(C5[i], H25, V2[i], m2[i], J5[i], L5, l5); sink += L5(1, 1); });
  }
  (void)n6;

  std::printf("{\n  \"unit\": \"ns per call, median of 31\",\n  \"rows\": [\n");
  for (std::size_t i = 0; i < rows.size(); ++i)
    std::printf("    {\"group\": \"%s\", \"name\": \"%s\", \"ns\": %.2f}%s\n",
                rows[i].group.c_str(), rows[i].name.c_str(), rows[i].ns,
                i + 1 < rows.size() ? "," : "");
  std::printf("  ]\n}\n");
  std::fprintf(stderr, "sink %g\n", sink);
  return 0;
}
