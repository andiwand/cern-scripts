#!/usr/bin/env python
"""Compare two extract_pv.py dumps and produce the diff plots.

    compare_pv.py REF.npz NEW.npz LABEL OUTDIR

Everything is a *paired* comparison: vertices are matched on
(run, event, vertex index), track weights on (run, event, vertex, track).
"""
import argparse
import os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

UM = 1000.0  # mm -> um

TAUTRK_VARS = ['d0TJVA', 'd0SigTJVA', 'z0sinthetaTJVA', 'z0sinthetaSigTJVA',
               'rnn_chargedScore', 'rnn_conversionScore', 'rnn_fakeScore',
               'rnn_isolationScore']
TAUJET_VARS = ['NNDecayModeProb_1p0n', 'NNDecayModeProb_1p1n',
               'NNDecayModeProb_1pXn', 'NNDecayModeProb_3p0n',
               'NNDecayModeProb_3pXn', 'absipSigLeadTrk', 'RNNEleScore',
               'RNNEleScoreSigTrans', 'trFlightPathSig', 'mIntermediateAxis']


def load(p):
    return dict(np.load(p, allow_pickle=True))


def save(fig, outdir, fname):
    """Write the figure as both PNG and PDF.

    PNG for pasting into the MR thread, PDF because the pulls sit at 1e-6 and
    only stay readable zoomed in.
    """
    stem = os.path.join(outdir, os.path.splitext(fname)[0])
    for ext in ('png', 'pdf'):
        fig.savefig('%s.%s' % (stem, ext), dpi=130, bbox_inches='tight')


def evkeys(d):
    return list(zip(d['ev_run'].tolist(), d['ev_evt'].tolist()))


def match(keys_a, keys_b):
    """Return row indices into a and b for the common keys, in a's order."""
    mb = {}
    for j, k in enumerate(keys_b):
        mb.setdefault(k, j)
    ia, ib = [], []
    for i, k in enumerate(keys_a):
        j = mb.get(k)
        if j is not None:
            ia.append(i)
            ib.append(j)
    return np.asarray(ia, dtype=int), np.asarray(ib, dtype=int)


def sub_keys(d, prefix, *idx_fields):
    ek = evkeys(d)
    rows = d[prefix + 'ev'].astype(int)
    cols = [d[prefix + f].astype(int) for f in idx_fields]
    return [tuple([ek[r]] + [int(c[n]) for c in cols]) for n, r in enumerate(rows)]


def stats(x):
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if x.size == 0:
        return dict(n=0, nz=0, med=np.nan, p99=np.nan, mx=np.nan, mean=np.nan)
    ax = np.abs(x)
    nz = ax[ax > 0]
    return dict(n=x.size, nz=int(nz.size), mean=float(x.mean()),
                med=float(np.median(nz)) if nz.size else 0.0,
                p99=float(np.percentile(nz, 99)) if nz.size else 0.0,
                mx=float(ax.max()))


def two_panel(fig, gs_row, delta, name, unit=''):
    """Left: |delta| on log x. Right: signed delta, linear, clipped to p99."""
    s = stats(delta)
    d = np.asarray(delta, dtype=float)
    d = d[np.isfinite(d)]
    ad = np.abs(d)
    nz = ad[ad > 0]

    ax1 = fig.add_subplot(gs_row[0])
    if nz.size:
        lo, hi = nz.min() * 0.5, nz.max() * 2
        lo = max(lo, hi * 1e-12)
        ax1.hist(nz, bins=np.geomspace(lo, hi, 60), histtype='step', lw=1.6)
        ax1.axvline(s['med'], ls='--', lw=1, color='C1',
                    label='median %.3g' % s['med'])
        ax1.axvline(s['mx'], ls=':', lw=1, color='C3', label='max %.3g' % s['mx'])
        ax1.set_xscale('log')
        if np.histogram(nz, bins=60)[0].max() > 30:
            ax1.set_yscale('log')
    ax1.set_xlabel('|d(%s)|%s' % (name, unit))
    ax1.set_ylabel('entries')
    ax1.set_title('%s  (N=%d, changed=%d)' % (name, s['n'], s['nz']), fontsize=9)
    if nz.size:
        ax1.legend(fontsize=7)

    ax2 = fig.add_subplot(gs_row[1])
    # only the vertices that actually moved: the zero spike would swamp the shape
    dnz = d[ad > 0]
    if dnz.size:
        lim = float(np.percentile(nz, 99)) or float(nz.max())
        ax2.hist(np.clip(dnz, -lim, lim), bins=61, range=(-lim, lim),
                 histtype='step', lw=1.6)
    ax2.axvline(0, color='k', lw=0.6)
    ax2.set_xlabel('d(%s)%s' % (name, unit))
    ax2.set_ylabel('entries')
    mean_nz = float(dnz.mean()) if dnz.size else 0.0
    ax2.set_title('signed, changed only, clipped at p99; mean %.3g' % mean_nz,
                  fontsize=8)
    return s


def block(outdir, label, deltas, fname, title):
    """deltas: list of (name, values, unit)."""
    import matplotlib.gridspec as gridspec
    nrow = len(deltas)
    fig = plt.figure(figsize=(9, 3.0 * nrow))
    gs = gridspec.GridSpec(nrow, 2, figure=fig, hspace=0.55, wspace=0.28)
    out = {}
    for r, (name, vals, unit) in enumerate(deltas):
        out[name] = two_panel(fig, [gs[r, 0], gs[r, 1]], vals, name, unit)
    fig.suptitle('%s - %s' % (label, title), fontsize=11)
    save(fig, outdir, fname)
    plt.close(fig)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('ref')
    ap.add_argument('new')
    ap.add_argument('label')
    ap.add_argument('outdir')
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)

    R, N = load(a.ref), load(a.new)
    S = {}

    # ---- events -----------------------------------------------------------
    er, en = match(evkeys(R), evkeys(N))
    S['events_ref'] = len(evkeys(R))
    S['events_new'] = len(evkeys(N))
    S['events_matched'] = len(er)

    nvr, nvn = R['ev_nvtx'][er], N['ev_nvtx'][en]
    S['events_nvtx_changed'] = int((nvr != nvn).sum())

    # ---- vertices ---------------------------------------------------------
    vr, vn = match(sub_keys(R, 'v_', 'i'), sub_keys(N, 'v_', 'i'))
    S['vertices_matched'] = len(vr)

    def dv(k, scale=1.0):
        return (N['v_' + k][vn] - R['v_' + k][vr]) * scale

    dx, dy, dz = dv('x', UM), dv('y', UM), dv('z', UM)
    sx = np.sqrt(np.where(R['v_cxx'][vr] > 0, R['v_cxx'][vr], np.nan)) * UM
    sy = np.sqrt(np.where(R['v_cyy'][vr] > 0, R['v_cyy'][vr], np.nan)) * UM
    sz = np.sqrt(np.where(R['v_czz'][vr] > 0, R['v_czz'][vr], np.nan)) * UM

    chi2r, chi2n = R['v_chi2'][vr], N['v_chi2'][vn]
    ndofr, ndofn = R['v_ndof'][vr], N['v_ndof'][vn]
    dchi2 = chi2n - chi2r
    dndof = ndofn - ndofr
    with np.errstate(divide='ignore', invalid='ignore'):
        dchi2ndof = np.where(ndofr > 0, chi2n / np.where(ndofn > 0, ndofn, np.nan)
                             - chi2r / np.where(ndofr > 0, ndofr, np.nan), np.nan)
    dntrk = N['v_ntrk'][vn] - R['v_ntrk'][vr]
    dsumw = N['v_sumw'][vn] - R['v_sumw'][vr]
    S['vertices_ntrk_changed'] = int((dntrk != 0).sum())

    changed = ((dx != 0) | (dy != 0) | (dz != 0) | (dchi2 != 0) |
               (dndof != 0) | (dsumw != 0))
    S['vertices_changed'] = int(changed.sum())
    S['vertices_changed_frac'] = (float(changed.mean()) if len(vr) else float('nan'))

    # fig 01 / 02 / 03 / 05
    s1 = block(a.outdir, a.label,
               [('x', dx, ' [um]'), ('y', dy, ' [um]'), ('z', dz, ' [um]')],
               'fig01_delta_position.png', 'vertex position shift')
    s2 = block(a.outdir, a.label,
               [('x/sigma_x', dx / sx, ''), ('y/sigma_y', dy / sy, ''),
                ('z/sigma_z', dz / sz, '')],
               'fig02_delta_position_pull.png',
               'shift relative to fitted resolution  <-- HEADLINE')
    s3 = block(a.outdir, a.label,
               [('chi2', dchi2, ''), ('chi2/ndof', dchi2ndof, ''),
                ('ndof', dndof, '')],
               'fig03_delta_fitquality.png', 'fit quality')
    with np.errstate(divide='ignore', invalid='ignore'):
        rsx = np.sqrt(np.where(N['v_cxx'][vn] > 0, N['v_cxx'][vn], np.nan)) * UM / sx - 1
        rsy = np.sqrt(np.where(N['v_cyy'][vn] > 0, N['v_cyy'][vn], np.nan)) * UM / sy - 1
        rsz = np.sqrt(np.where(N['v_czz'][vn] > 0, N['v_czz'][vn], np.nan)) * UM / sz - 1
    s5 = block(a.outdir, a.label,
               [('sigma_x ratio-1', rsx, ''), ('sigma_y ratio-1', rsy, ''),
                ('sigma_z ratio-1', rsz, '')],
               'fig05_delta_sigma.png', 'fitted uncertainty')

    # ---- track weights (fig 04) -------------------------------------------
    wr, wn = match(sub_keys(R, 'w_', 'iv', 'it'), sub_keys(N, 'w_', 'iv', 'it'))
    dw = N['w_val'][wn] - R['w_val'][wr]
    S['trackweights_matched'] = len(wr)
    S['trackweights_changed'] = int((dw != 0).sum())
    s4 = block(a.outdir, a.label,
               [('track weight', dw, ''), ('sum of weights', dsumw, ''),
                ('n tracks / vertex', dntrk.astype(float), '')],
               'fig04_delta_weights.png', 'annealing weights (the root cause)')

    # ---- fig 06 trends ----------------------------------------------------
    fig, axs = plt.subplots(1, 3, figsize=(13, 3.8))
    for ax, xv, xl in ((axs[0], R['v_z'][vr], 'vertex z [mm]'),
                       (axs[1], R['v_ntrk'][vr].astype(float), 'n tracks'),
                       (axs[2], sz, 'sigma_z [um]')):
        ax.scatter(xv, np.abs(dz), s=6, alpha=0.4)
        ax.set_yscale('log')
        ax.set_xlabel(xl)
        ax.set_ylabel('|dz| [um]')
    if np.isfinite(sz).any():
        axs[2].set_xscale('log')
    fig.suptitle('%s - is the shift correlated with anything?' % a.label)
    save(fig, a.outdir, 'fig06_trends.png')
    plt.close(fig)

    # ---- fig 07 nVtx ------------------------------------------------------
    fig, axs = plt.subplots(1, 2, figsize=(10, 3.8))
    mx = int(max(nvr.max(), nvn.max())) if len(nvr) else 1
    bins = np.arange(-0.5, mx + 1.5)
    axs[0].hist(nvr, bins=bins, histtype='step', lw=1.8, label='reference')
    axs[0].hist(nvn, bins=bins, histtype='step', lw=1.8, ls='--', label='new')
    axs[0].set_xlabel('n vertices / event')
    axs[0].set_ylabel('events')
    axs[0].legend(fontsize=8)
    axs[1].hist(nvn - nvr, bins=np.arange(-5.5, 6.5), histtype='step', lw=1.8)
    axs[1].set_xlabel('d(n vertices) / event')
    axs[1].set_title('events changed: %d / %d' % (S['events_nvtx_changed'], len(er)),
                     fontsize=9)
    fig.suptitle('%s - vertex multiplicity' % a.label)
    save(fig, a.outdir, 'fig07_nvtx.png')
    plt.close(fig)

    # ---- fig 08 hard-scatter vertex ---------------------------------------
    hs = (R['v_i'][vr] == 0)
    dz_hs = dz[hs]
    S['hs_vertex_reassigned'] = int((np.abs(dz_hs) > 1000.0).sum())  # >1 mm = different vertex
    fig, axs = plt.subplots(1, 2, figsize=(10, 3.8))
    if dz_hs.size:
        nzh = np.abs(dz_hs)[np.abs(dz_hs) > 0]
        if nzh.size:
            axs[0].hist(nzh, bins=np.geomspace(nzh.min() * 0.5, nzh.max() * 2, 40),
                        histtype='step', lw=1.8)
            axs[0].set_xscale('log')
        axs[0].set_yscale('log')
        axs[0].set_xlabel('|dz| of PV[0] [um]')
        axs[1].plot(np.abs(dz_hs), 'o', ms=3)
        axs[1].set_yscale('log')
        axs[1].set_xlabel('matched event')
        axs[1].set_ylabel('|dz| of PV[0] [um]')
    axs[1].set_title('PV[0] moved by >1 mm in %d events' % S['hs_vertex_reassigned'],
                     fontsize=9)
    fig.suptitle('%s - hard-scatter vertex' % a.label)
    save(fig, a.outdir, 'fig08_hs_vertex.png')
    plt.close(fig)

    # ---- fig 09 / 10 tau --------------------------------------------------
    def tau_fig(prefix, varlist, fname, title):
        kr = sub_keys(R, prefix, 'i')
        kn = sub_keys(N, prefix, 'i')
        if not kr or not kn:
            return 0
        ir, inn = match(kr, kn)
        if len(ir) == 0:
            return 0
        ncol = 4
        nrow = int(np.ceil(len(varlist) / ncol))
        fig, axs = plt.subplots(nrow, ncol, figsize=(3.1 * ncol, 3.0 * nrow))
        axs = np.atleast_1d(axs).ravel()
        nch = 0
        for k, var in enumerate(varlist):
            ax = axs[k]
            o = R[prefix + var][ir]
            n_ = N[prefix + var][inn]
            m = np.isfinite(o) & np.isfinite(n_)
            nch += int((o[m] != n_[m]).sum())
            ax.scatter(o[m], n_[m], s=5, alpha=0.4)
            if m.any():
                lo, hi = float(np.nanmin(o[m])), float(np.nanmax(o[m]))
                ax.plot([lo, hi], [lo, hi], 'k-', lw=0.6)
            ax.set_title('%s (%d differ)' % (var, int((o[m] != n_[m]).sum())), fontsize=7)
            ax.tick_params(labelsize=6)
        for k in range(len(varlist), len(axs)):
            axs[k].axis('off')
        fig.suptitle('%s - %s (reference on x, new on y)' % (a.label, title))
        fig.tight_layout(rect=[0, 0, 1, 0.95])
        save(fig, a.outdir, fname)
        plt.close(fig)
        return nch

    S['tautrack_values_changed'] = tau_fig('tt_', TAUTRK_VARS, 'fig09_tau_tracks.png',
                                           'tau track TJVA / RNN')
    S['taujet_values_changed'] = tau_fig('tj_', TAUJET_VARS, 'fig10_tau_jets.png',
                                         'tau jet')

    # ---- fig 11 the overlays (for completeness) ---------------------------
    fig, axs = plt.subplots(2, 3, figsize=(13, 6.4),
                            gridspec_kw=dict(height_ratios=[3, 1]))
    with np.errstate(divide='ignore', invalid='ignore'):
        qr = np.where(ndofr > 0, chi2r / ndofr, np.nan)
        qn = np.where(ndofn > 0, chi2n / ndofn, np.nan)
    panels = [('n tracks / vertex', R['v_ntrk'][vr].astype(float), N['v_ntrk'][vn].astype(float)),
              ('chi2 / ndof', qr, qn),
              ('vertex z [mm]', R['v_z'][vr], N['v_z'][vn])]
    for c, (nm, o, n_) in enumerate(panels):
        m = np.isfinite(o) & np.isfinite(n_)
        lo, hi = float(np.nanmin(o[m])), float(np.nanmax(o[m]))
        bins = np.linspace(lo, hi, 41)
        ho, _ = np.histogram(o[m], bins=bins)
        hn, _ = np.histogram(n_[m], bins=bins)
        ctr = 0.5 * (bins[1:] + bins[:-1])
        axs[0, c].step(ctr, ho, where='mid', lw=1.8, label='reference')
        axs[0, c].step(ctr, hn, where='mid', lw=1.8, ls='--', label='new')
        axs[0, c].set_ylabel('entries')
        axs[0, c].legend(fontsize=7)
        axs[0, c].set_title(nm, fontsize=9)
        axs[1, c].step(ctr, hn - ho, where='mid', lw=1.4, color='C3')
        axs[1, c].axhline(0, color='k', lw=0.6)
        axs[1, c].set_ylabel('new - ref')
        axs[1, c].set_xlabel(nm)
    fig.suptitle('%s - unpaired overlays (%d events; low stats by construction)'
                 % (a.label, S['events_matched']))
    save(fig, a.outdir, 'fig11_overlays.png')
    plt.close(fig)

    # ---- summary ----------------------------------------------------------
    lines = ['# %s' % a.label, '']
    lines.append('| quantity | value |')
    lines.append('|---|---|')
    for k in ('events_ref', 'events_new', 'events_matched', 'events_nvtx_changed',
              'vertices_matched', 'vertices_changed', 'vertices_changed_frac',
              'vertices_ntrk_changed', 'trackweights_matched',
              'trackweights_changed', 'hs_vertex_reassigned',
              'tautrack_values_changed', 'taujet_values_changed'):
        val = S[k]
        lines.append('| %s | %s |' % (k, ('%.4f' % val) if isinstance(val, float) else val))
    lines.append('')
    lines.append('| shift | changed | median | p99 | max |')
    lines.append('|---|---|---|---|---|')
    for nm, s in (('dx [um]', s1['x']), ('dy [um]', s1['y']), ('dz [um]', s1['z']),
                  ('dx/sx', s2['x/sigma_x']), ('dy/sy', s2['y/sigma_y']),
                  ('dz/sz', s2['z/sigma_z']),
                  ('dchi2', s3['chi2']), ('dchi2/ndof', s3['chi2/ndof']),
                  ('dndof', s3['ndof']),
                  ('dw', s4['track weight']), ('dsumw', s4['sum of weights']),
                  ('dsigma_z/sigma_z', s5['sigma_z ratio-1'])):
        lines.append('| %s | %d | %.4g | %.4g | %.4g |'
                     % (nm, s['nz'], s['med'], s['p99'], s['mx']))
    txt = '\n'.join(lines) + '\n'
    with open(os.path.join(a.outdir, 'summary.md'), 'w') as fh:
        fh.write(txt)
    print(txt)


if __name__ == '__main__':
    main()
