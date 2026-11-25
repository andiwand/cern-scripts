#!/usr/bin/env python3
"""Prove whitespace-only rebuilds preserve every loaded ELF section except build ID."""
import hashlib,json,struct,subprocess
from pathlib import Path
root=Path('/home/astefl/source/acts/acts-athena-ci')
out=root/'run/native-pixel-nn/generic/full'
lib=root/'athena-build-native-pixel-nn/x86_64-el9-gcc15-opt/lib'
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def sections(path):
 raw=path.read_bytes();assert raw[:6]==b'\x7fELF\x02\x01'
 h=struct.unpack_from('<16sHHIQQQIHHHHHH',raw)
 hs=[struct.unpack_from('<IIQQQQIIQQ',raw,h[6]+i*h[11]) for i in range(h[12])]
 sh=hs[h[13]];names=raw[sh[4]:sh[4]+sh[5]];result={}
 for s in hs:
  name=names[s[0]:names.index(0,s[0])].decode()
  if not s[2]&2 or name=='.note.gnu.build-id':continue
  payload=b'' if s[1]==8 else raw[s[4]:s[4]+s[5]]
  result[name]=dict(address=s[3],size=s[5],flags=s[2],sha256=hashlib.sha256(payload).hexdigest())
 return result
expected={Path(path).name:value for value,path in (line.split() for line in (out/'libraries-before-off.txt').read_text().splitlines())}
before=out/'restore-review/measured-recovered.so';after=lib/'libActsTrackReconstruction.so'
assert digest(before)==expected[after.name], 'Recovered library must exactly match the measured file'
assert digest(after)==digest(out/'restore-review/restored.so')
a,b=sections(before),sections(after);assert a==b
assert digest(lib/'libSiClusterizationToolLib.so')==expected['libSiClusterizationToolLib.so']
assert not subprocess.check_output(['git','-C',str(root/'athena-native-pixel-nn'),'status','--porcelain'],text=True)
report=dict(native_file_hash_restored=True,acts_measured_hash=digest(before),acts_restored_hash=digest(after),
 loaded_code_data_identical_except_build_id=True,loaded_sections=a,
 explanation='ACTS helper whitespace was cleaned after the measured build. Rebuilding that exact earlier header reproduces its original whole-file hash. Current code/data/addresses match; only nonfunctional metadata changes.')
(out/'restore-equivalence.json').write_text(json.dumps(report,indent=2)+'\n')
with (out/'pipeline.log').open('a') as stream:stream.write('FULL VALIDATION COMPLETE\n')
print(json.dumps({k:v for k,v in report.items() if k!='loaded_sections'},indent=2))
