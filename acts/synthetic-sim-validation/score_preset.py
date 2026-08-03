#!/usr/bin/env python3
"""Score configurations against the cached reference, without fitting.

Used to decide whether a refit is actually better than the shipped preset it
would replace, rather than only different.

    ./score_preset.py itk <dump.root> "refit|secondaryRate=8.167,decayYield=0.270"
"""

import os
import sys

from acts.fatras import synthetic as syn

import fit_event_config as fit

DETECTOR = sys.argv[1]
DUMP = sys.argv[2] or None
EVENTS = int(os.environ.get("SCORE_EVENTS", "10"))
REFERENCE_EVENTS = int(os.environ.get("REFERENCE_EVENTS",
                                      "5" if DETECTOR == "itk" else "20"))
#: events the fit was given, which the validation must not reuse
SKIP_EVENTS = int(os.environ.get("SKIP_EVENTS", "0"))

description, target, _ = fit.reference(DETECTOR, fullsim=DUMP,
                                       events=REFERENCE_EVENTS,
                                       skip_events=SKIP_EVENTS)

# the description carries its own material now, measured off the geometry
base = (syn.EventConfig.itkPixelTtbarPu200 if DETECTOR == "itk"
        else syn.EventConfig.openDataDetectorTtbarPu200)

layout = syn.makeLayout(description)

cases = [("shipped, rates rescaled", {})]
for item in sys.argv[3:]:
    label, _, fields = item.partition("|")
    cases.append((label, dict(kv.split("=") for kv in fields.split(","))))

for label, overrides in cases:
    config = base()
    for name, value in overrides.items():
        setattr(config, name, type(getattr(config, name))(float(value)))
    print("== %s" % label)
    fit.report(config, layout, target, EVENTS)
    print()
