"""Archive completed diagnostics; reuse byte-identical reference event files."""
import argparse,gzip,hashlib,json,shutil
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--work',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
if a.output.exists():p.error('Refusing to overwrite results')
a.output.mkdir(parents=True)
def copy(src,dest):
 dest.parent.mkdir(parents=True,exist_ok=True)
 if src.suffix in ('.csv','.tsv') and src.name!='observer.tsv.cuts.tsv':
  with src.open('rb') as r,gzip.GzipFile(filename=str(dest)+'.gz',mode='wb',mtime=0,compresslevel=6) as z:shutil.copyfileobj(r,z)
 else:shutil.copy2(src,dest)
for name in ['surfaces.json','material-surfaces.json','birth-geometry.json','observer-summary.json','probe-summary.json','priorities.pdf','observer-build.json','gap_observer.so']:
 copy(a.work/name,a.output/name)
for folder in ['probe-input','probe-fatras','probe-vacuum','probe-geant4-observed','geant4-observed']:
 src=a.work/folder;dest=a.output/folder;dest.mkdir()
 hashes={}
 for file in src.iterdir():
  if folder=='geant4-observed' and file.name.startswith('event'):
   hashes[file.name]=hashlib.sha256(file.read_bytes()).hexdigest()
  else:copy(file,dest/file.name)
 if hashes:(dest/'observed-csv-hashes.json').write_text(json.dumps(hashes,indent=2))
for name in ['geant4-observed.log','probe-geant4-observed.log','probe-fatras.log','probe-vacuum.log','probe-fatras.command.json','probe-vacuum.command.json','geometry.log']:
 if (a.work/name).exists():copy(a.work/name,a.output/name)
records=a.output/'records';records.mkdir()
for src in Path(__file__).resolve().parent.iterdir():
 if src.suffix in ('.py','.cpp') or src.name=='README.md':shutil.copy2(src,records/src.name)
files={str(f.relative_to(a.output)):{'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()} for f in a.output.rglob('*') if f.is_file()}
(a.output/'inventory.json').write_text(json.dumps(files,indent=2))
print(a.output,round(sum(v['bytes'] for v in files.values())/1024**2,1),'MiB')
