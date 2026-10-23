#!/usr/bin/env python3
"""Build and run a synthetic Fatras cut/CPU scan using an existing ACTS build."""
import argparse
import hashlib
import json
import platform
from pathlib import Path
import random
import shlex
import subprocess


def command(args, **kwargs):
    return subprocess.check_output(args, text=True, **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--events', type=int, default=1000)
    parser.add_argument('--repeats', type=int, default=3)
    parser.add_argument('--cuts', type=float, nargs='+', default=[0.05, 0.1, 0.5])
    parser.add_argument('--pt-cuts', type=float, nargs='+', default=[0.0])
    parser.add_argument('--first-event', type=int, default=0)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--table', type=Path)
    parser.add_argument('--v0-only', action='store_true')
    args = parser.parse_args()
    args.source = args.source.resolve()
    args.build = args.build.resolve()
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=False)
    source = Path(__file__).with_name('scan.cpp').resolve()
    (args.output / 'scan.cpp').write_bytes(source.read_bytes())
    (args.output / 'scan.py').write_bytes(Path(__file__).read_bytes())
    entries = json.loads((args.build / 'compile_commands.json').read_text())
    entry = next(e for e in entries if e['file'].endswith('/FatrasSimulationTests.cpp'))
    flags = shlex.split(entry['command'])
    compile_flags = []
    i = 0
    while i < len(flags):
        if flags[i] in ('-o', '-c'):
            i += 2
            continue
        if flags[i].startswith('-DBOOST'):
            i += 1
            continue
        compile_flags.append(flags[i])
        i += 1
    libraries = []
    for name in ('ActsTestsCommonHelpers', 'ActsFatras', 'ActsCore'):
        candidates = [p for p in (args.build / 'lib').glob(f'lib{name}.*') if p.suffix in ('.dylib', '.so', '.a')]
        libraries.append(str(sorted(candidates)[0]))
    flags_extra = ['-DFATRAS_TRANSPORT_SELECTION'] + (['-DV0_ONLY'] if args.v0_only else [])
    variants = {'disabled': flags_extra, 'native': flags_extra}
    revision = None
    build_commands = {}
    for variant, includes in variants.items():
        executable = args.output / variant
        invocation = [compile_flags[0], *includes, *compile_flags[1:], str(source), '-o', str(executable),
                      *libraries, '-Wl,-rpath,' + str(args.build / 'lib')]
        build_commands[variant] = invocation
        with (args.output / f'{variant}-build.log').open('w') as log:
            subprocess.run(invocation, cwd=entry['directory'], stdout=log, stderr=subprocess.STDOUT, check=True)
    runs = [(v, cut, ptcut, repeat) for v in variants for cut in args.cuts
            for ptcut in args.pt_cuts
            for repeat in range(args.repeats)]
    random.Random(17).shuffle(runs)
    results = []
    for variant, cut, ptcut, repeat in runs:
        print(f'{variant}: pMin={cut}, pTMin={ptcut}, repetition={repeat + 1}', flush=True)
        completed = subprocess.run([str(args.output / variant), str(args.events), str(cut), str(args.seed), str(args.first_event), str(ptcut), str(int(variant == "native")),
                                    *([str(args.table.resolve())] if args.table else [])],
                                   text=True, capture_output=True, check=True)
        (args.output / f'{variant}-{cut}-{ptcut}-{repeat}.log').write_text(completed.stderr)
        row = json.loads(completed.stdout)
        results.append(dict(row, variant=variant, repetition=repeat))
        (args.output / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
    patch = command(['git', 'diff', 'HEAD'], cwd=args.source)
    (args.output / 'fatras.patch').write_text(patch)
    metadata = {
        'parameters': {'events': args.events, 'first_event': args.first_event,
                       'seed': args.seed, 'repeats': args.repeats, 'v0_only': args.v0_only,
                       'p_cuts_GeV': args.cuts, 'pt_cuts_GeV': args.pt_cuts},
        'source': str(args.source), 'build': str(args.build), 'platform': platform.platform(),
        'revision': command(['git', 'rev-parse', 'HEAD'], cwd=args.source).strip(),
        'table': str(args.table.resolve()) if args.table else None,
        'table_sha256': hashlib.sha256(args.table.read_bytes()).hexdigest() if args.table else None, 'build_commands': build_commands,
        'libraries_sha256': {p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in libraries},
        'scan_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'limitations': 'Synthetic four-layer geometry; native decays disabled/enabled, same material physics in both; wall time of transport calls; no full-detector Geant4 comparison. Production and process-level cuts are not counted as rejected inputs.',
    }
    (args.output / 'metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')


if __name__ == '__main__':
    main()
