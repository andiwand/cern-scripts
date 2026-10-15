"""Validation bridge for soft physics; optional bounded-navigation experiment.
Uses the recorded d25514208b build ABI. No production monkey-patching.
"""

import argparse, json, subprocess, sys
from pathlib import Path

p = argparse.ArgumentParser(add_help=False)
p.add_argument(
    "--ion-cut",
    type=float,
    default=0.0001,
    help="Electron kinetic production cut in GeV; inf retains legacy loss",
)
p.add_argument("--photon-cut", type=float, default=0.0010219979)
p.add_argument(
    "--legacy-decays",
    action="store_true",
    help="Use ca045e1435 native decay for ablation",
)
p.add_argument("--prepare-only", action="store_true")
p.add_argument("--tools-root", type=Path, default=Path.home() / "cern/scripts/acts")
a, rest = p.parse_known_args()
source = Path(rest[rest.index("--source") + 1])
output = Path(rest[rest.index("--output") + 1])
output.mkdir(parents=True, exist_ok=True)
script = (a.tools_root / "fatras-runtime-model/build-bridge.py").read_text()
cut = (
    repr(a.ion_cut)
    if a.ion_cut != float("inf")
    else "std::numeric_limits<double>::infinity()"
)
field = "    std::shared_ptr<const ActsFatras::NuclearInteractionModel> nuclearInteractionModel;"
assert field in script
script = script.replace(
    field,
    field
    + f"\n    double emIonisationSecondaryMinEnergy = {cut};\n    double photonPMin = {a.photon_cut};",
)
extra = [
    source / "Fatras/src/Physics/Ionisation.cpp",
    source / "Fatras/src/Physics/NativeDecay.cpp",
]
override = output.parent / ("legacy-" + output.name)
if a.legacy_decays:
    header = override / "ActsFatras/Physics/Decay/NativeDecay.hpp"
    header.parent.mkdir(parents=True, exist_ok=True)
    for dest, path in [
        (header, "Fatras/include/ActsFatras/Physics/Decay/NativeDecay.hpp"),
        (override / "NativeDecay.cpp", "Fatras/src/Physics/NativeDecay.cpp"),
    ]:
        dest.write_text(
            subprocess.check_output(
                ["git", "-C", str(source), "show", "ca045e1435:" + path], text=True
            )
        )
    extra[-1] = override / "NativeDecay.cpp"
# Compile the changed out-of-line physics; do not silently use installed symbols.
script = script.replace(
    "sources = [", "sources = " + repr([str(x) for x in extra]) + " + ["
)
script = script.replace("libs = (", "sources = list(map(Path,sources))\nlibs = (")
if a.legacy_decays:
    script = script.replace(
        "args += [", "args[1:1] = [" + repr("-I" + str(override)) + "]\nargs += ["
    )
if a.prepare_only:
    script = script.replace(
        "subprocess.run(cmd, check=True)",
        "pass # compile via bounded-navigation builder",
    )
(output / "bridge-builder.py").write_text(script)
sys.argv = [str(output / "bridge-builder.py"), *rest]
exec(
    compile(script, str(output / "bridge-builder.py"), "exec"), {"__name__": "__main__"}
)
(output / "soft-physics.json").write_text(
    json.dumps(
        {
            "ionisation_cut_GeV": a.ion_cut if a.ion_cut != float("inf") else None,
            "photon_cut_GeV": a.photon_cut,
            "legacy_decays": a.legacy_decays,
            "source": str(source),
        },
        indent=2,
    )
)
