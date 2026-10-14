// External validation helper: bound Geant4 by the same cylinder as Fatras.
// No per-step callbacks or random draws during event transport.
#include <G4GeometryManager.hh>
#include <G4LogicalVolume.hh>
#include <G4Navigator.hh>
#include <G4RunManager.hh>
#include <G4SystemOfUnits.hh>
#include <G4TransportationManager.hh>
#include <G4Tubs.hh>
#include <G4VPhysicalVolume.hh>
#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <pybind11/pybind11.h>

namespace py = pybind11;

PYBIND11_MODULE(id_world, module) {
  module.def("confine", [](double radius, double halfLength) {
    auto* world = G4TransportationManager::GetTransportationManager()
                      ->GetNavigatorForTracking()->GetWorldVolume();
    if (world == nullptr || radius <= 0 || halfLength <= 0) {
      throw std::runtime_error("Initialize the tracker geometry first");
    }
    auto* logical = world->GetLogicalVolume();
    py::list children;
    // Check conservative bounds of every top-level placement. Descendants
    // remain in their original mothers; no detector volume is removed.
    for (std::size_t i = 0; i < logical->GetNoDaughters(); ++i) {
      const auto* child = logical->GetDaughter(i);
      const auto* solid = child->GetLogicalVolume()->GetSolid();
      const auto translation = child->GetObjectTranslation();
      const auto rotation = child->GetObjectRotationValue();
      double rmax = 0, zmax = 0;
      if (const auto* tube = dynamic_cast<const G4Tubs*>(solid);
          tube && std::abs(rotation.zz()) > 1 - 1e-12) {
        rmax = translation.perp() + tube->GetOuterRadius();
        zmax = std::abs(translation.z()) + tube->GetZHalfLength();
      } else {
        G4ThreeVector lower, upper;
        solid->BoundingLimits(lower, upper);
        for (int corner = 0; corner < 8; ++corner) {
          G4ThreeVector point(corner & 1 ? upper.x() : lower.x(),
                              corner & 2 ? upper.y() : lower.y(),
                              corner & 4 ? upper.z() : lower.z());
          point = rotation * point + translation;
          rmax = std::max(rmax, point.perp());
          zmax = std::max(zmax, std::abs(point.z()));
        }
      }
      if (rmax > radius * mm || zmax > halfLength * mm) {
        throw std::runtime_error("Daughter exceeds ID world: " + child->GetName() +
                                 ", r=" + std::to_string(rmax / mm) +
                                 ", |z|=" + std::to_string(zmax / mm));
      }
      py::dict item;
      item["name"] = std::string(child->GetName());
      item["solid"] = std::string(solid->GetEntityType());
      item["max_r_mm"] = rmax / mm;
      item["max_abs_z_mm"] = zmax / mm;
      children.append(item);
    }
    py::dict report;
    report["old_world_solid"] = std::string(logical->GetSolid()->GetEntityType());
    report["radius_mm"] = radius;
    report["half_length_mm"] = halfLength;
    report["top_level_placements"] = children;
    G4GeometryManager::GetInstance()->OpenGeometry();
    logical->SetSolid(new G4Tubs("IDValidationWorld", 0, radius * mm,
                               halfLength * mm, 0, 2 * CLHEP::pi));
    G4RunManager::GetRunManager()->GeometryHasBeenModified();
    report["world_solid"] = "G4Tubs";
    return report;
  });
}
