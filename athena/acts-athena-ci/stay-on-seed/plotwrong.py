#!/usr/bin/env python3
"""PNG plots for the note: seed truth classes (counts) and wrong SPs (% of matched + duplicate seeds).
usage: plotwrong.py gbtswrong2.json seedclass.json outdir truthpart.json matchedwho.json"""
import sys, json, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
d = json.load(open(sys.argv[1])); sc = json.load(open(sys.argv[2])); out = sys.argv[3]
POS = [("pos:front", "front", "#2a78d6"), ("pos:middle", "middle", "#eb6834"), ("pos:back", "back", "#1baf7a"), ("pos:several places", "several places", "#eda100")]
RUN = [("run:1", "1 SP", "#86b6ef"), ("run:2", "2 in a row", "#3987e5"), ("run:3", "3 in a row", "#1c5cab"), ("run:>=4", "≥4 in a row", "#0d366b")]
CLS = [("matched", "matched", "#2a78d6"), ("duplicate", "duplicate", "#eb6834"), ("fake", "fake", "#1baf7a"), ("unlinked", "unlinked", "#eda100")]
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": "#888", "axes.grid": True,
                     "grid.color": "#e6e6e6", "grid.linewidth": 0.6, "axes.axisbelow": True})
def nbins(D, det): return max(int(b) for b in D[det]["bins"]) + 1 - (det == "strip")
def stack(ax, D, det, series, frac, title, ylabel, xlabel="|η| of the seed", ncol=4):
    e = D[det]["edges"]; bins = D[det]["bins"]; nb = nbins(D, det)
    x = [(e[i] + e[i + 1]) / 2 for i in range(nb)]; bottom = [0] * nb
    for key, lab, c in series:
        v = [bins.get(str(i), {}).get(key, 0) for i in range(nb)]
        if frac: v = [100 * a / max(bins.get(str(i), {}).get("all", 1), 1) for i, a in enumerate(v)]
        ax.bar(x, v, width=0.25 * 0.88, bottom=bottom, color=c, label=lab, edgecolor="white", linewidth=0.8)
        bottom = [b + a for a, b in zip(v, bottom)]
    ax.set_ylim(0, max(bottom) * (1.22 if ncol >= len(series) else 1.35)); ax.legend(frameon=False, fontsize=8, loc="upper left", ncol=ncol)
    ax.set_title(title, fontsize=10, loc="left"); ax.set_xlabel(xlabel); ax.set_ylabel(ylabel)
fig, axs = plt.subplots(1, 2, figsize=(10, 3.6))
for ax, det in zip(axs, ("pixel", "strip")):
    stack(ax, sc, det, CLS, False, f"{det} seeds: truth", "seeds per bin (100 events)")
fig.tight_layout(); fig.savefig(f"{out}/gbts-seed-truth.png", dpi=130); plt.close(fig)
for det in ("pixel", "strip"):
    fig, axs = plt.subplots(1, 2, figsize=(10, 3.6))
    stack(axs[0], d, det, POS, True, f"{det} seeds: position of the wrong SPs", "% of matched + duplicate seeds")
    stack(axs[1], d, det, RUN, True, f"{det} seeds: longest run of wrong SPs", "% of matched + duplicate seeds")
    fig.tight_layout(); fig.savefig(f"{out}/gbts-wrong-sp-{det}.png", dpi=130); plt.close(fig)
tp = {"particles": json.load(open(sys.argv[4]))}
fig, axs = plt.subplots(1, 2, figsize=(10, 3.6))
stack(axs[0], tp, "particles", [("PU", "pileup", "#2a78d6"), ("HS", "hard scatter", "#eb6834"), ("sec", "reconstructable secondaries", "#1baf7a")], False, "reconstructable truth particles", "particles per bin (100 events)", "|η| of the particle")
stack(axs[1], tp, "particles", [("HS", "hard scatter", "#eb6834")], False, "reconstructable hard-scatter particles", "particles per bin (100 events)", "|η| of the particle")
fig.tight_layout(); fig.savefig(f"{out}/truth-particles.png", dpi=130); plt.close(fig)
mw = json.load(open(sys.argv[5]))
fig, axs = plt.subplots(1, 2, figsize=(10, 3.6))
MW = [("reco", "reconstructable", "#2a78d6"), ("lowpt", "primary, pT < 0.9 GeV", "#eb6834"), ("sec", "secondary (any pT)", "#1baf7a"), ("other", "other", "#eda100")]
for ax, det in zip(axs, ("pixel", "strip")):
    stack(ax, mw, det, MW, False, f"{det}: particles of the matched seeds", "matched seeds per bin (100 events)", ncol=2)
fig.tight_layout(); fig.savefig(f"{out}/matched-seed-particles.png", dpi=130); plt.close(fig)
print("ok")
