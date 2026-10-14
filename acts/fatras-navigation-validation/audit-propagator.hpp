#pragma once
#include "Acts/Propagator/TryAllNavigator.hpp"
#include "ActsExamples/Fatras/FatrasSimulation.hpp"
#include <array>

struct NavigationAuditStats {
  std::array<std::uint64_t, 2> calls{}, failures{}, steps{};
  std::array<double, 2> path{};
};
inline NavigationAuditStats navigationStats;

// Dispatch at the start of each charged-particle trajectory. No new random
// draws. Both propagators use the same stepper, geometry and Fatras actors.
class AuditPropagator {
  using Fast = Acts::Propagator<Acts::SympyStepper, Acts::Navigator>;
  using Slow = Acts::Propagator<Acts::SympyStepper, Acts::Experimental::TryAllNavigator>;
  Fast fast;
  Slow slow;
  double ptMax, farLimit, stepMax, loopFraction;
  unsigned maxSteps;
 public:
  template<class Cfg>
  AuditPropagator(const Cfg& cfg, std::unique_ptr<const Acts::Logger> logger)
      : fast(Acts::SympyStepper(cfg.magneticField),
             Acts::Navigator({cfg.trackingGeometry}, logger->clone("FastNav")),logger->clone("FastProp")),
        slow(Acts::SympyStepper(cfg.magneticField),
             Acts::Experimental::TryAllNavigator({cfg.trackingGeometry}, logger->clone("TryAllNav")),logger->clone("TryAllProp")),
        ptMax(cfg.tryAllPtMax), farLimit(cfg.tryAllFarLimit), stepMax(cfg.tryAllStepMax),
        loopFraction(cfg.chargedLoopFraction), maxSteps(cfg.chargedMaxSteps) {}
  template<class Actors> using Options=typename Fast::template Options<Actors>;
  template<class Parameters,class Opt>
  auto propagate(const Parameters& initial, const Opt& input) const {
    auto options=input;
    options.loopFraction=loopFraction;
    options.maxSteps=maxSteps;
    const bool useTryAll=initial.momentum().template head<2>().norm()<ptMax;
    const auto record=[&](auto result) {
      const unsigned i=useTryAll ? 1 : 0;
      ++navigationStats.calls[i];
      if(result.ok()) {navigationStats.steps[i]+=result->steps;navigationStats.path[i]+=result->pathLength;}
      else ++navigationStats.failures[i];
      return result;
    };
    if(!useTryAll)return record(fast.propagate(initial,options));
    typename Slow::template Options<typename Opt::actor_list_type> trial(
        static_cast<Acts::PropagatorPlainOptions>(options));
    trial.actorList=options.actorList;
    trial.stepping=options.stepping;
    trial.stepping.maxStepSize=std::min(trial.stepping.maxStepSize,stepMax);
    trial.navigation.farLimit=farLimit;
    return record(slow.propagate(initial,trial));
  }
};
