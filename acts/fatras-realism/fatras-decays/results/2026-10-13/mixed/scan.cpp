#include "Acts/MagneticField/ConstantBField.hpp"
#include "Acts/Propagator/Navigator.hpp"
#include "Acts/Propagator/Propagator.hpp"
#include "Acts/Propagator/StraightLineStepper.hpp"
#include "Acts/Propagator/SympyStepper.hpp"
#include "Acts/Utilities/UnitVectors.hpp"
#include "ActsFatras/Kernel/MultiParticleSimulation.hpp"
#include "ActsFatras/Kernel/SingleParticleSimulation.hpp"
#include "ActsFatras/Physics/Decay/NoDecay.hpp"
#include "ActsFatras/Physics/Decay/NativeDecay.hpp"
#include "ActsFatras/Selectors/DecayParticleSelector.hpp"
#include "ActsFatras/Physics/StandardInteractions.hpp"
#include "ActsFatras/Selectors/SurfaceSelectors.hpp"
#include "ActsTests/CommonHelpers/CylindricalTrackingGeometry.hpp"

#include <algorithm>
#include <array>
#include <chrono>
#include <cstdlib>
#include <numbers>
#include <cmath>
#include <iostream>
#include <iomanip>
#include <fstream>
#include <map>
#include <random>
#include <stdexcept>
#include <vector>

using namespace Acts;
using namespace Acts::UnitLiterals;
using namespace ActsFatras;

struct Sensitive {
  bool operator()(const Surface& surface) const { return surface.isSensitive(); }
};

int main(int argc, char** argv) {
  if (argc < 7 || argc > 8) {
    std::cerr << "usage: scan EVENTS PMIN_GEV SEED FIRST_EVENT PTMIN_GEV ENABLE_DECAYS [NUCLEAR_TABLE]\n";
    return 2;
  }
  const int events = std::stoi(argv[1]);
  const int firstEvent = argc >= 5 ? std::stoi(argv[4]) : 0;
  const auto level = std::getenv("FATRAS_TRACE") ? Logging::VERBOSE : Logging::ERROR;
  const auto logger = [level](const char* name) {
    return getDefaultLogger(name, level, &std::cerr);
  };
  const double pMin = std::stod(argv[2]);
  const double pTMin = argc >= 6 ? std::stod(argv[5]) : 0;
  const unsigned int seed = std::stoul(argv[3]);
  if (events < 1 || pMin < 0.05 || pTMin < 0) {
    throw std::invalid_argument("positive events and pMin >= 0.05 GeV required");
  }
  auto geoCtx = GeometryContext::dangerouslyDefaultConstruct();
  MagneticFieldContext magCtx;
  ActsTests::CylindricalTrackingGeometry builder(geoCtx);
  auto geometry = builder();
  auto field = std::make_shared<ConstantBField>(Vector3(0, 0, 2_T));
  using CP = Propagator<SympyStepper, Navigator>;
  using NP = Propagator<StraightLineStepper, Navigator>;
  using Cut = Min<Casts::P>;
#ifdef FATRAS_TRANSPORT_SELECTION
  using ChargedCut = CombineAnd<Cut, Min<Casts::Pt>>;
  using CS = SingleParticleSimulation<CP, StandardChargedInteractions,
                                      Sensitive, NoDecay, ChargedCut>;
#else
  using ChargedCut = Cut;
  using CS = SingleParticleSimulation<CP, StandardChargedInteractions,
                                      Sensitive, NoDecay>;
  if (pTMin != 0) { throw std::invalid_argument("historical headers require pTMin=0"); }
#endif
  // Match the Examples Fatras neutral configuration.
  using NS = SingleParticleSimulation<NP, InteractionList<PhotonConversion>,
                                      NoSurface, NativeDecay>;
  using NCut = DecayParticleSelector<NativeDecay, Cut>;
  MultiParticleSimulation<ChargedCut, CS, NCut, NS> simulation(
      CS(CP(SympyStepper(field), Navigator({geometry}, logger("ChargedNav")), logger("ChargedProp")),
         logger("Charged")),
      NS(NP(StraightLineStepper(), Navigator({geometry}, logger("NeutralNav")), logger("NeutralProp")),
         logger("Neutral")));
#ifdef FATRAS_TRANSPORT_SELECTION
  simulation.selectCharged.get<Cut>().valMin = pMin;
  simulation.selectCharged.get<Min<Casts::Pt>>().valMin = pTMin;
  simulation.charged.selectParticle = simulation.selectCharged;
#else
  simulation.selectCharged.valMin = pMin;
#endif
  simulation.selectNeutral.selectStable.valMin = pMin;
  simulation.selectNeutral.decay.enabled = simulation.neutral.decay.enabled = std::stoi(argv[6]) != 0;
  std::shared_ptr<const NuclearInteractionTable> table;
  if(argc == 8) {
    std::ifstream input(argv[7]);
    table=std::make_shared<NuclearInteractionTable>(NuclearInteractionTable::read(input));
  }
  simulation.charged.interactions = makeStandardChargedInteractions(pMin,table);
  simulation.charged.maxStepSize = simulation.neutral.maxStepSize = 1_m;
  simulation.charged.pathLimit = simulation.neutral.pathLimit = 10_m;
#ifdef V0_ONLY
  const std::array<PdgParticle, 3> species = {eKaon0Short, eLambda0, static_cast<PdgParticle>(-eLambda0)};
  constexpr double minimumP = 0.001;
#else
  const std::array<PdgParticle, 11> species = {
      eElectron, ePositron, eGamma, eGamma, ePionPlus, ePionMinus, eProton, eMuon,
      eKaon0Short, eLambda0, static_cast<PdgParticle>(-eLambda0)};
  constexpr double minimumP = 0.1;
#endif
  std::size_t particles = 0, secondaryParticles = 0, hits = 0, secondaryHits = 0;
  std::size_t failures = 0, rejectedInputs = 0, stopped = 0;
  std::map<std::uint64_t, std::pair<std::size_t, std::size_t>> layers;
  std::map<int, std::size_t> secondaryByProcess;
  std::map<std::string, std::size_t> failuresByError;
  std::size_t nuclearHits=0, decayHits=0;
  std::map<int, std::size_t> decayed;
  double elapsed = 0;
  std::vector<double> eventTimes;
  for (int event = firstEvent; event < firstEvent + events; ++event) {
    // Separate generation and transport streams, identical inputs for every cut.
    std::mt19937_64 inputRng(seed + static_cast<unsigned int>(event));
    std::ranlux48 rng(seed + 100000u + static_cast<unsigned int>(event));
    std::uniform_real_distribution<double> uniform(0., 1.);
    std::vector<Particle> input, initial, final;
    std::vector<Hit> eventHits;
    for (std::size_t i = 0; i < species.size(); ++i) {
      const double p = std::exp(std::log(minimumP) + uniform(inputRng) * std::log(10. / minimumP));
      const double phi = (2 * uniform(inputRng) - 1) * std::numbers::pi;
      const double eta = 2 * uniform(inputRng) - 1;
      input.emplace_back(Barcode().withParticle(i + 1), species[i]);
      input.back().setAbsoluteMomentum(p).setDirection(makeDirectionFromPhiEta(phi, eta));
      rejectedInputs += input.back().charge() != 0
          ? !simulation.selectCharged(input.back())
          : !simulation.selectNeutral(input.back());
    }
    const auto start = std::chrono::steady_clock::now();
    auto result = simulation.simulate(geoCtx, magCtx, rng, input, initial, final, eventHits);
    const double seconds = std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
    elapsed += seconds;
    eventTimes.push_back(seconds);
    if (!result.ok()) {
      std::cerr << result.error().message() << '\n';
      return 1;
    }
    failures += result->size();
    for (const auto& failure : result.value()) {
      ++failuresByError[failure.error.message()];
      std::cerr << "event=" << event << " " << failure.particle
                << " error=" << failure.error.message() << '\n';
    }
    particles += initial.size();
    for (const auto& particle : initial) {
      if (particle.particleId().generation() > 0) {
        ++secondaryParticles;
        ++secondaryByProcess[static_cast<int>(particle.process())];
      }
    }
    for (const auto& particle : final) { stopped += !particle.isAlive(); if (particle.outcome() == SimulationOutcome::Decayed) ++decayed[static_cast<int>(particle.pdg())]; }
    hits += eventHits.size();
    for (const auto& hit : eventHits) {
      const bool secondary = hit.particleId().generation() > 0;
      secondaryHits += secondary;
      const auto found=std::find_if(initial.begin(),initial.end(),[&](const auto& p){return p.particleId()==hit.particleId();});
      if(found!=initial.end() && found->process()==GenerationProcess::eNuclearInteraction)++nuclearHits;
      if(found!=initial.end() && found->process()==GenerationProcess::eDecay)++decayHits;
      const auto key = GeometryIdentifier().withVolume(hit.geometryId().volume())
                                          .withLayer(hit.geometryId().layer()).value();
      ++layers[key].first;
      layers[key].second += secondary;
    }
  }
  std::ranges::sort(eventTimes);
  std::cout << "{\"events\":" << events << ",\"seed\":" << seed
            << ",\"pT_min_GeV\":" << pTMin << ",\"p_min_GeV\":" << pMin << ",\"input_particles\":" << species.size() * events
            << ",\"rejected_inputs\":" << rejectedInputs
            << ",\"simulated_particles\":" << particles
            << ",\"secondary_particles\":" << secondaryParticles
            << ",\"hits\":" << hits << ",\"secondary_hits\":" << secondaryHits
            << ",\"direct_decay_hits\":" << decayHits
            << ",\"nuclear_secondary_hits\":" << nuclearHits << ",\"failed_particles\":" << failures << ",\"killed_particles\":" << stopped
            << ",\"transport_seconds\":" << elapsed
            << ",\"median_event_seconds\":" << eventTimes[eventTimes.size()/2]
            << ",\"p95_event_seconds\":" << eventTimes[static_cast<std::size_t>(0.95 * (eventTimes.size()-1))]
            << ",\"secondary_by_process\":{";
  bool separator = false;
  for (const auto& [process, count] : secondaryByProcess) {
    if (separator) { std::cout << ','; } separator = true;
    std::cout << '\"' << process << "\":" << count;
  }
  std::cout << "},\"failures_by_error\":{";
  separator = false;
  for (const auto& [error, count] : failuresByError) {
    if (separator) { std::cout << ','; } separator = true;
    std::cout << std::quoted(error) << ':' << count;
  }
  std::cout << "},\"decayed_by_pdg\":{";
  separator = false;
  for (const auto& [pdg, count] : decayed) {
    if (separator) { std::cout << ','; } separator = true;
    std::cout << '\"' << pdg << "\":" << count;
  }
  std::cout << "},\"layers\":{";
  separator = false;
  for (const auto& [layer, count] : layers) {
    if (separator) { std::cout << ','; } separator = true;
    std::cout << '\"' << layer << "\":{\"hits\":" << count.first
              << ",\"secondary_hits\":" << count.second << '}';
  }
  std::cout << "}}\n";
}
