#pragma once
#include "Acts/Propagator/TryAllNavigator.hpp"
#include "bounded-navigator.hpp"
#include <array>
#include <chrono>

struct NavigationAuditStats {
  // Bins: birth pT <5, <20, <50, <200, >=200 MeV. One worker only.
  std::array<std::uint64_t, 5> calls{}, failures{}, steps{};
  std::array<double, 5> path{}, seconds{};
};
inline NavigationAuditStats navigationStats;
class AuditPropagator {
  using Fast = Acts::Propagator<Acts::SympyStepper, Acts::Navigator>;
  using All =
      Acts::Propagator<Acts::SympyStepper, Acts::Experimental::TryAllNavigator>;
  using Local = Acts::Propagator<Acts::SympyStepper,
                                 Acts::Experimental::BoundedNavigator>;
  Fast fast;
  All all;
  Local local;
  int mode;
  double ptMax, farLimit, stepMax, loopFraction;
  unsigned maxSteps;

public:
  template <class Cfg>
  AuditPropagator(const Cfg &cfg, std::unique_ptr<const Acts::Logger> logger)
      : fast(Acts::SympyStepper(cfg.magneticField),
             Acts::Navigator({cfg.trackingGeometry}, logger->clone("FastNav")),
             logger->clone("FastProp")),
        all(Acts::SympyStepper(cfg.magneticField),
            Acts::Experimental::TryAllNavigator({cfg.trackingGeometry},
                                                logger->clone("AllNav")),
            logger->clone("AllProp")),
        local(Acts::SympyStepper(cfg.magneticField),
              Acts::Experimental::BoundedNavigator({cfg.trackingGeometry},
                                                   logger->clone("LocalNav")),
              logger->clone("LocalProp")),
        mode(cfg.navigationMode), ptMax(cfg.tryAllPtMax),
        farLimit(cfg.tryAllFarLimit), stepMax(cfg.tryAllStepMax),
        loopFraction(cfg.chargedLoopFraction), maxSteps(cfg.chargedMaxSteps) {}
  template <class Actors>
  using Options = typename Fast::template Options<Actors>;
  template <class Parameters, class Opt>
  auto propagate(const Parameters &initial, const Opt &input) const {
    auto options = input;
    options.loopFraction = loopFraction;
    options.maxSteps = maxSteps;
    const double pt = initial.momentum().template head<2>().norm();
    const unsigned bin = pt < .005  ? 0
                         : pt < .02 ? 1
                         : pt < .05 ? 2
                         : pt < .2  ? 3
                                    : 4;
    const auto start = std::chrono::steady_clock::now();
    const auto record = [&](auto result) {
      navigationStats.seconds[bin] +=
          std::chrono::duration<double>(std::chrono::steady_clock::now() -
                                        start)
              .count();
      ++navigationStats.calls[bin];
      if (result.ok()) {
        navigationStats.steps[bin] += result->steps;
        navigationStats.path[bin] += result->pathLength;
      } else
        ++navigationStats.failures[bin];
      return result;
    };
    if (mode == 0 || pt >= ptMax)
      return record(fast.propagate(initial, options));
    const auto propagate = [&](const auto &propagator) {
      using Prop = std::decay_t<decltype(propagator)>;
      typename Prop::template Options<typename Opt::actor_list_type> trial(
          static_cast<Acts::PropagatorPlainOptions>(options));
      trial.actorList = options.actorList;
      trial.stepping = options.stepping;
      trial.stepping.maxStepSize =
          std::min(trial.stepping.maxStepSize, stepMax);
      trial.navigation.farLimit = farLimit;
      return record(propagator.propagate(initial, trial));
    };
    if (mode == 1)
      return propagate(all);
    return propagate(local);
  }
};
