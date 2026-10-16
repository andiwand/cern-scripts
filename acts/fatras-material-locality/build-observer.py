import json,shlex,subprocess
from pathlib import Path
import argparse
p=argparse.ArgumentParser(description='Build observational G4 callback module')
p.add_argument('--output',type=Path,required=True)
a=p.parse_args()
root=a.output
root.mkdir(parents=True,exist_ok=True)
build=Path.home()/'cern/build/acts/acts/dev3'
e=next(e for e in json.loads((build/'compile_commands.json').read_text()) if e['file'].endswith('/plugins/Geant4.cpp'))
f=shlex.split(e['command']);args=[];i=0
while i<len(f):
 if f[i] in ['-o','-c']:i+=2;continue
 if f[i].startswith('-DActsExamplesPythonBindingsGeant4_EXPORTS'):i+=1;continue
 args.append(f[i]);i+=1
lib=Path.home()/'cern/source/acts/ci-dependencies/.spack-env/view/lib'
cmd=args+[str(Path(__file__).with_name('observer.cpp')),'-shared','-undefined','dynamic_lookup','-o',str(root/'gap_observer.so')]+[str(x) for x in lib.glob('libG4*.dylib')]+['-Wl,-rpath,'+str(lib)]
(root/'observer-build.json').write_text(json.dumps(cmd,indent=2))
subprocess.run(cmd,cwd=e['directory'],check=True)
