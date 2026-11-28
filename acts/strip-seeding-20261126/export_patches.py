#!/usr/bin/env python3
"""Export the production changes separately from the diagnostic prototype."""
from pathlib import Path
import argparse,difflib,re,subprocess,tempfile
root=Path('/home/astefl/source/acts/acts-athena-ci')
repo=root/'athena-strip-seeding'
parser=argparse.ArgumentParser();parser.add_argument('--output',default=str(root/'studies/strip-seeding-inline-20261126'));args=parser.parse_args()
out=Path(args.output).resolve();out.mkdir(parents=True,exist_ok=True)
first=root/'studies/strip-seeding-20261126/athena-tuning.patch'
paths=re.findall(r'^diff --git a/(.*?) b/.*$',first.read_text(),re.M)
def base(path):
 r=subprocess.run(['git','show','HEAD:'+path],cwd=repo,capture_output=True,text=True)
 return r.stdout if r.returncode==0 else ''
def patch(before,after):
 s=''
 for path in sorted(set(before)|set(after)):
  a=before.get(path,'');b=after.get(path,'')
  if a==b:continue
  s+=f'diff --git a/{path} b/{path}\n'
  if not a:s+='new file mode 100644\n'
  s+=''.join(difflib.unified_diff(a.splitlines(True),b.splitlines(True),fromfile='a/'+path if a else '/dev/null',tofile='b/'+path))
 return s
with tempfile.TemporaryDirectory(prefix='strip-patch-') as tmp:
 t=Path(tmp);old={p:base(p) for p in paths}
 for p,s in old.items():
  if s:(t/p).parent.mkdir(parents=True,exist_ok=True);(t/p).write_text(s)
 subprocess.run(['git','apply',str(first)],cwd=t,check=True)
 prod={p:(t/p).read_text() for p in paths}
 for p in paths:
  if 'ActsConfig/python/' in p:
   if (repo/p).exists():prod[p]=(repo/p).read_text()
   else:prod.pop(p,None)
 allpaths=set(paths)
 allpaths.update(str(p.relative_to(repo)) for p in (repo/'Tracking/Acts/ActsStripSeedStudy').rglob('*') if p.is_file())
 allpaths.update(['Tracking/Acts/ActsPatternRecognition/src/GbtsSeedingTool.h','Tracking/Acts/ActsPatternRecognition/src/GbtsSeedingTool.cxx'])
 current={p:(repo/p).read_text() for p in allpaths if (repo/p).exists()}
 old={p:base(p) for p in allpaths}
 (out/'athena-tuning.patch').write_text(patch(old,prod))
 (out/'athena-diagnostics.patch').write_text(patch(prod,current))
 (out/'athena-full-study.patch').write_text(patch(old,current))
 # Restore the scratch base and check both patches in their documented order.
 for p in allpaths:
  f=t/p
  if f.exists():f.unlink()
  if old[p]:f.parent.mkdir(parents=True,exist_ok=True);f.write_text(old[p])
 subprocess.run(['git','apply','--check',str(out/'athena-tuning.patch')],cwd=t,check=True)
 subprocess.run(['git','apply',str(out/'athena-tuning.patch')],cwd=t,check=True)
 subprocess.run(['git','apply','--check',str(out/'athena-diagnostics.patch')],cwd=t,check=True)
 subprocess.run(['git','apply',str(out/'athena-diagnostics.patch')],cwd=t,check=True)
 assert all((t/p).read_text()==current[p] for p in current)
 assert all(not (t/p).exists() for p in allpaths-current.keys())
 print('Production + diagnostics patches apply cleanly and reproduce every changed source.')
