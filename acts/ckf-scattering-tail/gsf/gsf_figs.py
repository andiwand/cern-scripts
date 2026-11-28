"""Inline SVG figures for the GSF study note."""
import math, sys
sys.path.insert(0, sys.argv[1])
from figs import box, arrow

EPS, S, D = 0.02, 1.0, 8.0


def flow():
    W, H = 760, 250
    g = ['<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ahead" d="M0,0 L10,5 L0,10 z"/></marker></defs>']
    g.append('<text class="lane" x="10" y="22">two-way, collapsed tail (acts#6572)</text>')
    g.append('<text class="lane" x="10" y="140">GSF study</text>')
    bw, bh = 124, 50
    xs = [10, 160, 310, 460, 610]
    top = ["seed", "outward pass\nC + w D per surface", "RTS smoothing", "inward pass\nseed → perigee", "join"]
    for i, (x, t) in enumerate(zip(xs, top)):
        g.append(box(x, 38, bw, bh, t, "node"))
    for a, b in ((0, 1), (1, 2), (2, 3), (3, 4)):
        g.append(arrow(xs[a] + bw, 63, xs[b], 63))
    low = ["seed", "outward GSF pass\ncore + tail kept", "outermost state\ncovariance ×100", "inward GSF pass\nall surfaces", "perigee\nfrom inward filter"]
    for i, (x, t) in enumerate(zip(xs, low)):
        g.append(box(x, 156, bw, bh, t, "node good" if i in (1, 3) else "node"))
    for a, b in ((0, 1), (1, 2), (2, 3), (3, 4)):
        g.append(arrow(xs[a] + bw, 181, xs[b], 181))
    g.append(f'<text class="edgelab" x="{xs[3]+bw/2}" y="228" text-anchor="middle">one measurement per surface, kept on the outward hits</text>')
    return f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Flow of the two-way search and of the GSF study">' + "".join(g) + "</svg>"


def gauss(x, var):
    return math.exp(-0.5 * x * x / var) / math.sqrt(2 * math.pi * var)


def components():
    W, H, L, R, T, B = 700, 300, 56, 16, 30, 44
    pw = (W - L - R - 40) / 2
    ymin, ymax = -4.0, 0.0   # log10 density
    xmax = 8.0
    r = 4.0
    # posterior tail weight of a hit at r
    lc = math.log((1 - EPS) * gauss(r, S)); lt = math.log(EPS * gauss(r, S + D))
    w = 1 / (1 + math.exp(lc - lt))
    g = []
    def panel(x0, title, curves):
        X = lambda v: x0 + pw * (v + xmax) / (2 * xmax)
        Y = lambda v: T + (H - T - B) * (ymax - max(min(v, ymax), ymin)) / (ymax - ymin)
        for e in range(int(ymin), 1):
            g.append(f'<line class="grid" x1="{x0}" x2="{x0+pw:.1f}" y1="{Y(e):.1f}" y2="{Y(e):.1f}"/>')
            if x0 == L:
                g.append(f'<text class="tick" x="{x0-6}" y="{Y(e)+4:.1f}" text-anchor="end">1e{e}</text>')
        for v in (-8, -4, 0, 4, 8):
            g.append(f'<text class="tick" x="{X(v):.1f}" y="{H-B+16}" text-anchor="middle">{v}</text>')
        g.append(f'<text class="axis" x="{x0+pw/2:.1f}" y="{H-8}" text-anchor="middle">residual / σ_core</text>')
        g.append(f'<text class="lane" x="{x0}" y="18">{title}</text>')
        g.append(f'<line class="cut" x1="{X(r):.1f}" x2="{X(r):.1f}" y1="{T}" y2="{H-B}"/>')
        g.append(f'<text class="cutlab" x="{X(r)+4:.1f}" y="{T+12}">hit</text>')
        for cls, f, lab, lx, ly in curves:
            xs_ = [i * xmax / 200 - xmax for i in range(401)]
            pts = " ".join(f"{X(x):.1f},{Y(math.log10(f(x))):.1f}" for x in xs_ if f(x) >= 10 ** ymin)
            g.append(f'<polyline class="{cls}" points="{pts}"/>')
            if lab:
                g.append(f'<text class="{cls}lab" x="{X(lx):.1f}" y="{Y(ly):.1f}" text-anchor="middle">{lab}</text>')
    panel(L, "prediction on the surface", [
        ("core", lambda x: (1 - EPS) * gauss(x, S), "core 0.98", -2.4, -0.25),
        ("tailc", lambda x: EPS * gauss(x, S + D), "tail 0.02", -5.4, -2.25),
    ])
    panel(L + pw + 40, f"update with the hit at {r:.0f}σ", [
        ("gsfcore", lambda x: (1 - w) * gauss(x, S), f"GSF core {1-w:.2f}", -5.6, -3.4),
        ("tailc", lambda x: w * gauss(x, S + D), f"GSF tail {w:.2f}", -5.2, -2.6),
        ("collapse", lambda x: gauss(x, S + w * D), "collapsed C + w D", 0.0, -0.3),
    ])
    return f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Core and tail components against the collapsed prediction">' + "".join(g) + "</svg>"


open(sys.argv[2], "w").write(flow())
open(sys.argv[3], "w").write(components())
