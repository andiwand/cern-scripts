"""Matched-input numerical transport sensitivities; physics and G4 unchanged."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--output',type=Path,required=True)
p.add_argument('--tools-root',type=Path,default=Path.home()/'cern/scripts/acts')
p.add_argument('--module',type=Path,required=True)
p.add_argument('--source',type=Path,required=True)
p.add_argument('--variant', nargs=3, action='append', metavar=('NAME','STEP_MM','TURNS'))
a = p.parse_args()
a.output.mkdir(parents=True,exist_ok=True)
revision = subprocess.check_output(['git','-C',str(a.source),'rev-parse','HEAD'],text=True).strip()
for name, step, loops in a.variant or [('loops8',5,8), ('step2p5',2.5,4)]:
    dest=a.output/name
    if dest.exists():
        raise RuntimeError(f'Refusing to overwrite {dest}')
    cmd=[str(a.tools_root/'fatras-neutral-hadrons/odd/run-env.sh'),str(a.tools_root/'fatras-low-momentum/run.py'),
         '--mode','live','--source',str(a.source),'--revision',revision,
         '--build',str(Path.home()/'cern/build/acts/acts/dev3'),
         '--input',str(a.tools_root/'fatras-runtime-model/results/2026-10-15/inputs'),
         '--output',str(dest),'--module-dir',str(a.module),'--events','3','--threads','1',
         '--material-map',str(a.tools_root/'fatras-pion-validation/data/2026-10-14/odd-material-beampipe.root'),
         '--navigation-mode','2','--navigation-step',str(step),'--max-steps','50000','--loops',str(loops),
         '--p-min','0.0002','--pt-min','0.00005']
    dest.with_suffix('.command.json').write_text(json.dumps(cmd,indent=2))
    with dest.with_suffix('.log').open('w') as log:
        subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True)
    path=dest/'metadata.json'
    meta=json.loads(path.read_text())
    meta['transport_experiment']=json.loads((a.module/'experiment-build.json').read_text())
    meta['module_sha256']=hashlib.sha256((a.module/'runtime_fatras.so').read_bytes()).hexdigest()
    meta['soft_physics']={'ionisation_cut_GeV':.0001,'photon_cut_GeV':.0010219979,'legacy_decays':False}
    path.write_text(json.dumps(meta,indent=2))
    print(name,meta['sequencer_cpu_seconds']/3,flush=True)
