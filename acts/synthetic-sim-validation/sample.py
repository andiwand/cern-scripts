"""The set of distributions every sample in the comparison provides.

One `Sample` is one simulated sample - a full-simulation dump or a fast-simulation
event - reduced to the flat arrays the plots need. Keeping the shape in one place
is what lets `validate.py` treat a GNN4ITk dump, a ColliderML shard and the
generator's own CSV pair identically.
"""

from __future__ import annotations

import numpy as np

#: Space point positions in mm and whether each came from a generator particle,
#: then one entry per particle: transverse momentum in GeV, the perigee
#: parameters in mm and rad, the production vertex in mm, whether the particle
#: comes from the generator rather than from the detector simulation, and how
#: many space points it left.
#:
#: `sp_primary` is what splits the space points into the two components the
#: generator models separately. Note that it is not the same population as
#: `primary`: a space point counts as primary when the particle behind it came
#: from the generator, whether or not that particle is inside the acceptance the
#: particle fields are selected on, and a space point with no truth link at all
#: is not primary.
FIELDS = (
    "sp_x", "sp_y", "sp_z", "sp_primary",
    "pt", "eta", "phi", "d0", "z0", "prod_r", "prod_z", "primary", "num_hits",
)


class Sample:
    """Flat, per-event-concatenated arrays of one sample."""

    def __init__(self) -> None:
        self.num_events = 0
        self._parts: dict[str, list[np.ndarray]] = {f: [] for f in FIELDS}
        for field in FIELDS:
            setattr(self, field, np.empty(0))

    def add_event(self, **arrays: np.ndarray) -> None:
        """Append one event.

        The space point and the particle arrays have different lengths, which is
        why each field is concatenated on its own.

        @param arrays one array per entry of `FIELDS`
        """
        if set(arrays) != set(FIELDS):
            raise KeyError("expected exactly %s, got %s"
                           % (sorted(FIELDS), sorted(arrays)))
        for field, values in arrays.items():
            self._parts[field].append(np.asarray(values))
        self.num_events += 1

    def finish(self) -> "Sample":
        """Concatenate the events added so far.
        @return self, with every field a single array
        """
        for field, parts in self._parts.items():
            if parts:
                setattr(self, field, np.concatenate(parts))
        return self


def perigee(vx, vy, vz, px, py, pz, charge, b_field_t: float = 2.0):
    """Transverse and longitudinal impact parameters of a helix.

    This is the same perigee `ActsFatras::Synthetic` reports, so that the two
    sides of the comparison mean the same thing, and both full-simulation
    loaders go through here so the two detectors do too.

    It used to be the straight-line expression, on the grounds that a production
    point this close to the beam line makes the curvature correction negligible.
    That is true of primaries, which are produced at a few tens of microns, and
    false of secondaries, which are produced out at the layers - and the |d0|
    comparison is entirely about secondaries. A daughter made at r = 100 mm with
    400 MeV of pT curls with a radius of 670 mm, so the two definitions differ by
    about r^2 / 2 rho = 7 mm, which is wider than the band structure being
    compared. Against the generator's helix perigee that left the model looking
    short of small-|d0| secondaries by a factor of ten, all of it definition.

    @param vx the production point x in mm
    @param vy the production point y in mm
    @param vz the production point z in mm
    @param px the momentum x in GeV
    @param py the momentum y in GeV
    @param pz the momentum z in GeV
    @param charge the charge sign
    @param b_field_t the solenoid field in Tesla
    @return (phi, d0, z0), in rad and mm
    """
    phi = np.arctan2(py, px)
    pt = np.hypot(px, py)
    charge = np.sign(np.asarray(charge, dtype=float))
    with np.errstate(divide="ignore", invalid="ignore"):
        # radius of curvature in mm for a pT in GeV, i.e. pT / (0.3 B)
        rho = pt * 1000.0 / (0.3 * b_field_t)

        # The centre of the circle sits one radius of curvature to the side of
        # the momentum, on the side the charge bends towards; the impact
        # parameter is how much closer to the beam axis than that the track
        # comes. Same expressions as `makeHelixFromPoint`.
        cx = vx + charge * rho * np.sin(phi)
        cy = vy - charge * rho * np.cos(phi)
        r_centre = np.hypot(cx, cy)
        d0 = charge * (rho - r_centre)

        # Walk back along the arc to the point of closest approach. The turning
        # angle follows from sin^2(gamma/2) = (r^2 - d0^2) / (4 rCentre rho),
        # signed by whether the production point is ahead of the perigee or
        # behind it, which is what the straight-line form got from the sign of
        # the longitudinal distance.
        r = np.hypot(vx, vy)
        half_sin_squared = np.clip(
            (r * r - d0 * d0) / (4.0 * r_centre * rho), 0.0, 1.0)
        gamma = 2.0 * np.arcsin(np.sqrt(half_sin_squared))
        ahead = np.sign(vx * np.cos(phi) + vy * np.sin(phi))
        z0 = vz - ahead * gamma * rho * pz / pt
    return phi, d0, z0
