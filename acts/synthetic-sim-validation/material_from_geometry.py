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


def measure_beam_pipe(name: str, radius: float, tolerance: float = 8.0):
    """The beam pipe's material, which no pixel volume contains.

    The selector below keeps the pixel volumes, and a beam pipe sits in one of
    its own -- so it is reduced separately, by radius rather than by volume.
    Without this it comes out as vacuum, and a beam pipe is where a good share
    of the secondaries at small |d0| are made.

    @param name the detector
    @param radius the radius the description puts the beam pipe at
    @param tolerance how far a cylinder may sit from it
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
    # nearest, not thickest: the innermost barrel layer is within a centimetre
    # of the beam pipe on the ITk and carries twenty times its material, so
    # picking the thickest returns the layer and counts it twice
    best, distance = None, None
    for surface in layout.surfaces:
        if (surface.shape != syn.SurfaceShape.Cylinder
                or surface.material.thickness <= 0):
            continue
        away = abs(surface.refCoord - radius)
        if away <= tolerance and (distance is None or away < distance):
            best, distance = surface.material, away
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


def nearest(table: dict, coord: float, tolerance: float):
    """The measured surface closest to a coordinate, within a tolerance.

    @param table the measured material, keyed on reference coordinate
    @param coord the coordinate to match
    @param tolerance how far away a match may be
    @return the slab, or None if nothing is close enough
    """
    if not table:
        return None
    best = min(table, key=lambda k: abs(k - coord))
    return table[best] if abs(best - coord) <= tolerance else None


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

    cylinders, discs, passive = {}, {}, []
    for s in layout.surfaces:
        if s.material.thickness <= 0:
            continue
        if s.passive:
            # one side only; the description mirrors a disc itself
            if s.refCoord >= 0:
                passive.append(s)
            continue
        key = round(abs(s.refCoord), 1)
        (cylinders if s.shape == syn.SurfaceShape.Cylinder
         else discs)[key] = s.material

    print("  // Read off the geometry by "
          "`material_from_geometry.py %s`." % args.detector)
    print("  description.barrelMaterials = {")
    for r in description.barrelRadii:
        slab = nearest(cylinders, r, args.tolerance)
        print("      %s,%s" % (slab_literal(slab) if slab else "{}",
                               "" if slab else "  // nothing at r = %.1f" % r))
    print("  };")

    if description.beamPipeRadius is not None:
        slab = (nearest(cylinders, description.beamPipeRadius, args.tolerance)
                or measure_beam_pipe(args.detector, description.beamPipeRadius))
        if slab is None:
            raise SystemExit("no beam pipe material found at r = %.1f; a "
                             "vacuum beam pipe makes no secondaries at all"
                             % description.beamPipeRadius)
        print("  description.beamPipeMaterial =\n      %s;" % slab_literal(slab))

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
                     lo, hi, slab_literal(s.material)))
        print("  };")

    print("  // clang-format off")
    print("  description.discs = {")
    unmatched = 0
    for disc in description.discs:
        slab = nearest(discs, disc.absZ, args.tolerance)
        unmatched += slab is None
        rings = ", ".join("{%.2ff, %.2ff}" % (r.rMin, r.rMax)
                          for r in disc.rings)
        print("      {%.2ff, {%s},\n       %s},"
              % (disc.absZ, rings,
                 slab_literal(slab) if slab is not None else "{}"))
    print("  };")
    print("  // clang-format on")
    print("  // %d of %d discs matched a measured surface"
          % (len(description.discs) - unmatched, len(description.discs)))


if __name__ == "__main__":
    main()
