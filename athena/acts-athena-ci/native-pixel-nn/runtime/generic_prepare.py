#!/usr/bin/env python3
"""Prepare a fresh full campaign; never overwrite an existing measurement."""
import shutil,subprocess
from pathlib import Path
root=Path('/home/astefl/source/acts/acts-athena-ci')
out=root/'run/native-pixel-nn/generic/full'
assert not subprocess.check_output(['git','-C',str(root/'athena-native-pixel-nn'),'status','--porcelain'],text=True)
out.mkdir(exist_ok=False)
(out/'standalone').mkdir()
(out/'source-commit.txt').write_text(subprocess.check_output(['git','-C',str(root/'athena-native-pixel-nn'),'rev-parse','HEAD'],text=True))
shutil.copyfile(root/'athena-build-native-pixel-nn/tests.log',out/'tests-final-on.log')
models=out/'fallback-models';models.mkdir()
calibration=Path('/cvmfs/atlas.cern.ch/repo/sw/database/GroupData/ITkPixelClusterization/nn-01-01-01')
for name in ('number','pos1','pos2','pos3'):
 data=(calibration/(name+'.onnx')).read_bytes()
 if name=='number':
  i=data.rfind(b'\x22\x07Sigmoid');assert i>=0
  data=data[:i+2]+b'Softmax'+data[i+9:]
 (models/(name+'.onnx')).write_bytes(data)
print(out)
