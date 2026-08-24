#!/usr/bin/env python
"""Dump PrimaryVertices (+ tau) quantities from an xAOD into a .npz.

    extract_pv.py INPUT.pool.root OUTPUT.npz [-n NEVENTS]

Needs an Athena/AnalysisBase environment (reads via the xAOD transient tree).
Part of the ACTS 47.5.0 bump study, athena!90327.
"""
import argparse
import numpy as np
import ROOT

# Amg::compress packs a symmetric 3x3 row-major over the lower triangle:
#   (0,0) (1,0) (1,1) (2,0) (2,1) (2,2)  ->  xx yx yy zx zy zz
# EventPrimitives/EventPrimitivesHelpers.h:55
CIDX = dict(xx=0, yx=1, yy=2, zx=3, zy=4, zz=5)

TAUTRK_VARS = ['d0TJVA', 'd0SigTJVA', 'z0sinthetaTJVA', 'z0sinthetaSigTJVA',
               'rnn_chargedScore', 'rnn_conversionScore', 'rnn_fakeScore',
               'rnn_isolationScore']
TAUJET_VARS = ['NNDecayModeProb_1p0n', 'NNDecayModeProb_1p1n',
               'NNDecayModeProb_1pXn', 'NNDecayModeProb_3p0n',
               'NNDecayModeProb_3pXn', 'absipSigLeadTrk', 'RNNEleScore',
               'RNNEleScoreSigTrans', 'trFlightPathSig', 'mIntermediateAxis']

NAN = float('nan')


def aux(obj, name):
    """Read a float aux variable; NaN if it is not on the object."""
    try:
        if not obj.isAvailable['float'](name):
            return NAN
        return float(obj.auxdataConst['float'](name))
    except Exception:
        return NAN


def container(tree, name):
    try:
        c = getattr(tree, name)
        return c if c else None
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('infile')
    ap.add_argument('outfile')
    ap.add_argument('-n', '--nevents', type=int, default=-1)
    ap.add_argument('--pv', default='PrimaryVertices')
    ap.add_argument('--tree', default='CollectionTree')
    a = ap.parse_args()

    ROOT.xAOD.Init().ignore()
    fin = ROOT.TFile.Open(a.infile)
    if not fin or fin.IsZombie():
        raise SystemExit('cannot open ' + a.infile)
    t = ROOT.xAOD.MakeTransientTree(fin, a.tree)

    n = int(t.GetEntries())
    if a.nevents > 0:
        n = min(n, a.nevents)
    print('%s: %d entries' % (a.infile, n))

    ev = dict(run=[], evt=[], nvtx=[])
    vk = ('ev', 'i', 'x', 'y', 'z', 'chi2', 'ndof', 'ntrk', 'sumw', 'vtype',
          'cxx', 'cyx', 'cyy', 'czx', 'czy', 'czz')
    v = {k: [] for k in vk}
    w = {k: [] for k in ('ev', 'iv', 'it', 'val')}
    tt = {k: [] for k in ['ev', 'i'] + TAUTRK_VARS}
    tj = {k: [] for k in ['ev', 'i'] + TAUJET_VARS}

    for ie in range(n):
        t.GetEntry(ie)
        ei = t.EventInfo
        ev['run'].append(int(ei.runNumber()))
        ev['evt'].append(int(ei.eventNumber()))

        pvs = container(t, a.pv)
        ev['nvtx'].append(0 if pvs is None else int(pvs.size()))
        if pvs is not None:
            for iv in range(pvs.size()):
                vx = pvs.at(iv)
                cov = vx.covariance()
                tw = vx.trackWeights()
                tws = [float(tw[j]) for j in range(tw.size())]
                v['ev'].append(ie)
                v['i'].append(iv)
                v['x'].append(float(vx.x()))
                v['y'].append(float(vx.y()))
                v['z'].append(float(vx.z()))
                v['chi2'].append(float(vx.chiSquared()))
                v['ndof'].append(float(vx.numberDoF()))
                v['ntrk'].append(len(tws))
                v['sumw'].append(float(sum(tws)))
                try:
                    v['vtype'].append(int(vx.vertexType()))
                except Exception:
                    v['vtype'].append(-1)
                for key, j in CIDX.items():
                    v['c' + key].append(float(cov[j]) if cov.size() > j else NAN)
                for it_, val in enumerate(tws):
                    w['ev'].append(ie)
                    w['iv'].append(iv)
                    w['it'].append(it_)
                    w['val'].append(val)

        trks = container(t, 'TauTracks')
        if trks is not None:
            for i in range(trks.size()):
                o = trks.at(i)
                tt['ev'].append(ie)
                tt['i'].append(i)
                for var in TAUTRK_VARS:
                    tt[var].append(aux(o, var))

        taus = container(t, 'TauJets')
        if taus is not None:
            for i in range(taus.size()):
                o = taus.at(i)
                tj['ev'].append(ie)
                tj['i'].append(i)
                for var in TAUJET_VARS:
                    tj[var].append(aux(o, var))

        if (ie + 1) % 10 == 0:
            print('  %d/%d' % (ie + 1, n))

    out = {}
    for k, val in ev.items():
        out['ev_' + k] = np.asarray(val, dtype=np.int64)
    for k, val in v.items():
        out['v_' + k] = np.asarray(val, dtype=(np.int64 if k in ('ev', 'i', 'ntrk', 'vtype') else np.float64))
    for k, val in w.items():
        out['w_' + k] = np.asarray(val, dtype=(np.float64 if k == 'val' else np.int64))
    for k, val in tt.items():
        out['tt_' + k] = np.asarray(val, dtype=(np.int64 if k in ('ev', 'i') else np.float64))
    for k, val in tj.items():
        out['tj_' + k] = np.asarray(val, dtype=(np.int64 if k in ('ev', 'i') else np.float64))
    out['meta_src'] = np.asarray([a.infile])

    np.savez_compressed(a.outfile, **out)
    print('wrote %s  (%d events, %d vertices, %d track weights)'
          % (a.outfile, n, len(v['ev']), len(w['ev'])))


if __name__ == '__main__':
    main()
