#include "ActsFatras/Physics/Hadronic/NuclearInteractionTable.hpp"
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <numbers>
#include <random>
using Table = ActsFatras::NuclearInteractionTable;
void compare(std::ostream &out, const Table &model, const Table &reference,
             const char *label, bool training) {
  std::mt19937_64 rng(49142);
  std::uniform_real_distribution<double> uniform(0, 1);
  for (const auto &refChannel : reference.channels()) {
    const auto *channel =
        training ? model.findReferenceChannel(refChannel.pdg) : &refChannel;
    for (const auto &point : refChannel.bins) {
      const auto *bin = Table::findBin(*channel, point.momentum);
      if (!bin || bin->events.empty())
        continue;
      ActsFatras::Particle incident(ActsFatras::Barcode().withParticle(1),
                                    refChannel.pdg);
      incident.setAbsoluteMomentum(point.momentum).setDirection(1, 0, 0);
      // Exactly one pass over independent reference events. For training,
      // resample its library with the same number of trials.
      std::uniform_int_distribution<std::size_t> pick(0,
                                                      bin->events.size() - 1);
      std::array<double, 3> count{}, count2{}, pt{}, angle{};
      for (std::size_t i = 0; i < point.events.size(); ++i) {
        auto final =
            Table::sample(bin->events[training ? pick(rng) : i], incident,
                          2 * std::numbers::pi * uniform(rng));
        std::array<unsigned, 3> n{};
        for (const auto &product : final.products) {
          if (product.charge == 0)
            continue;
          const auto momentum = product.momentum.norm();
          const auto transverse = product.momentum.head<2>().norm();
          if (momentum < 0.1 || transverse < 0.05)
            continue;
          const unsigned group = std::abs(product.pdg) == 211 ? 0
                                 : product.pdg == 2212        ? 1
                                                              : 2;
          ++n[group];
          pt[group] += transverse;
          angle[group] +=
              std::acos(std::clamp(product.momentum.x() / momentum, -1., 1.));
        }
        for (unsigned g = 0; g < 3; ++g) {
          count[g] += n[g];
          count2[g] += n[g] * n[g];
        }
      }
      for (unsigned g = 0; g < 3; ++g) {
        const double n = point.events.size(), mean = count[g] / n;
        out << label << ',' << static_cast<int>(refChannel.pdg) << ','
            << point.momentum << ',' << g << ','
            << Table::ratePerL0(*channel, point.momentum) << ',' << mean << ','
            << std::sqrt(std::max(0., count2[g] / n - mean * mean) / n) << ','
            << (count[g] > 0 ? pt[g] / count[g] : 0) << ','
            << (count[g] > 0 ? angle[g] / count[g] : 0) << '\n';
      }
    }
  }
}
int main(int argc, char **argv) {
  if (argc != 6)
    return 2;
  std::ifstream file(argv[1]);
  auto model = Table::read(file);
  std::ofstream out(argv[5]);
  out << std::setprecision(12)
      << "model,projectile,p_GeV,group,rate_per_L0,accepted_mean,accepted_sem,"
         "accepted_mean_pt,accepted_mean_angle\n";
  for (unsigned i = 2; i < 5; ++i) {
    std::ifstream input(argv[i]);
    auto reference = Table::read(input);
    compare(out, model, reference,
            i == 2   ? "Geant4-C"
            : i == 3 ? "Geant4-Al"
                     : "Geant4-Si",
            false);
    if (i == 4)
      compare(out, model, reference, "Fatras-Si", true);
  }
}
