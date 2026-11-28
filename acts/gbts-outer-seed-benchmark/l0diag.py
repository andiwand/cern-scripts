#!/usr/bin/env python3
"""Why does the inward pass miss the innermost hit? Run in the uv env."""

import collections
import pathlib
import sys

import awkward as ak
import numpy as np
import uproot

exec(open(pathlib.Path(__file__).parent / "analyze.py").read().split("def innermost_pixel_layer")[0])

PIXEL = (16, 17, 18)
d = pathlib.Path(sys.argv[1])
v = sys.argv[2]
stage = sys.argv[3] if len(sys.argv) > 3 else "ambi"

# sim hits per (event, particle): innermost pixel layer and the hits on it
h = uproot.open(d / "hits.root")["hits"].arrays(
    ["event_id", "volume_id", "layer_id", "sensitive_id", "tx", "ty", "tz"]
    + [f"barcode_{i}" for i in ID], library="np")
hk = key([h[f"barcode_{i}"].astype(np.int64) for i in ID])
pix = np.isin(h["volume_id"], PIXEL)
hr = np.hypot(h["tx"], h["ty"])
innerLayer = {}
hitsOn = collections.defaultdict(list)
order = np.argsort(hr)
for j in order:
    if not pix[j]:
        continue
    p = (int(h["event_id"][j]), int(hk[j]))
    lay = (int(h["volume_id"][j]), int(h["layer_id"][j]))
    innerLayer.setdefault(p, lay)
    hitsOn[(p, lay)].append((int(h["sensitive_id"][j]),
                             np.array([h["tx"][j], h["ty"][j], h["tz"][j]])))

S = uproot.open(d / v / f"tracksummary_{v}_{stage}.root")["tracksummary"].arrays(
    ["event_nr", "trackClassification", "t_pT", "t_eta"]
    + [f"majorityParticleId_{i}" for i in ID])
sm = {}
for e in range(len(S)):
    for n in range(len(S.trackClassification[e])):
        sm[(int(S.event_nr[e]), n)] = (
            int(S.trackClassification[e][n]),
            key([int(S[f"majorityParticleId_{i}"][e][n]) for i in ID]),
            float(S.t_pT[e][n]), float(S.t_eta[e][n]))

T = uproot.open(d / v / f"trackstates_{v}_{stage}.root")["trackstates"].arrays(
    ["event_nr", "track_nr", "stateType", "volume_id", "layer_id", "module_id",
     "chi2", "t_x", "t_y", "g_x_prt", "g_y_prt", "g_z_prt", "err_eLOC0_prt",
     "err_eLOC1_prt", "predicted"] + [f"particle_ids_{i}" for i in ID])
L = {k: T[k].tolist() for k in T.fields}
PK = key([ak.values_astype(T[f"particle_ids_{i}"], np.int64) for i in ID]).tolist()

cats = collections.Counter()
lastStates = collections.Counter()
outlierChi2 = []
holePull = []
etaMissing = []
chi2ByLayer = collections.defaultdict(list)
for j in range(len(T)):
    e, n = int(L["event_nr"][j]), int(L["track_nr"][j])
    c, m, pt, eta = sm[(e, n)]
    if c not in (1, 2):
        continue
    st = np.array(L["stateType"][j])
    vol = L["volume_id"][j]
    lay = L["layer_id"][j]
    mod = L["module_id"][j]
    chi2 = L["chi2"][j]
    # chi2 of the own accepted hits per pixel layer, for the calibration
    for k in np.where(st == 0)[0]:
        if vol[k] in PIXEL and m in PK[j][k]:
            chi2ByLayer[(vol[k], lay[k])].append(chi2[k])
    mi = np.where(st == 0)[0]
    if len(mi) == 0:
        continue
    r = np.hypot(np.array(L["t_x"][j], float), np.array(L["t_y"][j], float))
    i = mi[np.argmin(r[mi])]
    p = (e, m)
    true = innerLayer.get(p)
    if true is None or m not in PK[j][i] or (vol[i], lay[i]) == true:
        continue
    # missing: what does the track hold on the true innermost layer?
    etaMissing.append(abs(eta))
    onTrue = [k for k in range(len(st)) if (vol[k], lay[k]) == true and st[k] != 3]
    if not onTrue:
        mat = any((vol[k], lay[k]) == true for k in range(len(st)))
        # states are ordered outermost first, so the last one is the innermost
        last = (vol[-1], lay[-1], int(st[-1]))
        cats[f"no state on layer 0, {'material state there' if mat else 'layer not crossed'}"] += 1
        lastStates[last] += 1
        continue
    k = onTrue[0]
    modules = {s for s, _ in hitsOn[(p, true)]}
    if st[k] == 1:
        own = m in PK[j][k]
        cats[f"outlier ({'own' if own else 'other'} hit)"] += 1
        if own:
            outlierChi2.append(chi2[k])
    elif st[k] == 2:
        if mod[k] not in modules:
            cats["hole on another module"] += 1
            continue
        cats["hole on the hit's module"] += 1
        pos = [x for s, x in hitsOn[(p, true)] if s == mod[k]][0]
        pred = np.array([L["g_x_prt"][j][k], L["g_y_prt"][j][k], L["g_z_prt"][j][k]])
        if not np.all(np.isfinite(pred)):
            continue
        delta = pos - pred
        rphi = np.array([-pos[1], pos[0]]) / np.hypot(pos[0], pos[1])
        holePull.append((abs(delta[:2] @ rphi) / L["err_eLOC0_prt"][j][k],
                         abs(delta[2]) / L["err_eLOC1_prt"][j][k],
                         abs(delta[:2] @ rphi) * 1e3, abs(delta[2]) * 1e3))
    else:
        cats[f"state type {st[k]}"] += 1

print(d.name, v, stage, "missing", sum(cats.values()))
for k, c in cats.most_common():
    print(f"  {c:5d}  {k}")
if outlierChi2:
    print("  outlier chi2 of own hits: median", round(float(np.median(outlierChi2)), 1))
if holePull:
    hp = np.array(holePull)
    print("  holes on the hit's module: median |res rphi| µm", round(float(np.median(hp[:, 2])), 1),
          "|res z| µm", round(float(np.median(hp[:, 3])), 1),
          " median |pull| rphi", round(float(np.median(hp[:, 0])), 1), "z", round(float(np.median(hp[:, 1])), 1))
print("  innermost state of the no-state tracks (vol, layer, type):", lastStates.most_common(6))
print("  |eta| of missing", np.histogram(etaMissing, bins=[0, 0.5, 1, 1.5, 2, 2.5, 3])[0])
print("  chi2 of own accepted hits per pixel layer: layer, n, mean, P(>15) %, P(>10) %")
for lk in sorted(chi2ByLayer):
    x = np.array(chi2ByLayer[lk])
    if len(x) > 500:
        print(f"    {lk}  {len(x):7d}  {x.mean():.2f}  {100*np.mean(x>15):.3f}  {100*np.mean(x>10):.3f}")
