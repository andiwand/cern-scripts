#!/usr/bin/env python3
"""Compare four-head output dumps (33 floats per input) against a reference dump.

check_outputs.py DIR [--ref onnx] [--identical A=B]... [LABEL...]
Fails on any element outside 1e-5+1e-4|ref|, any multiplicity (argmax) change or
a non-identical --identical pair. Without labels, every DIR/*.bin except the
reference is checked. Writes DIR/validation.json.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

parser = argparse.ArgumentParser()
parser.add_argument('directory', type=Path)
parser.add_argument('labels', nargs='*')
parser.add_argument('--ref', default='onnx')
parser.add_argument('--identical', action='append', default=[], metavar='A=B')
args = parser.parse_args()

def load(label):
    return np.fromfile(args.directory/f'{label}.bin', dtype='<f4').reshape(-1, 33)

reference = load(args.ref)
labels = args.labels or sorted(p.stem for p in args.directory.glob('*.bin') if p.stem != args.ref)
report = {'reference': args.ref, 'inputs': len(reference), 'heads': 4, 'labels': {}, 'identical': {}}
ok = True
for label in labels:
    actual = load(label)
    assert actual.shape == reference.shape, (label, actual.shape, reference.shape)
    delta = np.abs(actual.astype(float) - reference)
    violations = int(np.count_nonzero(delta > 1e-5 + 1e-4*np.abs(reference)))
    choices = int(np.count_nonzero(actual[:, :3].argmax(1) != reference[:, :3].argmax(1)))
    finite = bool(np.isfinite(actual).all())
    ok &= violations == choices == 0 and finite
    report['labels'][label] = dict(finite=finite, outside_tolerance=violations, argmax_changes=choices,
                                   max_abs=float(delta.max()), bit_identical=bool(np.array_equal(actual, reference)))
for pair in args.identical:
    a, b = pair.split('=')
    same = (args.directory/f'{a}.bin').read_bytes() == (args.directory/f'{b}.bin').read_bytes()
    ok &= same
    report['identical'][pair] = same
(args.directory/'validation.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2))
sys.exit(0 if ok else 1)
