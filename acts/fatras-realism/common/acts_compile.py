#!/usr/bin/env python3
"""Compile a standalone C++ file with the flags of an existing ACTS build.

The compiler command of a template translation unit is taken from
compile_commands.json (dropping -o/-c and unit-specific defines), then the
given sources are compiled and linked against ACTS (and optionally Geant4).

  acts_compile.py --template fatras-test --output check check.cpp
  acts_compile.py --template geant4-plugin --shared --geant4 run geometry global \
      --output id_world.so g4/id-world.cpp
"""

import argparse
import hashlib
import json
import shlex
import subprocess
from pathlib import Path

import paths

# Template translation unit and the flag prefixes that must not be reused.
TEMPLATES = {
    "fatras-test": ("/FatrasSimulationTests.cpp", ("-DBOOST",)),
    "geant4-test": ("/Geant4DecayTests.cpp", ("-DBOOST_TEST", "-g")),
    "geant4-plugin": ("/plugins/Geant4.cpp", ("-DActsExamplesPythonBindingsGeant4_EXPORTS",)),
    "examples": ("/ExampleAlgorithms.cpp", ("-g",)),
}


def configured_source(build):
    """Source directory the build was configured with."""
    for line in (build / "CMakeCache.txt").read_text().splitlines():
        if line.startswith("CMAKE_HOME_DIRECTORY:"):
            return line.split("=", 1)[1]
    raise RuntimeError(f"No CMAKE_HOME_DIRECTORY in {build}/CMakeCache.txt")


def compile_flags(build, template, source=None):
    """Return (flags, directory); flags[0] is the compiler.

    With `source`, the configured source path is replaced so headers come
    from that checkout instead of the one the build was configured with.
    """
    suffix, drop = TEMPLATES[template]
    entry = next(
        e
        for e in json.loads((build / "compile_commands.json").read_text())
        if e["file"].endswith(suffix)
    )
    old = configured_source(build) if source else None
    words = shlex.split(entry["command"])
    flags = []
    i = 0
    while i < len(words):
        if words[i] in ("-o", "-c"):
            i += 2
            continue
        if words[i] in drop or any(
            words[i].startswith(d) for d in drop if d.startswith("-D")
        ):
            i += 1
            continue
        flags.append(words[i].replace(old, str(source)) if old else words[i])
        i += 1
    return flags, entry["directory"]


def acts_libraries(build, names):
    out = []
    for name in names:
        found = sorted(
            p
            for p in (build / "lib").glob(f"lib{name}.*")
            if p.suffix in (".dylib", ".so", ".a")
        )
        if not found:
            raise FileNotFoundError(f"lib{name} in {build / 'lib'}")
        out.append(str(found[0]))
    return out


def geant4_libraries(lib, names=None, clhep=False):
    """All libG4*.dylib in `lib`, or only the named components."""
    if names:
        out = [str(lib / f"libG4{n}.dylib") for n in names]
    else:
        out = sorted(str(x) for x in lib.glob("libG4*.dylib"))
    if clhep:
        out.append(str(lib / "libCLHEP.dylib"))
    return out


def command(
    build,
    template,
    sources,
    output,
    acts=("ActsFatras", "ActsCore"),
    geant4_lib=None,
    geant4=None,
    clhep=False,
    shared=False,
    source=None,
    extra=(),
):
    flags, directory = compile_flags(build, template, source)
    cmd = [flags[0], *extra, *flags[1:], *map(str, sources)]
    if shared:
        cmd += ["-shared", "-undefined", "dynamic_lookup"]
    cmd += ["-o", str(output), *acts_libraries(build, acts)]
    if geant4_lib is not None:
        cmd += geant4_libraries(geant4_lib, geant4, clhep)
    cmd += ["-Wl,-rpath," + str(build / "lib")]
    if geant4_lib is not None:
        cmd += ["-Wl,-rpath," + str(geant4_lib)]
    return cmd, directory


def build(record=None, log=None, **kwargs):
    """Compile; optionally write the command and source hashes to `record`."""
    cmd, directory = command(**kwargs)
    if record:
        Path(record).write_text(
            json.dumps(
                {
                    "command": cmd,
                    "source_sha256": {
                        str(s): hashlib.sha256(Path(s).read_bytes()).hexdigest()
                        for s in kwargs["sources"]
                    },
                },
                indent=2,
            )
        )
    if log:
        with open(log, "w") as stream:
            subprocess.run(
                cmd, cwd=directory, stdout=stream, stderr=subprocess.STDOUT, check=True
            )
    else:
        subprocess.run(cmd, cwd=directory, check=True)
    return cmd


def main():
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("sources", type=Path, nargs="+")
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--template", choices=TEMPLATES, default="fatras-test")
    p.add_argument("--build", type=Path, default=paths.BUILD)
    p.add_argument("--source", type=Path, help="Replace the configured source path")
    p.add_argument("--acts", nargs="*", default=["ActsFatras", "ActsCore"])
    p.add_argument("--geant4-lib", type=Path, help="Link Geant4 from this directory")
    p.add_argument("--geant4", nargs="*", help="Geant4 components (default: all)")
    p.add_argument("--clhep", action="store_true")
    p.add_argument("--shared", action="store_true", help="Python extension module")
    p.add_argument("--record", type=Path, help="Write command and source hashes")
    a = p.parse_args()
    if a.geant4 is not None and a.geant4_lib is None:
        a.geant4_lib = paths.GEANT4_LIB
    build(
        record=a.record,
        build=a.build,
        template=a.template,
        sources=[s.resolve() for s in a.sources],
        output=a.output.resolve(),
        acts=a.acts,
        geant4_lib=a.geant4_lib,
        geant4=a.geant4 or None,
        clhep=a.clhep,
        shared=a.shared,
        source=a.source,
    )


if __name__ == "__main__":
    main()
