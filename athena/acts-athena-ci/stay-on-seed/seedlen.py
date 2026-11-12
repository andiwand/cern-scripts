#!/usr/bin/env python3
"""Seed length (space points) vs |eta| from the S lines of the dump (all processed primary seeds).
Pixel: nmeas = nSP; strip: nmeas = 2 nSP. usage: seedlen.py sos.txt out.json out_dir"""
import sys, json, collections, statistics as st
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt, matplotlib.ticker
V = {0: collections.defaultdict(list), 1: collections.defaultdict(list)}
for l in open(sys.argv[1]):
    if l[0] != 'S': continue
    f = l.split(); ty = int(f[2]); e = abs(float(f[4]))
    if e >= 4: continue
    V[ty][int(e / 0.25)].append(int(f[7]) // (1 if ty == 0 else 2))
def q(v, p): v = sorted(v); return v[min(int(p * len(v)), len(v) - 1)]
out = {}
for ty, name in ((0, "pixel"), (1, "strip")):
    bins = {}
    for b, v in sorted(V[ty].items()):
        if len(v) < 50: continue
        c = collections.Counter(min(x, 6) for x in v)
        bins[b] = dict(**{f"len:{k}": c[k] for k in (3, 4, 5, 6)}, all=len(v), n=len(v), p5=q(v, .05), p25=q(v, .25), p50=q(v, .5), p75=q(v, .75), p95=q(v, .95), mean=st.mean(v), min=min(v), max=max(v))
    out[name] = dict(edges=[i * 0.25 for i in range(17)], bins=bins)
    print(name, " ".join(f"{b*0.25:.2f}:{x['p50']}({x['p25']}-{x['p75']}) " for b, x in bins.items()))
json.dump(out, open(sys.argv[2], "w"), indent=1)
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": "#e6e6e6", "axes.axisbelow": True})
fig, axs = plt.subplots(1, 2, figsize=(10, 3.6))
for ax, (name, c) in zip(axs, (("pixel", "#2a78d6"), ("strip", "#eb6834"))):
    B = out[name]["bins"]
    stats = [dict(med=x["p50"], q1=x["p25"], q3=x["p75"], whislo=x["min"], whishi=x["max"], mean=x["mean"], label=f"{b*0.25:g}") for b, x in B.items()]
    pos = [b * 0.25 + 0.125 for b in B]
    ax.bxp(stats, positions=pos, widths=0.18, showmeans=True, showfliers=False, patch_artist=True,
           boxprops=dict(facecolor=c, alpha=0.35, edgecolor=c), medianprops=dict(color=c, linewidth=2),
           whiskerprops=dict(color=c), capprops=dict(color=c), meanprops=dict(marker="o", markerfacecolor="white", markeredgecolor=c, markersize=4))
    ax.set_xticks([i * 0.5 for i in range(9 if name == "pixel" else 6)]); ax.set_xticklabels([f"{i*0.5:g}" for i in range(9 if name == "pixel" else 6)])
    ax.yaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True)); ax.set_xlabel("|η| of the seed"); ax.set_ylabel("space points per seed"); ax.set_title(f"{name} seeds: space points per seed", loc="left", fontsize=10)
fig.text(0.01, 0.01, "box: 25–75%, line: median, dot: mean, whiskers: min to max", fontsize=8, color="#666")
fig.tight_layout(rect=(0, 0.04, 1, 1)); fig.savefig(f"{sys.argv[3]}/gbts-seed-length.png", dpi=130)
