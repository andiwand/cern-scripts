#include "ActsFatras/Geant4/Geant4Decay.hpp"
#include "ActsFatras/Physics/Decay/NativeDecay.hpp"
#include <chrono>
#include <fstream>
#include <iostream>
#include <map>
#include <random>
#include <string>
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
    auto &s = stats[channel];
    ++s.decays;
    for (auto &d : children)
      if (d.charge() != 0) {
        ++s.charged;
        s.energy += d.energy();
        ++s.energies[std::min(99, std::max(0, int(d.energy() / 0.3 * 100)))];
      }
  }
  double seconds =
      std::chrono::duration<double>(std::chrono::steady_clock::now() - start)
          .count();
  for (auto &[channel, s] : stats) {
    out << model << ',' << pdg << ',' << channel << ',' << s.decays << ','
        << s.charged << ',' << s.energy << ',' << seconds;
    for (auto b : s.energies)
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
  ActsFatras::Geant4Decay g4;
  for (int pdg : {211, -211, 321, -321}) {
    sample(native, pdg, "native", out);
    sample(g4, pdg, "geant4", out);
  }
}
