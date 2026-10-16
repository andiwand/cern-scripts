"""Archive diagnostic outputs; reuse existing physics-reference archives."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--work',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
a=p.parse_args()
if a.output.exists():
    p.error('Refusing to overwrite an archive')
a.output.mkdir(parents=True)
for name in ['summary.json','sensitivity.json','loops16.json','revisits.json','carriers.json','checks.json','secondary_gap.pdf']:
    shutil.copy2(a.work/name,a.output/name)
for src in sorted((a.work/'runs').iterdir()):
    if src.is_file():
        shutil.copy2(src,a.output/src.name)
        continue
    dest=a.output/src.name;dest.mkdir()
    for file in src.iterdir():
        if file.suffix=='.csv':
            with file.open('rb') as f,gzip.GzipFile(filename=str(dest/(file.name+'.gz')),mode='wb',compresslevel=6,mtime=0) as z:
                shutil.copyfileobj(f,z)
        else:
            shutil.copy2(file,dest/file.name)
for name in ['sensitivity.json','loops16.json']:
    path=a.output/name;s=json.loads(path.read_text())
    for label,run in s['runs'].items():
        run['original_path']=run['path'];run['path']=str(a.output.resolve()/label)
        # Existing hashes describe decompressed source bytes, independently of gzip.
        run['sha256_scope']='Uncompressed original CSV bytes'
    path.write_text(json.dumps(s,indent=2))
records=a.output/'records';records.mkdir()
for src in Path(__file__).resolve().parent.glob('*.py'):
    shutil.copy2(src,records/src.name)
files={}
for src in sorted(a.output.rglob('*')):
    if src.is_file():files[str(src.relative_to(a.output))]={'bytes':src.stat().st_size,'sha256':hashlib.sha256(src.read_bytes()).hexdigest()}
(a.output/'inventory.json').write_text(json.dumps(files,indent=2))
print(a.output,round(sum(f['bytes'] for f in files.values())/1024**2,1),'MiB')
