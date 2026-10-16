"""Install observational wrappers after normal G4 setup and ID confinement."""
import sys,runpy,json
from pathlib import Path
import argparse
parser=argparse.ArgumentParser(add_help=False)
parser.add_argument('--observer-module',type=Path,required=True)
a,rest=parser.parse_known_args()
sys.path.insert(0,str(a.observer_module))
sys.argv=[sys.argv[0],*rest]
tools=Path.home()/'cern/scripts/acts'
sys.path.insert(0,str(tools/'fatras-charged-mesons/data/2026-10-14'))
import id_world,gap_observer
confine=id_world.confine
out=Path(sys.argv[sys.argv.index('--output')+1])
def install(*args):
 result=confine(*args)
 gap_observer.install(str(out/'observer.tsv'))
 return result
id_world.confine=install
runpy.run_path(str(tools/'fatras-runtime-model/run.py'),run_name='__main__')
gap_observer.flush()

meta=out/'metadata.json'
data=json.loads(meta.read_text())
data['observer']={'module':str(a.observer_module/'gap_observer.so'),'scope':'Read-only callback forwarding; exact reference CSV replay checked separately'}
if (Path(sys.argv[sys.argv.index('--input')+1])/'probes.json').exists():
 data['pileup']=None
 data['sample']='2400 controlled ODD pixel electron probes; 240 per energy/origin combination'
meta.write_text(json.dumps(data,indent=2))
