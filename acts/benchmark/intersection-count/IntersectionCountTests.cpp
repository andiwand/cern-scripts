// Intersection count: Gen1 vs Gen3 on an ITk-like toy detector.
//
// Builds the same module layout three ways and drives curved tracks through
// each with the EigenStepper. Counts every Surface::intersect call through a
// temporary counter in Core/src/Surfaces (see the note), split by the phase of
// the propagation loop that issued it.
//
//   gen1          Athena ActsLayerBuilder recipe: three approach surfaces per
//                 layer, material on the inner one, CylinderVolumeBuilder
//                 triples per subsystem, TrackingGeometryBuilder wrapping.
//   gen3-abut     Athena ItkBlueprintNodeBuilder recipe (main, 19.10.2026):
//                 layer volumes attached with AttachmentStrategy::Second, so
//                 they abut; SurfaceArray + Cylinder navigation policy;
//                 material on the outer cylinder / outward disc portal.
//   gen3-sandwich the proposal: thin layer volumes with gap volumes between
//                 (AttachmentStrategy::Gap), same policies.
//   gen3-tryall   gen3-abut with TryAll portal candidates instead of the
//                 Cylinder policy, to price the portal pre-selection.
//   gen3-window   gen3-abut with the Gen1 per-subsystem neighbor windows
//                 (atlas/athena!91643).
//   gen3-floor1   gen3-abut with a neighbor window floor of one bin per axis.

#include <boost/test/unit_test.hpp>

#include "Acts/Definitions/Algebra.hpp"
#include "Acts/Definitions/Units.hpp"
#include "Acts/Geometry/Blueprint.hpp"
#include "Acts/Geometry/BlueprintNode.hpp"
#include "Acts/Geometry/BlueprintOptions.hpp"
#include "Acts/Geometry/ContainerBlueprintNode.hpp"
#include "Acts/Geometry/CylinderVolumeBounds.hpp"
#include "Acts/Geometry/CylinderVolumeBuilder.hpp"
#include "Acts/Geometry/CylinderVolumeHelper.hpp"
#include "Acts/Geometry/GenericApproachDescriptor.hpp"
#include "Acts/Geometry/GeometryContext.hpp"
#include "Acts/Geometry/ILayerBuilder.hpp"
#include "Acts/Geometry/Layer.hpp"
#include "Acts/Geometry/LayerArrayCreator.hpp"
#include "Acts/Geometry/LayerBlueprintNode.hpp"
#include "Acts/Geometry/LayerCreator.hpp"
#include "Acts/Geometry/MaterialDesignatorBlueprintNode.hpp"
#include "Acts/Geometry/PassiveLayerBuilder.hpp"
#include "Acts/Geometry/ProtoLayer.hpp"
#include "Acts/Geometry/SurfaceArrayCreator.hpp"
#include "Acts/Geometry/TrackingGeometry.hpp"
#include "Acts/Geometry/TrackingGeometryBuilder.hpp"
#include "Acts/Geometry/TrackingVolume.hpp"
#include "Acts/Geometry/TrackingVolumeArrayCreator.hpp"
#include "Acts/Geometry/VolumeAttachmentStrategy.hpp"
#include "Acts/Geometry/VolumeResizeStrategy.hpp"
#include "Acts/MagneticField/ConstantBField.hpp"
#include "Acts/Material/HomogeneousSurfaceMaterial.hpp"
#include "Acts/Material/MaterialSlab.hpp"
#include "Acts/Navigation/CylinderNavigationPolicy.hpp"
#include "Acts/Navigation/SurfaceArrayNavigationPolicy.hpp"
#include "Acts/Navigation/TryAllNavigationPolicy.hpp"
#include "Acts/Propagator/ActorList.hpp"
#include "Acts/Propagator/EigenStepper.hpp"
#include "Acts/Propagator/Navigator.hpp"
#include "Acts/Propagator/NavigatorInitializeArguments.hpp"
#include "Acts/Propagator/Propagator.hpp"
#include "Acts/Propagator/StandardAborters.hpp"
#include "Acts/Surfaces/CylinderSurface.hpp"
#include "Acts/Surfaces/DiscSurface.hpp"
#include "Acts/Surfaces/Surface.hpp"
#include "Acts/Surfaces/SurfaceArray.hpp"
#include "Acts/Utilities/Logger.hpp"
#include "ActsTests/CommonHelpers/CylindricalTrackingGeometry.hpp"
#include "ActsTests/CommonHelpers/PredefinedMaterials.hpp"

#include <cmath>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <map>
#include <memory>
#include <numbers>
#include <random>
#include <string>
#include <unordered_map>
#include <vector>

using namespace Acts;
using namespace Acts::UnitLiterals;

namespace Acts::detail {
extern std::size_t g_intersectCount[10];
extern int g_intersectPhase;
}  // namespace Acts::detail

namespace ActsTests {

// ---------------------------------------------------------------------------
// Phase bookkeeping

enum Phase : int { kStepper = 0, kNextTarget = 1, kInitialize = 2, kReached = 3 };

struct PhaseGuard {
  int previous;
  explicit PhaseGuard(int phase) : previous(detail::g_intersectPhase) {
    detail::g_intersectPhase = phase;
  }
  ~PhaseGuard() { detail::g_intersectPhase = previous; }
};

struct TrackRecord {
  std::size_t volumeSwitches = 0;
  std::size_t reachedSensitive = 0;
  std::size_t reachedMaterial = 0;
  std::size_t reachedStructure = 0;
  std::vector<std::uint32_t> hits;
};

TrackRecord* g_record = nullptr;
std::unordered_map<const Surface*, std::uint32_t>* g_moduleIndex = nullptr;

class CountingNavigator {
 public:
  using Config = Navigator::Config;
  using Options = Navigator::Options;
  using State = Navigator::State;

  CountingNavigator(Config cfg, std::shared_ptr<const Logger> logger)
      : m_navigator(std::move(cfg), std::move(logger)) {}

  State makeState(const Options& options) const { return m_navigator.makeState(options); }
  const Surface* currentSurface(const State& s) const { return m_navigator.currentSurface(s); }
  const TrackingVolume* currentVolume(const State& s) const { return m_navigator.currentVolume(s); }
  const IVolumeMaterial* currentVolumeMaterial(const State& s) const { return m_navigator.currentVolumeMaterial(s); }
  const Surface* startSurface(const State& s) const { return m_navigator.startSurface(s); }
  const Surface* targetSurface(const State& s) const { return m_navigator.targetSurface(s); }
  bool endOfWorldReached(const State& s) const { return m_navigator.endOfWorldReached(s); }
  bool navigationBreak(const State& s) const { return m_navigator.navigationBreak(s); }
  bool checkTargetValid(State& s, const Vector3& p, const Vector3& d) const {
    PhaseGuard guard(kNextTarget);
    return m_navigator.checkTargetValid(s, p, d);
  }

  Result<void> initialize(State& state,
                          const NavigatorInitializeArguments& args) const {
    PhaseGuard guard(kInitialize);
    return m_navigator.initialize(state, args);
  }

  NavigationTarget nextTarget(State& state, const Vector3& position,
                              const Vector3& direction) const {
    PhaseGuard guard(kNextTarget);
    return m_navigator.nextTarget(state, position, direction);
  }

  void handleSurfaceReached(State& state, const Vector3& position,
                            const Vector3& direction,
                            const Surface& surface) const {
    PhaseGuard guard(kReached);
    if (g_record != nullptr) {
      if (surface.isSensitive()) {
        ++g_record->reachedSensitive;
        auto it = g_moduleIndex->find(&surface);
        if (it != g_moduleIndex->end()) {
          g_record->hits.push_back(it->second);
        }
      } else if (surface.surfaceMaterial() != nullptr) {
        ++g_record->reachedMaterial;
      } else {
        ++g_record->reachedStructure;
      }
    }
    const TrackingVolume* before = m_navigator.currentVolume(state);
    m_navigator.handleSurfaceReached(state, position, direction, surface);
    if (g_record != nullptr && m_navigator.currentVolume(state) != before) {
      ++g_record->volumeSwitches;
    }
  }

 private:
  Navigator m_navigator;
};

// ---------------------------------------------------------------------------
// Layout

struct BarrelSpec {
  double r;
  double halfZ;
  double halfX;
  double halfY;
  double tilt;
};

struct RingSpec {
  double r;
  double halfXmin;
  double halfXmax;
  double halfY;
};

struct DiscSpec {
  double z;  // positive side; mirrored
  std::vector<RingSpec> rings;
};

struct SubsystemSpec {
  std::string name;
  std::vector<BarrelSpec> barrel;
  std::vector<DiscSpec> discs;
  SurfaceArray::NeighborWindow barrelWindow;
  SurfaceArray::NeighborWindow endcapWindow;
  double zStagger;  // ring stagger, drives the Gen1 disc layer thickness
};

constexpr double kModuleThickness = 0.3_mm;
constexpr double kBinsFactor = 5.0;  // Athena NumberOfBinsFactor

std::vector<SubsystemSpec> itkLikeLayout() {
  std::vector<SubsystemSpec> out;
  // Inner pixel: 2 barrel layers, 4 discs per side with 2 rings
  out.push_back({"InnerPixel",
                 {{39_mm, 245_mm, 10_mm, 20_mm, 0.14},
                  {99_mm, 245_mm, 10_mm, 20_mm, 0.14}},
                 {{330_mm, {{60_mm, 8_mm, 11_mm, 20_mm}, {110_mm, 8_mm, 11_mm, 20_mm}}},
                  {450_mm, {{60_mm, 8_mm, 11_mm, 20_mm}, {110_mm, 8_mm, 11_mm, 20_mm}}},
                  {650_mm, {{60_mm, 8_mm, 11_mm, 20_mm}, {110_mm, 8_mm, 11_mm, 20_mm}}},
                  {950_mm, {{60_mm, 8_mm, 11_mm, 20_mm}, {110_mm, 8_mm, 11_mm, 20_mm}}}},
                 SurfaceArray::NeighborWindow{{0, 0}, {1, 8}},
                 SurfaceArray::NeighborWindow{{0, 0}, {2, 1}},
                 4_mm});
  // Outer pixel: 3 barrel layers, 4 discs per side with 2 rings
  out.push_back({"OuterPixel",
                 {{160_mm, 380_mm, 10_mm, 20_mm, 0.14},
                  {228_mm, 380_mm, 10_mm, 20_mm, 0.14},
                  {291_mm, 380_mm, 10_mm, 20_mm, 0.14}},
                 {{500_mm, {{180_mm, 9_mm, 12_mm, 25_mm}, {250_mm, 9_mm, 12_mm, 25_mm}}},
                  {700_mm, {{180_mm, 9_mm, 12_mm, 25_mm}, {250_mm, 9_mm, 12_mm, 25_mm}}},
                  {950_mm, {{180_mm, 9_mm, 12_mm, 25_mm}, {250_mm, 9_mm, 12_mm, 25_mm}}},
                  {1250_mm, {{180_mm, 9_mm, 12_mm, 25_mm}, {250_mm, 9_mm, 12_mm, 25_mm}}}},
                 SurfaceArray::NeighborWindow{{0, 0}, {1, 3}},
                 SurfaceArray::NeighborWindow{{0, 0}, {4, 1}},
                 1_mm});
  // Strip: 4 barrel layers, 6 discs per side with 4 rings
  std::vector<RingSpec> stripRings = {{450_mm, 25_mm, 32_mm, 55_mm},
                                      {580_mm, 25_mm, 32_mm, 55_mm},
                                      {720_mm, 25_mm, 32_mm, 55_mm},
                                      {880_mm, 25_mm, 32_mm, 55_mm}};
  out.push_back({"Strip",
                 {{405_mm, 1400_mm, 50_mm, 50_mm, 0.1},
                  {562_mm, 1400_mm, 50_mm, 50_mm, 0.1},
                  {762_mm, 1400_mm, 50_mm, 50_mm, 0.1},
                  {1000_mm, 1400_mm, 50_mm, 50_mm, 0.1}},
                 {{1500_mm, stripRings},
                  {1750_mm, stripRings},
                  {2000_mm, stripRings},
                  {2300_mm, stripRings},
                  {2600_mm, stripRings},
                  {3000_mm, stripRings}},
                 SurfaceArray::NeighborWindow{{0, 0}, {1, 4}},
                 SurfaceArray::NeighborWindow{{0, 0}, {2, 1}},
                 1_mm});
  return out;
}

// Deterministic module generation shared by every variant. Modules are
// numbered in creation order so hits can be compared across variants.
struct Modules {
  CylindricalTrackingGeometry helper;
  std::unordered_map<const Surface*, std::uint32_t> index;
  // per subsystem: barrel layers, then discs (negative side first, then
  // positive) in spec order
  std::vector<std::vector<std::vector<Surface*>>> barrel;
  std::vector<std::vector<std::pair<int, std::vector<Surface*>>>> discs;
  std::vector<std::pair<int, int>> barrelBinning;  // nPhi, nZ per layer
  std::vector<std::string> table;                  // one csv line per module

  explicit Modules(const GeometryContext& gctx,
                   const std::vector<SubsystemSpec>& layout)
      : helper(gctx) {
    std::uint32_t next = 0;
    auto reg = [&](const std::vector<Surface*>& sfs, const std::string& sub,
                   const char* kind, int layer) {
      for (Surface* s : sfs) {
        const Vector3 c = s->center(gctx);
        table.push_back(std::to_string(next) + "," + sub + "," + kind + "," +
                        std::to_string(layer) + "," +
                        std::to_string(std::hypot(c.x(), c.y())) + "," +
                        std::to_string(c.z()));
        index[s] = next++;
      }
    };
    for (const SubsystemSpec& sub : layout) {
      barrel.emplace_back();
      discs.emplace_back();
      for (const BarrelSpec& b : sub.barrel) {
        const double pitchPhi = 2 * b.halfX * 0.9;
        const double pitchZ = 2 * b.halfY * 0.9;
        int nPhi = static_cast<int>(std::ceil(2 * std::numbers::pi * b.r / pitchPhi));
        int nZ = static_cast<int>(std::ceil(2 * b.halfZ / pitchZ));
        auto sfs = helper.surfacesCylinder(helper.detectorStore, b.halfX,
                                           b.halfY, kModuleThickness, b.tilt,
                                           b.r, 2_mm, 2 * b.halfY * 0.1,
                                           {nPhi, nZ});
        reg(sfs, sub.name, "barrel", static_cast<int>(barrel.back().size()));
        barrel.back().push_back(sfs);
        barrelBinning.emplace_back(nPhi, nZ);
      }
      for (int side : {-1, 1}) {
        for (const DiscSpec& d : sub.discs) {
          std::vector<Surface*> all;
          for (const RingSpec& ring : d.rings) {
            const double pitch = 2 * ring.halfXmax * 0.9;
            int nPhi = static_cast<int>(std::ceil(2 * std::numbers::pi * ring.r / pitch));
            nPhi += nPhi % 2;
            auto sfs = helper.surfacesRing(helper.detectorStore, ring.halfXmin,
                                           ring.halfXmax, ring.halfY,
                                           kModuleThickness, 0., ring.r,
                                           side * d.z, sub.zStagger, nPhi);
            all.insert(all.end(), sfs.begin(), sfs.end());
          }
          reg(all, sub.name, "disc", static_cast<int>(discs.back().size()));
          discs.back().emplace_back(side, all);
        }
      }
    }
  }
};

std::shared_ptr<const ISurfaceMaterial> supportMaterial() {
  static auto mat = std::make_shared<const HomogeneousSurfaceMaterial>(
      MaterialSlab(makeSilicon(), 1.5_mm));
  return mat;
}

// ---------------------------------------------------------------------------
// Gen1: Athena ActsLayerBuilder recipe

class SpecLayerBuilder : public ILayerBuilder {
 public:
  SpecLayerBuilder(const GeometryContext& gctx, const SubsystemSpec& spec,
                   const Modules& modules, std::size_t isub,
                   std::shared_ptr<const LayerCreator> layerCreator,
                   bool centralApproach)
      : m_name(spec.name) {
    using enum AxisDirection;
    // barrel
    for (std::size_t il = 0; il < spec.barrel.size(); ++il) {
      const auto& sfs = modules.barrel[isub][il];
      std::vector<std::shared_ptr<const Surface>> owned;
      std::vector<const Surface*> raw;
      for (Surface* s : sfs) {
        owned.push_back(s->getSharedPtr());
        raw.push_back(s);
      }
      ProtoLayer pl(gctx, raw);
      pl.envelope[AxisR] = {2_mm, 2_mm};
      pl.envelope[AxisZ] = {2_mm, 2_mm};
      const double layerZ = pl.medium(AxisZ, true);
      const double halfZ = 0.5 * pl.range(AxisZ);
      Transform3 transform(Translation3(0., 0., -layerZ));
      auto inner = Surface::makeShared<CylinderSurface>(transform, pl.min(AxisR), halfZ);
      auto central = Surface::makeShared<CylinderSurface>(
          transform, 0.5 * (pl.min(AxisR) + pl.max(AxisR)), halfZ);
      auto outer = Surface::makeShared<CylinderSurface>(transform, pl.max(AxisR), halfZ);
      inner->assignSurfaceMaterial(supportMaterial());
      std::vector<std::shared_ptr<const Surface>> approach{inner};
      if (centralApproach) {
        approach.push_back(central);
      }
      approach.push_back(outer);
      auto ad = std::make_unique<GenericApproachDescriptor>(std::move(approach));
      std::size_t idx = 0;
      for (std::size_t s = 0; s < isub; ++s) {
        idx += modules.barrel[s].size();
      }
      auto [nPhi, nZ] = modules.barrelBinning[idx + il];
      auto layer = layerCreator->cylinderLayer(
          gctx, std::move(owned), static_cast<std::size_t>(nPhi * kBinsFactor),
          static_cast<std::size_t>(nZ * kBinsFactor), pl, transform,
          std::move(ad), spec.barrelWindow, 0);
      m_central.push_back(layer);
    }
    // endcaps
    for (const auto& [side, sfs] : modules.discs[isub]) {
      std::vector<std::shared_ptr<const Surface>> owned;
      std::vector<const Surface*> raw;
      for (Surface* s : sfs) {
        owned.push_back(s->getSharedPtr());
        raw.push_back(s);
      }
      ProtoLayer pl(gctx, raw);
      pl.envelope[AxisR] = {2_mm, 2_mm};
      pl.envelope[AxisZ] = {2_mm, 2_mm};
      const double layerZ = pl.medium(AxisZ);
      const double halfZ = 0.5 * pl.range(AxisZ);
      const double thickness = pl.range(AxisZ);
      double zInner = layerZ - halfZ;
      double zOuter = layerZ + halfZ;
      if (std::abs(zInner) > std::abs(zOuter)) {
        std::swap(zInner, zOuter);
      }
      std::vector<std::shared_ptr<const Surface>> approach;
      auto inner = Surface::makeShared<DiscSurface>(
          Transform3(Translation3(0., 0., zInner)), pl.min(AxisR), pl.max(AxisR));
      auto nominal = Surface::makeShared<DiscSurface>(
          Transform3(Translation3(0., 0., layerZ)), pl.min(AxisR), pl.max(AxisR));
      auto outer = Surface::makeShared<DiscSurface>(
          Transform3(Translation3(0., 0., zOuter)), pl.min(AxisR), pl.max(AxisR));
      inner->assignSurfaceMaterial(supportMaterial());
      approach.push_back(inner);
      if (centralApproach) {
        approach.push_back(nominal);
      }
      approach.push_back(outer);
      if (thickness > 2_mm) {
        Transform3 trf(Translation3(0., 0., layerZ));
        approach.push_back(Surface::makeShared<CylinderSurface>(trf, pl.min(AxisR), halfZ));
        approach.push_back(Surface::makeShared<CylinderSurface>(trf, pl.max(AxisR), halfZ));
      }
      auto ad = std::make_unique<GenericApproachDescriptor>(std::move(approach));
      // bins: rings x min modules per ring, times the factor
      const DiscSpec& d = spec.discs[0];
      int nPhiMin = 1 << 30;
      for (const RingSpec& ring : d.rings) {
        const double pitch = 2 * ring.halfXmax * 0.9;
        int nPhi = static_cast<int>(std::ceil(2 * std::numbers::pi * ring.r / pitch));
        nPhi += nPhi % 2;
        nPhiMin = std::min(nPhiMin, nPhi);
      }
      auto layer = layerCreator->discLayer(
          gctx, std::move(owned),
          static_cast<std::size_t>(d.rings.size() * kBinsFactor),
          static_cast<std::size_t>(nPhiMin * kBinsFactor), pl,
          Transform3::Identity(), std::move(ad), spec.endcapWindow, 0);
      if (side < 0) {
        m_negative.push_back(layer);
      } else {
        m_positive.push_back(layer);
      }
    }
    // Gen1 wants the negative layers ordered along +z
    std::reverse(m_negative.begin(), m_negative.end());
  }

  const LayerVector negativeLayers(const GeometryContext&) const override { return m_negative; }
  const LayerVector centralLayers(const GeometryContext&) const override { return m_central; }
  const LayerVector positiveLayers(const GeometryContext&) const override { return m_positive; }
  const std::string& identification() const override { return m_name; }

 private:
  std::string m_name;
  LayerVector m_negative, m_central, m_positive;
};

std::shared_ptr<const TrackingGeometry> buildGen1(
    const GeometryContext& gctx, const std::vector<SubsystemSpec>& layout,
    const Modules& modules, bool centralApproach) {
  auto lvl = Logging::WARNING;
  auto surfaceArrayCreator = std::make_shared<const SurfaceArrayCreator>(
      getDefaultLogger("SurfaceArrayCreator", lvl));
  LayerCreator::Config lcConfig;
  lcConfig.surfaceArrayCreator = surfaceArrayCreator;
  auto layerCreator = std::make_shared<const LayerCreator>(
      lcConfig, getDefaultLogger("LayerCreator", lvl));
  LayerArrayCreator::Config lacConfig;
  auto layerArrayCreator = std::make_shared<const LayerArrayCreator>(
      lacConfig, getDefaultLogger("LayerArrayCreator", lvl));
  TrackingVolumeArrayCreator::Config tvacConfig;
  auto tVolumeArrayCreator = std::make_shared<const TrackingVolumeArrayCreator>(
      tvacConfig, getDefaultLogger("TrackingVolumeArrayCreator", lvl));
  CylinderVolumeHelper::Config cvhConfig;
  cvhConfig.layerArrayCreator = layerArrayCreator;
  cvhConfig.trackingVolumeArrayCreator = tVolumeArrayCreator;
  auto cylinderVolumeHelper = std::make_shared<const CylinderVolumeHelper>(
      cvhConfig, getDefaultLogger("CylinderVolumeHelper", lvl));

  TrackingGeometryBuilder::Config tgbConfig;
  tgbConfig.trackingVolumeHelper = cylinderVolumeHelper;

  // beam pipe as in Athena: passive layer, build to radius zero
  tgbConfig.trackingVolumeBuilders.push_back(
      [=](const GeometryContext& gctx_, const auto& inner, const auto&) {
        PassiveLayerBuilder::Config bplConfig;
        bplConfig.layerIdentification = "BeamPipe";
        bplConfig.centralLayerRadii = {25_mm};
        bplConfig.centralLayerHalflengthZ = {3200_mm};
        bplConfig.centralLayerThickness = {0.8_mm};
        bplConfig.centralLayerMaterial = {std::make_shared<const HomogeneousSurfaceMaterial>(
            MaterialSlab(makeBeryllium(), 0.8_mm))};
        auto beamPipeBuilder = std::make_shared<const PassiveLayerBuilder>(
            bplConfig, getDefaultLogger("BeamPipeLayerBuilder", lvl));
        CylinderVolumeBuilder::Config bpvConfig;
        bpvConfig.trackingVolumeHelper = cylinderVolumeHelper;
        bpvConfig.volumeName = "BeamPipe";
        bpvConfig.layerBuilder = beamPipeBuilder;
        bpvConfig.layerEnvelopeR = {1_mm, 1_mm};
        bpvConfig.buildToRadiusZero = true;
        CylinderVolumeBuilder cvb(bpvConfig, getDefaultLogger("BeamPipeVolumeBuilder", lvl));
        return cvb.trackingVolume(gctx_, inner);
      });

  for (std::size_t isub = 0; isub < layout.size(); ++isub) {
    auto lb = std::make_shared<const SpecLayerBuilder>(gctx, layout[isub], modules, isub, layerCreator, centralApproach);
    tgbConfig.trackingVolumeBuilders.push_back(
        [=](const GeometryContext& gctx_, const auto& inner, const auto&) {
          CylinderVolumeBuilder::Config cvbConfig;
          cvbConfig.layerEnvelopeR = {5_mm, 5_mm};
          cvbConfig.layerEnvelopeZ = 1_mm;
          cvbConfig.trackingVolumeHelper = cylinderVolumeHelper;
          cvbConfig.volumeName = layout[isub].name;
          cvbConfig.layerBuilder = lb;
          cvbConfig.buildToRadiusZero = false;
          CylinderVolumeBuilder cvb(cvbConfig, getDefaultLogger("CylVolBldr", lvl));
          return cvb.trackingVolume(gctx_, inner);
        });
  }

  TrackingGeometryBuilder tgb(tgbConfig, getDefaultLogger("TrackingGeometryBuilder", lvl));
  return tgb.trackingGeometry(gctx);
}

// ---------------------------------------------------------------------------
// Gen3: Athena ItkBlueprintNodeBuilder recipe, with variants

enum class Gen3Variant { Abut, Sandwich, TryAllPortals, Gen1Windows, FloorOne };

std::shared_ptr<const TrackingGeometry> buildGen3(
    const GeometryContext& gctx, const std::vector<SubsystemSpec>& layout,
    const Modules& modules, Gen3Variant variant) {
  using enum AxisDirection;
  using enum CylinderVolumeBounds::Face;
  using Attach = VolumeAttachmentStrategy;
  using Resize = VolumeResizeStrategy;
  using SAType = SurfaceArrayNavigationPolicy::LayerType;

  const bool sandwich = variant == Gen3Variant::Sandwich;

  auto policyFactory = [&](SAType type, const SubsystemSpec& spec) {
    SurfaceArrayNavigationPolicy::Config cfg{
        .layerType = type, .bins = {0, 0}, .numberOfBinsFactor = kBinsFactor};
    if (variant == Gen3Variant::Gen1Windows) {
      cfg.neighborWindow = type == SAType::Cylinder ? spec.barrelWindow : spec.endcapWindow;
    }
    if (variant == Gen3Variant::FloorOne) {
      // one bin in each direction regardless of the crossing angle
      cfg.neighborWindow = SurfaceArray::NeighborWindow{{1, 1}, {2, 2}};
    }
    if (variant == Gen3Variant::TryAllPortals) {
      return NavigationPolicyFactory{}
          .add<SurfaceArrayNavigationPolicy>(cfg)
          .add<TryAllNavigationPolicy>(TryAllNavigationPolicy::Config{
              .portals = true, .sensitives = false, .passives = false})
          .asUniquePtr();
    }
    return NavigationPolicyFactory{}
        .add<SurfaceArrayNavigationPolicy>(cfg)
        .add<CylinderNavigationPolicy>()
        .asUniquePtr();
  };

  auto toShared = [](const std::vector<Surface*>& sfs) {
    std::vector<std::shared_ptr<Surface>> out;
    for (Surface* s : sfs) {
      out.push_back(s->getSharedPtr());
    }
    return out;
  };

  Blueprint::Config cfg;
  cfg.envelope = ExtentEnvelope{{.z = {20_mm, 20_mm}, .r = {0_mm, 20_mm}}};
  Blueprint root{cfg};

  root.addCylinderContainer("ITk", AxisR, [&](auto& itk) {
    itk.setAttachmentStrategy(Attach::Second);
    itk.setResizeStrategy(Resize::Gap);

    itk.addMaterial("BeamPipe_Material", [&](auto& bpMat) {
      bpMat.configureFace(OuterCylinder, std::make_shared<const HomogeneousSurfaceMaterial>(
                                             MaterialSlab(makeBeryllium(), 0.8_mm)));
      auto bounds = std::make_unique<CylinderVolumeBounds>(0_mm, 25_mm, 3200_mm);
      bpMat.addStaticVolume(std::make_unique<TrackingVolume>(
          Transform3::Identity(), std::move(bounds), "BeamPipe"));
    });

    for (std::size_t isub = 0; isub < layout.size(); ++isub) {
      const SubsystemSpec& spec = layout[isub];
      auto& sub = itk.addCylinderContainer(spec.name, AxisZ);
      // Athena leaves the z container at its defaults (Midpoint, Expand)
      auto& brl = sub.addCylinderContainer(spec.name + "_Brl", AxisR);
      brl.setAttachmentStrategy(sandwich ? Attach::Gap : Attach::Second);
      brl.setResizeStrategies(sandwich ? Resize::Gap : Resize::Expand,
                              sandwich ? Resize::Gap : Resize::Expand);
      for (std::size_t il = 0; il < spec.barrel.size(); ++il) {
        std::string name = spec.name + "_Brl_" + std::to_string(il);
        auto configureLayer = [&](auto& node) {
          auto& layer = node.addLayer(name);
          layer.setNavigationPolicyFactory(policyFactory(SAType::Cylinder, spec));
          layer.setUseCenterOfGravity(false, false, true);
          layer.setSurfaces(toShared(modules.barrel[isub][il]));
          layer.setEnvelope(ExtentEnvelope{{.z = {5_mm, 5_mm}, .r = {2_mm, 2_mm}}});
        };
        if (il + 1 != spec.barrel.size()) {
          brl.addMaterial(name + "_Material", [&](auto& lmat) {
            lmat.configureFace(OuterCylinder, supportMaterial());
            configureLayer(lmat);
          });
        } else {
          configureLayer(brl);
        }
      }
      for (int side : {-1, 1}) {
        auto& ec = sub.addCylinderContainer(
            spec.name + (side > 0 ? "_pEC" : "_nEC"), AxisZ);
        if (sandwich) {
          ec.setAttachmentStrategy(Attach::Gap);
          ec.setResizeStrategies(Resize::Gap, Resize::Gap);
        } else {
          ec.setAttachmentStrategy(side > 0 ? Attach::Second : Attach::First);
          ec.setResizeStrategies(side > 0 ? Resize::Expand : Resize::Gap,
                                 side > 0 ? Resize::Gap : Resize::Expand);
        }
        std::size_t idisc = 0;
        for (const auto& [dside, sfs] : modules.discs[isub]) {
          if (dside != side) {
            continue;
          }
          std::string name = spec.name + (side > 0 ? "_pEC_" : "_nEC_") + std::to_string(idisc++);
          const auto outwardDisc = side > 0 ? PositiveDisc : NegativeDisc;
          ec.addMaterial(name + "_Material", [&](auto& lmat) {
            lmat.configureFace(outwardDisc, supportMaterial());
            auto& layer = lmat.addLayer(name);
            layer.setNavigationPolicyFactory(policyFactory(SAType::Disc, spec));
            layer.setUseCenterOfGravity(false, false, true);
            layer.setSurfaces(toShared(sfs));
            layer.setEnvelope(ExtentEnvelope{{.z = {1_mm, 1_mm}, .r = {2_mm, 2_mm}}});
          });
        }
      }
    }
  });

  BlueprintOptions opts;
  return root.construct(opts, gctx, *getDefaultLogger("Blueprint", Logging::WARNING));
}

// ---------------------------------------------------------------------------

struct GeometrySummary {
  std::size_t volumes = 0;
  std::size_t portals = 0;
  std::size_t boundaries = 0;
  std::size_t layers = 0;
  std::size_t sensitives = 0;
  std::size_t approach = 0;
  std::size_t materialSurfaces = 0;
};

GeometrySummary summarize(const TrackingGeometry& geometry) {
  GeometrySummary s;
  geometry.visitVolumes([&](const TrackingVolume* volume) {
    ++s.volumes;
    s.portals += volume->portals().size();
    s.boundaries += volume->boundarySurfaces().size();
    if (volume->confinedLayers() != nullptr) {
      for (const auto& layer : volume->confinedLayers()->arrayObjects()) {
        if (layer->surfaceArray() != nullptr) {
          ++s.layers;
        }
        if (layer->approachDescriptor() != nullptr) {
          s.approach += layer->approachDescriptor()->containedSurfaces().size();
        }
      }
    }
  });
  geometry.visitSurfaces([&](const Surface* surface) {
    if (surface->isSensitive()) {
      ++s.sensitives;
    } else if (surface->surfaceMaterial() != nullptr) {
      ++s.materialSurfaces;
    }
  }, false);
  return s;
}

struct Track {
  double pt;
  double eta;
  double phi;
  int charge;
};

std::vector<Track> makeTracks(std::size_t n) {
  std::mt19937 rng(42);
  std::uniform_real_distribution<double> phiDist(-std::numbers::pi, std::numbers::pi);
  std::uniform_real_distribution<double> etaDist(-2.5, 2.5);
  std::uniform_real_distribution<double> uDist(0., 1.);
  const std::vector<double> pts = {0.5_GeV, 1_GeV, 2_GeV, 5_GeV, 20_GeV};
  std::vector<Track> tracks;
  tracks.reserve(n);
  for (std::size_t i = 0; i < n; ++i) {
    Track t;
    t.pt = pts[i % pts.size()];
    t.eta = etaDist(rng);
    t.phi = phiDist(rng);
    t.charge = uDist(rng) < 0.5 ? -1 : 1;
    tracks.push_back(t);
  }
  return tracks;
}

void runVariant(const std::string& label,
                std::shared_ptr<const TrackingGeometry> geometry,
                const Modules& modules, const std::vector<Track>& tracks,
                std::ostream& csv) {
  GeometryContext gctx = GeometryContext::dangerouslyDefaultConstruct();
  MagneticFieldContext mctx;

  GeometrySummary s = summarize(*geometry);
  std::cout << label << ": volumes=" << s.volumes << " portals=" << s.portals
            << " boundaries=" << s.boundaries << " gen1layers=" << s.layers
            << " approach=" << s.approach << " sensitives=" << s.sensitives
            << " materialSurfaces=" << s.materialSurfaces << std::endl;

  using Stepper = EigenStepper<>;
  using Prop = Propagator<Stepper, CountingNavigator>;
  const char* bEnv = std::getenv("ACTS_ICOUNT_BFIELD");
  const double bz = (bEnv != nullptr ? std::stod(bEnv) : 2.0) * 1_T;
  auto bField = std::make_shared<ConstantBField>(Vector3(0., 0., bz));
  CountingNavigator::Config navCfg;
  navCfg.trackingGeometry = geometry;
  CountingNavigator navigator(navCfg, getDefaultLogger("Navigator", Logging::WARNING));
  Prop propagator(Stepper(bField), std::move(navigator),
                  getDefaultLogger("Propagator", Logging::WARNING));

  std::unordered_map<const Surface*, std::uint32_t> index = modules.index;
  g_moduleIndex = &index;

  std::size_t itrack = 0;
  std::size_t failures = 0;
  for (const Track& t : tracks) {
    TrackRecord record;
    g_record = &record;
    for (auto& c : detail::g_intersectCount) {
      c = 0;
    }
    detail::g_intersectPhase = kStepper;

    const double theta = 2 * std::atan(std::exp(-t.eta));
    Vector3 dir(std::sin(theta) * std::cos(t.phi), std::sin(theta) * std::sin(t.phi), std::cos(theta));
    const double p = t.pt / std::sin(theta);
    auto start = BoundTrackParameters::createCurvilinear(
        Vector4::Zero(), dir, t.charge / p, std::nullopt, ParticleHypothesis::pion());

    Prop::Options<ActorList<EndOfWorldReached>> options(gctx, mctx);
    options.maxSteps = 20000;
    options.stepping.maxStepSize = 1_m;
    auto result = propagator.propagate(start, options);
    g_record = nullptr;

    std::size_t steps = 0, nVol = record.volumeSwitches, nRenav = 0;
    bool ok = result.ok();
    if (ok) {
      steps = result->steps;
      nRenav = result->statistics.navigation.nRenavigations;
    } else {
      ++failures;
    }
    std::sort(record.hits.begin(), record.hits.end());
    csv << label << ',' << itrack << ',' << t.pt << ',' << t.eta << ',' << t.phi
        << ',' << t.charge << ',' << (ok ? 1 : 0) << ',' << steps << ','
        << detail::g_intersectCount[0] << ',' << detail::g_intersectCount[1] << ','
        << detail::g_intersectCount[2] << ',' << detail::g_intersectCount[3] << ','
        << detail::g_intersectCount[4] << ',' << detail::g_intersectCount[5] << ','
        << detail::g_intersectCount[6] << ',' << detail::g_intersectCount[7] << ','
        << detail::g_intersectCount[8] << ',' << detail::g_intersectCount[9] << ','
        << nVol << ',' << nRenav
        << ',' << record.reachedSensitive << ',' << record.reachedMaterial
        << ',' << record.reachedStructure << ',';
    for (std::size_t i = 0; i < record.hits.size(); ++i) {
      csv << (i > 0 ? ";" : "") << record.hits[i];
    }
    csv << '\n';
    ++itrack;
  }
  std::cout << label << ": tracks=" << itrack << " failures=" << failures << std::endl;
  g_moduleIndex = nullptr;
}

BOOST_AUTO_TEST_SUITE(IntersectionCount)

BOOST_AUTO_TEST_CASE(Gen1VsGen3) {
  GeometryContext gctx = GeometryContext::dangerouslyDefaultConstruct();
  const char* outPath = std::getenv("ACTS_ICOUNT_OUT");
  std::string out = outPath != nullptr ? outPath : "intersection-count.csv";
  const char* nTracksEnv = std::getenv("ACTS_ICOUNT_TRACKS");
  std::size_t nTracks = nTracksEnv != nullptr ? std::stoul(nTracksEnv) : 2000;
  const char* variantsEnv = std::getenv("ACTS_ICOUNT_VARIANTS");
  std::string variants = variantsEnv != nullptr ? variantsEnv : "gen1,gen1-2ap,gen3-abut,gen3-sandwich,gen3-tryall,gen3-window,gen3-floor1";

  std::ofstream csv(out);
  csv << "variant,track,pt,eta,phi,q,ok,steps,ix_stepper,ix_navother,ix_initialize,ix_reached,ix_g1layers,ix_g1surfaces,ix_g1boundaries,ix_g3portals,ix_g3surfaces,ix_g3other,volume_switches,renavigations,reached_sensitive,reached_material,reached_structure,hits\n";

  auto layout = itkLikeLayout();
  auto tracks = makeTracks(nTracks);

  auto has = [&](const std::string& v) { return variants.find(v) != std::string::npos; };

  {
    Modules modules(gctx, layout);
    std::ofstream table(out + ".modules.csv");
    table << "index,subsystem,kind,layer,r,z\n";
    for (const std::string& line : modules.table) {
      table << line << '\n';
    }
  }
  if (has("gen1,") || variants == "gen1" || variants.ends_with(",gen1")) {
    Modules modules(gctx, layout);
    std::cout << "modules: " << modules.index.size() << std::endl;
    auto geometry = buildGen1(gctx, layout, modules, true);
    runVariant("gen1", geometry, modules, tracks, csv);
  }
  if (has("gen1-2ap")) {
    Modules modules(gctx, layout);
    auto geometry = buildGen1(gctx, layout, modules, false);
    runVariant("gen1-2ap", geometry, modules, tracks, csv);
  }
  const std::vector<std::pair<std::string, Gen3Variant>> gen3s = {
      {"gen3-abut", Gen3Variant::Abut},
      {"gen3-sandwich", Gen3Variant::Sandwich},
      {"gen3-tryall", Gen3Variant::TryAllPortals},
      {"gen3-window", Gen3Variant::Gen1Windows},
      {"gen3-floor1", Gen3Variant::FloorOne}};
  for (const auto& [label, variant] : gen3s) {
    if (!has(label)) {
      continue;
    }
    Modules modules(gctx, layout);
    auto geometry = buildGen3(gctx, layout, modules, variant);
    runVariant(label, geometry, modules, tracks, csv);
  }
  std::cout << "wrote " << out << std::endl;
}

BOOST_AUTO_TEST_SUITE_END()

}  // namespace ActsTests
