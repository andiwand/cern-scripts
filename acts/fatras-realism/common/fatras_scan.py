#!/usr/bin/env python3
"""Build and run a synthetic Fatras cut/CPU scan using an existing ACTS build.

Four-layer silicon test geometry, 2 T, eight primaries per event (log-uniform
0.1-10 GeV, |eta|<1). Variants (each compiles scan/<variant>.cpp):

  em        EM interactions; --compare-ref adds a build with historical Fatras headers
  hadronic  EM-only vs. table-driven hadronic interactions (--table required)
  decays    native decays disabled vs. enabled (optional --table, --v0-only)

Cuts are in GeV. The output directory must not exist.
"""

import argparse
import hashlib
import json
import platform
from pathlib import Path
import random
import subprocess

import acts_compile
import paths

HERE = Path(__file__).resolve().parent
LIMITATIONS = {
    "em": "Synthetic four-layer geometry; EM only; wall time of transport calls; no Geant4 comparison; historical comparison substitutes Fatras headers only.",
    "hadronic": "Synthetic four-layer geometry; EM vs table-driven hadronic model; wall time of transport calls; no full-detector Geant4 comparison.",
    "decays": "Synthetic four-layer geometry; native decays disabled/enabled, same material physics in both; wall time of transport calls; no full-detector Geant4 comparison.",
}


def git(source, *args):
    return subprocess.check_output(["git", "-C", str(source), *args], text=True)


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--variant", choices=LIMITATIONS, default="em")
    parser.add_argument("--source", type=Path, default=paths.SOURCE)
    parser.add_argument("--build", type=Path, default=paths.BUILD)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--events", type=int, default=1000)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--cuts", type=float, nargs="+", default=[0.05, 0.1, 0.5])
    parser.add_argument("--pt-cuts", type=float, nargs="+", default=[0.0])
    parser.add_argument("--first-event", type=int, default=0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--table", type=Path, help="Hadronic interaction table")
    parser.add_argument("--v0-only", action="store_true", help="decays: K-short/Lambda only")
    parser.add_argument(
        "--compare-ref",
        help="em: also build with Fatras headers from this git ref; libraries stay at the built revision",
    )
    args = parser.parse_args()
    if args.variant == "hadronic" and args.table is None:
        parser.error("--table is required for the hadronic variant")
    args.source = args.source.resolve()
    args.build = args.build.resolve()
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=False)
    source = HERE / "scan" / f"{args.variant}.cpp"
    (args.output / "scan.cpp").write_bytes(source.read_bytes())
    table = [str(args.table.resolve())] if args.table else []

    selection = ["-DFATRAS_TRANSPORT_SELECTION"]
    if args.variant == "em":
        variants = {"current": selection}
    elif args.variant == "hadronic":
        variants = {"em_only": selection, "hadronic": selection}
    else:
        selection += ["-DV0_ONLY"] if args.v0_only else []
        variants = {"disabled": selection, "native": selection}
    revision = None
    if args.compare_ref:
        if args.variant != "em":
            parser.error("--compare-ref is only supported for the em variant")
        revision = git(args.source, "rev-parse", args.compare_ref).strip()
        overlay = args.output / "baseline-headers"
        for name in git(
            args.source, "ls-tree", "-r", "--name-only", revision, "--", "Fatras/include"
        ).splitlines():
            path = overlay / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(
                subprocess.check_output(
                    ["git", "-C", str(args.source), "show", f"{revision}:{name}"]
                )
            )
        variants["baseline_headers"] = ["-I" + str(overlay / "Fatras/include")]

    def run_arguments(variant):
        if args.variant == "hadronic":
            return table if variant == "hadronic" else []
        if args.variant == "decays":
            return [str(int(variant == "native")), *table]
        return []

    libraries = ["ActsTestsCommonHelpers", "ActsFatras", "ActsCore"]
    build_commands = {}
    for variant, extra in variants.items():
        build_commands[variant] = acts_compile.build(
            build=args.build,
            template="fatras-test",
            sources=[source],
            output=args.output / variant,
            acts=libraries,
            extra=extra,
            log=args.output / f"{variant}-build.log",
        )
    runs = [
        (v, cut, ptcut, repeat)
        for v in variants
        for cut in args.cuts
        for ptcut in args.pt_cuts
        if v != "baseline_headers" or ptcut == 0
        for repeat in range(args.repeats)
    ]
    random.Random(17).shuffle(runs)
    results = []
    for variant, cut, ptcut, repeat in runs:
        print(f"{variant}: pMin={cut}, pTMin={ptcut}, repetition={repeat + 1}", flush=True)
        completed = subprocess.run(
            [
                str(args.output / variant),
                str(args.events),
                str(cut),
                str(args.seed),
                str(args.first_event),
                str(ptcut),
                *run_arguments(variant),
            ],
            text=True,
            capture_output=True,
            check=True,
        )
        (args.output / f"{variant}-{cut}-{ptcut}-{repeat}.log").write_text(completed.stderr)
        results.append(dict(json.loads(completed.stdout), variant=variant, repetition=repeat))
        (args.output / "results.json").write_text(json.dumps(results, indent=2) + "\n")
    (args.output / "acts.patch").write_text(git(args.source, "diff", "HEAD"))
    used = acts_compile.acts_libraries(args.build, libraries)
    metadata = {
        "variant": args.variant,
        "parameters": {
            "events": args.events,
            "first_event": args.first_event,
            "seed": args.seed,
            "repeats": args.repeats,
            "p_cuts_GeV": args.cuts,
            "pt_cuts_GeV": args.pt_cuts,
            "v0_only": args.v0_only,
        },
        "source": str(args.source),
        "build": str(args.build),
        "platform": platform.platform(),
        "revision": git(args.source, "rev-parse", "HEAD").strip(),
        "baseline_header_revision": revision,
        "build_commands": build_commands,
        "libraries_sha256": {p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in used},
        "scan_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "table": table[0] if table else None,
        "table_sha256": hashlib.sha256(args.table.read_bytes()).hexdigest() if table else None,
        "limitations": LIMITATIONS[args.variant]
        + " Production and process-level cuts are not counted as rejected inputs.",
    }
    (args.output / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")


if __name__ == "__main__":
    main()
