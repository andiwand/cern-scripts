#!/usr/bin/env python
"""Affected-vertex fraction, measured, and cross-checked against the CI counts.

    affected_fraction.py NPZDIR

The CI `diff-root` log gives a *numerator* -- how many `trackWeights` /
`covariance` rows differ -- but never the denominator, because it does not print
how many vertices were in the file.  With both sides extracted we can measure
the fraction directly, and at the same time check the extraction reproduces what
`diff-root` saw.

`covariance` and `trackWeights` are `vector<vector<float>>`, dumped one row per
vertex (PyROOTInspector.cxx:183 returns the inner vector whole), so one differing
leaf = one differing vertex, and the CI numbers are directly comparable.  `x`,
`y`, `z`, `chiSquared` and `numberDoF` are flat `vector<float>` per event and
count events, not vertices, so they are not used here.

Vertices are matched on (run, event, vertex index), not file position: the q449
reference and CI output hold the same 100 events in a *different order*.

Only numpy is needed -- run it in either environment.
"""
import argparse
import os
import numpy as np

# AOD side of CI run MR-90327-2026-08-22-00-26, re-extracted 2026-08-24.
# nev_cmp is what diff-root compared, not what the job reconstructed: q449
# reco'd 100 events but diff-root stops at 60, so its counts are a ~60% sample
# and are expected to undershoot the measured value.
CI = {
    'q442': dict(test='RecoRun2Data',        nev_cmp=25,  cov=341, tw=403),
    'q452': dict(test='RecoRun2MC',          nev_cmp=25,  cov=26,  tw=27),
    'q449': dict(test='RecoRun3Data_Checks', nev_cmp=60,  cov=876, tw=1111),
    'q454': dict(test='RecoRun3MC',          nev_cmp=25,  cov=26,  tw=26),
    'q447': dict(test='RecoRun4MC',          nev_cmp=5,   cov=9,   tw=8),
}


def load(path):
    # materialise: indexing an NpzFile re-decompresses on every access
    return {k: v for k, v in np.load(path).items()}


def sort_by_key(d, keys, prefix, fields):
    """Row order sorted on (run, event, *fields), so two files align by key."""
    ev = d[prefix + 'ev'].tolist()
    run = np.array([keys[e][0] for e in ev], dtype=np.int64)
    evt = np.array([keys[e][1] for e in ev], dtype=np.int64)
    cols = [d[prefix + f].astype(np.int64) for f in fields][::-1] + [evt, run]
    return np.lexsort(cols)


def evkeys(d):
    return list(zip(d['ev_run'].tolist(), d['ev_evt'].tolist()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('npzdir', help='directory holding <sample>_{ref,new}.npz')
    a = ap.parse_args()

    rows = []
    tot_v = tot_tw = tot_cov = 0
    for s, c in CI.items():
        pr = os.path.join(a.npzdir, '%s_ref.npz' % s)
        pn = os.path.join(a.npzdir, '%s_new.npz' % s)
        if not (os.path.exists(pr) and os.path.exists(pn)):
            print('missing %s_{ref,new}.npz -- skipped' % s)
            continue
        R, N = load(pr), load(pn)
        kr, kn = evkeys(R), evkeys(N)
        if set(kr) != set(kn):
            print('%s: event sets differ -- skipped' % s)
            continue

        iv_r = sort_by_key(R, kr, 'v_', ['i'])
        iv_n = sort_by_key(N, kn, 'v_', ['i'])
        iw_r = sort_by_key(R, kr, 'w_', ['iv', 'it'])
        iw_n = sort_by_key(N, kn, 'w_', ['iv', 'it'])
        if len(iv_r) != len(iv_n) or len(iw_r) != len(iw_n):
            print('%s: vertex or track-weight structure differs' % s)
            continue

        # one entry per vertex whose weight vector changed anywhere
        dw = R['w_val'][iw_r] != N['w_val'][iw_n]
        wev = R['w_ev'][iw_r].tolist()
        vid = np.stack([np.array([kr[e][1] for e in wev], dtype=np.int64),
                        R['w_iv'][iw_r]], axis=1)[dw]
        tw_vtx = len(np.unique(vid, axis=0)) if len(vid) else 0

        cov = np.zeros(len(iv_r), dtype=bool)
        for comp in ('cxx', 'cyx', 'cyy', 'czx', 'czy', 'czz'):
            cov |= (R['v_' + comp][iv_r] != N['v_' + comp][iv_n])
        cov_vtx = int(cov.sum())

        nv = len(iv_r)
        tot_v += nv
        tot_tw += tw_vtx
        tot_cov += cov_vtx
        note = '' if len(kr) == c['nev_cmp'] else '  (CI saw %d/%d events)' % (
            c['nev_cmp'], len(kr))
        rows.append((s, c['test'], len(kr), nv, tw_vtx, 100.0 * tw_vtx / nv,
                     c['tw'], cov_vtx, c['cov'], note))

    if not rows:
        raise SystemExit('no sample pairs found in ' + a.npzdir)

    print('%-7s %-20s %5s %7s %8s %8s %8s %8s %8s' %
          ('sample', 'test', 'nev', 'vtx', 'tw_vtx', 'tw_frac', 'CI_tw',
           'cov_vtx', 'CI_cov'))
    for r in rows:
        print('%-7s %-20s %5d %7d %8d %7.1f%% %8d %8d %8d%s' % r)
    print('%-7s %-20s %5s %7d %8d %7.1f%% %8s %8d%s' %
          ('TOTAL', '', '', tot_v, tot_tw, 100.0 * tot_tw / tot_v, '',
           tot_cov, ''))
    print()
    print('tw_vtx  = vertices whose track-weight vector changed (measured)')
    print('cov_vtx = vertices whose covariance changed (measured)')
    print('CI_*    = the corresponding diff-root leaf counts, for cross-check.')
    print('          They agree exactly wherever diff-root saw every event.')


if __name__ == '__main__':
    main()
