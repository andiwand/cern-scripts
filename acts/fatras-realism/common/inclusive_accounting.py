"""Inclusive secondary-hit accounting; diagnostic bins partition hits, never select them.

  inclusive_accounting.py summary --run Fatras DIR --run Geant4 DIR --output summary.json
      Per process, detector volume, PDG, ancestry, momentum, time, birth distance
      and unique carrier/sensor counts for every secondary hit; totals asserted.
  inclusive_accounting.py revisits --summary summary.json --output revisits.json
      Time-ordered audit of repeated carrier/sensor visits.
  inclusive_accounting.py carriers --summary summary.json --output carriers.json
      Retained truth vs particles with hits for decay/conversion/ionisation,
      by parent and birth energy. Retained Fatras truth is not an unbiased
      produced-particle count.
  inclusive_accounting.py observer --run DIR --output observer.json
      Geant4 creator process, birth material and parent of every secondary hit
      recorded by inclusive_run.py --observer-module (observer.tsv).
Plain or gzipped CSVs are read.
"""
import argparse
from bisect import bisect_right
from collections import Counter, defaultdict
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path

IDS = ['pv', 'sv', 'part', 'gen', 'subpart']
PROCESSES = {'0':'Undefined', '1':'Decay', '2':'Conversion', '3':'Radiation', '4':'Nuclear', '5':'Ionisation', '6':'Other'}
EDGES = {
    'birth_ke_MeV': [.01, .04, .1, .2, 1, 5, 20, 100, 1000],
    'birth_pt_MeV': [.05, .2, 1, 5, 20, 50, 100, 500],
    'hit_pt_MeV': [.05, .2, 1, 5, 20, 50, 100, 500],
    'distance_mm': [.1, 1, 10, 100, 1000],
    'time_ns': [1, 10, 100, 1000, 10000],
    'radius_mm': [50, 100, 200, 400, 600, 800, 1000],
    'abs_z_mm': [200, 500, 1000, 1500, 2000, 3000],
}

def identity(row, prefix='particle_id_'):
    return tuple(row[prefix + s] for s in IDS)

def rows(path, delimiter=','):
    path = Path(path)
    if not path.exists():
        path = path.with_name(path.name + '.gz')
    with gzip.open(path, 'rt') if path.suffix == '.gz' else path.open() as f:
        yield from csv.DictReader(f, delimiter=delimiter)

def analyse(root):
    events = []
    hashes = {}
    meta = json.loads((root / 'metadata.json').read_text())
    for event in range(meta['events']):
        def file(suffix):
            path = root / f'event{event:09d}-{suffix}.csv'
            if not path.exists():
                path = path.with_suffix('.csv.gz')
            hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
            return path
        truth = {}
        for row in rows(file('particles_simulated')):
            p = math.sqrt(sum(float(row[k])**2 for k in ['px','py','pz']))
            mass = float(row['m'])
            truth[identity(row)] = (row['particle_type'], row['process'],
                tuple(float(row[k]) for k in ['vx','vy','vz']),
                p, math.hypot(float(row['px']),float(row['py'])),
                p*p/(math.hypot(p,mass)+mass) if p or mass else 0,
                float(row['q']), identity(row,'parent_id_'), float(row['vt']))
        ancestry = {}
        def other_ancestor(pid):
            chain = []
            key = pid
            while key in truth and key not in ancestry:
                assert key not in chain, 'Cycle in truth ancestry'
                chain.append(key)
                t = truth[key]
                if t[1] == '6':
                    parent = truth.get(t[7])
                    result = t[0] + ':' + (parent[0] if parent else 'unknown')
                    break
                key = t[7]
            else:
                result = ancestry.get(key, 'none')
            for key in chain:
                ancestry[key] = result
            return result
        counters = defaultdict(Counter)
        carriers = {region: defaultdict(Counter) for region in ['ID','pixel','strip']}
        sensors = {region: set() for region in carriers}
        for t in truth.values():
            counters['retained_truth'][t[1]] += 1
        for hit in rows(file('hits')):
            pid = identity(hit)
            secondary = int(pid[3]) > 0
            volume = int(hit['geometry_id']) >> 56
            region = 'pixel' if volume in [16,17,18] else 'strip'
            for scope in ['ID', region]:
                counters[scope+'_totals']['secondary' if secondary else 'primary'] += 1
            pos = tuple(float(hit[k]) for k in ['tx','ty','tz'])
            assert math.hypot(*pos[:2]) <= 1202.001 and abs(pos[2]) <= 4002.001
            if not secondary:
                continue
            t = truth[pid]
            pdg, proc, birth, p, pt, ke, q, parent_id, time = t
            parent = truth.get(parent_id)
            origin = other_ancestor(pid)
            values = {
                'birth_ke_MeV': ke*1000,
                'birth_pt_MeV': pt*1000,
                'hit_pt_MeV': math.hypot(float(hit['tpx']),float(hit['tpy']))*1000,
                'distance_mm': math.dist(pos,birth),
                'time_ns': float(hit['tt'])/299.792458,
                'radius_mm': math.hypot(*pos[:2]),
                'abs_z_mm': abs(pos[2]),
            }
            for scope in ['ID',region]:
                c = lambda key: counters[scope+'_'+key]
                c('process')[proc] += 1
                c('pdg')[proc+':'+pdg] += 1
                c('volume')[str(volume)] += 1
                c('volume_process')[str(volume)+':'+proc] += 1
                c('parent')[proc+':'+(parent[0] if parent else 'unknown')] += 1
                c('parent_process')[proc+':'+(parent[1] if parent else 'unknown')] += 1
                c('other_ancestry')[origin] += 1
                c('process_other_ancestry')[proc+':'+origin] += 1
                charged_cut = q != 0 and (p < .0002 or pt < .00005)
                ion_cut = proc == '5' and pdg == '11' and ke < .0001
                c('acceptance_partition')[proc+':'+('charged cut' if charged_cut else 'ion cut' if ion_cut else 'above both')] += 1
                for key,value in values.items():
                    c(key)[proc+':'+str(bisect_right(EDGES[key],value))] += 1
                c('time_distance')[proc+':'+str(bisect_right(EDGES['time_ns'],values['time_ns']))+':'+str(bisect_right(EDGES['distance_mm'],values['distance_mm']))] += 1
                carriers[scope][proc][pid] += 1
                sensors[scope].add((pid,hit['geometry_id']))
        for scope in carriers:
            for proc,counts in carriers[scope].items():
                counters[scope+'_carriers'][proc] = len(counts)
                counters[scope+'_single_hit_carriers'][proc] = sum(n==1 for n in counts.values())
                counters[scope+'_max_hits_carrier'][proc] = max(counts.values())
            for pid,geometry in sensors[scope]:
                counters[scope+'_carrier_sensors'][truth[pid][1]] += 1
            assert sum(counters[scope+'_process'].values()) == counters[scope+'_totals']['secondary']
            for key in EDGES:
                assert sum(counters[scope+'_'+key].values()) == counters[scope+'_totals']['secondary']
            assert sum(counters[scope+'_acceptance_partition'].values()) == counters[scope+'_totals']['secondary']
        assert counters['ID_totals'] == counters['pixel_totals'] + counters['strip_totals']
        events.append(dict(counters))
        print(root.name,event,dict(counters['ID_totals']),flush=True)
    average = {}
    for field in events[0]:
        total = Counter()
        for event in events:
            total.update(event[field])
        average[field] = {key:value/len(events) for key,value in total.items()}
    return {'path':str(root.resolve()),'metadata':meta,'sha256':hashes,'events':events,'mean':average}

def event_file(root, event, suffix):
    path = root / f'event{event:09d}-{suffix}.csv'
    return path if path.exists() else path.with_suffix('.csv.gz')

def revisits(summary):
    out = {}
    for name, run in summary['runs'].items():
        root = Path(run['path']); events = []
        for ev in range(run['metadata']['events']):
            truth = {identity(r): r['process'] for r in rows(event_file(root, ev, 'particles_simulated'))}
            visits = defaultdict(list)
            for h in rows(event_file(root, ev, 'hits')):
                if int(h['particle_id_gen']) == 0:
                    continue
                visits[(identity(h), h['geometry_id'])].append(tuple(float(h[k]) for k in ['tt','tx','ty','tz']))
            count = Counter()
            for (pid, geo), hits in visits.items():
                proc = truth[pid]; reg = 'pixel' if int(geo) >> 56 in (16,17,18) else 'strip'
                hits.sort()
                for prev, cur in zip(hits, hits[1:]):
                    local = math.dist(prev[1:], cur[1:]) < 1
                    quick = (cur[0]-prev[0])/299.792458 < 1
                    for scope in ['ID', reg]:
                        count[scope+':'+proc+':all'] += 1
                        count[scope+':'+proc+':within_1mm'] += local
                        count[scope+':'+proc+':within_1ns'] += quick
                        count[scope+':'+proc+':both'] += local and quick
            events.append(dict(count))
        total = Counter()
        for event in events:
            total.update(event)
        out[name] = {'events': events, 'mean': {k: v/len(events) for k, v in total.items()}}
    return out

def carriers(summary):
    out = {}
    for name, run in summary['runs'].items():
        root = Path(run['path']); events = []
        for ev in range(run['metadata']['events']):
            truth = {identity(r): r for r in rows(event_file(root, ev, 'particles_simulated'))}
            hits = Counter(); pixels = Counter()
            for h in rows(event_file(root, ev, 'hits')):
                pid = identity(h); hits[pid] += 1; pixels[pid] += (int(h['geometry_id']) >> 56) in (16,17,18)
            counts = defaultdict(Counter); parents = defaultdict(set)
            for pid, t in truth.items():
                if int(pid[3]) == 0 or t['process'] not in ('1','2','5'):
                    continue
                proc = t['process']; parentid = identity(t, 'parent_id_'); parent = truth.get(parentid)
                m = float(t['m']); p2 = sum(float(t[k])**2 for k in ['px','py','pz'])
                ke = p2/(math.sqrt(p2+m*m)+m) if p2 or m else 0
                keys = [proc+':parent_pdg:'+(parent['particle_type'] if parent else 'unknown'),
                        proc+':parent_process:'+(parent['process'] if parent else 'unknown')]
                if proc == '5':
                    keys.append('5:birth_ke_bin:'+str(bisect_right(EDGES['birth_ke_MeV'], ke*1000)))
                for key in keys:
                    counts['retained_truth'][key] += 1
                    counts['hit_carriers'][key] += hits[pid] > 0
                    counts['hits'][key] += hits[pid]
                    counts['pixel_hits'][key] += pixels[pid]
                    if hits[pid]:
                        parents[key].add(parentid)
            counts['parents_with_hit_daughters'] = Counter({k: len(v) for k, v in parents.items()})
            events.append(dict(counts))
            print(name, ev, flush=True)
        average = {}
        for field in events[0]:
            total = Counter()
            for event in events:
                total.update(event[field])
            average[field] = {k: v/len(events) for k, v in total.items()}
        out[name] = {'events': events, 'mean': average}
    return out

def observer(root):
    counters = defaultdict(Counter)
    for r in rows(root / 'observer.tsv', delimiter='\t'):
        if r['parent'] == '0':
            continue
        proc = r['creator']
        region = 'pixel' if math.hypot(float(r['x']), float(r['y'])) < 190 else 'strip'
        assert math.hypot(float(r['x']), float(r['y'])) <= 1202.001 and abs(float(r['z'])) <= 4002.001
        for scope in ['ID', region]:
            counters[scope+'_creator'][proc] += 1
            counters[scope+'_born_sensitive'][proc] += 'ActsSensitive#' in r['birth_volume']
            counters[scope+'_parent_below_pair_threshold'][proc] += float(r['parent_birth_ke_MeV']) < 1.0219979
            counters[scope+'_stopping_hit'][proc] += r['stopped'] == '1'
            counters[scope+'_birth_material'][proc+':'+r['birth_material']] += 1
            counters[scope+'_parent_process'][proc+':'+r['parent_creator']] += 1
        counters['events'][r['event']] += 1
    n = len(counters['events'])
    return {'path': str(root.resolve()), 'counts': counters,
            'means': {k: {kk: vv/n for kk, vv in v.items()} for k, v in counters.items()}}

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    s = sub.add_parser('summary')
    s.add_argument('--run', action='append', nargs=2, metavar=('NAME','DIRECTORY'), required=True)
    for name in ['revisits', 'carriers']:
        sub.add_parser(name).add_argument('--summary', type=Path, required=True)
    sub.add_parser('observer').add_argument('--run', type=Path, required=True)
    for command in sub.choices.values():
        command.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'summary':
        result = {'edges':EDGES,'processes':PROCESSES,'runs':{name:analyse(Path(path)) for name,path in args.run}}
    elif args.command == 'observer':
        result = observer(args.run)
    else:
        result = globals()[args.command](json.loads(args.summary.read_text()))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2))

if __name__ == '__main__':
    main()
