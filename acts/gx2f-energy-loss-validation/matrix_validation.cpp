// This file is part of the ACTS project.
//
// Copyright (C) 2016 CERN for the benefit of the ACTS project
//
// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

#include "Acts/TrackFitting/GlobalChiSquareFitter.hpp"
#include <fstream>
#include <iomanip>
#include <random>
using namespace Acts;
using namespace Acts::Experimental;
int main(int argc,char** argv) {
  std::ofstream out(argc>1?argv[1]:"matrix.csv");
  out << "diagonal_decades,trial,unscaled_error,equilibrated_error,covariance_error\n" << std::setprecision(17);
  std::mt19937_64 rng(91723); std::normal_distribution<double> normal;
  constexpr Eigen::Index n=18;
  for(const double decades:{0.,6.,12.,18.,24.,30.,36.}) for(int trial=0;trial<200;++trial) {
    Eigen::MatrixXd m(n,n);
    for(Eigen::Index i=0;i<n;++i) for(Eigen::Index j=0;j<n;++j) m(i,j)=normal(rng);
    Eigen::MatrixXd c=m.transpose()*m/n+Eigen::MatrixXd::Identity(n,n);
    Eigen::VectorXd d(n),v(n);
    for(Eigen::Index i=0;i<n;++i){d[i]=std::pow(10.,decades*(static_cast<double>(i)/(n-1)-.5)/2.);v[i]=normal(rng);}
    Gx2fSystem system{Gx2fParameterLayout{false,true,n-eBoundSize}};
    system.aMatrix()=d.asDiagonal()*c*d.asDiagonal();
    const Eigen::VectorXd truth=d.cwiseInverse().asDiagonal()*v;
    system.bVector()=system.aMatrix()*truth;
    const Eigen::VectorXd old=system.aMatrix().colPivHouseholderQr().solve(system.bVector());
    const Eigen::VectorXd current=computeGx2fDeltaParams(system);
    BoundMatrix covariance=BoundMatrix::Identity(); updateGx2fCovarianceParams(covariance,system);
    const BoundMatrix expected=c.inverse().topLeftCorner<eBoundSize,eBoundSize>();
    const BoundMatrix observed=d.head<eBoundSize>().asDiagonal()*covariance*d.head<eBoundSize>().asDiagonal();
    out << decades << ',' << trial << ',' << (d.asDiagonal()*(old-truth)).norm()/v.norm() << ',' << (d.asDiagonal()*(current-truth)).norm()/v.norm() << ',' << (observed-expected).norm()/expected.norm() << '\n';
  }
}
