#!/usr/bin/env python3
"""Sum the CPU counters of the samples that fall inside the finder's signpost
intervals: c0 cycles, c1 instructions, c5 backend stalls, c4 flushes."""
import re, sys, xml.etree.ElementTree as ET

def resolve(root):
    # the export interns repeated values as id/ref pairs
    byid = {}
    for el in root.iter():
        i = el.get('id')
        if i is not None:
            byid[i] = el
    def val(el):
        r = el.get('ref')
        return byid[r] if r is not None else el
    return val

def intervals(path):
    """Pair the begin and end events of the signposts, by identifier."""
    root = ET.parse(path).getroot()
    val = resolve(root)
    begins = {}
    out = []
    for row in root.iter('row'):
        t = None; kind = None; ident = None; name = None
        for k in row:
            k = val(k)
            tag = k.tag
            if tag in ('event-time', 'sample-time', 'start-time'):
                t = int(k.text)
            elif tag == 'event-type':
                kind = (k.text or '').strip()
            elif tag == 'os-signpost-identifier':
                ident = k.text
            elif tag == 'signpost-name':
                name = k.text
        if t is None:
            continue
        if kind.lower().startswith('begin'):
            begins[ident] = (t, name)
        elif kind.lower().startswith('end') and ident in begins:
            t0, name0 = begins.pop(ident)
            out.append((t0, t, name0))
    return out

def counters(path, ivs):
    root = ET.parse(path).getroot()
    val = resolve(root)
    last = {}   # (thread, core) -> (time, counters)
    tot = [0] * 12; n = 0; covered = 0
    def inside(t):
        return any(a <= t <= b for a, b, _ in ivs)
    for row in root.iter('row'):
        kids = [val(k) for k in row]
        t = core = state = tid = None; pmc = None
        for k in kids:
            if k.tag == 'sample-time': t = int(k.text)
            elif k.tag == 'core': core = k.text
            elif k.tag == 'thread-state': state = k.text
            elif k.tag == 'thread': tid = k.get('id')
            elif k.tag == 'pmc-events': pmc = [int(x) for x in k.text.split()]
        if t is None or pmc is None or state != 'Running' or core is None:
            continue
        key = (tid, core)
        if key in last:
            t0, p0 = last[key]
            if inside(t) and inside(t0) and 0 < t - t0 < 5_000_000:
                d = [a - b for a, b in zip(pmc, p0)]
                if all(x >= 0 for x in d):
                    tot = [a + b for a, b in zip(tot, d)]; n += 1; covered += t - t0
        last[key] = (t, pmc)
    return tot, n, covered

if __name__ == '__main__':
    tag = sys.argv[1]
    ivs = intervals(f'{tag}-signpost.xml')
    ivs = [iv for iv in ivs if iv[2] in (None, 'find')]
    span = sum(b - a for a, b, _ in ivs)
    tot, n, covered = counters(f'{tag}-counters.xml', ivs)
    c0, c1, c4, c5 = tot[0], tot[1], tot[4], tot[5]
    print(f'{tag}: {len(ivs)} intervals, {span/1e9:.2f} s inside, {covered/1e9:.2f} s covered by {n} sample pairs')
    print(f'  cycles {c0/1e9:.2f} G, instr {c1/1e9:.2f} G, IPC {c1/c0:.2f}, GHz {c0/covered:.2f}')
    print(f'  backend stall c5 {100*c5/c0:.1f} % of cycles, flush c4 {100*c4/c0:.2f} %, uops/instr {tot[3]/c1:.2f}')
    print(f'  per 1000 instr: stall cycles {1000*c5/c1:.0f}, cycles {1000*c0/c1:.0f}')
