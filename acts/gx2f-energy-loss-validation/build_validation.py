#!/usr/bin/env python3
import argparse, json, pathlib, shlex, subprocess
p=argparse.ArgumentParser(); p.add_argument('--build',required=True); p.add_argument('--source',default='validation.cpp'); a=p.parse_args()
build=pathlib.Path(a.build).resolve(); here=pathlib.Path(__file__).resolve().parent
entry=next(e for e in json.loads((build/'compile_commands.json').read_text()) if e['file'].endswith('/Gx2fTests.cpp'))
args=shlex.split(entry['command']); i=args.index('-o'); del args[i:i+2]; args.remove('-c'); args.remove(entry['file'])
args=[a for a in args if not a.startswith('-DBOOST')]
args += [str(here/a.source),'-L'+str(build/'lib'),'-lActsCore','-lActsTestsCommonHelpers','-Wl,-rpath,'+str(build/'lib'),'-o',str(here/pathlib.Path(a.source).stem)]
(here/'compile-command.txt').write_text(shlex.join(args)+'\n')
subprocess.run(args,check=True)
