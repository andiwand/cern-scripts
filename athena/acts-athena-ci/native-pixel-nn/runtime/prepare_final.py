#!/usr/bin/env python3
"""Prepare a fresh final run, retaining the unchanged ONNX references."""
import shutil
import subprocess
from pathlib import Path

root = Path('/home/astefl/source/acts/acts-athena-ci')
previous = root/'run/native-pixel-nn/runtime-mr'
out = root/'run/native-pixel-nn/runtime-final'
out.mkdir(exist_ok=False)
(out/'standalone').mkdir()
for compiler in ['gcc', 'clang']:
    (out/'standalone'/f'bench_{compiler}').symlink_to(previous/'standalone'/f'bench_{compiler}')
    destination = out/'standalone'/compiler/'validation'
    destination.mkdir(parents=True)
    shutil.copyfile(previous/'standalone'/compiler/'validation/validation.json', destination/'validation.json')
for stage in ['physics', 'smoke-pre', 'smoke-default-threshold']:
    (out/stage).mkdir()
    (out/stage/'OnnxRuntime').symlink_to(previous/stage/'OnnxRuntime', target_is_directory=True)
for name in ['loc.json', 'isa-audit.json', 'tests-off.log', 'tests-final-on.log', 'release-equivalence.json']:
    shutil.copyfile(previous/name, out/name)
(out/'debug-audit').mkdir()
shutil.copyfile(previous/'debug-audit/summary.json', out/'debug-audit/summary.json')
(out/'source-commit.txt').write_text(subprocess.check_output(
    ['git', '-C', str(root/'athena-native-pixel-nn'), 'rev-parse', 'HEAD'], text=True))
