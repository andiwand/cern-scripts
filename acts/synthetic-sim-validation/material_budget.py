#!/usr/bin/env python3
"""What a straight ray collects, in the shipped layout and in the geometry.

The shipped descriptions carry the material of the real detector, compressed:
each surface keeps one slab and a profile of a few bands along itself. This
prints what that costs, by walking the same ray through the shipped layout and
through a reduction of the geometry fine enough to be the geometry.

Both sides use the same reduction, so this checks the transcription and the
compression rather than `materialOf` itself. It is the closure test for the
material: the fast simulation cannot make the right secondaries anywhere the
two lines disagree.

    python material_budget.py itk
    python material_budget.py odd --bands 200
"""

from __future__ import annotations

import argparse

import numpy as np

import acts
from acts.fatras import synthetic as syn

import material_from_geometry as mfg

PRESET = {"itk": syn.makeItkPixelLayout,
          "odd": syn.makeOpenDataDetectorPixelLayout,
          "generic": syn.makeGenericDetectorPixelLayout}
#: Path length a crossing is worth is clamped the way the propagator clamps it.
MAX_CYLINDER_PATH = 100.0
MAX_DISC_PATH = 4.0


def collect(layout, eta: float):
    """Walk a straight ray from the origin through a layout.

    Mirrors `acceptCrossing`: a crossing counts where it lands on a layer or
    where the surface has material under it, and a passive surface is bounded
    by its own extent. Getting that wrong inflates the forward budget by the
    number of ring planes a ray passes outside of.

    @param layout the layout to walk
    @param eta the pseudorapidity of the ray
    @return x/X0, x/L0 and the number of crossings that counted
    """
    sinh, cosh = np.sinh(eta), np.cosh(eta)
    x0 = l0 = 0.0
    met = 0
    for s in layout.surfaces:
        cylinder = s.shape == syn.SurfaceShape.Cylinder
        if cylinder:
            z = s.refCoord * sinh
            if abs(z) > layout.escapeHalfZ:
                continue
            along, r = abs(z), s.refCoord
            path = min(max(cosh, 1.0), MAX_CYLINDER_PATH)
        else:
            if eta == 0.0 or (s.refCoord > 0) != (eta > 0):
                continue
            z = abs(s.refCoord)
            r = z / max(abs(sinh), 1e-9)
            if r > layout.escapeRadius:
                continue
            along = r
            path = min(max(cosh / max(abs(sinh), 1e-9), 1.0), MAX_DISC_PATH)
        if s.layers:
            on = any(layout.layers[i].minBound <= (z if cylinder else r)
                     <= layout.layers[i].maxBound for i in s.layers)
        else:
            on = s.passiveMinBound <= along <= s.passiveMaxBound
        scale = s.material.scaleAt(along) if on else 0.0
        if scale <= 0.0:
            continue
        met += 1
        x0 += s.material.slab.thicknessInX0 * scale * path
        l0 += s.material.slab.thicknessInL0 * scale * path
    return x0, l0, met


def reduce_geometry(detector: str, bands: int):
    """Reduce a detector into a layout whose surfaces keep every band.

    @param detector the detector
    @param bands how many bands each surface keeps
    @return the layout
    """
    _, geometry = mfg.build(detector)
    gctx = acts.GeometryContext.dangerouslyDefaultConstruct()
    options = syn.TrackingGeometryLayoutOptions()
    volumes = mfg.DETECTORS[detector]["volumes"]
    options.setSurfaceSelector(
        lambda s: s is not None and s.geometryId.volume in volumes)
    options.includeMaterialSurfaces = True
    options.materialBands = bands
    options.materialBandTolerance = 0.0
    return syn.makeLayoutFromTrackingGeometry(geometry, gctx, options)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("detector", choices=sorted(PRESET))
    parser.add_argument("--bands", type=int, default=200,
                        help="bands the reference reduction keeps per surface")
    parser.add_argument("--max-eta", type=float, default=4.0)
    parser.add_argument("--steps", type=int, default=17)
    parser.add_argument("--closure-eta", type=float, default=3.5,
                        help="integrate the closure ratio inside this |eta|; "
                             "past it the maps run out and both sides are noise")
    args = parser.parse_args()

    etas = np.linspace(0.0, args.max_eta, args.steps)
    shipped = PRESET[args.detector]()
    reference = reduce_geometry(args.detector, args.bands)
    # the beam pipe sits in a volume the pixel selector excludes, so the
    # reference has to be told about it the same way the description is
    print("shipped %d surfaces, reference %d"
          % (len(shipped.surfaces), len(reference.surfaces)))

    rows = [(collect(shipped, e), collect(reference, e)) for e in etas]
    print("  %-14s" % "|eta|" + "".join("%7.2f" % e for e in etas))
    for name, index in (("x/X0", 0), ("x/L0", 1)):
        print("  %-14s" % (name + " shipped")
              + "".join("%7.3f" % a[index] for a, _ in rows))
        print("  %-14s" % (name + " geometry")
              + "".join("%7.3f" % b[index] for _, b in rows))
        print("  %-14s" % "ratio"
              + "".join("%7.2f" % (a[index] / b[index] if b[index] > 0 else 0)
                        for a, b in rows))
    print("  %-14s" % "crossings"
          + "".join("%7d" % a[2] for a, _ in rows))

    # Integrated over the acceptance, which is the number the fitted rates see:
    # a secondary rate is per X0 and per L0, so a layout carrying a tenth too
    # little material fits a tenth too high a rate and the two cancel.
    inside = [i for i, e in enumerate(etas) if e <= args.closure_eta]
    print("\nover |eta| < %.1f, shipped / geometry:" % args.closure_eta)
    for name, index in (("x/X0", 0), ("x/L0", 1)):
        ship = sum(rows[i][0][index] for i in inside)
        geom = sum(rows[i][1][index] for i in inside)
        print("  %-6s %.3f / %.3f = %.3f"
              % (name, ship, geom, ship / geom if geom > 0 else 0))


if __name__ == "__main__":
    main()
