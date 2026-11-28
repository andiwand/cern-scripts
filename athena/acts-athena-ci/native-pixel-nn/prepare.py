#!/usr/bin/env python3
"""Prepare a fresh campaign directory; never overwrite an existing measurement.

prepare.py OUT
Requires a clean source tree and a finished tests.sh. Records the source commit,
copies the build's tests.log and writes fallback-models/ (number model with its
Sigmoid renamed to Softmax, which the native loader must reject).
"""
import shutil
import subprocess
import sys
from pathlib import Path

root = Path('/home/astefl/source/acts/acts-athena-ci')
out = Path(sys.argv[1]).resolve()
assert not subprocess.check_output(['git', '-C', str(root/'athena-native-pixel-nn'), 'status', '--porcelain'], text=True)
out.mkdir(parents=True, exist_ok=False)
(out/'standalone').mkdir()
(out/'source-commit.txt').write_text(subprocess.check_output(['git', '-C', str(root/'athena-native-pixel-nn'), 'rev-parse', 'HEAD'], text=True))
shutil.copyfile(root/'athena-build-native-pixel-nn/tests.log', out/'tests-final-on.log')
models = out/'fallback-models'
models.mkdir()
calibration = Path('/cvmfs/atlas.cern.ch/repo/sw/database/GroupData/ITkPixelClusterization/nn-01-01-01')
for name in ('number', 'pos1', 'pos2', 'pos3'):
    data = (calibration/(name+'.onnx')).read_bytes()
    if name == 'number':
        i = data.rfind(b'\x22\x07Sigmoid'); assert i >= 0
        data = data[:i+2]+b'Softmax'+data[i+9:]
    (models/(name+'.onnx')).write_bytes(data)
print(out)
