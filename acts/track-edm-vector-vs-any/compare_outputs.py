"""Compare all persisted CKF track/state values, not ROOT file metadata."""
import json,sys
from pathlib import Path
import awkward as ak
import numpy as np
import uproot
base=Path(sys.argv[1]);report={}
for variant in ['vector','any']:
 result={'csv_files':0,'csv_identical':True,'root_trees':{},'passed':True}
 for ref in sorted((base/'main').glob('event*.csv')):
  other=base/variant/ref.name
  same=other.exists() and ref.read_bytes()==other.read_bytes()
  result['csv_files']+=1;result['csv_identical'] &= same
 for name in ['tracksummary_ckf.root','trackstates_ckf.root']:
  with uproot.open(base/'main'/name) as f,uproot.open(base/variant/name) as g:
   tree=f[name.split('_')[0]];other=g[name.split('_')[0]]
   info={'entries':tree.num_entries,'branches':len(tree.keys()),'exact':True,'within_tolerance':True,'max_abs':0.,'differences':[]}
   if tree.num_entries!=other.num_entries or set(tree.keys())!=set(other.keys()):
    info['within_tolerance']=False
   else:
    for key in tree.keys():
     fa,la,ba=ak.to_buffers(ak.to_packed(tree[key].array()))
     fb,lb,bb=ak.to_buffers(ak.to_packed(other[key].array()))
     if fa!=fb or la!=lb or ba.keys()!=bb.keys():
      info['within_tolerance']=False;info['differences'].append({'branch':key,'structure_mismatch':True});continue
     for k,a in ba.items():
      b=bb[k];same=a.shape==b.shape and np.array_equal(a,b,equal_nan=True)
      info['exact'] &= same
      if same:continue
      close=False;delta=None
      if a.shape==b.shape and a.dtype.kind=='f':
       close=bool(np.allclose(a,b,rtol=64*np.finfo(a.dtype).eps,atol=64*np.finfo(a.dtype).eps,equal_nan=True))
       finite=np.isfinite(a)&np.isfinite(b)
       delta=float(np.max(np.abs(a[finite]-b[finite]),initial=0));info['max_abs']=max(info['max_abs'],delta)
      info['within_tolerance'] &= close
      info['differences'].append({'branch':key,'buffer':k,'max_abs':delta,'within_tolerance':close})
   result['root_trees'][name]=info;result['passed'] &= info['within_tolerance']
 result['passed'] &= result['csv_identical'];report[variant]=result
print(json.dumps(report,indent=2))
if not all(v['passed'] for v in report.values()):sys.exit(1)
