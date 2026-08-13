#!/usr/bin/env python3
"""Derive the ITk pixel description from the official ITKLayouts geometry.

The ITk has no description in ACTS, so the synthetic detector has to come from
somewhere else. It should not come from a fit to simulated data: the geometry is
a known thing, published as GeoModelXml in

    ssh://git@gitlab.cern.ch:7999/Atlas-Inner-Tracking/ITKLayouts.git

and every number the synthetic model needs is a named constant in the `*Defines.gmx`
files of `ITKLayouts/data/Pixel`. This reads them and writes
`itk-description.json`: where the layers are, and nothing about what they are made
of, which `material_from_geometry.py itk` measures off the ACTS ITk geometry and
writes beside it.

The nine sections of the ITk pixel detector, in the naming of those files:

  InnerBarrel      layers 0 and 1, flat staves around the beam line
  InnerEndcap      three sets of coupled rings, `RingPositions`, `...L1`, `...E0`
  OuterBarrel      the flat part of layers 2, 3 and 4
  OuterIncline     the inclined part of the same three layers
  OuterEndcap      the ring sets that close them off

Only the sensor positions matter here, so a module is reduced to the radial extent
of its sensor: a ring at radius R carries modules whose silicon spans
R +- sensorLength / 2. That reproduces the radial extent of the clusters in a
GNN4ITk dump to better than a millimetre for all nine sections, and the ring z
positions to better than half of one, which is the cross-check that the reduction
below is the right reading of the XML.
"""

from __future__ import annotations

import argparse
import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from acts.fatras import synthetic as syn

import presets

#: The `*Defines.gmx` files holding the constants, in dependency order: a `var`
#: may be an expression over the ones before it.
DEFINES = [
    "ModuleDefines.gmx",
    "InnerBarrelDefines.gmx",
    "InnerEndcapDefines.gmx",
    "OuterBarrelDefines.gmx",
    "OuterInclineDefines.gmx",
    "OuterEndcapDefines.gmx",
]

#: The ITk beam pipe is not part of ITKLayouts - Athena builds it in C++ - so it
#: stays a hand-written number. It is passive here anyway: the description only
#: needs it as the material in front of layer 0, and it belongs to the detector
#: rather than to the pixels because that is where a real geometry keeps it.
BEAM_PIPE_RADIUS = 25.0

#: What the description says beyond the geometry, none of which is in the XML.
#:
#: The overlap numbers are measured on a GNN4ITk dump off the module identifiers
#: its clusters carry (`measure_overlaps.py`): layer 0 is low because its staves
#: do not alternate in radius the way the outer ones do. Adjacent staves are eight
#: millimetres apart in radius and the modules of a ring five in z; the track's
#: own slope covers the rest.
#:
#: The escape bounds are the whole inner detector's rather than the pixels': past
#: this radius is the ITk's outer support and the calorimeter, and a track leaving
#: the pixels curls back through the strips in the same field.
BARREL_OVERLAP_PROBABILITIES = (0.02, 0.15, 0.16, 0.13, 0.13)
DISC_OVERLAP_PROBABILITY = 0.15
BARREL_OVERLAP_OFFSET = 7.9
DISC_OVERLAP_OFFSET = 5.0
ESCAPE_RADIUS = 1000.0
ESCAPE_HALF_Z = 3050.0

#: The subsystem the pixels are, and the prefix the files ship under.
SUBSYSTEM = "itk-pixel"
SHIPS_AS = "itk"


def read_defines(pixel_dir: Path) -> dict[str, object]:
    """Resolve the constants of the pixel defines files.

    @param pixel_dir the `ITKLayouts/data/Pixel` directory
    @return a mapping from name to float, or to a list of floats for a vector
    """
    values: dict[str, object] = {"PI": math.pi}

    for name in DEFINES:
        root = ET.parse(pixel_dir / name).getroot()
        for element in root:
            if element.tag == "var":
                values[element.attrib["name"]] = _evaluate(
                    element.attrib["value"], values, name)
            elif element.tag == "vector":
                values[element.attrib["name"]] = [
                    float(v) for v in element.attrib["value"].split()]

    return values


def _evaluate(expression: str, values: dict[str, object], where: str) -> float:
    """Evaluate a `var` expression over the constants defined so far.

    The expressions in these files are arithmetic over earlier names, e.g.
    `67*(PI/180)` or `OuterPixBarrel_DzBetweenModules + OuterQuadMod_SensorLength`.

    @param expression the value attribute
    @param values the constants defined so far
    @param where the file the expression came from, for the error message
    @return the value
    """
    # Only names and arithmetic are allowed through, so that a surprise in the
    # XML is an error here rather than something executing.
    if not re.fullmatch(r"[0-9A-Za-z_.+\-*/() \t]*", expression):
        raise ValueError("%s: cannot evaluate %r" % (where, expression))
    scalars = {k: v for k, v in values.items() if not isinstance(v, list)}
    try:
        return float(eval(expression, {"__builtins__": {}}, scalars))
    except NameError as error:
        raise ValueError("%s: %s in %r" % (where, error, expression)) from error


class Layout:
    """The barrel cylinders and endcap rings, as the synthetic model wants them."""

    def __init__(self) -> None:
        #: (radius, halfLengthZ, name)
        self.cylinders: list[tuple[float, float, str]] = []
        #: (absZ, rMin, rMax, name)
        self.rings: list[tuple[float, float, float, str]] = []

    def add_cylinder(self, radius: float, half_length: float, name: str) -> None:
        self.cylinders.append((radius, half_length, name))

    def add_rings(self, radius: float, sensor_length: float,
                  positions: list[float], name: str) -> None:
        """Add one set of rings, all at the same radius.

        @param radius the ring radius in mm
        @param sensor_length the module sensor length in mm, which is what the
               ring spans radially
        @param positions the absolute z positions of the rings in mm
        @param name what the section is called, for the report
        """
        for absZ in positions:
            self.rings.append((absZ, radius - 0.5 * sensor_length,
                               radius + 0.5 * sensor_length, name))


def build(d: dict[str, object]) -> Layout:
    """Reduce the ITk pixel geometry to cylinders and rings.

    @param d the resolved constants
    @return the layout
    """
    layout = Layout()

    # --- inner barrel: a stave of modules staggered along z, half each side
    layout.add_cylinder(
        d["InnerPixBarrel_PixelLayer0Radius"],
        d["InnerPixBarrel_NrOfModulesPerHalfStave"] * d["InnerPixBarrel_ModStaggerLayer0"],
        "InnerBarrel L0")
    layout.add_cylinder(
        d["InnerPixBarrel_PixelLayer1Radius"],
        d["InnerPixBarrel_NrOfModulesPerHalfStaveLayer1"] * d["InnerPixBarrel_ModStaggerLayer1"],
        "InnerBarrel L1")

    # --- outer flat barrel: `ModPerRow` modules per side, plus half the gap left
    # at z = 0 by `ZOffset`
    outer_stagger = d["OutPixFlatBarrel_ModStagger"]
    outer_half = (d["OutPixFlatBarrel_ModPerRow"] * outer_stagger
                  + 0.5 * d["OutPixFlatBarrel_ZOffset"])
    for layer in (2, 3, 4):
        layout.add_cylinder(d["OutPixFlatBarrel%d_Radius" % layer], outer_half,
                            "OuterBarrel L%d" % layer)

    # --- inner endcap: three sets of coupled rings. Layer 0 and E0 carry single
    # modules, layer 1 quads, which is what sets their radial extent.
    single = d["InnerSingleMod_SensorLength"]
    quad = d["InnerQuadMod_SensorLength"]
    layout.add_rings(d["InnerPixEndcap_EndcapRadiusLayer0"], single,
                     d["InnerPixEndcap_RingPositions"], "InnerEndcap L0")
    layout.add_rings(d["InnerPixEndcap_EndcapRadiusLayerE0"], single,
                     d["InnerPixEndcap_RingPositionsE0"], "InnerEndcap E0")
    layout.add_rings(d["InnerPixEndcap_EndcapRadiusLayer1"], quad,
                     d["InnerPixEndcap_RingPositionsL1"], "InnerEndcap L1")

    # --- outer inclined sections and outer endcap: rings at a fixed radius,
    # stepping outwards from an overall offset by an incremental spacing
    outer_quad = d["OuterQuadMod_SensorLength"]
    for prefix, label in (("OutPixIncSec", "OuterIncline"),
                          ("OutPixEndCap", "OuterEndcap")):
        overall = d.get("%s_OverallZSpace" % prefix)
        for layer in (2, 3, 4):
            offset = d.get("%s%d_OverallZSpace" % (prefix, layer), overall)
            spacing = d["%s%d_ZSpace" % (prefix, layer)]
            layout.add_rings(d["%s%d_Radius" % (prefix, layer)], outer_quad,
                             [offset + s for s in spacing],
                             "%s L%d" % (label, layer))

    return layout


def planes(rings: list[tuple[float, float, float, str]], tolerance: float):
    """Collapse rings that sit at the same z onto one disk.

    Rings of different sections genuinely share a z - the three outer endcap ring
    sets all start at 1145.5 mm and all end at 2850 mm - and one disk carrying
    concentric rings is exactly how the synthetic model wants to hear that.

    @param rings the rings, as (absZ, rMin, rMax, name)
    @param tolerance how far apart in mm two rings may be and still be one disk
    @return a list of (z, [(rMin, rMax, name)])
    """
    out: list[tuple[float, list]] = []
    for absZ, rMin, rMax, name in sorted(rings):
        if out and absZ - out[-1][0] <= tolerance:
            out[-1][1].append((rMin, rMax, name))
        else:
            out.append((absZ, [(rMin, rMax, name)]))
    return [(z, sorted(annuli)) for z, annuli in out]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("itklayouts",
                        help="a checkout of the ITKLayouts repository")
    parser.add_argument("--z-tolerance", type=float, default=5.0,
                        help="rings within this many mm in z become one disk")
    parser.add_argument("-o", "--out", default=None,
                        help="what to write: a shipped name, or a path prefix. "
                             "Defaults to what the ITk ships as.")
    parser.add_argument("--report", action="store_true",
                        help="print the sections rather than writing them")
    args = parser.parse_args()

    root = Path(args.itklayouts)
    pixel = root / "ITKLayouts" / "data" / "Pixel"
    if not pixel.is_dir():
        raise SystemExit("%s does not look like an ITKLayouts checkout" % root)

    layout = build(read_defines(pixel))
    disks = planes(layout.rings, args.z_tolerance)

    if args.report:
        print("%-16s %9s %9s %9s" % ("section", "r", "z", "rings"))
        for radius, half, name in layout.cylinders:
            print("%-16s %9.1f %9.1f %9s" % (name, radius, half, "cylinder"))
        by_section: dict[str, list] = {}
        for absZ, rMin, rMax, name in layout.rings:
            by_section.setdefault(name, []).append((absZ, rMin, rMax))
        for name, rs in by_section.items():
            print("%-16s %9.1f %9s %9d"
                  % (name, 0.5 * (rs[0][1] + rs[0][2]),
                     "%.0f-%.0f" % (min(r[0] for r in rs), max(r[0] for r in rs)),
                     len(rs)))
        print()
        print("%d cylinders, %d rings on %d disks per side"
              % (len(layout.cylinders), len(layout.rings), len(disks)))
        return

    description = build_description(layout, disks)
    for written in presets.write_description(args.out or SHIPS_AS, description,
                                            split=False):
        print("wrote %s" % written)
    print("# from ITKLayouts %s" % _describe(root))
    print("# %d barrel cylinders, %d discs per side carrying %d rings"
          % (len(layout.cylinders), len(disks), len(layout.rings)))
    print("# %d of the discs carry more than one ring"
          % sum(1 for _, annuli in disks if len(annuli) > 1))
    print("# no material: `material_from_geometry.py itk` reads that off the "
          "ACTS ITk geometry and writes it beside this")


def build_description(layout, disks):
    """The description the reduction amounts to.

    Only the geometry: the material is measured off the ACTS ITk geometry by
    `material_from_geometry.py`, which matches it onto the layers this names.

    @param layout the cylinders and rings read out of the XML
    @param disks the rings grouped into z planes
    @return the description
    """
    description = syn.DetectorDescription()
    description.escapeRadius = ESCAPE_RADIUS
    description.escapeHalfZ = ESCAPE_HALF_Z

    beam_pipe = syn.PassiveSurfaceDescription()
    beam_pipe.shape = syn.SurfaceShape.Cylinder
    beam_pipe.refCoord = BEAM_PIPE_RADIUS
    # the beam pipe ends where the detector does
    beam_pipe.maxBound = max([c[1] for c in layout.cylinders]
                             + [z for z, _ in disks])
    description.passives = [beam_pipe]

    barrel = syn.BarrelDescription()
    cylinders = []
    for index, (radius, half, _name) in enumerate(layout.cylinders):
        cylinder = syn.CylinderDescription()
        cylinder.radius = radius
        cylinder.halfLengthZ = half
        # coarser than the real detector, whose staves carry nine or twelve
        # modules along z; only a seeder that reasons about eta modules sees it
        cylinder.modules = 1
        cylinder.overlapProbability = (
            BARREL_OVERLAP_PROBABILITIES[index]
            if index < len(BARREL_OVERLAP_PROBABILITIES) else 0.0)
        cylinder.overlapOffset = BARREL_OVERLAP_OFFSET
        cylinder.layer = index
        cylinders.append(cylinder)
    barrel.cylinders = cylinders

    endcap = syn.EndcapDescription()
    # the two sides of the ITk are the same, so it is stated once
    endcap.placement = syn.EndcapPlacement.Mirrored
    discs = []
    for index, (absZ, annuli) in enumerate(disks):
        disc = syn.DiscDescription()
        disc.absZ = absZ
        disc.rings = [syn.RingBounds(rMin, rMax) for rMin, rMax, _name in annuli]
        disc.overlapProbability = DISC_OVERLAP_PROBABILITY
        disc.overlapOffset = DISC_OVERLAP_OFFSET
        disc.layer = index
        discs.append(disc)
    endcap.discs = discs

    subsystem = syn.SubsystemDescription()
    subsystem.name = SUBSYSTEM
    subsystem.barrels = [barrel]
    subsystem.endcaps = [endcap]
    description.subsystems = [subsystem]
    return description


def _describe(root: Path) -> str:
    """@param root the checkout @return a human-readable version of it"""
    import subprocess
    try:
        return subprocess.run(["git", "-C", str(root), "log", "-1",
                               "--format=%h (%ad)", "--date=short"],
                              capture_output=True, text=True,
                              check=True).stdout.strip()
    except Exception:
        return "an unknown revision"


if __name__ == "__main__":
    main()
