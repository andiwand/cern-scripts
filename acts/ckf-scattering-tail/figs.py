"""Inline SVG figures for the implementation note."""
import math

S, D, EPS, CUT, OUT = 1.0, 8.0, 0.02, 15.0, 25.0
LPR = math.log(EPS / (1 - EPS))


def mix(r):
    c, t = r * r / S, r * r / (S + D)
    a = LPR + 0.5 * math.log(S / (S + D)) + 0.5 * (c - t)
    sp = a + math.log1p(math.exp(-a)) if a > 0 else math.log1p(math.exp(a))
    return c - 2 * sp, 1 / (1 + math.exp(-a))


def chi2_plot():
    W, H, L, R, T, B = 640, 300, 52, 16, 16, 44
    xmax, ymax = 8.0, 50.0
    X = lambda r: L + (W - L - R) * r / xmax
    Y = lambda v: T + (H - T - B) * (1 - min(v, ymax) / ymax)
    rs = [i * xmax / 400 for i in range(401)]
    core = " ".join(f"{X(r):.1f},{Y(r*r):.1f}" for r in rs if r * r <= ymax)
    mixl = " ".join(f"{X(r):.1f},{Y(mix(r)[0]):.1f}" for r in rs)
    g = []
    # axes, grid
    for v in range(0, 51, 10):
        g.append(f'<line class="grid" x1="{L}" x2="{W-R}" y1="{Y(v):.1f}" y2="{Y(v):.1f}"/>')
        g.append(f'<text class="tick" x="{L-8}" y="{Y(v)+4:.1f}" text-anchor="end">{v}</text>')
    for r in range(0, 9, 2):
        g.append(f'<text class="tick" x="{X(r):.1f}" y="{H-B+18}" text-anchor="middle">{r}</text>')
    g.append(f'<text class="axis" x="{(L+W-R)/2}" y="{H-6}" text-anchor="middle">residual / σ_core</text>')
    g.append(f'<text class="axis" transform="translate(14 {(T+H-B)/2}) rotate(-90)" text-anchor="middle">χ²</text>')
    # cuts
    for v, lab in ((CUT, "measurement cut 15"), (OUT, "outlier cut 25")):
        g.append(f'<line class="cut" x1="{L}" x2="{W-R}" y1="{Y(v):.1f}" y2="{Y(v):.1f}"/>')
        g.append(f'<text class="cutlab" x="{L+6}" y="{Y(v)-5:.1f}">{lab}</text>')
    g.append(f'<polyline class="core" points="{core}"/>')
    g.append(f'<polyline class="mix" points="{mixl}"/>')
    g.append(f'<text class="corelab" x="{X(5.6):.1f}" y="{Y(44):.1f}" text-anchor="end">χ²_core</text>')
    g.append(f'<text class="mixlab" x="{X(7.9):.1f}" y="{Y(5):.1f}" text-anchor="end">χ²_mix</text>')
    for r in (1.0, 4.0, 5.5, 7.0):
        m, w = mix(r)
        g.append(f'<line class="drop" x1="{X(r):.1f}" x2="{X(r):.1f}" y1="{Y(min(r*r,ymax)):.1f}" y2="{Y(m):.1f}"/>')
        g.append(f'<circle class="hitcore" cx="{X(r):.1f}" cy="{Y(min(r*r,ymax)):.1f}" r="4"/>')
        g.append(f'<circle class="hitmix" cx="{X(r):.1f}" cy="{Y(m):.1f}" r="4"/>')
        g.append(f'<text class="wlab" x="{X(r):.1f}" y="{Y(m)+20:.1f}" text-anchor="middle">w {w:.2f}</text>')
    return f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Core and mixture chi2 against the residual">' + "".join(g) + "</svg>"


def box(x, y, w, h, text, cls="node"):
    lines = text.split("\n")
    t = "".join(
        f'<text class="nodetext" x="{x+w/2}" y="{y+h/2+5+(i-(len(lines)-1)/2)*15:.1f}" text-anchor="middle">{l}</text>'
        for i, l in enumerate(lines))
    return f'<rect class="{cls}" x="{x}" y="{y}" width="{w}" height="{h}" rx="5"/>' + t


def arrow(x1, y1, x2, y2, label=None, cls="edge"):
    s = f'<line class="{cls}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" marker-end="url(#ah)"/>'
    if label:
        s += f'<text class="edgelab" x="{(x1+x2)/2+6}" y="{(y1+y2)/2-5}">{label}</text>'
    return s


def flow():
    W, H = 760, 250
    g = ['<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ahead" d="M0,0 L10,5 L0,10 z"/></marker></defs>']
    g.append('<text class="lane" x="10" y="22">nominal KF</text>')
    g.append('<text class="lane" x="10" y="122">with the tail</text>')
    bw, bh = 120, 46
    # nominal lane
    xs = [10, 160, 310, 460, 610]
    nom = ["material\nC += Q", "transport\nto surface", "select\ncore χ²", "hole /\noutlier", "kink lost"]
    for i, (x, t) in enumerate(zip(xs, nom)):
        g.append(box(x, 40, bw, bh, t, "node bad" if i >= 3 else "node"))
        if i:
            g.append(arrow(xs[i-1] + bw, 63, x, 63))
    # tail lane
    tl = ["material\nC += Q\nΣεD += ε(k²−1)Q", "transport\nC, ΣεD with J", "select\ncore χ²", "select\nχ²_mix", "update with\nC + w D,\nreset ΣεD"]
    for i, (x, t) in enumerate(zip(xs, tl)):
        g.append(box(x, 134, bw, 58 if i in (0, 4) else bh, t, "node good" if i >= 3 else "node"))
    for i in range(1, 5):
        if i == 4:
            continue
        g.append(arrow(xs[i-1] + bw, 157, xs[i], 157))
    g.append(f'<text class="edgelab" x="{xs[2]+bw+15}" y="151" text-anchor="middle">miss</text>')
    g.append(arrow(xs[3] + bw, 157, xs[4], 157))
    # hit path from core select straight to update
    g.append(f'<path class="edge" d="M{xs[2]+bw/2},{134+bh} C{xs[2]+bw/2},236 {xs[4]+bw/2},236 {xs[4]+bw/2},{134+58}" fill="none" marker-end="url(#ah)"/>')
    g.append(f'<text class="edgelab" x="{(xs[2]+xs[4])/2+bw/2}" y="244" text-anchor="middle">hit: the KF selection</text>')
    return f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Flow of the nominal KF and of the KF with the scattering tail">' + "".join(g) + "</svg>"


if __name__ == "__main__":
    import sys
    open(sys.argv[1], "w").write(flow())
    open(sys.argv[2], "w").write(chi2_plot())
