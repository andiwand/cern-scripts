#!/usr/bin/env python3
"""Write the files of a synthetic detector out of a detector ACTS can build.

Unlike the ITk, the Open Data Detector and the ACTS Generic detector are
detectors ACTS builds itself, so their descriptions need neither a fit nor a
transcription of XML by hand: `makeDescriptionFromTrackingGeometry` reduces the
built `Acts::TrackingGeometry` to exactly the cylinders and rings the synthetic
model wants, and reads their material off the geometry's own maps while it is
there. This runs that reduction and writes the two files the detector ships as.

`Python/Examples/tests/test_fatras_synthetic_layout.py` runs the same reduction
and compares it against the shipped files, which is what keeps them honest.

Run it as

    python layout_from_geometry.py odd --report
    python layout_from_geometry.py odd -o /tmp/odd
    python layout_from_geometry.py odd -o odd        # overwrite what ships

Note the `python x.py` invocation: DD4hep needs the spack view on
`DYLD_LIBRARY_PATH`, which a shebang run through `/usr/bin/env` strips.
"""

from __future__ import annotations

import argparse

import acts
from acts.fatras import synthetic as syn

import presets

#: Pixel volumes, beam pipe radius and containment per detector. The beam pipe
#: sits in a volume of its own that the pixel selector excludes, so it is added
#: by hand: 23.6 to 24.4 mm of beryllium in the ODD's
#: `OpenDataDetectorEnvelopes.xml`, and `kBeamPipeRadius` in the generic
#: detector's `GenericDetectorBuilder.hpp`. The escape bounds are the whole
#: tracker's rather than the pixels', which is what a track leaving them curls
#: back through.
DETECTORS = {
    "odd": {"volumes": (16, 17, 18), "beamPipeRadius": 24.0,
            "subsystem": "odd-pixel", "escapeRadius": 1100.0,
            "escapeHalfZ": 3000.0},
    "generic": {"volumes": (7, 8, 9), "beamPipeRadius": 19.0,
                "subsystem": "generic-pixel", "escapeRadius": 1100.0,
                "escapeHalfZ": 3000.0},
}

#: What each of them ships as, i.e. the prefix of its files in `Fatras/data`.
SHIPS_AS = {"odd": "odd", "generic": "generic-pixel"}


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


def _same_disc(a, b, tolerance: float) -> bool:
    """@return whether two discs of opposite sides are the same disc mirrored"""
    if abs(a.absZ - b.absZ) > tolerance or len(a.rings) != len(b.rings):
        return False
    return all(abs(x.rMin - y.rMin) <= tolerance
               and abs(x.rMax - y.rMax) <= tolerance
               for x, y in zip(a.rings, b.rings))


def mirror(description, tolerance: float) -> int:
    """Fold a subsystem's two one-sided endcaps into one mirrored one.

    The reduction measures each side of the detector separately, because a real
    detector is only nearly symmetric. Where the two sides do agree, saying so
    once halves the file, and it is what the shipped descriptions do.

    @param description the description to fold in place
    @param tolerance how far two mirrored discs may sit apart, in mm
    @return how many subsystems were folded
    """
    folded = 0
    for subsystem in description.subsystems:
        sides = {endcap.placement: endcap for endcap in subsystem.endcaps}
        if len(subsystem.endcaps) != 2 or set(sides) != {
                syn.EndcapPlacement.Positive, syn.EndcapPlacement.Negative}:
            continue
        positive = sides[syn.EndcapPlacement.Positive]
        negative = sides[syn.EndcapPlacement.Negative]
        if len(positive.discs) != len(negative.discs):
            continue
        if not all(_same_disc(a, b, tolerance)
                   for a, b in zip(positive.discs, negative.discs)):
            continue
        both = syn.EndcapDescription()
        both.placement = syn.EndcapPlacement.Mirrored
        # the positive side's numbers, the two having been shown to agree
        both.discs = positive.discs
        subsystem.endcaps = [both]
        folded += 1
    return folded


def reduce_geometry(name: str, *, mirrored: bool = True,
                    tolerance: float = 1.0, disc_z_tolerance=None,
                    ring_r_tolerance=None):
    """Reduce a built detector to a description of it.

    @param name the detector
    @param mirrored whether to fold symmetric endcaps onto one side
    @param tolerance how far two mirrored discs may sit apart, in mm
    @param disc_z_tolerance surfaces of a layer within this many mm are one disc
    @param ring_r_tolerance radial gap below which two rings count as one
    @return the description
    """
    setup = DETECTORS[name]
    detector, geometry = build(name)
    assert detector is not None  # keeps the geometry's owner alive
    gctx = acts.GeometryContext.dangerouslyDefaultConstruct()

    options = syn.TrackingGeometryLayoutOptions()
    # the selector takes a pointer, so it may be handed a null surface
    options.setSurfaceSelector(
        lambda s: s is not None and s.geometryId.volume in setup["volumes"])
    # One subsystem: a geometry names them by the volume they are in, and the
    # pixel volumes of these two are one system as far as anything reading the
    # description is concerned.
    options.setSubsystemName(lambda s: setup["subsystem"])
    options.passiveBeamPipeRadius = setup["beamPipeRadius"]
    options.escapeRadius = setup["escapeRadius"]
    options.escapeHalfZ = setup["escapeHalfZ"]
    if disc_z_tolerance is not None:
        options.discZTolerance = disc_z_tolerance
    if ring_r_tolerance is not None:
        options.ringRTolerance = ring_r_tolerance

    description = syn.makeDescriptionFromTrackingGeometry(
        geometry, gctx, options)
    if mirrored and not mirror(description, tolerance):
        print("# the two endcaps disagree, so both sides are written out")
    return description


def report(description) -> None:
    """Print what the reduction found, rather than writing it.

    @param description the description to print
    """
    print("%-16s %9s %9s %6s %s"
          % ("surface", "position", "x/X0", "layer", "extent"))
    for subsystem in description.subsystems:
        print("subsystem %s" % subsystem.name)
        for barrel in subsystem.barrels:
            for cylinder in barrel.cylinders:
                print("%-16s %9.2f %9.4f %6s %.1f"
                      % ("cylinder", cylinder.radius,
                         cylinder.material.average().thicknessInX0,
                         cylinder.layer, cylinder.halfLengthZ))
        for endcap in subsystem.endcaps:
            side = str(endcap.placement).split(".")[-1].lower()
            for disc in endcap.discs:
                print("%-16s %9.2f %9.4f %6s %s"
                      % ("disc " + side, disc.absZ,
                         disc.material.average().thicknessInX0, disc.layer,
                         " ".join("%.2f-%.2f" % (r.rMin, r.rMax)
                                  for r in disc.rings)))
        for passive in subsystem.passives:
            print("%-16s %9.2f %9.4f %6s %.1f-%.1f"
                  % ("service", passive.refCoord,
                     passive.material.average().thicknessInX0, passive.layer,
                     passive.minBound, passive.maxBound))
    for passive in description.passives:
        print("%-16s %9.2f %9.4f %6s %.1f-%.1f"
              % ("beam pipe", passive.refCoord,
                 passive.material.average().thicknessInX0, passive.layer,
                 passive.minBound, passive.maxBound))

    cylinders = sum(len(b.cylinders) for s in description.subsystems
                    for b in s.barrels)
    discs = [d for s in description.subsystems for e in s.endcaps
             for d in e.discs]
    print()
    print("%d cylinders, %d discs, %d rings"
          % (cylinders, len(discs), sum(len(d.rings) for d in discs)))


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("detector", choices=sorted(DETECTORS))
    parser.add_argument("-o", "--out", default=None,
                        help="what to write: a shipped name, or a path prefix. "
                             "Defaults to what the detector ships as.")
    parser.add_argument("--report", action="store_true",
                        help="print what was found rather than writing it")
    parser.add_argument("--no-mirror", action="store_true",
                        help="write both endcaps out even where they agree")
    parser.add_argument("--mirror-tolerance", type=float, default=1.0,
                        help="how far two mirrored discs may sit apart, in mm")
    parser.add_argument("--disc-z-tolerance", type=float, default=None,
                        help="surfaces of a layer within this many mm in z are "
                             "one disc")
    parser.add_argument("--ring-r-tolerance", type=float, default=None,
                        help="radial gap below which two rings count as one")
    args = parser.parse_args()

    description = reduce_geometry(
        args.detector, mirrored=not args.no_mirror,
        tolerance=args.mirror_tolerance,
        disc_z_tolerance=args.disc_z_tolerance,
        ring_r_tolerance=args.ring_r_tolerance)

    if args.report:
        report(description)
        return

    out = args.out or SHIPS_AS[args.detector]
    for written in presets.write_description(out, description):
        print("wrote %s" % written)


if __name__ == "__main__":
    main()
