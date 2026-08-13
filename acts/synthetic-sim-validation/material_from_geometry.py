#!/usr/bin/env python3
"""Read the material of a shipped synthetic detector off the real geometry.

`layout_from_geometry.py` reduces a geometry into a description wholesale, which
is all a detector ACTS can build needs. This does only the material half: it
reduces the geometry, then matches what it measured onto the layers of the
*shipped* description by reference coordinate, so a detector whose positions came
from somewhere else -- the ITk's, from ITKLayouts -- keeps its layers and gains
their material.

It writes `<detector>-material.json`, keyed by the layers of the description it
was matched against. A description that is renumbered afterwards therefore has
to be re-matched, which `decorate` will say rather than silently mis-key.

Emits real slabs, not weights in sensors. A weight fixes only `x/X0`, and the
nuclear length drives the hadronic half of the yield: forcing silicon's `L0/X0`
onto a carbon support understates it by two and a half.

Service surfaces -- material the geometry carries away from any sensitive layer
-- come out too. They are where a mapped geometry keeps what no weight on a
layer can express.

    python material_from_geometry.py itk --report
    python material_from_geometry.py itk -o /tmp/itk
    python material_from_geometry.py itk -o itk      # overwrite what ships

Note the `python x.py` invocation: DD4hep needs the spack view on
`DYLD_LIBRARY_PATH`, which a shebang run through `/usr/bin/env` strips.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np

import acts
from acts.fatras import synthetic as syn

import presets

#: Sensitive volumes per detector, and how to build it. The ITk's are the ten
#: pixel volumes and the three strip ones, 22, 23 and 24.
DETECTORS = {
    "itk": {"volumes": {8, 9, 10, 13, 14, 15, 16, 18, 19, 20, 22, 23, 24}},
    "odd": {"volumes": {16, 17, 18}},
    "generic": {"volumes": {7, 8, 9}},
}

#: What each of them ships as, i.e. the prefix of its files in `Fatras/data`.
SHIPS_AS = {"itk": "itk", "odd": "odd", "generic": "generic-pixel"}


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
                or surface.material.average().thickness <= 0
                or abs(surface.refCoord - radius) > tolerance):
            continue
        if any(abs(surface.refCoord - r) <= tolerance for r in barrel_radii):
            continue
        if surface.material.average().thicknessInX0 > most:
            best, most = surface.material, surface.material.average().thicknessInX0
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


def composition_of(slab):
    """What the bands of a surface share, from the slab they were quoted at.

    @param slab the average slab
    @return the `BandComposition`
    """
    m = slab.material
    return syn.BandComposition(m.Ar, m.Z, m.molarDensity * m.X0, slab.thickness)


#: `L0/X0` of the lightest and heaviest thing a tracker is built out of:
#: beryllium at 1.19, carbon 2.0, silicon 5.0, copper 10.7, tungsten 28.4. A
#: mapped slab is an accumulated mixture rather than one substance, but a
#: mixture still lands between its components, so a band outside this is a bug
#: in the reduction and not a material.
PHYSICAL_L0_OVER_X0 = (1.1, 32.0)


def report_composition(materials: list) -> None:
    """Hold every band against what matter can actually be.

    This is what carrying the two lengths per band buys that a thickness could
    not: a thickness scale keeps `L0/X0` at whatever the surface average was, so
    it never reads as impossible however wrong it is.

    @param materials the emitted `SurfaceMaterial`s, with a label each
    """
    ratios, bad = [], []
    for label, material in materials:
        if material is None:
            continue
        for lo, band in zip(material.bounds, material.bands):
            if band.thicknessInX0 <= 0:
                continue
            ratio = band.material.L0 / band.material.X0
            ratios.append(ratio)
            if not PHYSICAL_L0_OVER_X0[0] <= ratio <= PHYSICAL_L0_OVER_X0[1]:
                bad.append((label, lo, ratio))
    if not ratios:
        return
    ratios.sort()
    print("  L0/X0 over %d bands: %.2f to %.2f, median %.2f"
          % (len(ratios), ratios[0], ratios[-1], ratios[len(ratios) // 2]))
    for label, lo, ratio in bad[:10]:
        print("  NOT A MATERIAL: %s from %.1f has L0/X0 = %.2f"
              % (label, lo, ratio))
    if len(bad) > 10:
        print("  ... and %d more" % (len(bad) - 10))


def profile(edges: list, bands: list):
    """A `SurfaceMaterial` from a slab per band, `None` being vacuum.

    @param edges the band bounds, one more than there are bands
    @param bands the slab of each band
    @return the material, whose slab is the mean over the whole surface and
            whose bands state their own two lengths at that slab's thickness
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
    x0s, l0s = [], []
    for slab in bands:
        # the band keeps its x/X0 and x/L0 at the shared thickness, which is
        # what fixes its two lengths
        if slab is None or slab.thicknessInX0 <= 0:
            x0s.append(0.0)
            l0s.append(0.0)
            continue
        x0s.append(mean.thickness / slab.thicknessInX0)
        l0s.append(mean.thickness / slab.thicknessInL0
                   if slab.thicknessInL0 > 0 else 0.0)
    # every edge, the first one included: a band is the gap between two of them
    return syn.SurfaceMaterial(composition_of(mean),
                               [float(e) for e in edges], x0s, l0s)


def bands_of(material, edges: list) -> list:
    """@return the slab of `material` in each band of `edges`, None for vacuum"""
    out = []
    for lo, hi in zip(edges, edges[1:]):
        slab = material.at(0.5 * (lo + hi))
        out.append(slab if slab.thicknessInX0 > 0 else None)
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
    # the union of their edges; each already states where its own material
    # starts, so nothing has to be prepended
    edges = sorted({b for m in materials for b in m.bounds})
    bands = []
    for lo, hi in zip(edges, edges[1:]):
        here = []
        for m in materials:
            slab = m.at(0.5 * (lo + hi))
            if slab.thicknessInX0 <= 0:
                continue
            part = syn.MaterialSlab(slab.material, slab.thickness)
            part.scaleThickness(1.0 / len(materials))
            here.append(part)
        bands.append(syn.MaterialSlab.combineLayers(here) if here else None)
    return profile(edges, bands) or materials[0]


def fill_rings(material, rings):
    """Give a ring what the rest of the surface carries where nothing was
    measured over it.

    The ITk description and the ACTS geometry do not agree on which rings share
    a disc, so a handful of rings have no surface of their own to read. Leaving
    those at vacuum is worse than the stand-in.

    The stand-in is the mean over what *was* measured, not over the whole
    surface: the latter is diluted by however much of the disc is empty, which
    on a disc that is mostly beam hole is most of it.

    @param material the disc's material, or None
    @param rings the rings of the disc
    @return the material, or None if there was none to start with
    """
    if material is None or not material.bounds:
        return material
    missing = [r for r in rings
               if material.at(0.5 * (r.rMin + r.rMax)).thicknessInX0 <= 0]
    if not missing:
        return material
    edges = sorted(set(material.bounds)
                   | {r.rMin for r in missing} | {r.rMax for r in missing})
    bands = bands_of(material, edges)

    filled = sum(hi - lo for (lo, hi), slab
                 in zip(zip(edges, edges[1:]), bands) if slab is not None)
    parts = []
    for (lo, hi), slab in zip(zip(edges, edges[1:]), bands):
        if slab is None:
            continue
        part = syn.MaterialSlab(slab.material, slab.thickness)
        part.scaleThickness((hi - lo) / filled)
        parts.append(part)
    if not parts:
        return material
    standIn = syn.MaterialSlab.combineLayers(parts)

    for k, (lo, hi) in enumerate(zip(edges, edges[1:])):
        mid = 0.5 * (lo + hi)
        if bands[k] is None and any(r.rMin <= mid <= r.rMax for r in missing):
            bands[k] = standIn
    return profile(edges, bands) or material


def clip(material, lo: float, hi: float):
    """Keep only the part of a surface's material between two coordinates.

    Two subsystems may put a layer at the same place -- the ITk pixel and strip
    endcaps both end at |z| = 2850 -- and the match is by reference coordinate
    alone, so each of them takes the whole measured disc. A track crossing the
    plane then picks the same material up twice, once on either surface.

    The empty bands outside the window are dropped rather than kept at vacuum:
    a surface is bounded by what its material spans, so leaving them would
    stretch the pixel disc across the strip endcap and put it back in the way.

    @param material the material to clip, or None
    @param lo the lower bound to keep, in the coordinate the surface extends in
    @param hi the upper bound
    @return the clipped material, or None if there was none to start with
    """
    if material is None or not material.bounds:
        return material
    edges = sorted(e for e in set(material.bounds) | {lo, hi} if lo <= e <= hi)
    bands = bands_of(material, edges)
    while bands and bands[0] is None:
        bands.pop(0)
        edges.pop(0)
    while bands and bands[-1] is None:
        bands.pop()
        edges.pop()
    if not bands:
        return material
    return profile(edges, bands) or material


def assign_discs(measured: list, spans: dict, tolerance: float) -> dict:
    """Hand every measured disc to the described disc whose rings it covers.

    Same nearest assignment as `assign`, except that where two subsystems put a
    disc at one |z| -- the ITk pixel and strip endcaps both end at 2850 -- the
    two are told apart by radius. Merging them instead averages each into the
    other over radii it does not reach, and `merge` divides by the number of
    materials it was given, so the pixel disc comes out at half its thickness.

    @param measured pairs of reference coordinate and material
    @param spans the radial extent of each described disc, by its |z|
    @param tolerance how far a measured disc may sit from the one it goes to
    @return the merged material per (|z|, index into that |z|'s spans)
    """
    out: dict = {}
    for coord, material in measured:
        if not spans:
            break
        closest = min(spans, key=lambda w: abs(w - coord))
        if abs(closest - coord) > tolerance:
            continue
        here = spans[closest]
        index = 0
        if len(here) > 1 and material.bounds:
            lo, hi = material.bounds[0], material.bounds[-1]
            index = max(range(len(here)),
                        key=lambda k: min(hi, here[k][1]) - max(lo, here[k][0]))
        out.setdefault((closest, index), []).append(material)
    return {k: merge(v) for k, v in out.items()}


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
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("detector", choices=sorted(DETECTORS))
    parser.add_argument("-o", "--out", default=None,
                        help="what to write the material of: a shipped name, or "
                             "a path prefix. Defaults to the detector itself.")
    parser.add_argument("--against", default=None,
                        help="the description to match onto; defaults to the "
                             "one the detector ships with")
    parser.add_argument("--report", action="store_true",
                        help="print what was matched rather than writing it")
    parser.add_argument("--tolerance", type=float, default=6.0,
                        help="how far a measured surface may sit from the "
                             "shipped one it is matched to, in mm")
    parser.add_argument("--no-services", action="store_true",
                        help="leave out the material away from any sensitive "
                             "layer")
    args = parser.parse_args()

    shipped = presets.description(args.against or SHIPS_AS[args.detector],
                                  material=False)
    layout = measure(args.detector, services=not args.no_services)

    # What the reduction found, split the way the shipped layers are named: a
    # sensitive cylinder or disc is matched by its reference coordinate, a
    # service by its shape and position.
    cylinders, discs, passive = [], [], []
    for s in layout.surfaces:
        if s.material.average().thickness <= 0:
            continue
        if s.passive:
            # one side only; a description states a disc once and mirrors it
            if s.refCoord >= 0:
                passive.append(s)
            continue
        (cylinders if s.shape == syn.SurfaceShape.Cylinder
         else discs).append((abs(s.refCoord), s.material))

    # Coincident services come from separate volume groups -- the same shell
    # seen from either side of a volume boundary -- and a track crosses that
    # position once. `materialOfGroup` does this within a group; across groups
    # it has to be done here.
    coincident = {}
    for s in passive:
        coincident.setdefault((str(s.shape), round(abs(s.refCoord), 1)),
                              []).append(s)
    for key, group in sorted(coincident.items()):
        if len(group) > 1:
            print("# %d coincident services at %s %.1f, taking the first"
                  % (len(group), key[0].rsplit(".", 1)[-1], key[1]))
    # A measured cylinder at the beam pipe's radius is the volume boundary just
    # outside the pipe, not the pipe. Left in, it wins the match on distance --
    # 25.3 is nearer the description's 25.0 than the pipe's own 23.9 is -- and
    # `measure_beam_pipe` is then never asked, which costs the ITk two thirds of
    # its beam pipe and most of the secondaries at small |d0|.
    beam_pipes = [presets.position(layer)
                  for layer_id, layer in presets.layers(shipped)
                  if layer_id.kind == syn.LayerKind.Passive
                  and not layer_id.subsystem
                  and layer.shape == syn.SurfaceShape.Cylinder]
    services = [(abs(group[0].refCoord), group[0].material)
                for group in coincident.values()
                if group[0].shape != syn.SurfaceShape.Cylinder
                or not any(abs(abs(group[0].refCoord) - b) <= args.tolerance
                           for b in beam_pipes)]

    positions = {}
    for layer_id, layer in presets.layers(shipped):
        positions.setdefault(_kind_of(layer_id, layer), []).append(
            presets.position(layer))
    # Discs of two subsystems can land on one measured plane; see `clip`. Each
    # keeps the radii up to halfway to whatever the next one covers, rather than
    # its own rings exactly: a disc carries support out past its last ring.
    spans, disc_index = {}, {}
    for layer_id, layer in presets.layers(shipped):
        if _kind_of(layer_id, layer) != "endcap" or not layer.rings:
            continue
        where = presets.position(layer)
        here = spans.setdefault(where, [])
        disc_index[(layer_id.subsystem, layer_id.placement, layer_id.layer)] = (
            where, len(here))
        here.append((min(r.rMin for r in layer.rings),
                     max(r.rMax for r in layer.rings)))

    by_radius = assign(cylinders, positions.get("barrel", []), args.tolerance)
    by_z = assign_discs(discs, spans, args.tolerance)
    by_service = assign(services, positions.get("passive", []), args.tolerance)

    decoration = []
    emitted, missing = [], []
    for layer_id, layer in presets.layers(shipped):
        kind = _kind_of(layer_id, layer)
        where = presets.position(layer)
        if kind == "barrel":
            material = by_radius.get(where)
        elif kind == "endcap":
            key = disc_index[(layer_id.subsystem, layer_id.placement,
                              layer_id.layer)]
            material = by_z.get(key)
            here = spans.get(where, [])
            if len(here) > 1 and layer.rings:
                # Halfway to whatever the next disc covers, rather than at its
                # own rings: a disc carries support out past its last ring.
                mine = here[key[1]]
                material = clip(
                    material,
                    max((0.5 * (other[1] + mine[0]) for other in here
                         if other[1] <= mine[0]), default=0.0),
                    min((0.5 * (other[0] + mine[1]) for other in here
                         if other[0] >= mine[1]), default=math.inf))
            # the description and the geometry do not always agree on which
            # rings share a disc, so a ring with nothing measured over it takes
            # what the rest of its disc carries
            material = fill_rings(material, layer.rings)
        else:
            material = by_service.get(where)
            if material is None and not layer_id.subsystem:
                # the beam pipe, which no pixel volume contains
                material = measure_beam_pipe(args.detector, where,
                                             positions.get("barrel", []))
                if material is None:
                    raise SystemExit(
                        "no beam pipe material at r = %.1f; a vacuum beam pipe "
                        "makes no secondaries at all" % where)
        label = "%s %s %d at %.1f" % (layer_id.subsystem or "detector", kind,
                                      layer_id.layer, where)
        if material is None:
            missing.append(label)
            continue
        emitted.append((label, material))
        entry = syn.MaterialEntry()
        entry.layer = layer_id
        entry.material = material
        decoration.append(entry)

    print("# matched %d of %d layers of %s"
          % (len(decoration), len(decoration) + len(missing), args.detector))
    for label in missing:
        print("# nothing measured over %s" % label)
    report_composition(emitted)

    if args.report:
        for label, material in emitted:
            print("%-40s %8.4f x/X0  %3d band(s)"
                  % (label, material.average().thicknessInX0,
                     len(material.bands)))
        return

    where = presets.path(args.out or SHIPS_AS[args.detector],
                         "-material.json")
    syn.writeMaterialDecoration(str(where), decoration)
    print("wrote %s" % where)


def _kind_of(layer_id, layer) -> str:
    """@return `barrel`, `endcap` or `passive` for one described layer"""
    if layer_id.kind == syn.LayerKind.Barrel:
        return "barrel"
    if layer_id.kind == syn.LayerKind.Endcap:
        return "endcap"
    return "passive"


if __name__ == "__main__":
    main()
