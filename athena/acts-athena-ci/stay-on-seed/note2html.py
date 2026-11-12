#!/usr/bin/env python3
"""Standalone HTML of the stay-on-seed note: markdown body + interactive per-eta charts. usage: note2html.py note.md gbtswrong.json out.html seedlen.json seedclass.json truthpart.json matchedwho.json"""
import sys, re, json, html
md = open(sys.argv[1]).read()
def jarg(i, default):
    return json.load(open(sys.argv[i])) if len(sys.argv) > i and sys.argv[i] != "-" else default
data = jarg(2, {})
def inline(t):
    codes = []
    def keep(m): codes.append(html.escape(m.group(1))); return f"\0{len(codes)-1}\0"
    t = re.sub(r"`([^`]+)`", keep, t.replace("\\|", "\1"))
    t = html.escape(t, quote=False).replace("\1", "|")
    # links: web links become anchors, local files plain text (they are not published with the page)
    t = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r'<a href="\2">\1</a>', t)
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<![\w*])\*(?!\s)(.+?)\*(?![\w*])", r"<em>\1</em>", t)
    return re.sub(r"\0(\d+)\0", lambda m: f"<code>{codes[int(m.group(1))]}</code>", t)
cells = lambda l: [c.strip() for c in re.split(r"(?<!\\)\|", l.strip().strip("|"))]
L = md.split("\n"); i = 0; out = []; title = ""
while i < len(L):
    l = L[i]
    if not l.strip(): i += 1; continue
    if l.startswith("# "): title = l[2:]; i += 1; continue
    if l.startswith("## "):
        h = l[3:]; out.append(f'<h2 id="{re.sub("[^a-z0-9]+","-",h.lower()).strip("-")}">{inline(h)}</h2>'); i += 1; continue
    m = re.match(r"!\[(\w+)\]", l)
    if m and m.group(1) == "seedlen": out.append('<div class="lenplot"></div>'); i += 1; continue
    if m and m.group(1) == "particles": out.append('<div class="partplot"></div>'); i += 1; continue
    if m and m.group(1) == "matchedwho": out.append('<div class="mwplot"></div>'); i += 1; continue
    if m and m.group(1) == "seedtruth": out.append('<div class="truthplot"></div>'); i += 1; continue
    if m and m.group(1) in ("pixel", "strip"): out.append(f'<div class="charts" data-det="{m.group(1)}"></div>'); i += 1; continue
    if m:
        # any other image: embed the file so the page stays a single file
        import base64, os
        pm = re.match(r"!\[[^\]]*\]\(([^)]+)\)", l)
        fn = os.path.join(os.path.dirname(os.path.abspath(sys.argv[1])), pm.group(1)) if pm else ""
        if os.path.exists(fn):
            out.append(f'<figure><img alt="{html.escape(m.group(1))}" src="data:image/png;base64,{base64.b64encode(open(fn, "rb").read()).decode()}"></figure>')
        i += 1; continue
    if l.startswith("|") and i + 1 < len(L) and L[i + 1].startswith("|---"):
        hd = cells(l); i += 2; rows = []
        while i < len(L) and L[i].startswith("|"): rows.append(cells(L[i])); i += 1
        # numeric columns (every non-empty cell starts with a number or a sign) are right-aligned
        num = lambda c: bool(re.match(r"^\s*(\*\*)?[−+\-±]?\s*\(?[0-9.]", c))
        ncol = [all(num(r[j]) for r in rows if j < len(r) and r[j].strip()) and any(j < len(r) and r[j].strip() for r in rows) for j in range(len(hd))]
        cl = lambda j: ' class="n"' if j < len(ncol) and ncol[j] else ""
        t = "<thead><tr>" + "".join(f"<th{cl(j)}>{inline(c)}</th>" for j, c in enumerate(hd)) + "</tr></thead><tbody>"
        t += "".join("<tr>" + "".join(f"<td{cl(j)}>{inline(c)}</td>" for j, c in enumerate(r)) + "</tr>" for r in rows) + "</tbody>"
        out.append(f'<div class="tw"><table>{t}</table></div>'); continue
    if l.startswith("- "):
        items = []
        while i < len(L) and (L[i].startswith("- ") or L[i].startswith("  ")):
            if L[i].startswith("- "): items.append(L[i][2:])
            else: items[-1] += " " + L[i].strip()
            i += 1
        out.append("<ul>" + "".join(f"<li>{inline(x)}</li>" for x in items) + "</ul>"); continue
    p = []
    while i < len(L) and L[i].strip() and not (re.match(r"(#|- |!\[)", L[i]) or (L[i].startswith("|") and i + 1 < len(L) and L[i + 1].startswith("|---"))): p.append(L[i]); i += 1
    out.append(f"<p>{inline(' '.join(p))}</p>")
body = "\n".join(out)
# the first paragraphs before the summary are the intro; the summary gets its own box
body = re.sub(r'(<h2 id="summary">.*?</h2>)\s*(<ul>.*?</ul>)', r'<section class="verdict">\1\2</section>', body, count=1, flags=re.S)
nav = "".join(f'<a href="#{a}">{t}</a>' for a, t in re.findall(r'<h2 id="([^"]+)">(.*?)</h2>', body) if a != "summary")
TPL = r"""<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>@@PAGETITLE@@</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* Same report layout as the other TSI notes: one reading column, tables and charts in their own scrollers */
:root {
  --bg: #f7f7f4; --surface: #fcfcfb; --fg: #15171a; --fg-2: #4d5257; --fg-3: #7a8087;
  --line: #d9dbd6; --wash: #eeefea; --grid: #e6e6e0; --axis: #b9bab2; --accent: #2a78d6;
  --p1: #2a78d6; --p2: #eb6834; --p3: #1baf7a; --p4: #eda100; --p5: #e87ba4;
  --r1: #86b6ef; --r2: #3987e5; --r3: #1c5cab; --r4: #0d366b;
  --font: "IBM Plex Sans", "Helvetica Neue", Arial, sans-serif;
  --mono: "IBM Plex Mono", "SFMono-Regular", Menlo, monospace;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --bg: #131413; --surface: #1a1a19; --fg: #f2f2ee; --fg-2: #c3c2b7; --fg-3: #8d8f88;
  --line: #34363a; --wash: #242523; --grid: #2a2b29; --axis: #4a4b47; --accent: #5598e7;
  --p1: #3987e5; --p2: #d95926; --p3: #199e70; --p4: #c98500; --p5: #d55181;
  --r1: #184f95; --r2: #2a78d6; --r3: #6da7ec; --r4: #cde2fb; color-scheme: dark; } }
:root[data-theme="dark"] {
  --bg: #131413; --surface: #1a1a19; --fg: #f2f2ee; --fg-2: #c3c2b7; --fg-3: #8d8f88;
  --line: #34363a; --wash: #242523; --grid: #2a2b29; --axis: #4a4b47; --accent: #5598e7;
  --p1: #3987e5; --p2: #d95926; --p3: #199e70; --p4: #c98500; --p5: #d55181;
  --r1: #184f95; --r2: #2a78d6; --r3: #6da7ec; --r4: #cde2fb; color-scheme: dark; }
body { background: var(--bg); color: var(--fg); font-family: var(--font); font-size: 15px; line-height: 1.55; margin: 0; }
.wrap { max-width: 880px; margin: 0 auto; padding-block: 32px 64px;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px));
  display: grid; gap: 14px; }
.wrap > * { min-width: 0; margin: 0; }
h1 { font-size: 1.65rem; font-weight: 600; line-height: 1.2; text-wrap: balance; margin: 0; }
h2 { font-size: 1.15rem; font-weight: 600; margin: 0; margin-top: 22px; padding-top: 18px; border-top: 1px solid var(--line); text-wrap: balance; }
p, ul { margin: 0; }
ul { padding-left: 20px; display: grid; gap: 6px; }
a { color: var(--accent); text-decoration: none; }
a:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
code { font-family: var(--mono); font-size: 0.86em; background: var(--wash); padding: 1px 4px; border-radius: 3px; overflow-wrap: anywhere; }
nav { display: flex; flex-wrap: wrap; gap: 4px 16px; font-size: 0.9rem; }
.verdict { background: var(--surface); border: 1px solid var(--line); border-radius: 6px; padding: 14px 18px; display: grid; gap: 10px; }
.verdict h2 { border: 0; margin: 0; padding: 0; }
.verdict ul { max-width: none; }
.tw { overflow-x: auto; }
table { min-width: 100%; border-collapse: collapse; font-size: 0.86rem; font-variant-numeric: tabular-nums; }
th, td { padding: 4px 10px; text-align: left; border-bottom: 1px solid var(--line); vertical-align: top; }
td.n { text-align: right; white-space: nowrap; }
th { font-weight: 600; color: var(--fg-2); vertical-align: bottom; }
th.n { text-align: right; }
.charts { display: grid; gap: 12px; }
figure { margin: 0; } figure img { width: 100%; height: auto; background: #fff; border-radius: 6px; }
.charts h3 { font-size: 0.98rem; font-weight: 600; margin: 8px 0 0; }
.grid2 { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 400px), 1fr)); gap: 14px; }
.chart { background: var(--surface); border: 1px solid var(--line); border-radius: 6px; padding: 10px 12px; min-width: 0; position: relative; }
.chart .ct { font-size: 0.86rem; font-weight: 500; }
.legend { display: flex; flex-wrap: wrap; gap: 2px 12px; font-size: 0.78rem; color: var(--fg-2); margin: 4px 0; }
.legend i { display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 4px; vertical-align: -1px; }
svg { display: block; width: 100%; height: auto; }
svg text { font-family: var(--font); font-size: 11px; fill: var(--fg-3); }
.tip { position: absolute; pointer-events: none; background: var(--fg); color: var(--bg); font-size: 0.76rem; padding: 4px 7px; border-radius: 4px; white-space: nowrap; z-index: 3; }
details { font-size: 0.86rem; } summary { cursor: pointer; color: var(--fg-2); }
</style>
<div class="wrap">
<h1>@@TITLE@@</h1>
<nav>@@NAV@@</nav>
@@BODY@@
</div>
<script>
const DATA = @@DATA@@;
const LEN = @@LEN@@;
const TRUTH = @@TRUTH@@;
const PART = {particles: @@PART@@};
const MWHO = @@MWHO@@;
const POS = [["pos:front","front","--p1"],["pos:middle","middle","--p2"],["pos:back","back","--p3"],["pos:several places","several places","--p4"]];
const CLS = [["matched","matched","--p1"],["duplicate","duplicate","--p2"],["fake","fake","--p3"],["unlinked","unlinked","--p4"]];
const RUN = [["run:1","1 SP","--r1"],["run:2","2 in a row","--r2"],["run:3","3 in a row","--r3"],["run:>=4","4 or more","--r4"]];
const NS = "http://www.w3.org/2000/svg";
const el = (n, a, p) => { const e = document.createElementNS(NS, n); for (const k in a) e.setAttribute(k, a[k]); if (p) p.appendChild(e); return e; };
function nice(m) { const p = Math.pow(10, Math.floor(Math.log10(m))); for (const s of [1, 2, 2.5, 5, 10]) if (m / (s * p) <= 5) return s * p; return 10 * p; }
function chart(host, det, series, frac, title, src = DATA, xlabel = "|η| of the seed") {
  const D = src[det], nb = Math.max(...Object.keys(D.bins).map(Number)) + 1 - (det === "strip" ? 1 : 0);
  const box = document.createElement("div"); box.className = "chart"; host.appendChild(box);
  box.innerHTML = `<div class="ct">${title}</div><div class="legend">` + series.map(s => `<span><i style="background:var(${s[2]})"></i>${s[1]}</span>`).join("") + "</div>";
  const W = 460, H = 240, l = 46, r = 8, t = 8, b = 36, pw = W - l - r, ph = H - t - b;
  const val = (i, k) => { const B = D.bins[i] || {}, v = B[k] || 0; return frac ? 100 * v / (B.all || 1) : v; };
  let mx = 0; for (let i = 0; i < nb; i++) mx = Math.max(mx, series.reduce((a, s) => a + val(i, s[0]), 0));
  const step = nice(mx), top = Math.ceil(mx / step) * step, y = v => t + ph - ph * v / top;
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": title }, box);
  for (let v = 0; v <= top + 1e-9; v += step) {
    el("line", { x1: l, x2: W - r, y1: y(v), y2: y(v), stroke: v ? "var(--grid)" : "var(--axis)" }, svg);
    const tx = el("text", { x: l - 6, y: y(v) + 4, "text-anchor": "end" }, svg); tx.textContent = frac ? v + "%" : v;
  }
  const bw = pw / nb, tip = document.createElement("div"); tip.className = "tip"; tip.hidden = true; box.appendChild(tip);
  for (let i = 0; i < nb; i++) {
    let acc = 0; const x = l + i * bw;
    for (const s of series) {
      const v = val(i, s[0]); if (!v) continue;
      const y1 = y(acc + v), h = y(acc) - y1;
      el("rect", { x: x + 2, y: y1, width: bw - 4, height: Math.max(h - 1, 0.6), fill: `var(${s[2]})` }, svg);
      acc += v;
    }
    const hit = el("rect", { x, y: t, width: bw, height: ph, fill: "transparent" }, svg);
    const lo = D.edges[i], hi = D.edges[i + 1];
    const show = ev => {
      const B = D.bins[i] || {};
      tip.innerHTML = `|η| ${lo}–${hi}, ${B.all || 0} seeds<br>` + series.map(s => `${s[1]}: ${B[s[0]] || 0} (${(100 * (B[s[0]] || 0) / (B.all || 1)).toFixed(2)}%)`).join("<br>");
      tip.hidden = false; const R = box.getBoundingClientRect(), px = ev.clientX - R.left, py = ev.clientY - R.top;
      tip.style.left = Math.min(px + 12, R.width - tip.offsetWidth - 4) + "px"; tip.style.top = Math.max(py - tip.offsetHeight - 8, 2) + "px";
    };
    hit.addEventListener("mousemove", show); hit.addEventListener("mouseleave", () => tip.hidden = true);
    if (i % 2 === 0) { const tx = el("text", { x, y: H - b + 15, "text-anchor": "middle" }, svg); tx.textContent = lo; }
  }
  const xl = el("text", { x: l + pw / 2, y: H - 4, "text-anchor": "middle" }, svg); xl.textContent = xlabel;
}
function boxplot(host, det, color, title) {
  const D = LEN[det], keys = Object.keys(D.bins).map(Number).sort((a, b) => a - b), nb = Math.max(...keys) + 1;
  const box = document.createElement("div"); box.className = "chart"; host.appendChild(box);
  box.innerHTML = `<div class="ct">${title}</div><div class="legend"><span>box 25–75%, bar median, dot mean, whiskers min to max</span></div>`;
  const W = 460, H = 240, l = 40, r = 8, t = 8, b = 36, pw = W - l - r, ph = H - t - b;
  const lo = 2, hi = Math.max(...keys.map(k => D.bins[k].max)) + 1, y = v => t + ph - ph * (v - lo) / (hi - lo);
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": title }, box);
  const step = hi - lo > 8 ? 2 : 1;
  for (let v = lo; v <= hi; v += step) {
    el("line", { x1: l, x2: W - r, y1: y(v), y2: y(v), stroke: v === lo ? "var(--axis)" : "var(--grid)" }, svg);
    const tx = el("text", { x: l - 6, y: y(v) + 4, "text-anchor": "end" }, svg); tx.textContent = v;
  }
  const bw = pw / nb, tip = document.createElement("div"); tip.className = "tip"; tip.hidden = true; box.appendChild(tip);
  for (let i = 0; i < nb; i++) {
    const x = l + i * bw, cx = x + bw / 2;
    if (i % 2 === 0) { const tx = el("text", { x, y: H - b + 15, "text-anchor": "middle" }, svg); tx.textContent = D.edges[i]; }
    const q = D.bins[i]; if (!q) continue;
    el("line", { x1: cx, x2: cx, y1: y(q.min), y2: y(q.max), stroke: `var(${color})`, "stroke-width": 1.5 }, svg);
    for (const v of [q.min, q.max]) el("line", { x1: x + bw * 0.32, x2: x + bw * 0.68, y1: y(v), y2: y(v), stroke: `var(${color})`, "stroke-width": 1.5 }, svg);
    el("rect", { x: x + bw * 0.2, y: y(q.p75), width: bw * 0.6, height: Math.max(y(q.p25) - y(q.p75), 1.5), rx: 2, fill: `var(${color})`, "fill-opacity": 0.3, stroke: `var(${color})` }, svg);
    el("line", { x1: x + bw * 0.2, x2: x + bw * 0.8, y1: y(q.p50), y2: y(q.p50), stroke: `var(${color})`, "stroke-width": 2.5 }, svg);
    el("circle", { cx, cy: y(q.mean), r: 3, fill: "var(--surface)", stroke: `var(${color})`, "stroke-width": 1.5 }, svg);
    const hit = el("rect", { x, y: t, width: bw, height: ph, fill: "transparent" }, svg);
    hit.addEventListener("mousemove", ev => {
      tip.innerHTML = `|η| ${D.edges[i]}–${D.edges[i + 1]}, ${q.n} seeds<br>median ${q.p50}, mean ${q.mean.toFixed(2)}<br>25–75%: ${q.p25}–${q.p75}, min–max: ${q.min}–${q.max}<br>3 / 4 / 5 / 6+: ` + [3, 4, 5, 6].map(k => (100 * q["len:" + k] / q.n).toFixed(1) + "%").join(" / ");
      tip.hidden = false; const R = box.getBoundingClientRect();
      tip.style.left = Math.min(ev.clientX - R.left + 12, R.width - tip.offsetWidth - 4) + "px"; tip.style.top = Math.max(ev.clientY - R.top - tip.offsetHeight - 8, 2) + "px";
    });
    hit.addEventListener("mouseleave", () => tip.hidden = true);
  }
  const xl = el("text", { x: l + pw / 2, y: H - 4, "text-anchor": "middle" }, svg); xl.textContent = "|η| of the seed";
}
function table(host, src, det, keys, label) {
  const D = src[det], d = document.createElement("details");
  d.innerHTML = `<summary>${label}: values per |η| bin</summary><div class="tw"><table><thead><tr><th>|η|</th><th>seeds</th>` + keys.map(k => `<th>${k[1]}</th><th>%</th>`).join("") + "</tr></thead><tbody>" +
    Object.keys(D.bins).map(Number).sort((a, b) => a - b).map(i => `<tr><td>${D.edges[i]}–${D.edges[i + 1]}</td><td>${D.bins[i].all}</td>` + keys.map(k => `<td>${D.bins[i][k[0]] || 0}</td><td>${(100 * (D.bins[i][k[0]] || 0) / D.bins[i].all).toFixed(2)}</td>`).join("") + "</tr>").join("") + "</tbody></table></div>";
  host.appendChild(d);
}
document.querySelectorAll(".partplot").forEach(host => {
  const g = document.createElement("div"); g.className = "grid2"; host.appendChild(g);
  const S = [["PU","pileup","--p1"],["HS","hard scatter","--p2"],["sec","reconstructable secondaries","--p3"]];
  chart(g, "particles", S, false, "Reconstructable truth particles per bin (100 events)", PART, "|η| of the particle");
  chart(g, "particles", [["HS","hard scatter","--p2"]], false, "Reconstructable hard-scatter particles per bin (100 events)", PART, "|η| of the particle");
  table(host, PART, "particles", S, "Truth particles");
});
document.querySelectorAll(".mwplot").forEach(host => {
  const g = document.createElement("div"); g.className = "grid2"; host.appendChild(g);
  const S = [["reco","reconstructable","--p1"],["lowpt","primary, pT < 0.9 GeV","--p2"],["sec","secondary (any pT)","--p3"],["other","other","--p4"]];
  chart(g, "pixel", S, false, "Pixel: particles of the matched seeds, per bin", MWHO);
  chart(g, "strip", S, false, "Strip: particles of the matched seeds, per bin", MWHO);
  table(host, MWHO, "pixel", S, "Pixel matched seeds"); table(host, MWHO, "strip", S, "Strip matched seeds");
});
document.querySelectorAll(".truthplot").forEach(host => {
  const g = document.createElement("div"); g.className = "grid2"; host.appendChild(g);
  chart(g, "pixel", CLS, false, "Pixel seeds, seeds per bin (100 events)", TRUTH);
  chart(g, "strip", CLS, false, "Strip seeds, seeds per bin (100 events)", TRUTH);
  table(host, TRUTH, "pixel", CLS, "Pixel seeds"); table(host, TRUTH, "strip", CLS, "Strip seeds");
});
document.querySelectorAll(".lenplot").forEach(host => {
  const g = document.createElement("div"); g.className = "grid2"; host.appendChild(g);
  boxplot(g, "pixel", "--p1", "Pixel seeds: space points per seed");
  boxplot(g, "strip", "--p2", "Strip seeds: space points per seed");
});
document.querySelectorAll(".charts").forEach(host => {
  const det = host.dataset.det, D = DATA[det], name = det[0].toUpperCase() + det.slice(1);
  const h = document.createElement("h3"); h.textContent = name + " seeds"; host.appendChild(h);
  const g = document.createElement("div"); g.className = "grid2"; host.appendChild(g);
  chart(g, det, POS, true, "Where the wrong SPs are, % of matched + duplicate seeds");
  chart(g, det, RUN, true, "Longest run of wrong SPs, % of matched + duplicate seeds");
  table(host, DATA, det, [...POS, ...RUN], name + " seeds, wrong SPs (% of matched + duplicate seeds)");
});
</script>
"""
slim = {k: dict(edges=v["edges"], bins=v["bins"]) for k, v in data.items()}
import os
page = TPL.replace("@@PAGETITLE@@", html.escape(os.environ.get("PAGETITLE", title))).replace("@@TITLE@@", html.escape(title)).replace("@@NAV@@", nav).replace("@@BODY@@", body).replace("@@DATA@@", json.dumps(slim, separators=(",", ":"))).replace("@@LEN@@", json.dumps(jarg(4, {}), separators=(",", ":"))).replace("@@TRUTH@@", json.dumps(jarg(5, {}), separators=(",", ":"))).replace("@@PART@@", json.dumps(jarg(6, {"edges": [], "bins": {}}), separators=(",", ":"))).replace("@@MWHO@@", json.dumps(jarg(7, {}), separators=(",", ":")))
open(sys.argv[3], "w").write(page)
print("written", len(page))
