"""Electron starts at a physical pixel sensor or its mapped material cylinder."""
import csv,json,math
from pathlib import Path
import numpy as np
import argparse
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--work',type=Path,required=True)
args=parser.parse_args()
root=args.work
root.mkdir(parents=True,exist_ok=True)
surfaces=json.loads((root/'surfaces.json').read_text())['entries']
sensor=min((x for x in surfaces if x['volume']==17 and x['layer']==2),key=lambda x: abs(x['value']['transform']['translation'][2])+abs(x['value']['transform']['translation'][1]))
v=sensor['value'];pos=np.array(v['transform']['translation']);rot=np.array(v['transform']['rotation']).reshape(3,3)
normal=rot[:,2];tangent=rot[:,0];longitudinal=rot[:,1]
assert normal[:2]@pos[:2]>0
rows=[];config=[]
for ke in [.1,.3,1,3,10]:
 for origin in ['sensor','mapped-cylinder']:
  for iz,zfrac in enumerate([0.,.5,-.5]):
   for phi in np.arange(8)*math.pi/4:
    direction=math.sqrt(1-zfrac*zfrac)*(math.cos(phi)*normal+math.sin(phi)*tangent)+zfrac*longitudinal
    for replica in range(10):
     birth=pos+(replica-4.5)*.05*tangent+.001*normal
     if origin=='mapped-cylinder':birth[:2]*=39.36/np.linalg.norm(birth[:2])
     momentum=math.sqrt(ke*(ke+2*.510998950))/1000*direction
     ident=len(rows)+1
     rows.append([1,0,ident,0,0,11,0,*birth,0,*momentum,.000510998950,-1])
     config.append({'particle':ident,'kinetic_MeV':ke,'origin':origin,'z_fraction':zfrac,'phi':float(phi),'replica':replica})
folder=root/'probe-input';folder.mkdir(exist_ok=True)
with (folder/'event000000000-particles.csv').open('w') as f:
 w=csv.writer(f,lineterminator='\n');w.writerow('particle_id_pv,particle_id_sv,particle_id_part,particle_id_gen,particle_id_subpart,particle_type,process,vx,vy,vz,vt,px,py,pz,m,q'.split(','));w.writerows(rows)
(folder/'probes.json').write_text(json.dumps({'sensor':sensor,'mapped_radius_mm':39.36,'particles':config},indent=2))
print(len(rows),pos,normal)
