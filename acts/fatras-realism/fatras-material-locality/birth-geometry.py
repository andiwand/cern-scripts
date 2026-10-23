"""Transverse reachability bound for ionisation births in the pixel-barrel envelope."""
import csv,gzip,json,math
from collections import Counter
from pathlib import Path
import numpy as np
import argparse
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--work',type=Path,required=True)
args=parser.parse_args()
root=args.work
root.mkdir(parents=True,exist_ok=True)
surfaces=json.loads((root/'surfaces.json').read_text())['entries']
segments={}
for s in surfaces:
 if s['volume']!=17:continue
 v=s['value'];r=np.array(v['transform']['rotation']).reshape(3,3);c=np.array(v['transform']['translation'])
 assert np.linalg.norm(r[:2,1])<1e-8 and abs(r[2,0])<1e-8
 bounds=v['bounds']['values'];assert v['bounds']['type']=='RectangleBounds'
 lo=c[:2]+bounds[0]*r[:2,0];hi=c[:2]+bounds[2]*r[:2,0]
 segments[tuple(np.round(np.r_[lo,hi],7))]=(lo,hi)
lo=np.array([x[0] for x in segments.values()]);hi=np.array([x[1] for x in segments.values()]);u=hi-lo;norm=(u*u).sum(axis=1)
paths={'Fatras':Path.home()/'cern/scripts/acts/fatras-realism/fatras-transport-performance/results/2026-10-16/pruned-check','Geant4':Path.home()/'cern/scripts/acts/fatras-realism/fatras-soft-secondaries/results/2026-10-15/geant4'}
out={'scope':'All retained ionisation electrons born at 25<r<190 mm, |z|<510 mm; geometry diagnostic only, not an occupancy selection. Pixel sensors projected into xy, longitudinal bounds ignored. d_xy > 2*r_L is a necessary-condition veto for vacuum uniform-field reachability, not a complete transport prediction.','segment_count':len(segments),'runs':{}}
for name,folder in paths.items():
 points=[]
 for ev in range(3):
  with gzip.open(folder/f'event{ev:09d}-particles_simulated.csv.gz','rt') as f:
   for row in csv.DictReader(f):
    if row['process']!='5' or row['particle_type']!='11':continue
    x,y,z=[float(row[k]) for k in ['vx','vy','vz']]
    if not (25<math.hypot(x,y)<190 and abs(z)<510):continue
    px,py,pz=[float(row[k]) for k in ['px','py','pz']];p2=px*px+py*py+pz*pz;m=float(row['m'])
    ke=p2/(math.sqrt(p2+m*m)+m)*1000
    points.append([x,y,math.hypot(px,py)*1000/(.299792458*2)*2,ke,ev])
 a=np.array(points);distance=[]
 for i in range(0,len(a),512):
  d=a[i:i+512,None,:2]-lo
  t=np.clip(np.einsum('bsi,si->bs',d,u)/norm,0,1)
  distance.extend(np.sqrt(((d-t[:,:,None]*u)**2).sum(axis=2).min(axis=1)).tolist())
 distance=np.array(distance);bins=[0,.1,.2,.423337527246,1,5,20,1e9];stats=[]
 for low,high in zip(bins,bins[1:]):
  mask=(a[:,3]>=low)&(a[:,3]<high);n=int(mask.sum())
  stats.append({'low_MeV':low,'high_MeV':high,'n':n,'median_dxy_mm':float(np.median(distance[mask])) if n else None,'dxy_gt_diameter':int((distance[mask]>a[mask,2]).sum())})
 out['runs'][name]={'n':len(a),'bins':stats,'median_dxy_mm':float(np.median(distance)),'dxy_gt_diameter':int((distance>a[:,2]).sum()),'distance_edges_mm':[0,.1,1,2,4,6,8,10,20,1000],'distance_counts':np.histogram(distance,[0,.1,1,2,4,6,8,10,20,1000])[0].tolist()}
 print(name,out['runs'][name],flush=True)
(root/'birth-geometry.json').write_text(json.dumps(out,indent=2))
