#include "ActsFatras/Geant4/Geant4Decay.hpp"
#include "ActsFatras/Physics/Decay/NativeDecay.hpp"
#include "G4DecayProducts.hh"
#include "G4DecayTable.hh"
#include "G4MesonConstructor.hh"
#include "G4ParticleTable.hh"
#include "G4ShortLivedConstructor.hh"
#include "G4SystemOfUnits.hh"
#include "Randomize.hh"
#include <chrono>
#include <fstream>
#include <iostream>
#include <map>
#include <random>
#include <string>
struct ReferenceDecay {
  std::vector<ActsFatras::Particle> run(std::mt19937_64 &,
                                        const ActsFatras::Particle &parent) {
    auto *def = G4ParticleTable::GetParticleTable()->FindParticle(
        static_cast<int>(parent.pdg()));
    if (!def || !def->GetDecayTable())
      throw std::runtime_error("missing reference decay");
    auto *channel =
        def->GetDecayTable()->SelectADecayChannel(parent.mass() * GeV);
    std::unique_ptr<G4DecayProducts> products(
        channel->DecayIt(parent.mass() * GeV));
    std::vector<ActsFatras::Particle> result;
    while (products->entries()) {
      std::unique_ptr<G4DynamicParticle> d(products->PopProducts());
      auto &p =
          result.emplace_back(parent.particleId().makeDescendant(result.size()),
                              static_cast<Acts::PdgParticle>(d->GetPDGcode()),
                              d->GetCharge() / eplus, d->GetMass() / GeV);
      const auto v = d->GetMomentum() / GeV;
      p.setDirection(Acts::Vector3(v.x(), v.y(), v.z()))
          .setAbsoluteMomentum(v.mag());
    }
    return result;
  }
};
struct Stats {
  unsigned decays = 0;
  std::array<unsigned, 100> energies{};
  double charged = 0, energy = 0;
};
template <class Decay>
void sample(Decay &decay, int pdg, const char *model, std::ostream &out) {
  ActsFatras::Particle parent(ActsFatras::Barcode().withParticle(1),
                              static_cast<Acts::PdgParticle>(pdg));
  std::mt19937_64 rng(6789);
  std::map<std::string, Stats> stats;
  constexpr unsigned n = 100000;
  auto start = std::chrono::steady_clock::now();
  for (unsigned i = 0; i < n; ++i) {
    auto children = decay.run(rng, parent);
    std::vector<int> codes;
    for (auto &d : children)
      codes.push_back(d.pdg());
    std::sort(codes.begin(), codes.end());
    std::string channel;
    for (int p : codes)
      channel += std::to_string(p) + ":";
    auto &stat = stats[channel];
    ++stat.decays;
    for (auto &d : children)
      if (d.charge() != 0) {
        ++stat.charged;
        stat.energy += d.energy();
        ++stat.energies[std::min(99, std::max(0, int(d.energy() / 0.5 * 100)))];
      }
  }
  double seconds =
      std::chrono::duration<double>(std::chrono::steady_clock::now() - start)
          .count();
  for (auto &[channel, stat] : stats) {
    out << model << ',' << pdg << ',' << channel << ',' << stat.decays << ','
        << stat.charged << ',' << stat.energy << ',' << seconds;
    for (auto b : stat.energies)
      out << ',' << b;
    out << '\n';
  }
}
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  std::ofstream out(argv[1]);
  out << "model,pdg,channel,count,charged,energy_sum_GeV,seconds";
  for (int i = 0; i < 100; ++i)
    out << ",bin" << i;
  out << '\n';
  ActsFatras::NativeDecay native;
  G4MesonConstructor().ConstructParticle();
  G4ShortLivedConstructor().ConstructParticle();
  ActsFatras::Geant4Decay definitions;
  G4ParticleTable::GetParticleTable()->SetReadiness(true);
  G4Random::setTheSeed(6789);
  ReferenceDecay g4;
  for (int pdg : {130, 221, 331, 113, 223}) {
    sample(native, pdg, "native", out);
    sample(g4, pdg, "geant4", out);
  }
}
