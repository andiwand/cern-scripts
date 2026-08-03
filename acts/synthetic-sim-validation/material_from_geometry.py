#!/usr/bin/env python3
"""Measure the material of a shipped synthetic layout off the real geometry.

`layout_from_geometry.py` reduces a geometry into a layout wholesale. This does
only the material half: it reduces the geometry, then matches what it measured
onto the *shipped* description by reference coordinate, so a layout that was
transcribed rather than reduced -- the ITk, whose geometry source describes only
its silicon -- keeps its own surfaces and gains their material.

Prints the `barrelMaterialWeights` and the per-disc weights to paste into
`Fatras/src/Synthetic/DetectorLayout.cpp`, in units of a bare sensor.

    ./material_from_geometry.py itk
    ./material_from_geometry.py odd
"""

from __future__ import annotations

import argparse
from pathlib import Path

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


def measure(name: str):
    """Reduce a detector and read the material of every surface it produces.

    @param name the detector
    @return the cylinder and disc material, keyed on reference coordinate and
            in units of a bare sensor
    """
    detector, geometry = build(name)
    assert detector is not None  # keeps the geometry's owner alive
    gctx = acts.GeometryContext.dangerouslyDefaultConstruct()

    volumes = DETECTORS[name]["volumes"]
    options = syn.TrackingGeometryLayoutOptions()
    options.setSurfaceSelector(
        lambda s: s is not None and s.geometryId.volume in volumes)
    layout = syn.makeLayoutFromTrackingGeometry(geometry, gctx, options)

    unit = syn.sensorMaterial().thicknessInX0
    cylinders, discs = {}, {}
    for surface in layout.surfaces:
        weight = surface.material.thicknessInX0 / unit
        # a disc is mirrored, so only one side is kept and keyed on |z|
        key = round(abs(surface.refCoord), 1)
        into = (cylinders if surface.shape == syn.SurfaceShape.Cylinder
                else discs)
        into.setdefault(key, []).append(weight)
    return ({k: sum(v) / len(v) for k, v in cylinders.items()},
            {k: sum(v) / len(v) for k, v in discs.items()})


def nearest(table: dict, coord: float, tolerance: float):
    """The measured weight closest to a coordinate, within a tolerance.

    @param table the measured weights, keyed on reference coordinate
    @param coord the coordinate to match
    @param tolerance how far away a match may be
    @return the weight, or None if nothing is close enough
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
    args = parser.parse_args()

    cylinders, discs = measure(args.detector)

    description = {"itk": syn.itkPixelDescription,
                   "odd": syn.openDataDetectorPixelDescription,
                   "generic": syn.genericDetectorPixelDescription}[
                       args.detector]()

    barrel = [nearest(cylinders, r, args.tolerance)
              for r in description.barrelRadii]
    print("  description.barrelMaterialWeights = {%s};"
          % ", ".join("%.2ff" % (w if w is not None else 1.0) for w in barrel))
    missing = [r for r, w in zip(description.barrelRadii, barrel) if w is None]
    if missing:
        print("  // no material found at r = %s"
              % ", ".join("%.1f" % r for r in missing))

    print("  // clang-format off")
    print("  description.discs = {")
    unmatched = 0
    for disc in description.discs:
        weight = nearest(discs, disc.absZ, args.tolerance)
        unmatched += weight is None
        rings = ", ".join("{%.1ff, %.1ff}" % (r.rMin, r.rMax)
                          for r in disc.rings)
        print("      {%.1ff, {%s}, %.2ff},"
              % (disc.absZ, rings, weight if weight is not None else 1.0))
    print("  };")
    print("  // clang-format on")
    print("// %d of %d discs matched a measured surface"
          % (len(description.discs) - unmatched, len(description.discs)))


if __name__ == "__main__":
    main()
