"""The synthetic detectors and configurations that ship with Fatras, as files.

A detector is three JSON files under `Fatras/data` that share a prefix: the
description (where its layers are), the material (what they are made of) and the
configuration fitted to it. `ActsFatras::Synthetic` no longer holds any of them
in C++, so every script here reads and writes them through this module rather
than through a preset function that no longer exists.

It also carries the *flat* field names the fitting scripts talk in --
`secondaryElectronRate` rather than
`simulation.secondaries.electronRate`. `EventConfig` is nested, the fit's search
is not, and one mapping in one place is better than the nesting spread over a
thousand lines of scoring code.
"""

from __future__ import annotations

import os
from pathlib import Path

from acts.fatras import synthetic as syn

#: The detectors that ship, and what a script may be asked for by name.
DETECTORS = ("itk", "odd", "generic-pixel")


def data_dir() -> Path:
    """Where the shipped files are.

    `ACTS_FATRAS_DATA_DIR` overrides it, which is how a script is pointed at a
    working copy of the files rather than at the ones in the source tree.

    @return the directory
    """
    override = os.environ.get("ACTS_FATRAS_DATA_DIR")
    if override:
        return Path(override)
    # the bindings know where the library was built or installed from
    return Path(syn.dataPath("generic-pixel-description.json")).parent


def path(detector: str, suffix: str) -> Path:
    """One of a detector's files.

    @param detector the detector, or a path prefix its files share
    @param suffix which file, e.g. `-description.json`
    @return the path
    """
    given = Path(detector)
    if given.parent != Path("."):
        return given.parent / (given.name + suffix)
    return data_dir() / (detector + suffix)


def description(detector: str, *, material: bool = True,
                sensors: bool = True):
    """A shipped detector, read as a description.

    @param detector the detector, or a path prefix its files share
    @param material whether to decorate it with the material file beside it
    @param sensors whether to decorate it with the sensor file beside it, where
           there is one; a detector of nothing but pixels ships without
    @return the description
    """
    out = syn.readDetectorDescription(str(path(detector, "-description.json")))
    if material:
        syn.decorate(out, syn.readMaterialDecoration(
            str(path(detector, "-material.json"))))
    if sensors and path(detector, "-sensors.json").exists():
        syn.decorate(out, syn.readSensorDecoration(
            str(path(detector, "-sensors.json"))))
    return out


def layout(detector: str, *, subsystems=None):
    """A shipped detector, expanded into the layout the generator runs on.

    @param detector the detector, or a path prefix its files share
    @param subsystems which of its subsystems to keep, None for all of them
    @return the layout
    """
    out = description(detector)
    if subsystems:
        out = syn.selectSubsystems(out, list(subsystems))
    return syn.makeLayout(out)


def config(detector: str):
    """The configuration fitted to a shipped detector.

    @param detector the detector, or a path prefix its files share
    @return the configuration
    """
    return syn.readEventConfig(str(path(detector, "-ttbar-pu200.json")))


def write_description(detector: str, value, *, split: bool = True) -> list:
    """Write a description out as the files a detector ships as.

    @param detector the detector, or a path prefix to write to
    @param value the description
    @param split whether to put the material and the sensors in their own
           files, which is how they ship; False leaves them in the description
    @return the paths written
    """
    syn.assignLayerIndices(value)
    written = []
    if split:
        # `stripMaterial` and `clearSensors` work in place, so the description
        # handed in is left holding only its geometry -- deliberate, the two
        # decorations having been taken off it a line earlier.
        decoration = syn.extractMaterial(value)
        syn.stripMaterial(value)
        material = path(detector, "-material.json")
        syn.writeMaterialDecoration(str(material), decoration)
        written.append(material)

        readout = syn.extractSensors(value)
        syn.clearSensors(value)
        if readout:
            sensors = path(detector, "-sensors.json")
            syn.writeSensorDecoration(str(sensors), readout)
            written.append(sensors)
    where = path(detector, "-description.json")
    syn.writeDetectorDescription(str(where), value)
    written.append(where)
    return written


def write_config(detector: str, value) -> Path:
    """Write a configuration out as the file a detector ships with.

    @param detector the detector, or a path prefix to write to
    @param value the configuration
    @return the path written
    """
    where = path(detector, "-ttbar-pu200.json")
    syn.writeEventConfig(str(where), value)
    return where


#: Every field of `EventConfig`, by the flat name the fitting scripts use, as the
#: path to it. The nesting is real -- a fitted number belongs to the generation,
#: the material or the secondaries -- but a search over it wants one name per
#: knob.
FIELDS = {
    # what the collisions make
    "pileup": ("generation", "pileup"),
    "chargedPerUnitRapidity": ("generation", "chargedPerUnitRapidity"),
    "minPt": ("generation", "minPt"),
    "ptScale": ("generation", "ptScale"),
    "ptExponent": ("generation", "ptExponent"),
    "minRapidity": ("generation", "minRapidity"),
    "maxRapidity": ("generation", "maxRapidity"),
    "rapidityEdge": ("generation", "rapidityEdge"),
    "rapidityEdgeWidth": ("generation", "rapidityEdgeWidth"),
    "beamspotSigmaZ": ("generation", "beamspotSigmaZ"),
    "d0Sigma": ("generation", "d0Sigma"),
    # how far a track is followed
    "maxTurns": ("simulation", "propagation", "maxTurns"),
    "tracksPerPrimary": ("simulation", "propagation", "tracksPerPrimary"),
    "hitsPerPrimary": ("simulation", "propagation", "hitsPerPrimary"),
    "maxTracksPerPrimary": ("simulation", "propagation", "maxTracksPerPrimary"),
    # what the material it crosses does to it
    "maxDiscPathLength": ("simulation", "material", "maxDiscPathLength"),
    "maxCylinderPathLength": ("simulation", "material",
                              "maxCylinderPathLength"),
    "materialScale": ("simulation", "material", "scale"),
    "multipleScattering": ("simulation", "material", "multipleScattering"),
    "energyLoss": ("simulation", "material", "energyLoss"),
    "energyLossModel": ("simulation", "material", "energyLossModel"),
    "maxEnergyLossFraction": ("simulation", "material",
                              "maxEnergyLossFraction"),
    # what a sensitive crossing is read out as
    "positionSmearing": ("simulation", "measurement", "positionSmearing"),
    "overlapScale": ("simulation", "measurement", "overlapScale"),
    # how much a crossing produces
    "secondaryElectronRate": ("simulation", "secondaries", "electronRate"),
    "secondaryNuclearRate": ("simulation", "secondaries", "nuclearRate"),
    "decayYield": ("simulation", "secondaries", "decayYield"),
    "decayLength": ("simulation", "secondaries", "decayLength"),
    "stubRate": ("simulation", "secondaries", "stubRate"),
    "stubClusters": ("simulation", "secondaries", "stubClusters"),
    "stubReach": ("simulation", "secondaries", "stubReach"),
    "maxGenerations": ("simulation", "secondaries", "maxGenerations"),
    "maxPerCrossing": ("simulation", "secondaries", "maxPerCrossing"),
    # and what one of them comes out as
    "secondaryMinPt": ("simulation", "secondaries", "sampling", "minPt"),
    "secondaryElectronScale": ("simulation", "secondaries", "sampling",
                               "electronScale"),
    "secondaryElectronExponent": ("simulation", "secondaries", "sampling",
                                  "electronExponent"),
    "secondaryElectronSpread": ("simulation", "secondaries", "sampling",
                                "electronSpread"),
    "secondaryElectronKt": ("simulation", "secondaries", "sampling",
                            "electronKt"),
    "secondaryMomentumScale": ("simulation", "secondaries", "sampling",
                               "momentumScale"),
    "secondaryMomentumExponent": ("simulation", "secondaries", "sampling",
                                  "momentumExponent"),
    "secondaryMomentumSpread": ("simulation", "secondaries", "sampling",
                                "momentumSpread"),
    "secondaryKt": ("simulation", "secondaries", "sampling", "kt"),
    "secondaryEvaporationFraction": ("simulation", "secondaries", "sampling",
                                     "evaporationFraction"),
    "secondaryEvaporationScale": ("simulation", "secondaries", "sampling",
                                  "evaporationScale"),
    # the few both halves share
    "particlePdg": ("particlePdg",),
    "bFieldZ": ("bFieldZ",),
    "seed": ("seed",),
}


def get(config, name: str):
    """Read one field of a configuration by its flat name.

    @param config the configuration
    @param name the flat name, see `FIELDS`
    @return the value
    """
    node = config
    for step in FIELDS[name]:
        node = getattr(node, step)
    return node


def set(config, name: str, value) -> None:  # noqa: A001 - reads as `presets.set`
    """Write one field of a configuration by its flat name.

    The value is cast to whatever the field already holds: `pileup` and `seed`
    are integers and pybind11 refuses a float for them.

    @param config the configuration to change in place
    @param name the flat name, see `FIELDS`
    @param value the value
    """
    path_ = FIELDS[name]
    node = config
    for step in path_[:-1]:
        node = getattr(node, step)
    setattr(node, path_[-1], type(getattr(node, path_[-1]))(value))


def copy_with(config, values: dict):
    """A copy of a configuration with some fields replaced.

    `EventConfig` exposes no copy constructor, so every field is carried over by
    hand -- all of them, so that nothing is silently left at its default.

    @param config the configuration to copy
    @param values the flat names to override, and their values
    @return the copy
    """
    out = syn.EventConfig()
    for name in FIELDS:
        set(out, name, get(config, name))
    for name, value in values.items():
        if name not in FIELDS:
            raise KeyError("no such configuration field: %s" % name)
        set(out, name, value)
    return out


def layers(description):
    """Every described layer of a detector, with the identifier it answers to.

    The Python side of `walkLayers`: what material is keyed onto, so that a
    script matching measurements onto a description has the same names the
    decoration does. Layer indices are read as they stand, so a description that
    has not been through `assignLayerIndices` has to be numbered first --
    everything read from file already is.

    @param description the detector to walk
    @return pairs of `LayerId` and the layer itself
    """
    def identify(subsystem, kind, layer, placement=None):
        out = syn.LayerId()
        out.subsystem = subsystem
        out.kind = kind
        out.layer = layer.layer if layer.layer is not None else 0
        if placement is not None:
            out.placement = placement
        return out

    for passive in description.passives:
        yield identify("", syn.LayerKind.Passive, passive), passive
    for subsystem in description.subsystems:
        for passive in subsystem.passives:
            yield identify(subsystem.name, syn.LayerKind.Passive, passive), passive
        for barrel in subsystem.barrels:
            for cylinder in barrel.cylinders:
                yield (identify(subsystem.name, syn.LayerKind.Barrel, cylinder),
                       cylinder)
        for endcap in subsystem.endcaps:
            for disc in endcap.discs:
                yield (identify(subsystem.name, syn.LayerKind.Endcap, disc,
                                endcap.placement), disc)


def position(layer) -> float:
    """Where a described layer sits, whichever kind it is.

    @param layer a cylinder, a disc or a passive surface
    @return its radius or its absolute z
    """
    for name in ("radius", "absZ", "refCoord"):
        if hasattr(layer, name):
            return getattr(layer, name)
    raise TypeError("not a described layer: %r" % layer)
