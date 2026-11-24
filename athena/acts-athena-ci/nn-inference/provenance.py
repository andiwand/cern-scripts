#!/usr/bin/env python3
import ctypes,hashlib,json,os,subprocess
from pathlib import Path

R=Path(os.environ['NN_STUDY_ROOT']);S=Path(os.environ['NN_STUDY_SCRIPTS'])
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
lib=ctypes.CDLL(str(Path(os.environ['NN_STUDY_LCG'])/'blas/0.3.33/x86_64-el9-gcc15-opt/lib/libopenblas.so'))
lib.openblas_get_config.restype=ctypes.c_char_p
lib.openblas_get_corename.restype=ctypes.c_char_p
a=R.parents[1]/'athena-nn-inference'
d={'date':'2026-11-24','nightly':os.environ['NIGHTLY_NAME'],'athena_head':subprocess.check_output(['git','-C',str(a),'rev-parse','HEAD'],text=True).strip(),
   'compiler':subprocess.check_output(['g++','--version'],text=True).splitlines()[0],
   'backend_compile_flags':'-O2 -DNDEBUG -std=c++23 -fPIC; direct_avx2 uses avx2,fma function target; no fast-math',
   'athena_compile_flags':next(line.strip() for line in (a.parent/'athena-build-nn-inference/build.ninja').read_text().splitlines() if line.startswith('  FLAGS = ')),
   'openblas_config':lib.openblas_get_config().decode(),'openblas_core':lib.openblas_get_corename().decode(),
   'openblas_runtime_threads':lib.openblas_get_num_threads(),
   'threads':{k:os.environ[k] for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']},
   'standalone_preload':os.environ.get('LD_PRELOAD',''),
   'standalone_preload_hashes':{p:sha(Path(p)) for p in os.environ.get('LD_PRELOAD','').split(':') if p},
   'scripts':{str(p.relative_to(S)):sha(p) for p in S.rglob('*')
              if p.is_file() and '__pycache__' not in p.parts},
   'models':{p.name:sha(p) for p in (R/'models').iterdir() if p.is_file()},
   'binaries':{str(p):sha(p) for p in [
       *[R/build/name for build in ['build','build-blocked','build-x86-v2']
         for name in ['libNNInferenceStudy.so','bench']],
       R/'vectorization/kernels',
       a.parent/'athena-build-nn-inference/x86_64-el9-gcc15-opt/lib/libActsTrackReconstruction.so'] if p.exists()},
   'blocked_source_snapshot':{p.name:sha(p) for p in (R/'build-blocked').glob('NNInferenceStudy.*')},
   'model_manifest':json.loads((R/'model-manifest.json').read_text()),
   'sofie_generation_fixes':json.loads((R/'sofie-generation-fixes.json').read_text())}
(R/'provenance.json').write_text(json.dumps(d,indent=2)+'\n')
(R/'athena-study.patch').write_bytes(subprocess.check_output(['git','-C',str(a),'diff']))
print(d['openblas_config'],d['openblas_core'])
