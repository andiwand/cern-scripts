// Standalone regression test of the Athena helper against the pinned ACTS API.
#include "detail/ScatteringTailScorer.h"
#include "Acts/EventData/TrackContainer.hpp"
#include "Acts/EventData/VectorTrackContainer.hpp"
#include "Acts/EventData/VectorMultiTrajectory.hpp"
#include "Acts/Surfaces/PlaneSurface.hpp"
#include "Acts/Utilities/TrackHelpers.hpp"
#include <cassert>
#include <iostream>
using namespace Acts;
using Scorer = ActsTrk::detail::ScatteringTailScorer;
int main() {
  const Vector2 r(.3,-.1);
  SquareMatrix2 c; c << .01,.002,.002,.02;
  SquareMatrix2 d; d << .2,.05,.05,.1;
  auto density=[&](const SquareMatrix2& s){return std::exp(-.5*r.dot(s.inverse()*r))/(2*std::numbers::pi*std::sqrt(s.determinant()));};
  for(double w:{0.,.02,.8,1.}) {
    const auto v=scatteringTailLikelihood<2>(r,c,d,w);
    const auto l=(1-w)*density(c)+w*density(c+d);
    assert(std::abs(v.logLikelihood-std::log(l))<1e-12);
    assert(std::abs(v.tailWeight-w*density(c+d)/l)<1e-12);
  }
  VectorTrackContainer tb;
  VectorMultiTrajectory sb;
  TrackContainer tracks(tb,sb);
  assert(!tracks.hasColumn(hashString("scatteringTailScore")));
  Scorer::addColumns(tracks);
  auto surface=Surface::makeShared<PlaneSurface>(Transform3::Identity());
  BoundVector p=BoundVector::Zero();p[eBoundTheta]=1.;p[eBoundQOverP]=1.;
  BoundTrackParameters prediction(surface,p,.5*BoundMatrix::Identity(),ParticleHypothesis::pion());
  ScatteringTailPrior prior{.weight=.02};prior.covariance(eBoundLoc0,eBoundLoc0)=8.;
  auto append=[&](auto track,double x){
    auto state=track.appendTrackState(TrackStatePropMask::All);
    state.setReferenceSurface(surface);state.typeFlags().setIsMeasurement();
    state.allocateCalibrated(1);state.setProjectorSubspaceIndices(std::array{eBoundLoc0});
    state.template calibrated<1>()[0]=x;state.template calibratedCovariance<1>()(0,0)=.5;
    state.predictedCovariance()=10*BoundMatrix::Identity(); // Already inflated.
    Scorer::record(state,prediction,&prior);
    const auto expected=scatteringTailLikelihood<1>(Vector<1>::Constant(x),SquareMatrix<1>::Identity(),8*SquareMatrix<1>::Identity(),.02);
    assert(std::abs(state.template component<double>(hashString("scatteringTailScore"))-expected.score)<1e-12);
    return expected.score;
  };
  auto root=tracks.makeTrack();const double a=append(root,1.);
  auto left=tracks.makeTrack();left.copyFromShallow(root);
  auto right=tracks.makeTrack();right.copyFromShallow(root);
  const double b=append(left,4.),cscore=append(right,7.);
  auto hole=left.appendTrackState(TrackStatePropMask::None);hole.typeFlags().setIsHole();
  hole.component<double>(hashString("scatteringTailScore"))=1000.;
  Scorer::summarize(left);Scorer::summarize(right);
  assert(std::abs(left.component<double>(hashString("scatteringTailScore"))-(a+b))<1e-12);
  assert(std::abs(right.component<double>(hashString("scatteringTailScore"))-(a+cscore))<1e-12);
  trimTrack(left,true,true,true,true);
  auto copy=tracks.makeTrack();copy.copyFrom(left);Scorer::summarize(copy);
  assert(copy.component<double>(hashString("scatteringTailDimensions"))==2.);
  assert(copy.component<double>(hashString("scatteringTailScore"))==left.component<double>(hashString("scatteringTailScore")));
  std::cout<<"Likelihood, original prediction, branch isolation, hole and copy checks passed\n";
}
