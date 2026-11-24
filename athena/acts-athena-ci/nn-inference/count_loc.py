#!/usr/bin/env python3
"""Attribute prototype implementation LOC; never include model weights or library internals."""
import hashlib
import json
import re
from pathlib import Path

S = Path(__file__).resolve().parent
R = Path('/home/astefl/source/acts/acts-athena-ci/run/nn-inference')
sources = {
    'adapter': S/'NNInferenceStudy.cxx',
    'export': S/'export_models.py',
    'generator': S/'generate_sofie.py',
    'blocked': R/'build-blocked/NNInferenceStudy.cxx',
}
# The attribution below refers to the measured source snapshots. Fail instead
# of silently counting different functions after an implementation edit.
expected = {
    'adapter': '41fd3738078798b0498aef5496685d6436e111024957b33e245b69822f6034ff',
    'export': '2b678ca70d2c60de0727d1996478ff2183749c8ea15ee1169cf140df3d5241d9',
    'generator': 'c55eea82c9beb65560d24142064fa859dbd8f69b411f516d67814af1f40df991',
    'blocked': '0f6c2a153353956ae85edb3fa6f5f459fd7e54b4515b5d04be3b3c4b90f25a55',
}
for key, path in sources.items():
    assert hashlib.sha256(path.read_bytes()).hexdigest() == expected[key], path

# Inclusive physical-line ranges, including function signatures and braces.
# Shared inference helpers are charged once to every backend that uses them.
ort = [(111,131),(153,153),(157,158),(172,178)]
direct = [(19,22),(52,74),(92,110),(159,159),(181,181),
          (225,225),(234,244),(246,246)]
lwtnn = [(92,94),(98,110),(183,184),(187,187),(225,225),(246,246)]
export_common = [(12,15),(17,23),(26,31)]
binary = export_common + [(25,25),(32,32),(35,35)]
json_export = export_common + [(24,24),(33,34),(36,36)]
simple = export_common + [(39,75)]
generate = [(7,8),(10,16),(18,21),(23,23),(25,28),(30,34)]

rows = {
    'original': {'cpp': [('adapter', ort + [(138,152),(203,203)])]},
    'ort_cached': {'cpp': [('adapter', ort + [(132,137),(204,204)])]},
    'ort_simple': {'cpp': [('adapter', ort + [(132,137),(204,204)])],
                   'conversion': [('export', simple)]},
    'direct': {'cpp': [('adapter', direct + [(75,82)])],
               'conversion': [('export', binary)]},
    'direct_blocked': {'cpp': [('adapter', direct), ('blocked', [(76,97)])],
                       'conversion': [('export', binary)]},
    'direct_avx2': {'cpp': [('adapter', direct + [(83,91),(180,180)])],
                    'conversion': [('export', binary)]},
    'sofie': {'cpp': [('adapter', [(19,22),(162,165),(189,192),(208,213)])],
              'conversion': [('export', simple), ('generator', generate)]},
    'sofie_gemv': {'cpp': [('adapter', [(19,22),(25,32),(166,169),(194,197),(217,222)])],
                   'conversion': [('export', simple), ('generator', generate + [(36,40)])]},
    'lwtnn': {'cpp': [('adapter', lwtnn + [(160,160),(185,185),(227,228)])],
              'conversion': [('export', json_export)]},
    'lwtnn_double': {'cpp': [('adapter', lwtnn + [(161,161),(186,186),(230,232)])],
                     'conversion': [('export', json_export)]},
}
for backend, suffix in [('sofie','_sofie.hxx'), ('sofie_gemv','_sofie_gemv.hxx')]:
    rows[backend]['generated'] = []
    for model in ['number','pos1','pos2','pos3']:
        key = model + suffix
        sources[key] = R/'models'/key
        rows[backend]['generated'].append((key, [(1,len(sources[key].read_text().splitlines()))]))

def code_lines(path):
    text = path.read_text()
    if path.suffix in {'.cxx', '.hxx'}:
        # Keep quoted strings; replace comments while preserving line numbers.
        pattern = r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|//[^\n]*|/\*[\s\S]*?\*/'
        text = re.sub(pattern, lambda m: ''.join('\n' if c == '\n' else ' ' for c in m[0])
                      if m[0].startswith(('//','/*')) else m[0], text)
    return {i for i, line in enumerate(text.splitlines(), 1)
            if line.strip() and not (path.suffix == '.py' and line.lstrip().startswith('#'))}

result = {'metric': 'Nonblank, noncomment physical source lines in attributed prototype regions; braces count.',
          'scope': 'Local C++ loading/inference/transforms/kernels plus Python model conversion/generation. Shared inference helpers count once per backend. Excludes includes/imports in handwritten regions, common Engine/dispatch glue, cluster preparation, build/test/profiling/report code, weights, and upstream library internals. Generated totals cover all four SOFIE headers, including their boilerplate. These are not production implementation estimates.',
          'sources': {key: {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
                      for key, path in sources.items()}, 'backends': {}}
for backend, categories in rows.items():
    row = {'cpp_loc': 0, 'conversion_loc': 0, 'generated_loc': 0, 'regions': []}
    for category, parts in categories.items():
        for key, ranges in parts:
            selected = set()
            for first, last in ranges:
                span = set(range(first,last+1))
                assert not selected & span, (backend, key, first, last)
                selected |= span
            assert max(selected) <= len(sources[key].read_text().splitlines())
            counted = sorted(selected & code_lines(sources[key]))
            row[category+'_loc'] += len(counted)
            row['regions'].append({'category': category, 'source': key,
                                   'ranges': ranges, 'loc': len(counted)})
    row['handwritten_loc'] = row['cpp_loc'] + row['conversion_loc']
    result['backends'][backend] = row
    print(f"{backend}: {row['cpp_loc']} C++ + {row['conversion_loc']} conversion = "
          f"{row['handwritten_loc']} handwritten; {row['generated_loc']} generated")
(R/'loc-counts.json').write_text(json.dumps(result,indent=2)+'\n')
