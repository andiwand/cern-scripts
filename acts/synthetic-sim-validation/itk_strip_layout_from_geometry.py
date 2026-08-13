#!/usr/bin/env python3
"""Add the ITk strip subsystem to the shipped ITk description.

The pixel half of `itk-description.json` comes from ITKLayouts by way of
`itk_layout_from_xml.py`, because ACTS has no ITk pixel geometry of its own that
is not already a reduction. The strips are different: `acts-itk` builds them,
volumes 22, 23 and 24, so the strip layers can be reduced out of the tracking
geometry exactly the way the ODD's are, and nothing has to be transcribed.

What comes out is the real strip detector: four barrel cylinders at r = 399,
562, 762 and 1000, and six discs per side between |z| = 1512 and 2850. The discs
reduce to one ring each, which is not a loss -- the strip endcap rings tile the
disc without the supports that make the pixel endcap's gaps.

    python itk_strip_layout_from_geometry.py --report
    python itk_strip_layout_from_geometry.py -o /tmp/itk
    python itk_strip_layout_from_geometry.py -o itk     # overwrite what ships

The module types the strip layers are built of go in with them, named in the
description's own `sensors` table: two barrel modules and one endcap module for
ten layers, so that the two short-strip layers are provably the same thing.

Material is not written here. Run `material_from_geometry.py itk` afterwards: it
matches the geometry's material onto whatever layers the description has, so it
picks the strips up once they are in it.

Note the `python x.py` invocation: the ITk geometry needs the spack view on
`DYLD_LIBRARY_PATH`, which a shebang run through `/usr/bin/env` strips.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np

import acts
import acts.examples.itk
from acts.fatras import synthetic as syn

import presets

#: The ACTS volumes the ITk strip detector is built in.
STRIP_VOLUMES = (22, 23, 24)

#: What the subsystem is called, and so what `--subsystems` selects it by.
SUBSYSTEM = "itk-strip"

#: Chance that a crossing is measured twice because the staves and the rings
#: overlap in phi, and how far the second module sits along the normal.
#:
#: Neither is measured here: the reduction sees module extents, not the
#: azimuthal tiling, and there is no strip reference sample to fit them against
#: the way the pixel numbers were fitted. They are the pixel detector's outer
#: barrel and endcap values, which is the closest thing to a measurement this
#: has, and they are the knob to turn if a strip occupancy ever gets compared
#: against a real one.
BARREL_OVERLAP_PROBABILITY = 0.13
BARREL_OVERLAP_OFFSET = 7.9
DISC_OVERLAP_PROBABILITY = 0.15
DISC_OVERLAP_OFFSET = 5.0

#: Radius past which a track has left the ITk for good. The description ships
#: with 1000, which is where the outermost strip barrel sits, so a track would
#: be gone before it could cross it.
ESCAPE_RADIUS = 1100.0

#: The module types the ITk strips are built of, and which layer is built of
#: which. Not measured off the geometry: ACTS builds the strip modules as single
#: planes, so the stereo pair is not in there to read.
#:
#: The ITk numbers, from the strip TDR: 75.5 um pitch throughout, 26 mrad
#: between the two sides of a barrel stave and 20 mrad in the endcap, and strips
#: of 24.1 mm on the two short-strip barrel layers against 48.2 mm on the two
#: long-strip ones. The endcap strips fan out and run 15 to 60 mm depending on
#: the ring; the discs reduce to one ring each, so they get one length.
#:
#: The separation between the two sensors of a stereo pair *is* in the geometry
#: -- the two faces of a stave are two rings of modules at different radii --
#: so it is measured rather than stated; see `measure_gaps`. It matters more
#: than anything else here: the beam-spot vertex walks a resolved space point
#: along the strip by `(kappa r / 2) * gap / sin(stereo)`, in proportion to it.
STRIP_PITCH = 0.0755
#: name -> (strip length, which region to measure the pair of). The lengths are
#: the module extent along the strips, `2 * hlX` of the ACTS surfaces: 24.41 mm
#: on the two short-strip barrel layers and 48.81 mm on the two long-strip ones.
#: The endcap strips fan out and run 15 to 60 mm depending on the ring; the
#: discs reduce to one ring each, so they get one length.
SENSORS = {
    "itk-strip-short": (24.41, "barrel"),
    "itk-strip-long": (48.81, "barrel"),
    "itk-strip-endcap": (30.0, "endcap"),
}

#: The endcap stereo angle, which the geometry will not give up: an annulus
#: module's local frame is the fan's focal frame, so the tilt it reports is
#: where the module sits in its ring and not how its strips are rotated. The
#: strip TDR's 20 mrad, doubled because the two faces are tilted the opposite
#: way by that much each -- which is what the barrel measurement shows.
ENDCAP_STEREO_ANGLE = 40e-3

#: which module each barrel layer is built of, outwards
BARREL_SENSORS = ("itk-strip-short", "itk-strip-short",
                  "itk-strip-long", "itk-strip-long")
ENDCAP_SENSOR = "itk-strip-endcap"


def reduce_strips(tolerance: float = 1.0):
    """Reduce the ITk strip volumes to a subsystem description.

    @param tolerance how far two mirrored discs may sit apart, in mm
    @return the subsystem and the module types its layers reference
    """
    detector = acts.examples.itk.buildITkGeometry(
        Path.home() / "cern/source/acts/acts-itk")
    geometry = detector.trackingGeometry()
    assert detector is not None  # keeps the geometry's owner alive
    gctx = acts.GeometryContext.dangerouslyDefaultConstruct()

    options = syn.TrackingGeometryLayoutOptions()
    # the selector takes a pointer, so it may be handed a null surface
    options.setSurfaceSelector(
        lambda s: s is not None and s.geometryId.volume in STRIP_VOLUMES)
    options.setSubsystemName(lambda s: SUBSYSTEM)
    # The strip services belong to the strips, but the description already
    # carries the pixel ones out to r = 265 and the beam pipe, and a second
    # reduction would key them onto strip layers. Left out deliberately;
    # `material_from_geometry.py` measures what the strip layers themselves
    # carry.
    options.includeMaterialSurfaces = False
    options.passiveBeamPipeRadius = 0.0

    description = syn.makeDescriptionFromTrackingGeometry(
        geometry, gctx, options)
    table = sensors(measure_modules(geometry, gctx))
    if len(description.subsystems) != 1:
        raise SystemExit("expected one strip subsystem, got %d"
                         % len(description.subsystems))
    subsystem = description.subsystems[0]

    for barrel in subsystem.barrels:
        for cylinder in barrel.cylinders:
            cylinder.overlapProbability = BARREL_OVERLAP_PROBABILITY
            cylinder.overlapOffset = BARREL_OVERLAP_OFFSET
    for endcap in subsystem.endcaps:
        for disc in endcap.discs:
            disc.overlapProbability = DISC_OVERLAP_PROBABILITY
            disc.overlapOffset = DISC_OVERLAP_OFFSET

    _sensors(subsystem)
    _mirror(subsystem, tolerance)
    return subsystem, table


def _rotation(surface, gctx):
    """@return the 3x3 rotation of a surface's local frame, as a numpy array"""
    rows = str(surface.localToGlobalTransform(gctx)).strip().splitlines()
    return np.array([[float(v) for v in row.split()] for row in rows])[:3, :3]


def measure_modules(geometry, gctx) -> dict:
    """Measure what a stereo pair is, off the geometry that has it.

    Two things, neither of them written down anywhere else:

    - **How far apart the two sensors sit.** A stave carries modules on both
      faces, so the pair a space point is formed from is two rings of modules at
      different radii. This is what decides how far the beam-spot vertex walks a
      resolved point along its strip: `(kappa r / 2) * gap / sin(stereo)`.
    - **The angle between them.** The two faces are tilted the opposite way by
      the same amount, so the angle between the strips is *twice* the tilt of
      either. Quoting the tilt as the stereo angle halves the resolution along
      the strip and doubles that walk, which is worth an order of magnitude in
      how many pairs resolve at all.

    @param geometry the ITk tracking geometry
    @param gctx the geometry context
    @return `gap` and `stereo` per region, in mm and rad
    """
    planes = {}

    def visit(surface):
        if surface is None:
            return
        volume = surface.geometryId.volume
        if volume not in STRIP_VOLUMES:
            return
        centre = surface.center(gctx)
        x, y, z = float(centre[0]), float(centre[1]), float(centre[2])
        r = math.hypot(x, y)
        phi = math.atan2(y, x)
        # the coordinate along the module normal: r in the barrel, z in an
        # endcap
        along = r if volume == 23 else z

        # the tilt of the strips out of the direction they nominally run in
        rotation = _rotation(surface, gctx)
        nominal = np.array([0.0, 0.0, 1.0]) if volume == 23 \
            else np.array([math.cos(phi), math.sin(phi), 0.0])
        across = np.array([-math.sin(phi), math.cos(phi), 0.0])
        axes = [rotation[:, 0], rotation[:, 1]]
        axis = max(axes, key=lambda a: abs(float(np.dot(a, nominal))))
        if float(np.dot(axis, nominal)) < 0:
            axis = -axis
        tilt = math.atan2(float(np.dot(axis, across)),
                          float(np.dot(axis, nominal)))
        planes.setdefault((volume, surface.geometryId.layer), []).append(
            (along, tilt))

    geometry.visitSurfaces(visit)

    out = {}
    for (volume, _), values in planes.items():
        values.sort()
        groups = [[values[0]]]
        for value in values[1:]:
            if value[0] - groups[-1][-1][0] > 1.0:
                groups.append([])
            groups[-1].append(value)
        centres = [sum(v[0] for v in g) / len(g) for g in groups]
        tilts = [sum(v[1] for v in g) / len(g) for g in groups]
        gaps = [centres[i + 1] - centres[i] for i in range(len(centres) - 1)]
        if not gaps:
            continue
        # A stave face carries one plane, and the pair is the closest two: the
        # smallest separation, not the step from one pair to the next.
        pair = min(range(len(gaps)), key=lambda i: gaps[i])
        region = "barrel" if volume == 23 else "endcap"
        out.setdefault(region, []).append(
            (gaps[pair], abs(tilts[pair + 1] - tilts[pair])))
    return {region: {"gap": sum(v[0] for v in values) / len(values),
                     "stereo": sum(v[1] for v in values) / len(values)}
            for region, values in out.items()}


def sensors(modules: dict) -> dict:
    """@param modules what a pair is, per region; see `measure_modules`
    @return the module types, by the name a layer references them under"""
    out = {}
    for name, (length, region) in SENSORS.items():
        sensor = syn.StripSensor()
        sensor.stereoAngle = (modules[region]["stereo"] if region == "barrel"
                              else ENDCAP_STEREO_ANGLE)
        sensor.pitch = STRIP_PITCH
        sensor.moduleGap = modules[region]["gap"]
        sensor.halfLength = 0.5 * length
        out[name] = sensor
    return out


def _sensors(subsystem) -> None:
    """Name the module each layer is built of, which is what makes it a strip
    layer.

    @param subsystem the subsystem to name in place
    """
    index = 0
    for barrel in subsystem.barrels:
        for cylinder in barrel.cylinders:
            cylinder.sensor = BARREL_SENSORS[
                min(index, len(BARREL_SENSORS) - 1)]
            index += 1
    for endcap in subsystem.endcaps:
        for disc in endcap.discs:
            disc.sensor = ENDCAP_SENSOR


def _same_disc(a, b, tolerance: float) -> bool:
    """@return whether two discs of opposite sides are the same disc mirrored"""
    if abs(a.absZ - b.absZ) > tolerance or len(a.rings) != len(b.rings):
        return False
    return all(abs(x.rMin - y.rMin) <= tolerance
               and abs(x.rMax - y.rMax) <= tolerance
               for x, y in zip(a.rings, b.rings))


def _mirror(subsystem, tolerance: float) -> bool:
    """Fold the two measured endcaps into one mirrored one where they agree.

    @param subsystem the subsystem to fold in place
    @param tolerance how far two mirrored discs may sit apart, in mm
    @return whether it was folded
    """
    sides = {endcap.placement: endcap for endcap in subsystem.endcaps}
    if set(sides) != {syn.EndcapPlacement.Positive,
                      syn.EndcapPlacement.Negative}:
        return False
    positive = sides[syn.EndcapPlacement.Positive]
    negative = sides[syn.EndcapPlacement.Negative]
    if len(positive.discs) != len(negative.discs):
        return False
    if not all(_same_disc(a, b, tolerance)
               for a, b in zip(positive.discs, negative.discs)):
        return False
    both = syn.EndcapDescription()
    both.placement = syn.EndcapPlacement.Mirrored
    # the positive side's numbers, the two having been shown to agree
    both.discs = positive.discs
    subsystem.endcaps = [both]
    return True


def report(subsystem) -> None:
    """Print what the reduction found, rather than writing it.

    @param subsystem the subsystem to print
    """
    for barrel in subsystem.barrels:
        for cylinder in barrel.cylinders:
            print("cylinder  r=%8.2f  halfZ=%8.2f  layer=%-4s %s"
                  % (cylinder.radius, cylinder.halfLengthZ, cylinder.layer,
                     cylinder.sensor))
    for endcap in subsystem.endcaps:
        side = str(endcap.placement).split(".")[-1].lower()
        for disc in endcap.discs:
            print("disc %-9s z=%8.2f  layer=%-4s %s"
                  % (side, disc.absZ, disc.layer,
                     " ".join("%.1f-%.1f" % (r.rMin, r.rMax)
                              for r in disc.rings)))


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-o", "--out", default=None,
                        help="what to write: a shipped name, or a path prefix. "
                             "Defaults to the ITk description in place.")
    parser.add_argument("--report", action="store_true",
                        help="print what was found rather than writing it")
    parser.add_argument("--mirror-tolerance", type=float, default=1.0,
                        help="how far two mirrored discs may sit apart, in mm")
    args = parser.parse_args()

    subsystem, table = reduce_strips(args.mirror_tolerance)
    if args.report:
        for name, sensor in sorted(table.items()):
            print("sensor %-20s stereo %.4f rad  pitch %.4f  gap %.2f  "
                  "strip %.1f mm"
                  % (name, sensor.stereoAngle, sensor.pitch, sensor.moduleGap,
                     2.0 * sensor.halfLength))
        report(subsystem)
        return

    # Read the pixel material back in, because writing a description splits it
    # off again: reading without it would leave the strips' new layers in the
    # file and nothing else, and the pixel material would be gone.
    description = presets.description("itk")
    description.subsystems = [s for s in description.subsystems
                              if s.name != SUBSYSTEM] + [subsystem]
    # The bound was the strips when the strips were only a bound. Now that the
    # outermost of them is a surface at r = 1000, a track has to be allowed past
    # it before it counts as gone.
    description.escapeRadius = ESCAPE_RADIUS
    merged = dict(description.sensors)
    merged.update(table)
    description.sensors = merged

    for written in presets.write_description(args.out or "itk", description):
        print("wrote %s" % written)


if __name__ == "__main__":
    main()
