#!/usr/bin/env python3
"""Derive a synthetic pixel layout from a detector ACTS can build.

Unlike the ITk, the Open Data Detector and the ACTS Generic detector are
detectors ACTS builds itself, so their layouts need neither a fit nor a
transcription of XML by hand: `makeLayoutFromTrackingGeometry` reduces the built
`Acts::TrackingGeometry` to exactly the cylinders and rings the synthetic model
wants. This runs that reduction and prints a `BarrelEndcapDescription` ready to
paste into `Fatras/src/Synthetic/DetectorLayout.cpp`, so that the presets stay
usable without DD4hep while still being the geometry's own numbers.

`Python/Examples/tests/test_fatras_synthetic_layout.py` is what keeps the pasted
numbers honest: it runs the same reduction and compares.

Run it as

    python layout_from_geometry.py odd
    python layout_from_geometry.py generic --report
"""

from __future__ import annotations

import argparse

import acts
from acts.fatras import synthetic as syn

#: Pixel volumes and beam pipe radius per detector. The beam pipe sits in a
#: volume of its own that the pixel selector excludes, so it is added by hand:
#: 23.6 to 24.4 mm of beryllium in the ODD's `OpenDataDetectorEnvelopes.xml`, and
#: `kBeamPipeRadius` in the generic detector's `GenericDetectorBuilder.hpp`.
DETECTORS = {
    "odd": {"volumes": (16, 17, 18), "beamPipeRadius": 24.0},
    "generic": {"volumes": (7, 8, 9), "beamPipeRadius": 19.0},
}


def build(name: str):
    """Build a detector.

    The detector is returned alongside its geometry deliberately: the geometry
    does not keep the detector alive, and letting the detector go out of scope
    leaves the geometry dangling.

    @param name the detector
    @return the detector and its tracking geometry
    """
    if name == "odd":
        from acts.examples.odd import getOpenDataDetector
        detector = getOpenDataDetector()
    else:
        from acts.examples import GenericDetector
        detector = GenericDetector()
    return detector, detector.trackingGeometry()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("detector", choices=sorted(DETECTORS))
    parser.add_argument("--report", action="store_true",
                        help="print the layout rather than the C++")
    parser.add_argument("--disk-z-tolerance", type=float, default=None,
                        help="surfaces of a layer within this many mm in z are "
                             "one disk")
    parser.add_argument("--ring-r-tolerance", type=float, default=None,
                        help="radial gap below which two rings count as one")
    parser.add_argument("--no-resolve-rings", action="store_true",
                        help="cover each endcap layer with one full-width disk, "
                             "which is what the layouts used to do")
    args = parser.parse_args()

    setup = DETECTORS[args.detector]
    detector, geometry = build(args.detector)
    assert detector is not None  # keeps the geometry's owner alive
    gctx = acts.GeometryContext.dangerouslyDefaultConstruct()

    options = syn.TrackingGeometryLayoutOptions()
    # the selector takes a pointer, so it may be handed a null surface
    options.setSurfaceSelector(
        lambda s: s is not None and s.geometryId.volume in setup["volumes"])
    options.passiveBeamPipeRadius = setup["beamPipeRadius"]
    if args.no_resolve_rings:
        options.resolveDiskRings = False
    if args.disk_z_tolerance is not None:
        options.diskZTolerance = args.disk_z_tolerance
    if args.ring_r_tolerance is not None:
        options.ringRTolerance = args.ring_r_tolerance

    layout = syn.makeLayoutFromTrackingGeometry(geometry, gctx, options)

    cylinders, disks = [], []
    for surface in layout.surfaces:
        if not surface.layers:
            continue
        rings = [(layout.layers[i].minBound, layout.layers[i].maxBound)
                 for i in surface.layers]
        if surface.shape == syn.SurfaceShape.Cylinder:
            cylinders.append((surface.refCoord,
                              max(abs(b) for r in rings for b in r)))
        elif surface.refCoord > 0:
            disks.append((surface.refCoord, rings))
    disks.sort()

    if args.report:
        print("%-10s %9s %s" % ("surface", "position", "extent"))
        for radius, half in cylinders:
            print("%-10s %9.2f %9.2f" % ("cylinder", radius, half))
        for absZ, rings in disks:
            print("%-10s %9.2f %s"
                  % ("disk", absZ, " ".join("%.2f-%.2f" % r for r in rings)))
        print()
        print("%d cylinders, %d disks per side, %d rings per side"
              % (len(cylinders), len(disks), sum(len(r) for _, r in disks)))
        return

    print("  description.beamPipeRadius = %.0f.f;" % setup["beamPipeRadius"])
    print("  description.barrelRadii = {%s};"
          % ", ".join("%.2ff" % c[0] for c in cylinders))
    print("  description.barrelHalfLengthsZ = {%s};"
          % ", ".join("%.2ff" % c[1] for c in cylinders))
    print("  description.barrelModules = 1;")
    print("  // clang-format off")
    print("  description.disks = {")
    for absZ, rings in disks:
        print("      {%.2ff, {%s}},"
              % (absZ, ", ".join("{%.2ff, %.2ff}" % r for r in rings)))
    print("  };")
    print("  // clang-format on")
    print()
    print("// %d barrel cylinders, %d disks per side carrying %d rings"
          % (len(cylinders), len(disks), sum(len(r) for _, r in disks)))


if __name__ == "__main__":
    main()
