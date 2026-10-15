#!/usr/bin/env python3
"""Account for bytes in the V1 hadronic library without loading its events."""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('table', type=Path)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
sizes = Counter()
digest = hashlib.sha256()

with a.table.open('rb') as f:
    def read(kind):
        line = f.readline()
        if not line:
            raise ValueError('Unexpected end of library')
        digest.update(line)
        sizes[kind] += len(line)
        return line.split()

    if read('format_header') != [b'ACTS_FATRAS_NUCLEAR_V1']:
        raise ValueError('Unsupported format')
    channels = []
    for _ in range(int(read('format_header')[0])):
        header = read('channel_headers')
        pdg, nodes = int(header[0]), int(header[4])
        events = products = 0
        for _ in range(nodes):
            node = read('momentum_rate_headers')
            for _ in range(int(node[2])):
                event = read('event_target_and_remnant')
                count = int(event[6])
                events += 1
                products += count
                for _ in range(count):
                    read('daughter_records')
        channels.append(dict(pdg=pdg, nodes=nodes, events=events, products=products))
    tail = f.read()
    if tail.strip():
        raise ValueError('Unexpected trailing content')
    digest.update(tail)
    sizes['trailing_whitespace'] += len(tail)

assert sum(sizes.values()) == a.table.stat().st_size
result = dict(table=str(a.table.resolve()), sha256=digest.hexdigest(),
              bytes=sum(sizes.values()), bytes_by_record=dict(sizes),
              channels=channels,
              scope='Serialized byte accounting only; no new physics or performance validation.')
a.output.parent.mkdir(parents=True, exist_ok=True)
a.output.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
