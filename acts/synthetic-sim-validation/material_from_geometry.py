#!/usr/bin/env python3
"""Read the material of a shipped synthetic layout off the real geometry.

`layout_from_geometry.py` reduces a geometry into a layout wholesale. This does
only the material half: it reduces the geometry, then matches what it measured
onto the *shipped* description by reference coordinate, so a layout whose
positions were transcribed -- the ITk's, from ITKLayouts -- keeps its surfaces
and gains their material.

Emits real slabs, not weights in sensors. A weight fixes only `x/X0`, and the
nuclear length drives the hadronic half of the yield: forcing silicon's `L0/X0`
onto a carbon support understates it by two and a half.

Service surfaces -- material the geometry carries away from any sensitive layer
-- come out too. They are where a mapped geometry keeps what no weight on a
layer can express.

    ./material_from_geometry.py itk
    ./material_from_geometry.py odd
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

import acts
from acts.fatras import synthetic as syn

#: Pixel volumes per detector, and how to build it.
DETECTORS = {
    "itk": {"volumes": {8, 9, 10, 13, 14, 15, 16, 18, 19, 20}},
    "odd": {"volumes": {16, 17, 18}},
    "generic": {"volumes": {7, 8, 9}},
}


def build(name: str):
    """Build a detector and its tracking geometry, with material.

    @param name the detector
    @return the detector, which owns the geometry, and the geometry
    """
    if name == "itk":
        import acts.examples.itk

        detector = acts.examples.itk.buildITkGeometry(
            Path.home() / "cern/source/acts/acts-itk")
    elif name == "odd":
        from acts.examples.odd import getOpenDataDetector

        detector = getOpenDataDetector()
    else:
        from acts.examples import GenericDetector

        detector = GenericDetector()
    return detector, detector.trackingGeometry()


def measure_beam_pipe(name: str, radius: float, barrel_radii,
                      tolerance: float = 8.0):
    """The beam pipe's material, which no pixel volume contains.

    The selector below keeps the pixel volumes, and a beam pipe sits in one of
    its own -- so it is reduced separately, by radius rather than by volume.
    Without this it comes out as vacuum, and a beam pipe is where a good share
    of the secondaries at small |d0| are made.

    Thickest of what is near, less whatever is already a barrel layer. Nearest
    is not enough: the ITk keeps the pixel volume boundary a millimetre outside
    the beam pipe, carrying a quarter of its material, and picking that loses
    the rest of it.

    @param name the detector
    @param radius the radius the description puts the beam pipe at
    @param barrel_radii the radii the description already has layers at
    @param tolerance how far a cylinder may sit from either
    @return the material, or None if the geometry has none there
    """
    detector, geometry = build(name)
    assert detector is not None
    gctx = acts.GeometryContext.dangerouslyDefaultConstruct()

    def near(surface):
        if surface is None or str(surface.type).rsplit(".", 1)[-1] != "Cylinder":
            return False
        values = list(surface.bounds.values())
        return bool(values) and abs(values[0] - radius) <= tolerance

    options = syn.TrackingGeometryLayoutOptions()
    options.setSurfaceSelector(near)
    options.includeMaterialSurfaces = True
    layout = syn.makeLayoutFromTrackingGeometry(geometry, gctx, options)
    best, most = None, 0.0
    for surface in layout.surfaces:
        if (surface.shape != syn.SurfaceShape.Cylinder
                or surface.material.slab.thickness <= 0
                or abs(surface.refCoord - radius) > tolerance):
            continue
        if any(abs(surface.refCoord - r) <= tolerance for r in barrel_radii):
            continue
        if surface.material.slab.thicknessInX0 > most:
            best, most = surface.material, surface.material.slab.thicknessInX0
    return best


def measure(name: str, services: bool = True):
    """Reduce a detector and read the material of every surface it produces.

    @param name the detector
    @param services also keep the material surfaces away from any sensitive
           layer, which is where the services are
    @return the layout
    """
    detector, geometry = build(name)
    assert detector is not None  # keeps the geometry's owner alive
    gctx = acts.GeometryContext.dangerouslyDefaultConstruct()

    options = syn.TrackingGeometryLayoutOptions()
    volumes = DETECTORS[name]["volumes"]
    options.setSurfaceSelector(
        lambda s: s is not None and s.geometryId.volume in volumes)
    options.includeMaterialSurfaces = services
    return syn.makeLayoutFromTrackingGeometry(geometry, gctx, options)


def slab_literal(slab) -> str:
    """@return the C++ that reconstructs a slab"""
    m = slab.material
    return ("materialSlab(%.4ff, %.4ff, %.4ff, %.1ff, %.10ff, %.6ff)"
            % (m.X0, m.L0, m.Ar, m.Z, m.molarDensity, slab.thickness))


def material_literal(material, indent: str = "       ") -> str:
    """The C++ that reconstructs a surface's material.

    @param material the `SurfaceMaterial`
    @param indent what to put in front of the continuation lines
    @return the literal
    """
    if material is None:
        return "{}"
    out = "{%s" % slab_literal(material.slab)
    if material.bounds:
        out += (",\n%s{%s},\n%s{%s}"
                % (indent, ", ".join("%.1ff" % b for b in material.bounds),
                   indent, ", ".join("%.3ff" % s for s in material.scales)))
    return out + "}"


def profile(edges: list, bands: list):
    """A `SurfaceMaterial` from a band of slabs each, `None` being vacuum.

    @param edges the band bounds, one more than there are bands
    @param bands the slab of each band
    @return the material, whose slab is the mean over the whole surface so that
            a scale of one means the average
    """
    widths = [hi - lo for lo, hi in zip(edges, edges[1:])]
    total = sum(widths)
    weighted = []
    for slab, width in zip(bands, widths):
        if slab is None:
            continue
        part = syn.MaterialSlab(slab.material, slab.thickness)
        part.scaleThickness(width / total)
        weighted.append(part)
    if not weighted:
        return None
    mean = syn.MaterialSlab.combineLayers(weighted)
    out = syn.SurfaceMaterial(mean)
    out.bounds = [float(hi) for hi in edges[1:]]
    out.scales = [0.0 if s is None else s.thicknessInX0 / mean.thicknessInX0
                  for s in bands]
    return out


def merge(materials: list):
    """One surface's material out of several the reduction put at one place.

    The ITk keeps each ring of an endcap disc as a layer of its own while the
    description puts the rings that share a z on one disc, so a disc collects
    several -- and dropping all but one leaves its other rings with nothing.

    Averaged where they overlap rather than added: material stacked at one
    position is already summed within a group, and what is left across groups is
    the same shell seen from the volumes either side of it. Adding those counts
    it twice, which at r = 124 on the ITk is most of the pixel radiation length.

    @param materials the `SurfaceMaterial`s to merge, at least one
    @return the merged material
    """
    if len(materials) == 1:
        return materials[0]
    edges = sorted({0.0} | {b for m in materials for b in m.bounds})
    bands = []
    for lo, hi in zip(edges, edges[1:]):
        here = []
        for m in materials:
            scale = m.scaleAt(0.5 * (lo + hi))
            if scale > 0:
                slab = syn.MaterialSlab(m.slab.material, m.slab.thickness)
                slab.scaleThickness(scale / len(materials))
                here.append(slab)
        bands.append(syn.MaterialSlab.combineLayers(here) if here else None)
    return profile(edges, bands) or materials[0]


def fill_rings(material, rings):
    """Give a ring the surface average where nothing was measured over it.

    The ITk description and the ACTS geometry do not agree on which rings share
    a disc, so a handful of rings have no surface of their own to read. Leaving
    those at vacuum is worse than the average they used to get.

    @param material the disc's material, or None
    @param rings the rings of the disc
    @return the material, or None if there was none to start with
    """
    if material is None or not material.bounds:
        return material
    missing = [r for r in rings
               if material.scaleAt(0.5 * (r.rMin + r.rMax)) <= 0]
    if not missing:
        return material
    edges = sorted({0.0} | set(material.bounds)
                   | {r.rMin for r in missing} | {r.rMax for r in missing})
    bands = []
    for lo, hi in zip(edges, edges[1:]):
        mid = 0.5 * (lo + hi)
        scale = material.scaleAt(mid)
        if scale <= 0 and any(r.rMin <= mid <= r.rMax for r in missing):
            scale = 1.0
        slab = syn.MaterialSlab(material.slab.material, material.slab.thickness)
        slab.scaleThickness(scale)
        bands.append(slab if scale > 0 else None)
    return profile(edges, bands) or material


def assign(measured: list, wanted: list, tolerance: float) -> dict:
    """Hand every measured surface to the shipped one it belongs to.

    Nearest assignment rather than nearest lookup, so that two measured surfaces
    at the same z both reach the disc that holds their rings instead of one
    overwriting the other.

    @param measured pairs of reference coordinate and material
    @param wanted the reference coordinates of the shipped surfaces
    @param tolerance how far a measured surface may sit from the one it goes to
    @return the merged material per shipped coordinate, absent where none is
            close enough
    """
    out: dict = {}
    for coord, material in measured:
        if not wanted:
            break
        closest = min(wanted, key=lambda w: abs(w - coord))
        if abs(closest - coord) <= tolerance:
            out.setdefault(closest, []).append(material)
    return {k: merge(v) for k, v in out.items()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("detector", choices=sorted(DETECTORS))
    parser.add_argument("--tolerance", type=float, default=6.0,
                        help="how far a measured surface may sit from the "
                             "shipped one it is matched to, in mm")
    parser.add_argument("--no-services", action="store_true",
                        help="leave out the material away from any sensitive "
                             "layer")
    args = parser.parse_args()

    layout = measure(args.detector, services=not args.no_services)
    description = {"itk": syn.itkPixelDescription,
                   "odd": syn.openDataDetectorPixelDescription,
                   "generic": syn.genericDetectorPixelDescription}[
                       args.detector]()

    cylinders, discs, passive = [], [], []
    for s in layout.surfaces:
        if s.material.slab.thickness <= 0:
            continue
        if s.passive:
            # one side only; the description mirrors a disc itself
            if s.refCoord >= 0:
                passive.append(s)
            continue
        (cylinders if s.shape == syn.SurfaceShape.Cylinder
         else discs).append((abs(s.refCoord), s.material))

    radii = list(description.barrelRadii)
    if description.beamPipeRadius is not None:
        radii.append(description.beamPipeRadius)
    byRadius = assign(cylinders, radii, args.tolerance)
    byZ = assign(discs, [d.absZ for d in description.discs], args.tolerance)

    print("  // Read off the geometry by "
          "`material_from_geometry.py %s`." % args.detector)
    print("  description.barrelMaterials = {")
    for r in description.barrelRadii:
        slab = byRadius.get(r)
        print("      %s,%s" % (material_literal(slab),
                               "" if slab else "  // nothing at r = %.1f" % r))
    print("  };")

    if description.beamPipeRadius is not None:
        slab = (byRadius.get(description.beamPipeRadius)
                or measure_beam_pipe(args.detector, description.beamPipeRadius,
                                     description.barrelRadii))
        if slab is None:
            raise SystemExit("no beam pipe material found at r = %.1f; a "
                             "vacuum beam pipe makes no secondaries at all"
                             % description.beamPipeRadius)
        print("  description.beamPipeMaterial =\n      %s;"
              % material_literal(slab, "      "))

    # Coincident services come from separate volume groups -- the same shell
    # seen from either side of a volume boundary -- and a track crosses that
    # position once. `materialOfGroup` does this within a group; across groups
    # it has to be done here.
    merged = {}
    for s in passive:
        key = (str(s.shape), round(abs(s.refCoord), 1))
        merged.setdefault(key, []).append(s)
    passive = []
    for group in merged.values():
        if len(group) > 1:
            print("  // %d coincident services at %.1f, averaged"
                  % (len(group), abs(group[0].refCoord)))
        passive.append(group[0])

    # the beam pipe is emitted on its own, so a service surface at the same
    # radius is the same object and would be crossed twice
    if description.beamPipeRadius is not None:
        passive = [s for s in passive
                   if s.shape != syn.SurfaceShape.Cylinder
                   or abs(abs(s.refCoord) - description.beamPipeRadius)
                   > args.tolerance]

    if passive:
        print("  // Services: material the geometry carries away from any")
        print("  // sensitive layer, which no weight on a layer can express.")
        print("  // The extent matters as much as the amount: a tube grazed at")
        print("  // cosh(eta) is worth ten times its thickness forward.")
        print("  description.passiveSurfaces = {")
        for s in sorted(passive, key=lambda s: (str(s.shape), s.refCoord)):
            cylinder = s.shape == syn.SurfaceShape.Cylinder
            lo, hi = s.passiveMinBound, s.passiveMaxBound
            if not np.isfinite(hi):
                raise SystemExit(
                    "unbounded passive surface at %.1f: the reduction did not "
                    "give it an extent" % s.refCoord)
            print("      {SurfaceShape::%s, %.1ff, %.1ff, %.1ff,\n       %s},"
                  % ("Cylinder" if cylinder else "Disc", abs(s.refCoord),
                     lo, hi, material_literal(s.material)))
        print("  };")

    print("  // clang-format off")
    print("  description.discs = {")
    unmatched = 0
    for disc in description.discs:
        slab = fill_rings(byZ.get(disc.absZ), disc.rings)
        unmatched += slab is None
        rings = ", ".join("{%.2ff, %.2ff}" % (r.rMin, r.rMax)
                          for r in disc.rings)
        print("      {%.2ff, {%s},\n       %s},"
              % (disc.absZ, rings, material_literal(slab)))
    print("  };")
    print("  // clang-format on")
    print("  // %d of %d discs matched a measured surface"
          % (len(description.discs) - unmatched, len(description.discs)))


if __name__ == "__main__":
    main()
