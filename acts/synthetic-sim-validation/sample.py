"""The set of distributions every sample in the comparison provides.

One `Sample` is one simulated sample - a full-simulation dump or a fast-simulation
event - reduced to the flat arrays the plots need. Keeping the shape in one place
is what lets `validate.py` treat a GNN4ITk dump, a ColliderML shard and the
generator's own CSV pair identically.
"""

from __future__ import annotations

import numpy as np

#: Space point positions in mm, then one entry per particle: transverse momentum
#: in GeV, the perigee parameters in mm and rad, the production vertex in mm,
#: whether the particle comes from the generator rather than from the detector
#: simulation, and how many space points it left.
FIELDS = (
    "sp_x", "sp_y", "sp_z",
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


def perigee(vx, vy, vz, px, py, pz):
    """Transverse and longitudinal impact parameters of a straight line.

    The synthetic generator reports the perigee parameters of the helix. For a
    production point this close to the beam line the curvature correction is far
    below the width of the distributions being compared, so the straight-line
    expressions are used. Both full-simulation loaders go through here, so the
    two detectors are compared against the same definition.

    @param vx the production point x in mm
    @param vy the production point y in mm
    @param vz the production point z in mm
    @param px the momentum x
    @param py the momentum y
    @param pz the momentum z
    @return (phi, d0, z0), in rad and mm
    """
    phi = np.arctan2(py, px)
    pt = np.hypot(px, py)
    # signed transverse distance of the production point from the beam axis,
    # measured perpendicular to the momentum
    d0 = vx * np.sin(phi) - vy * np.cos(phi)
    # walk back along the track to the point of closest approach
    longitudinal = vx * np.cos(phi) + vy * np.sin(phi)
    with np.errstate(divide="ignore", invalid="ignore"):
        z0 = vz - longitudinal * pz / pt
    return phi, d0, z0
