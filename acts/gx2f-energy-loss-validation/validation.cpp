// This file is part of the ACTS project.
//
// Copyright (C) 2016 CERN for the benefit of the ACTS project
//
// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

// Validation harness for ACTS e98eb100aa; geometry adapted from Gx2fTests.cpp.
#include "Acts/Definitions/Algebra.hpp"
#include "Acts/Definitions/Units.hpp"
#include "Acts/EventData/Types.hpp"
#include "Acts/EventData/VectorMultiTrajectory.hpp"
#include "Acts/EventData/VectorTrackContainer.hpp"
#include "Acts/EventData/detail/TestSourceLink.hpp"
#include "Acts/Geometry/CuboidVolumeBuilder.hpp"
#include "Acts/Geometry/TrackingGeometry.hpp"
#include "Acts/Geometry/TrackingGeometryBuilder.hpp"
#include "Acts/Material/HomogeneousSurfaceMaterial.hpp"
#include "Acts/Material/MaterialSlab.hpp"
#include "Acts/Propagator/EigenStepper.hpp"
#include "Acts/Propagator/Navigator.hpp"
#include "Acts/Propagator/Propagator.hpp"
#include "Acts/Propagator/StraightLineStepper.hpp"
#include "Acts/Surfaces/PlaneSurface.hpp"
#include "Acts/Surfaces/RectangleBounds.hpp"
#include "Acts/TrackFitting/GlobalChiSquareFitter.hpp"
#include "Acts/Utilities/Logger.hpp"
#include "Acts/Visualization/EventDataView3D.hpp"
#include "Acts/Visualization/GeometryView3D.hpp"
#include "Acts/Visualization/ObjVisualization3D.hpp"
#include "ActsTests/CommonHelpers/DetectorElementStub.hpp"
#include "ActsTests/CommonHelpers/MeasurementsCreator.hpp"
#include "ActsTests/CommonHelpers/PredefinedMaterials.hpp"

#include <numbers>
#include <vector>

#include "Acts/MagneticField/ConstantBField.hpp"
#include <fstream>
#include <iomanip>
#include <chrono>
#include <random>
#include <tuple>

using namespace Acts;
using namespace Acts::Experimental;
using namespace Acts::UnitLiterals;
using namespace Acts::detail::Test;


using namespace ActsTests;
BoundTrackParameters makeParameters(
    const double x = 0.0_m, const double y = 0.0_m, const double z = 0.0_m,
    const double w = 42_ns, const double phi = 0_degree,
    const double theta = 90_degree, const double p = 2_GeV,
    const double q = 1_e) {
  // create covariance matrix from reasonable standard deviations
  BoundVector stddev;
  stddev[eBoundLoc0] = 100_um;
  stddev[eBoundLoc1] = 100_um;
  stddev[eBoundTime] = 25_ns;
  stddev[eBoundPhi] = 2_degree;
  stddev[eBoundTheta] = 2_degree;
  stddev[eBoundQOverP] = 1 / 100_GeV;
  const BoundMatrix cov = stddev.cwiseProduct(stddev).asDiagonal();
  // define a track in the transverse plane along x
  const Vector4 mPos4(x, y, z, w);
  return BoundTrackParameters::createCurvilinear(mPos4, phi, theta, q / p, cov,
                                                 ParticleHypothesis::pion());
}

static std::vector<SourceLink> prepareSourceLinks(
    const std::vector<TestSourceLink>& sourceLinks) {
  std::vector<SourceLink> result;
  std::transform(sourceLinks.begin(), sourceLinks.end(),
                 std::back_inserter(result),
                 [](const auto& sl) { return SourceLink{sl}; });
  return result;
}

/// @brief Create a simple telescope detector
///
/// @param geoCtx
/// @param nSurfaces Number of surfaces
/// @param surfaceIndexWithMaterial A set of index of the material surfaces
std::shared_ptr<const TrackingGeometry> makeToyDetector(
    const GeometryContext& geoCtx, const std::size_t nSurfaces = 5,
    const std::set<std::size_t>& surfaceIndexWithMaterial = {},
    const double materialThickness = 5_mm) {
  if (nSurfaces < 1) {
    throw std::invalid_argument("At least 1 surfaces needs to be created.");
  }

  // Define the dimensions of the square surfaces
  const double halfSizeSurface = 5_m;

  // Rotation of the surfaces around the y-axis
  const double rotationAngle = std::numbers::pi / 2.;
  const Vector3 xPos(std::cos(rotationAngle), 0., std::sin(rotationAngle));
  const Vector3 yPos(0., 1., 0.);
  const Vector3 zPos(-std::sin(rotationAngle), 0., std::cos(rotationAngle));

  // Construct builder
  CuboidVolumeBuilder cvb;

  // Create configurations for surfaces
  std::vector<CuboidVolumeBuilder::SurfaceConfig> surfaceConfig;
  for (std::size_t surfPos = 1; surfPos <= nSurfaces; surfPos++) {
    // Position of the surfaces
    CuboidVolumeBuilder::SurfaceConfig cfg;
    cfg.position = {surfPos * UnitConstants::m, 0., 0.};

    // Rotation of the surfaces
    cfg.rotation.col(0) = xPos;
    cfg.rotation.col(1) = yPos;
    cfg.rotation.col(2) = zPos;

    // Boundaries of the surfaces (shape)
    cfg.rBounds = std::make_shared<const RectangleBounds>(
        RectangleBounds(halfSizeSurface, halfSizeSurface));

    // Add material only for selected surfaces
    if (surfaceIndexWithMaterial.contains(surfPos)) {
      // Material of the surfaces
      MaterialSlab matProp(makeSilicon(), materialThickness);
      cfg.surMat = std::make_shared<HomogeneousSurfaceMaterial>(matProp);
    }

    // Thickness of the detector element
    cfg.thickness = 1_um;

    cfg.detElementConstructor =
        [](const Transform3& trans,
           const std::shared_ptr<const RectangleBounds>& bounds,
           double thickness) {
          return new DetectorElementStub(trans, bounds, thickness);
        };
    surfaceConfig.push_back(cfg);
  }

  // Build layer configurations
  std::vector<CuboidVolumeBuilder::LayerConfig> layerConfig;
  for (auto& sCfg : surfaceConfig) {
    CuboidVolumeBuilder::LayerConfig cfg;
    cfg.surfaceCfg = {sCfg};
    cfg.active = true;
    cfg.envelopeX = {-0.1_mm, 0.1_mm};
    cfg.envelopeY = {-0.1_mm, 0.1_mm};
    cfg.envelopeZ = {-0.1_mm, 0.1_mm};
    layerConfig.push_back(cfg);
  }

  // Inner Volume - Build volume configuration
  CuboidVolumeBuilder::VolumeConfig volumeConfig;
  volumeConfig.length = {(nSurfaces + 1) * 1_m, 2 * halfSizeSurface,
                         2 * halfSizeSurface};
  volumeConfig.position = {volumeConfig.length.x() / 2, 0., 0.};
  volumeConfig.layerCfg = layerConfig;
  volumeConfig.name = "TestVolume";

  // Outer volume - Build TrackingGeometry configuration
  CuboidVolumeBuilder::Config config;
  config.length = {(nSurfaces + 1) * 1_m, 2 * halfSizeSurface,
                   2 * halfSizeSurface};
  config.position = {volumeConfig.length.x() / 2, 0., 0.};
  config.volumeCfg = {volumeConfig};

  cvb.setConfig(config);

  TrackingGeometryBuilder::Config tgbCfg;

  tgbCfg.trackingVolumeBuilders.push_back(
      [=](const auto& context, const auto& inner, const auto&) {
        return cvb.trackingVolume(context, inner, nullptr);
      });

  TrackingGeometryBuilder tgb(tgbCfg);

  std::unique_ptr<const TrackingGeometry> detector =
      tgb.trackingGeometry(geoCtx);
  return detector;
}


struct TruthMaterial {
  struct result_type { std::vector<std::pair<double,double>> qop; };
  int model = 0;  // 0: vacuum, 1: Bethe deterministic, 2: mean Gaussian, 3: +scattering
  std::mt19937_64* rng = nullptr;
  template <typename State, typename Stepper, typename Navigator>
  Result<void> act(State& state, const Stepper& stepper, const Navigator& nav,
                   result_type& result, const Logger&) const {
    const auto* surface = nav.currentSurface(state.navigation);
    if (surface == nullptr || !surface->isSensitive()) return Result<void>::success();
    if (model != 0 && surface->hasMaterial()) {
      auto slabResult = Acts::detail::evaluateMaterialSlab(
          state, stepper, *surface, MaterialUpdateMode::FullUpdate);
      if (!slabResult.ok()) return slabResult.error();
      const auto& slab = *slabResult;
      if (!slab.isVacuum()) {
        const auto& particle = stepper.particleHypothesis(state.stepping);
        const double qop = stepper.qOverP(state.stepping);
        const double p = particle.extractMomentum(qop);
        const double mass = particle.mass();
        const double charge = particle.absoluteCharge();
        const double loss = model == 1
            ? computeEnergyLossBethe(slab, mass, static_cast<float>(qop), charge)
            : computeEnergyLossMean(slab, particle.absolutePdg(), mass, static_cast<float>(qop), charge);
        const double energy = std::hypot(p,mass) - loss;
        if (energy <= mass) throw std::runtime_error("Truth particle stopped");
        double nextQop = std::copysign(charge,qop)/std::sqrt(energy*energy-mass*mass);
        std::normal_distribution<double> normal;
        if (model >= 2) {
          const double sigma = computeEnergyLossLandauSigmaQOverP(slab, mass, static_cast<float>(qop), charge);
          nextQop += sigma * normal(*rng);
        }
        Vector3 direction = stepper.direction(state.stepping);
        if (model == 3) {
          const double sigma = computeMultipleScatteringTheta0(slab,particle.absolutePdg(),mass,static_cast<float>(qop),charge);
          const double theta = VectorHelpers::theta(direction);
          const double phi = VectorHelpers::phi(direction) + sigma/std::sin(theta)*normal(*rng);
          const double nextTheta = theta + sigma*normal(*rng);
          direction = Vector3(std::sin(nextTheta)*std::cos(phi),std::sin(nextTheta)*std::sin(phi),std::cos(nextTheta));
        }
        stepper.update(state.stepping,stepper.position(state.stepping),direction,nextQop,stepper.time(state.stepping));
      }
    }
    result.qop.emplace_back(surface->center(state.geoContext).x()/1_m,stepper.qOverP(state.stepping));
    return Result<void>::success();
  }
};

int main(int argc, char** argv) {
  const int nEvents = argc > 1 ? std::stoi(argv[1]) : 500;
  const std::string output = argc > 2 ? argv[2] : ".";
  const std::size_t maxUpdates = argc > 3 ? std::stoul(argv[3]) : 20;
  const double cutoff = argc > 4 ? std::stod(argv[4]) : 1e-7;
  std::set<std::tuple<int,int,int,int,int>> selected;
  if (argc > 5) {
    std::ifstream selection(argv[5]);
    int model,thickness,momentum,charge,event;
    while(selection >> model >> thickness >> momentum >> charge >> event)
      selected.emplace(model,thickness,momentum,charge,event);
  }
  const auto geo = GeometryContext::dangerouslyDefaultConstruct();
  const MagneticFieldContext mag;
  const CalibrationContext cal;
  const auto logger = getDefaultLogger("Validation", Logging::ERROR);
  std::ofstream csv(output+"/tracks.csv");
  csv << "truth,thickness_mm,p_GeV,charge,event,fit,ok,error,nmeasurements,qop_true,qop_fit,sigma_qop,relative_qop_error,pull,chi2,ndof,nupdates,time_us\n";
  csv << std::setprecision(17);
  std::ofstream profile(output+"/trajectory.csv");
  profile << "series,x_m,qop\n" << std::setprecision(17);
  const MeasurementResolutionMap resolutions{{GeometryIdentifier(),{MeasurementType::eLoc01,{25_um,50_um}}}};
  std::uint64_t cell=0;
  for (const double thickness : {0.,5.,50.}) {
    auto geometry=makeToyDetector(geo,7, thickness==0. ? std::set<std::size_t>{} : std::set<std::size_t>{2,4,6},thickness*1_mm);
    Navigator::Config navConfig{geometry};
    navConfig.resolvePassive=false; navConfig.resolveSensitive=true; navConfig.resolveMaterial=true;
    using Prop = Propagator<EigenStepper<>,Navigator>;
    Prop prop(EigenStepper<>(std::make_shared<ConstantBField>(Vector3(0,0,0.3_T))),Navigator(navConfig,getDefaultLogger("Nav",Logging::ERROR)));
    Gx2Fitter<Prop,VectorMultiTrajectory> fitter(prop,logger->clone());
    TestSourceLink::SurfaceAccessor accessor{*geometry};
    Gx2FitterExtensions<VectorMultiTrajectory> extensions;
    extensions.calibrator.connect<&testSourceLinkCalibratorStrict<VectorMultiTrajectory>>();
    extensions.surfaceAccessor.connect<&TestSourceLink::SurfaceAccessor::operator()>(&accessor);
    for (const int model : {0,1,2,3}) {
      if ((thickness==0.) != (model==0)) continue;
      const std::string truthName=std::array{"vacuum","bethe_deterministic","mean_gaussian","mean_gaussian_scattering"}[model];
      for (const double momentum : {1.,2.,5.,10.}) for (const int charge : {-1,1}) {
        std::cerr << "cell " << cell << " " << truthName << " " << thickness << " mm " << momentum << " GeV q=" << charge << "\n";
        std::default_random_engine measurementsRng(static_cast<unsigned>(410000+cell));
        std::mt19937_64 materialRng(510000+cell++);
        const auto truth=makeParameters(0,0,0,42_ns,0,90_degree,momentum*1_GeV,charge*1_e);
        for (int event=0; event<nEvents; ++event) {
          using SimActors=ActorList<MeasurementsCreator,TruthMaterial,EndOfWorldReached>;
          Prop::Options<SimActors> options(geo,mag);
          auto& creator=options.actorList.get<MeasurementsCreator>();
          creator.resolutions=resolutions; creator.rng=&measurementsRng;
          auto& material=options.actorList.get<TruthMaterial>(); material.model=model; material.rng=&materialRng;
          const auto sim=prop.propagate(truth,options);
          if (!sim.ok()) throw std::runtime_error("Truth propagation failed: "+sim.error().message());
          const auto& measurements=sim->get<Measurements>();
          if (measurements.sourceLinks.size()!=7) throw std::runtime_error("Incomplete truth measurements");
          if (argc > 5 && !selected.contains({model,static_cast<int>(thickness),static_cast<int>(momentum),charge,event})) continue;
          const auto links=prepareSourceLinks(measurements.sourceLinks);
          BoundVector seed=truth.parameters();
          seed[eBoundLoc0]+=0.2_mm; seed[eBoundLoc1]-=0.3_mm;
          seed[eBoundPhi]+=0.002; seed[eBoundTheta]-=0.003; seed[eBoundQOverP]*=1.05;
          const BoundTrackParameters start(truth.referenceSurface().getSharedPtr(),seed,truth.covariance(),truth.particleHypothesis());
          const bool profileEvent=model==1 && thickness==50. && momentum==2. && charge==1 && event==0;
          if(profileEvent) {
            profile << "truth,0," << truth.parameters()[eBoundQOverP] << '\n';
            for(const auto& [x,qop]:sim->get<TruthMaterial::result_type>().qop) profile << "truth," << x << ',' << qop << '\n';
          }
          for (int setting=0; setting<4; ++setting) {
            const std::string fitName=std::array{"off","mean_1","mode_1","mean_3"}[setting];
            Gx2FitterOptions fitOptions(geo,mag,cal,extensions,PropagatorPlainOptions(geo,mag),&truth.referenceSurface(),model==3,setting!=0,FreeToBoundCorrection(false),maxUpdates,cutoff,setting==2?Gx2fEnergyLossMode::Mode:Gx2fEnergyLossMode::Mean,setting==3?3:1);
            TrackContainer tracks{VectorTrackContainer{},VectorMultiTrajectory{}};
            const auto begin=std::chrono::steady_clock::now();
            const auto fit=fitter.fit(links.begin(),links.end(),start,fitOptions,tracks);
            const double us=std::chrono::duration<double,std::micro>(std::chrono::steady_clock::now()-begin).count();
            csv << truthName << ',' << thickness << ',' << momentum << ',' << charge << ',' << event << ',' << fitName << ',' << fit.ok() << ',';
            if(!fit.ok()) { csv << fit.error().value() << ",0," << truth.parameters()[eBoundQOverP] << ",nan,nan,nan,nan,nan,9,0," << us << '\n'; continue; }
            const double qop=fit->parameters()[eBoundQOverP];
            const double sigma=std::sqrt(fit->covariance()(eBoundQOverP,eBoundQOverP));
            const double qtrue=truth.parameters()[eBoundQOverP];
            csv << "0," << fit->nMeasurements() << ',' << qtrue << ',' << qop << ',' << sigma << ',' << (qop-qtrue)/qtrue << ',' << (qop-qtrue)/sigma << ',' << fit->chi2() << ",9," << fit->component<std::uint32_t>("Gx2fnUpdateColumn") << ',' << us << '\n';
            if(profileEvent) {
              profile << fitName << ",0," << qop << '\n';
              for(const auto& state:fit->trackStates()) if(state.typeFlags().hasMeasurement()) profile << fitName << ',' << state.referenceSurface().center(geo).x()/1_m << ',' << state.smoothed()[eBoundQOverP] << '\n';
            }
          }
        }
        csv.flush();
      }
    }
  }
}
