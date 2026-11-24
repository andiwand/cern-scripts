#!/usr/bin/env python3
"""Strip experimental branches and count the selected compute implementation."""
from pathlib import Path
import hashlib,json,re,shutil,subprocess
ROOT=Path('/home/astefl/source/acts/acts-athena-ci')
PARENT=ROOT/'run/native-pixel-nn/cxxutils';OUT=PARENT/'tuning/clean'
(OUT/'SiClusterizationTool').mkdir(parents=True,exist_ok=True)
source=(PARENT/'tuning/Kernel.icc').read_text()
enabled={'NN_CXX_ACTIVATION':True,'NN_LOCAL_HEADS':True,'NN_BIAS_FIRST':False,'NN_FLATTEN_PACKET':False}
pattern=r'#ifdef ('+'|'.join(enabled)+r')\n(.*?)(?:#else\n(.*?))?#endif\n'
source=re.sub(pattern,lambda m:m.group(2) if enabled[m.group(1)] else (m.group(3) or ''),source,flags=re.S)
source=source.replace('#ifdef NN_UNROLL_ACTIVATION','#if NN_WIDTH == 8').replace('unsigned(NN_BLOCKS)','8u')
source=source.replace('// Prototype: explicit vector width and output blocking; no Eigen in ISA kernels.',
                      '// GEMV with explicit vector width and output blocking.')
assert set(re.findall(r'NN_[A-Z_]+',source))=={'NN_WIDTH','NN_ENTRY'}
(OUT/'Kernel.icc').write_text(source)
for name in ['SiClusterizationTool/NativePixelClusterNN.h','Loader.cxx','Sse.cxx','Avx2.cxx','bench.cxx']:
 shutil.copyfile(PARENT/name,OUT/name)
dispatch=(PARENT/'Dispatch.cxx').read_text()
start=dispatch.index('#ifdef NN_STATIC_SSE');end=dispatch.index('#endif',start)+len('#endif\n')
dispatch=dispatch[:start]+'''  if (m_useAvx2) inferAvx2(input, output);
  else inferSse(input, output);
'''+dispatch[end:]
(OUT/'Dispatch.cxx').write_text(dispatch)
def count_text(text):
 text=re.sub(r'/\*.*?\*/','',text,flags=re.S)
 return sum(bool(line.split('//')[0].strip()) for line in text.splitlines())
def count(p):return count_text(p.read_text())
files={name:{'lines':count(OUT/name),'sha256':hashlib.sha256((OUT/name).read_bytes()).hexdigest()} for name in ['Kernel.icc','SiClusterizationTool/NativePixelClusterNN.h','Dispatch.cxx','Sse.cxx','Avx2.cxx','Loader.cxx']}
def old_count(name):
 return count_text(subprocess.check_output(['git','-C',str(ROOT/'athena-native-pixel-nn'),'show',
  'fd1750c6d06:InnerDetector/InDetRecTools/SiClusterizationTool/'+name],text=True))
old_inference=sum(old_count(name) for name in ['src/NativePixelClusterNN.cxx','SiClusterizationTool/NativePixelClusterNN.h'])
new_inference=sum(v['lines'] for name,v in files.items() if name!='Loader.cxx')
record={'metric':'Nonblank, noncomment physical lines, including declarations, includes, braces and ISA entry wrappers.',
 'scope':'Compute/header/dispatch and conversion only. Athena build/config integration and new production tests are not implemented or counted for this prototype.',
 'current_eigen':{'inference_header_dispatch':old_inference,'conversion_validation':old_count('src/NativePixelClusterNNFromOnnx.cxx')},
 'clean_prototype':{'inference_header_dispatch':new_inference,'conversion_validation':files['Loader.cxx']['lines']},'files':files}
(PARENT/'tuning/loc.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({k:v for k,v in record.items() if k!='files'},indent=2))
