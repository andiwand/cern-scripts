#include "Acts/Definitions/Units.hpp"
#include "ActsFatras/Geant4/Geant4NuclearInteraction.hpp"
#include <FTFP_BERT.hh>
#include <G4Box.hh>
#include <G4LogicalVolume.hh>
#include <G4NistManager.hh>
#include <G4PVPlacement.hh>
#include <G4RunManager.hh>
#include <G4SystemOfUnits.hh>
#include <G4VUserDetectorConstruction.hh>
#include <Randomize.hh>
#include <chrono>
#include <ctime>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <memory>
#include <stdexcept>

struct Detector : G4VUserDetectorConstruction {
  G4Material *material =
      G4NistManager::Instance()->FindOrBuildMaterial("G4_Si");
  G4LogicalVolume *logical = nullptr;
  G4VPhysicalVolume *Construct() override {
    logical = new G4LogicalVolume(
        new G4Box("world", CLHEP::m, CLHEP::m, CLHEP::m), material, "world");
    return new G4PVPlacement(nullptr, {}, logical, "world", nullptr, false, 0);
  }
};
int main(int argc, char **argv) {
  try {
    if (argc < 3)
      throw std::runtime_error("usage: benchmark OUTDIR COUNT [TABLE]");
    const std::string out = argv[1];
    const int count = std::stoi(argv[2]);
    if (count <= 0)
      throw std::runtime_error("COUNT must be positive");
    auto t0 = std::clock();
    auto run = std::make_unique<G4RunManager>();
    auto *detector = new Detector;
    run->SetUserInitialization(detector);
    run->SetUserInitialization(new FTFP_BERT(0));
    run->Initialize();
    run->BeamOn(0);
    ActsFatras::Geant4NuclearInteraction model(
        *detector->material, *detector->logical->GetMaterialCutsCouple());
    const double setup = double(std::clock() - t0) / CLOCKS_PER_SEC;
    std::shared_ptr<ActsFatras::NuclearInteractionTable> table;
    double tableSetup = 0;
    if (argc > 3) {
      auto start = std::clock();
      std::ifstream input(argv[3]);
      table = std::make_shared<ActsFatras::NuclearInteractionTable>(
          ActsFatras::NuclearInteractionTable::read(input));
      tableSetup = double(std::clock() - start) / CLOCKS_PER_SEC;
    }
    auto material =
        Acts::Material::fromMolarDensity(93.7, 465.2, 28.0855, 14, 0.1);
    std::ofstream events(out + "/events.csv"), products(out + "/products.csv"),
        rates(out + "/rates.csv");
    events << std::setprecision(12);
    products << std::setprecision(12);
    rates << std::setprecision(12);
    events << "model,pdg,p,event,multiplicity,charged,energy_fraction,leading_"
              "fraction,closure,charge_closure,remnant_e_minus_p\n";
    products << "model,pdg,p,event,child_pdg,child_p,cos_theta\n";
    rates << "pdg,p,live,table\n";
    double liveCpu = 0, replayCpu = 0, maxClosure = 0, maxCharge = 0,
           minRemnant = 0;
    unsigned nulls = 0, liveCalls = 0, replayCalls = 0;
    auto *engine = G4Random::getTheEngine();
    const auto rngState = engine->put();
    for (int pdg : {211, -211, 2212, 2112, 130, -2212, -2112, 321, -321}) {
      for (double p : {0.05, 0.2, 0.5, 2., 10., 100.}) {
        auto particle =
            ActsFatras::Particle(ActsFatras::Barcode().withParticle(1),
                                 static_cast<Acts::PdgParticle>(pdg))
                .setAbsoluteMomentum(p)
                .setDirection(0, 0, 1);
        const auto *channel =
            table ? table->findReferenceChannel(particle.pdg()) : nullptr;
        double liveRate = model.ratePerL0(particle, material),
               replayRate = channel ? table->ratePerL0(*channel, p) : 0;
        rates << pdg << ',' << p << ',' << liveRate << ',' << replayRate
              << '\n';
        for (int mode = 0; mode < (table ? 2 : 1); ++mode) {
          if ((mode == 0 ? liveRate : replayRate) == 0)
            continue;
          const auto draws =
              mode == 0 ? static_cast<std::size_t>(count)
                        : std::min(static_cast<std::size_t>(count),
                                   table->findBin(*channel, p)->events.size());
          for (std::size_t i = 0; i < draws; ++i) {
            ActsFatras::NuclearInteractionTable::Sample sampled;
            const auto start = std::clock();
            if (mode == 0) {
              auto sample =
                  model.sample(particle, material,
                               100001 + static_cast<long>(i) +
                                   std::abs(pdg) * 101 + int(p * 100000));
              liveCpu += double(std::clock() - start) / CLOCKS_PER_SEC;
              ++liveCalls;
              if (!sample) {
                ++nulls;
                continue;
              }
              sampled = std::move(*sample);
            } else {
              const auto *bin = table->findBin(*channel, p);
              sampled = table->sample(bin->events[i], particle, 0.123 * i);
              replayCpu += double(std::clock() - start) / CLOCKS_PER_SEC;
              ++replayCalls;
            }
            Acts::Vector4 sum = sampled.remnant;
            double charge = sampled.remnantCharge, leading = 0, energy = 0;
            int charged = 0;
            for (const auto &c : sampled.products) {
              const double q = c.momentum.norm();
              const double e = std::hypot(q, c.mass);
              sum.head<3>() += c.momentum;
              sum[3] += e;
              charge += c.charge;
              energy += e;
              leading = std::max(leading, e);
              charged += c.charge != 0;
              products << mode << ',' << pdg << ',' << p << ',' << i << ','
                       << int(c.pdg) << ',' << q << ','
                       << (q > 0 ? c.momentum.z() / q : 0) << '\n';
            }
            auto expected = particle.fourMomentum();
            expected[3] += sampled.targetMass;
            const double closure = (sum - expected).norm() / expected[3],
                         cq = std::abs(charge - 14 - particle.charge());
            const double remnant =
                sampled.remnant[3] - sampled.remnant.head<3>().norm();
            maxClosure = std::max(maxClosure, closure);
            maxCharge = std::max(maxCharge, cq);
            minRemnant = std::min(minRemnant, remnant);
            if (closure > 1e-10 || cq > 1e-10)
              throw std::runtime_error("closure failed");
            events << mode << ',' << pdg << ',' << p << ',' << i << ','
                   << sampled.products.size() << ',' << charged << ','
                   << energy / particle.energy() << ','
                   << leading / particle.energy() << ',' << closure << ',' << cq
                   << ',' << remnant << '\n';
          }
        }
      }
    }
    if (G4Random::getTheEngine() != engine || engine->put() != rngState)
      throw std::runtime_error("caller RNG changed");
    auto particle = ActsFatras::Particle(ActsFatras::Barcode().withParticle(1),
                                         Acts::PdgParticle::ePionPlus)
                        .setAbsoluteMomentum(2)
                        .setDirection(1, 2, 3);
    auto a = model.sample(particle, material, 321),
         b = model.sample(particle, material, 321);
    if (!a || !b || a->products.size() != b->products.size())
      throw std::runtime_error("repeat mismatch");
    for (unsigned i = 0; i < a->products.size(); ++i)
      if (a->products[i].momentum != b->products[i].momentum ||
          a->products[i].pdg != b->products[i].pdg)
        throw std::runtime_error("seed mismatch");
    std::ofstream summary(out + "/benchmark.json");
    summary << std::setprecision(12) << "{\"live_setup_cpu_s\":" << setup
            << ",\"table_setup_cpu_s\":" << tableSetup
            << ",\"live_calls\":" << liveCalls
            << ",\"replay_calls\":" << replayCalls
            << ",\"live_sampling_cpu_s\":" << liveCpu
            << ",\"replay_sampling_cpu_s\":" << replayCpu
            << ",\"nulls\":" << nulls
            << ",\"max_relative_four_momentum_error\":" << maxClosure
            << ",\"max_charge_error\":" << maxCharge
            << ",\"min_remnant_E_minus_p_GeV\":" << minRemnant
            << ",\"rng_restore_and_repeatability\":true}\n";
  } catch (const std::exception &e) {
    std::cerr << e.what() << '\n';
    return 1;
  }
}
