#!/usr/bin/env python3
"""Compare an independent Geant4 sample to a Fatras interaction library."""
import argparse
import bisect
import json
from pathlib import Path
import statistics


def read(path):
    t = iter(path.read_text().split())
    if next(t) != 'ACTS_FATRAS_NUCLEAR_V1':
        raise ValueError('unknown format')
    channels = {}
    for _ in range(int(next(t))):
        pdg = int(next(t)); mass = float(next(t)); ar = float(next(t)); z = float(next(t))
        bins = []
        for _ in range(int(next(t))):
            p = float(next(t)); rate = float(next(t)); events = []
            for _ in range(int(next(t))):
                target, remnant, charge, x, y, zz = [float(next(t)) for _ in range(6)]
                products = []
                for _ in range(int(next(t))):
                    code = int(next(t)); m, q, px, py, pz = [float(next(t)) for _ in range(5)]
                    products.append((code, m, q, px, py, pz))
                events.append(products)
            bins.append(dict(p=p, rate=rate, events=events))
        channels[pdg] = bins
    if next(t, None) is not None:
        raise ValueError('trailing input')
    return channels


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('training', type=Path); p.add_argument('reference', type=Path)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(); train = read(a.training); ref = read(a.reference)
    rows = []
    for pdg, bins in ref.items():
        grid = [x['p'] for x in train[pdg]]
        for r in bins:
            i = bisect.bisect_right(grid, r['p']) - 1
            if i < 0 or r['p'] > grid[-1]:
                continue
            model = train[pdg][i]
            multiplicity = lambda b: [sum(q != 0 for _, _, q, *_ in event) for event in b['events']]
            x, y = multiplicity(model), multiplicity(r)
            rate = model['rate']
            if rate > 0 and i + 1 < len(grid):
                upper = train[pdg][i + 1]
                weight = (r['p'] - model['p']) / (upper['p'] - model['p'])
                rate += weight * (upper['rate'] - rate)
            rows.append(dict(pdg=pdg, p_GeV=r['p'], node_GeV=model['p'],
                             model_rate=rate, reference_rate=r['rate'],
                             model_charged_mean=statistics.mean(x),
                             reference_charged_mean=statistics.mean(y),
                             model_charged_se=statistics.stdev(x)/(len(x)**.5),
                             reference_charged_se=statistics.stdev(y)/(len(y)**.5)))
    a.output.write_text(json.dumps(rows, indent=2) + '\n')
    for r in rows:
        print(f"{r['pdg']:5} {r['p_GeV']:5g}: rate bias {r['model_rate']/r['reference_rate']-1:+.1%}; charged mean {r['model_charged_mean']:.2f} vs {r['reference_charged_mean']:.2f}")


if __name__ == '__main__':
    main()
