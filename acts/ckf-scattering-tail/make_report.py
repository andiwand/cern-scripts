#!/usr/bin/env python3
"""Build the standalone interactive report from the analysis export.

Usage: make_report.py export.json content.html out.html

content.html holds the prose sections; the charts are placed by
<div class="chart" data-chart="..."></div> placeholders.
"""

import json
import sys

export = json.load(open(sys.argv[1]))
content = open(sys.argv[2]).read()
out = sys.argv[3]

TEMPLATE = r"""<title>CKF Scattering Tail Prototype</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans+Condensed:wght@500;600&family=IBM+Plex+Sans:ital,wght@0,400;0,500;0,600;1,400&display=swap">
<style>
/* Layout: one reading column with full-width figures; a sticky contents rail on wide screens */
:root {
  --bg: #f4f6f8;
  --paper: #fbfcfd;
  --ink: #14181f;
  --muted: #5b6472;
  --rule: #d9dee5;
  --grid: #e7ebf0;
  --accent: #1f5f8b;
  --good-bg: #e7f4ec;
  --good: #1d6b3a;
  --font-display: "IBM Plex Sans Condensed", "Arial Narrow", sans-serif;
  --font-body: "IBM Plex Sans", "Helvetica Neue", Arial, sans-serif;
  --font-mono: "IBM Plex Mono", ui-monospace, Menlo, monospace;
  --c-base15: #2a78d6; --c-base49: #eb6834; --c-retry15: #1baf7a;
  --c-mix15: #eda100; --c-branch15: #e87ba4; --c-selonly15: #008300;
  --c-base25: #6250d6; --c-base35: #e34948;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #0f1318; --paper: #151a21; --ink: #e8ebef; --muted: #a3acb8; --rule: #2c343f; --grid: #222a33;
    --accent: #7db4dc; --good-bg: #13261b; --good: #7fd19b; color-scheme: dark;
    --c-base15: #3987e5; --c-base49: #d95926; --c-retry15: #199e70;
    --c-mix15: #c98500; --c-branch15: #d55181; --c-selonly15: #008300;
    --c-base25: #9085e9; --c-base35: #e66767;
  }
}
:root[data-theme="dark"] {
  --bg: #0f1318; --paper: #151a21; --ink: #e8ebef; --muted: #a3acb8; --rule: #2c343f; --grid: #222a33;
  --accent: #7db4dc; --good-bg: #13261b; --good: #7fd19b; color-scheme: dark;
  --c-base15: #3987e5; --c-base49: #d95926; --c-retry15: #199e70;
  --c-mix15: #c98500; --c-branch15: #d55181; --c-selonly15: #008300;
  --c-base25: #9085e9; --c-base35: #e66767;
}
body { background: var(--bg); color: var(--ink); font: 400 15px/1.6 var(--font-body); }
.wrap {
  max-width: 1180px; margin: 0 auto;
  padding-left: max(16px, env(safe-area-inset-left, 0px));
  padding-right: max(16px, env(safe-area-inset-right, 0px));
  padding-block: 32px 64px;
  display: grid; grid-template-columns: 200px minmax(0, 1fr); gap: 40px;
}
nav.toc { position: sticky; top: calc(env(safe-area-inset-top, 0px) + 24px); align-self: start; font-size: 13px; }
nav.toc ol { list-style: none; margin: 0; padding: 0; display: grid; gap: 6px; }
nav.toc a { color: var(--muted); text-decoration: none; }
nav.toc a:hover, nav.toc a:focus-visible { color: var(--accent); }
nav.toc .label { font: 600 11px/1 var(--font-display); letter-spacing: .08em; text-transform: uppercase; color: var(--muted); margin-bottom: 12px; display: block; }
main { min-width: 0; }
header.top { display: grid; gap: 10px; margin-bottom: 28px; }
.eyebrow { font: 500 12px/1 var(--font-mono); color: var(--muted); letter-spacing: .02em; }
h1 { font: 600 clamp(28px, 4vw, 40px)/1.1 var(--font-display); margin: 0; text-wrap: balance; }
h2 { font: 600 24px/1.2 var(--font-display); margin: 0; text-wrap: balance; }
h3 { font: 600 17px/1.3 var(--font-display); margin: 0; }
p, li { max-width: 72ch; }
p { margin: 0; }
a { color: var(--accent); }
code, .mono { font: 400 13px/1.5 var(--font-mono); }
section { display: grid; gap: 16px; padding-block: 28px; border-top: 1px solid var(--rule); }
section > *, .figure > *, .cfg > * { min-width: 0; }
.tablewrap { max-width: 100%; }
.tablewrap.prose td { white-space: normal; text-align: left; vertical-align: top; min-width: 140px; }
ul, ol.steps { margin: 0; padding-left: 20px; display: grid; gap: 6px; }
.verdict { background: var(--good-bg); border-left: 3px solid var(--good); padding: 12px 16px; border-radius: 0 6px 6px 0; display: grid; gap: 8px; }
.caption { font-size: 13px; color: var(--muted); max-width: 90ch; }
.tablewrap { overflow-x: auto; background: var(--paper); border: 1px solid var(--rule); border-radius: 6px; }
table { border-collapse: collapse; width: 100%; font-size: 13px; font-variant-numeric: tabular-nums; }
th, td { padding: 6px 10px; text-align: right; border-bottom: 1px solid var(--grid); white-space: nowrap; }
th:first-child, td:first-child { text-align: left; }
thead th { font: 600 12px/1.3 var(--font-display); letter-spacing: .02em; color: var(--ink); vertical-align: bottom; }
tbody tr:hover { background: var(--grid); }
td.best { font-weight: 600; color: var(--good); }
.sw { display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 6px; vertical-align: -1px; }
html, body { overflow-x: clip; }
.chips { display: flex; flex-wrap: wrap; gap: 8px; position: sticky; top: env(safe-area-inset-top, 0px); z-index: 5; padding-block: 10px; }
/* the bar background and rule run to the right edge of the window */
.chips::before { content: ""; position: absolute; inset: 0 calc(-100vw) 0 0; background: var(--bg); border-bottom: 1px solid var(--rule); z-index: -1; }
.chip { font: 500 12px/1 var(--font-body); border: 1px solid var(--rule); background: var(--paper); color: var(--ink); border-radius: 999px; padding: 6px 10px; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; }
.chip[aria-pressed="false"] { color: var(--muted); text-decoration: line-through; background: transparent; }
.chip[aria-pressed="false"] .sw { background: var(--rule) !important; }
.cfglist { display: grid; gap: 18px; }
.cfggroup { display: grid; gap: 8px; }
.cfggroup h3 { font: 600 11px/1 var(--font-display); letter-spacing: .08em; text-transform: uppercase; color: var(--muted); }
.cfgitems { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 380px), 1fr)); gap: 10px; }
.cfg { background: var(--paper); border: 1px solid var(--rule); border-radius: 6px; padding: 10px 12px; display: grid; gap: 6px; align-content: start; }
.cfg p { font-size: 13px; color: var(--muted); max-width: none; }
.cfg .chip { justify-self: start; }
.chips .hint { font: 600 11px/1 var(--font-display); letter-spacing: .08em; text-transform: uppercase; color: var(--muted); align-self: center; margin-right: 4px; }
.chip:focus-visible, .seg button:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.seg { display: inline-flex; border: 1px solid var(--rule); border-radius: 6px; overflow: hidden; }
.seg button { font: 500 12px/1 var(--font-body); background: var(--paper); color: var(--muted); border: 0; padding: 7px 10px; cursor: pointer; }
.seg button + button { border-left: 1px solid var(--rule); }
.seg button[aria-pressed="true"] { background: var(--accent); color: var(--paper); }
.controls { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }
.figure { background: var(--paper); border: 1px solid var(--rule); border-radius: 6px; padding: 12px; display: grid; gap: 10px; min-width: 0; }
.figrow { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px; }
.chart { position: relative; width: 100%; min-width: 0; }
.chart svg { display: block; width: 100%; max-width: 100%; height: auto; overflow: hidden; }
.chart text { fill: var(--muted); font: 400 11px var(--font-body); }
.chart .title { fill: var(--ink); font: 600 13px var(--font-display); }
.chart .axis { stroke: var(--muted); }
.chart .gridl { stroke: var(--grid); }
.chart .ref { stroke: var(--muted); stroke-dasharray: 4 3; }
.tip { position: absolute; pointer-events: none; background: var(--ink); color: var(--bg); font: 500 12px/1.4 var(--font-mono); padding: 6px 8px; border-radius: 4px; white-space: nowrap; transform: translate(-50%, calc(-100% - 10px)); z-index: 3; }
.tip[hidden] { display: none; }
@media (max-width: 860px) {
  .wrap { grid-template-columns: minmax(0, 1fr); }
  nav.toc { position: static; }
  nav.toc ol { grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); }
}
@media (prefers-reduced-motion: no-preference) { .chip, .seg button { transition: opacity .15s, background .15s; } }
</style>
<div class="wrap">
<nav class="toc" aria-label="Contents"><span class="label">Contents</span><ol id="toc"></ol></nav>
<main>
%CONTENT%
</main>
</div>
<script>
const DATA = %DATA%;
(() => {
  const cfgs = DATA.configs;
  const visible = new Set(cfgs.map(c => c.id));
  const css = getComputedStyle(document.documentElement);
  const color = id => `var(--c-${id})`;
  const fmt = (v, d = 3) => v == null || !isFinite(v) ? "–" : Math.abs(v) >= 1000 ? v.toFixed(0) : Math.abs(v) < 1e-3 && v !== 0 ? v.toExponential(2) : v.toFixed(d);

  // contents
  const toc = document.getElementById("toc");
  document.querySelectorAll("main section[id] > h2").forEach(h => {
    const li = document.createElement("li");
    const a = document.createElement("a");
    a.href = "#" + h.parentElement.id; a.textContent = h.textContent;
    li.appendChild(a); toc.appendChild(li);
  });

  // config chips
  const makeChip = c => {
    const b = document.createElement("button");
    b.className = "chip"; b.type = "button"; b.dataset.cfg = c.id;
    b.setAttribute("aria-pressed", "true");
    b.title = "Show or hide this configuration in the summary table and in all charts";
    b.innerHTML = `<span class="sw" style="background:${color(c.id)}"></span>${c.label}`;
    b.addEventListener("click", () => {
      if (visible.has(c.id)) visible.delete(c.id); else visible.add(c.id);
      document.querySelectorAll(`.chip[data-cfg="${c.id}"]`).forEach(x => x.setAttribute("aria-pressed", visible.has(c.id)));
      redraw();
    });
    return b;
  };
  document.querySelectorAll(".chips").forEach(box => {
    box.insertAdjacentHTML("beforeend", `<span class="hint">Show in table and charts</span>`);
    cfgs.forEach(c => box.appendChild(makeChip(c)));
  });
  document.querySelectorAll(".cfglist").forEach(box => {
    const groups = [...new Set(cfgs.map(c => c.group))];
    groups.forEach(gname => {
      const g = document.createElement("div");
      g.className = "cfggroup";
      g.innerHTML = `<h3>${gname}</h3><div class="cfgitems"></div>`;
      const items = g.querySelector(".cfgitems");
      const members = cfgs.filter(c => c.group === gname);
      members.sort((a, b) => a.id.startsWith("base") && b.id.startsWith("base") ? parseInt(a.id.slice(4)) - parseInt(b.id.slice(4)) : 0);
      members.forEach(c => {
        const d = document.createElement("div");
        d.className = "cfg";
        d.appendChild(makeChip(c));
        const p = document.createElement("p");
        p.textContent = c.desc;
        d.appendChild(p);
        items.appendChild(d);
      });
      box.appendChild(g);
    });
  });

  // a minimal SVG chart: series of points (with errors) or steps, linear or log axes
  function chart(el, o) {
    const W = Math.max(300, Math.round(el.getBoundingClientRect().width || 560)), H = o.height || Math.round(Math.min(380, Math.max(260, W * 0.5))), m = { l: 58, r: 14, t: o.title ? 26 : 10, b: 40 };
    const xs = o.xlog ? Math.log10 : x => x, ys = o.ylog ? Math.log10 : y => y;
    let xmin = o.xmin, xmax = o.xmax, ymin = o.ymin, ymax = o.ymax;
    const series = o.series.filter(s => visible.has(s.id) || s.always);
    if (ymin == null || ymax == null) {
      let lo = Infinity, hi = -Infinity;
      series.forEach(s => s.pts.forEach(p => {
        if (p.y == null || !isFinite(p.y) || (o.ylog && p.y <= 0)) return;
        lo = Math.min(lo, p.y - (o.ylog ? 0 : (p.err || 0))); hi = Math.max(hi, p.y + (p.err || 0));
      }));
      if (!isFinite(lo)) { lo = 0; hi = 1; }
      if (o.ylog) { lo = Math.max(lo, o.yfloor || 1e-9); ymin = ymin ?? Math.pow(10, Math.floor(Math.log10(lo))); ymax = ymax ?? Math.pow(10, Math.ceil(Math.log10(hi) + 0.05)); }
      else { const pad = (hi - lo) * 0.08 || 0.01; ymin = ymin ?? lo - pad; ymax = ymax ?? hi + pad; }
    }
    const X = x => m.l + (xs(x) - xs(xmin)) / (xs(xmax) - xs(xmin)) * (W - m.l - m.r);
    const Y = y => H - m.b - (ys(Math.max(y, o.ylog ? ymin : -Infinity)) - ys(ymin)) / (ys(ymax) - ys(ymin)) * (H - m.t - m.b);
    let g = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${o.title || o.ylabel}">`;
    if (o.title) g += `<text class="title" x="${m.l}" y="16">${o.title}</text>`;
    const ticks = (lo, hi, log, given) => {
      if (given) return given;
      if (log) { const t = []; for (let e = Math.ceil(Math.log10(lo)); e <= Math.floor(Math.log10(hi)); e++) t.push(Math.pow(10, e)); return t; }
      const span = hi - lo, step = Math.pow(10, Math.floor(Math.log10(span / 5)));
      const st = [1, 2, 2.5, 5, 10].map(f => f * step).find(s => span / s <= 6);
      const t = []; for (let v = Math.ceil(lo / st) * st; v <= hi + 1e-12; v += st) t.push(+v.toPrecision(10)); return t;
    };
    const yt = ticks(ymin, ymax, o.ylog, o.yticks), xt = ticks(xmin, xmax, o.xlog, o.xticks);
    const tl = (v, log) => log ? (Math.abs(Math.log10(v)) > 2 ? `1e${Math.round(Math.log10(v))}` : `${v}`) : (o.pct ? `${+(v * 100).toFixed(2)}` : `${+v.toPrecision(4)}`);
    yt.forEach(v => { if (v < ymin || v > ymax) return; const y = Y(v); g += `<line class="gridl" x1="${m.l}" x2="${W - m.r}" y1="${y}" y2="${y}"/><text x="${m.l - 6}" y="${y + 4}" text-anchor="end">${o.ylog ? tl(v, true) : tl(v)}</text>`; });
    xt.forEach(v => { if (v < xmin || v > xmax) return; const x = X(v); g += `<line class="gridl" x1="${x}" x2="${x}" y1="${m.t}" y2="${H - m.b}"/><text x="${x}" y="${H - m.b + 16}" text-anchor="middle">${o.xlog && !o.xticks ? tl(v, true) : (o.xfmt ? o.xfmt(v) : +v.toPrecision(4))}</text>`; });
    g += `<line class="axis" x1="${m.l}" x2="${W - m.r}" y1="${H - m.b}" y2="${H - m.b}"/><line class="axis" x1="${m.l}" x2="${m.l}" y1="${m.t}" y2="${H - m.b}"/>`;
    g += `<text x="${(m.l + W - m.r) / 2}" y="${H - 6}" text-anchor="middle">${o.xlabel}</text>`;
    g += `<text transform="translate(14 ${(m.t + H - m.b) / 2}) rotate(-90)" text-anchor="middle">${o.ylabel}</text>`;
    if (o.ref != null) { const y = Y(o.ref); g += `<line class="ref" x1="${m.l}" x2="${W - m.r}" y1="${y}" y2="${y}"/>`; }
    const hits = [];
    const n = series.length;
    series.forEach((s, k) => {
      const c = s.color || color(s.id);
      if (s.kind === "step") {
        let d = "";
        s.pts.forEach((p, i) => {
          const v = p.y == null || !isFinite(p.y) || (o.ylog && p.y <= 0) ? (o.ylog ? ymin : 0) : p.y;
          const x0 = X(p.x0), x1 = X(p.x1), y = Y(v);
          d += (i === 0 ? `M${x0},${Y(o.ylog ? ymin : 0)}L${x0},${y}` : `L${x0},${y}`) + `L${x1},${y}`;
          hits.push({ x: (x0 + x1) / 2, y, s, p });
        });
        g += `<path d="${d}" fill="none" stroke="${c}" stroke-width="${s.width || 1.6}" stroke-dasharray="${s.dash || ""}"/>`;
      } else if (s.kind === "line") {
        const d = s.pts.filter(p => p.y != null && isFinite(p.y) && (!o.ylog || p.y > 0)).map((p, i) => `${i ? "L" : "M"}${X(p.x)},${Y(p.y)}`).join("");
        g += `<path d="${d}" fill="none" stroke="${c}" stroke-width="${s.width || 2}" stroke-dasharray="${s.dash || ""}"/>`;
        s.pts.forEach(p => { if (p.y != null && isFinite(p.y)) hits.push({ x: X(p.x), y: Y(p.y), s, p }); });
      } else {
        const dx = o.dodge ? (k - (n - 1) / 2) * o.dodge : 0;
        s.pts.forEach(p => {
          if (p.y == null || !isFinite(p.y)) return;
          const x = X(p.x) + dx, y = Y(p.y);
          if (p.err) g += `<line x1="${x}" x2="${x}" y1="${Y(p.y - p.err)}" y2="${Y(p.y + p.err)}" stroke="${c}" stroke-width="2"/>`;
          g += `<circle cx="${x}" cy="${y}" r="${s.r || 4.5}" fill="${c}" stroke="var(--paper)" stroke-width="2"/>`;
          if (s.labels) { const right = x < W * 0.6; g += `<text x="${right ? x + 9 : x - 9}" y="${y + (s.dy || -7)}" text-anchor="${right ? "start" : "end"}" style="fill:var(--ink)">${p.label}</text>`; }
          hits.push({ x, y, s, p });
        });
      }
    });
    g += `<rect x="${m.l}" y="${m.t}" width="${W - m.l - m.r}" height="${H - m.t - m.b}" fill="transparent" class="hit"/></svg><div class="tip" hidden></div>`;
    el.innerHTML = g;
    const svg = el.querySelector("svg"), tip = el.querySelector(".tip");
    const move = ev => {
      const r = svg.getBoundingClientRect(), sx = W / r.width;
      const px = (ev.clientX - r.left) * sx, py = (ev.clientY - r.top) * sx;
      let best = null, bd = Infinity;
      hits.forEach(h => { const d = Math.hypot(h.x - px, (h.y - py) * 0.6); if (d < bd) { bd = d; best = h; } });
      if (!best || bd > 40) { tip.hidden = true; return; }
      tip.hidden = false;
      tip.style.left = `${best.x / sx}px`; tip.style.top = `${best.y / sx}px`;
      tip.textContent = o.tip ? o.tip(best.s, best.p) : `${best.s.label}: ${fmt(best.p.y, 4)}`;
    };
    svg.addEventListener("pointermove", move);
    svg.addEventListener("pointerleave", () => { tip.hidden = true; });
  }

  const label = id => cfgs.find(c => c.id === id).label;
  const centers = (b, log) => b.slice(0, -1).map((x, i) => log ? Math.sqrt(x * b[i + 1]) : (x + b[i + 1]) / 2);
  const state = { effSel: "tail", effVar: "pt", fakeVar: "pt", resMetric: "pull_eQOP_q68", dist: "pullqop_tail", pv: "state_tail", pvLog: "state_all" };

  const draws = {
    tradeoff(el) {
      chart(el, {
        title: "Tail efficiency against fake rate", xlabel: "fake rate [%]", ylabel: "efficiency, tail primaries [%]",
        xmin: 0, xmax: Math.max(...cfgs.map(c => DATA.summary[c.id].fake_rate)) * 100 * 1.15,
        series: cfgs.map(c => ({ id: c.id, label: c.label, r: 7, pts: [{ x: 100 * DATA.summary[c.id].fake_rate, y: 100 * DATA.summary[c.id].eff_tail, err: 100 * DATA.summary[c.id].eff_tail_err, label: c.label }] })),
        tip: (s, p) => `${s.label}: eff ${p.y.toFixed(2)} %, fake ${p.x.toFixed(3)} %`,
      });
    },
    cputradeoff(el) {
      const T = DATA.summary;
      chart(el, {
        title: "Tail efficiency against CKF time", xlabel: "CKF time, 1 thread [s / event]", ylabel: "efficiency, tail primaries [%]",
        xmin: Math.min(...cfgs.map(c => T[c.id].ckf_s_per_event || 9)) * 0.95, xmax: Math.max(...cfgs.map(c => T[c.id].ckf_s_per_event || 0)) * 1.06,
        series: cfgs.filter(c => T[c.id].ckf_s_per_event).map(c => ({ id: c.id, label: c.label, r: 7, pts: [{ x: T[c.id].ckf_s_per_event, y: 100 * T[c.id].eff_tail, label: c.label }] })),
        tip: (s, p) => `${s.label}: eff ${p.y.toFixed(2)} %, ${p.x.toFixed(3)} s/event`,
      });
    },
    eff(el) {
      const b = DATA[state.effVar === "pt" ? "ptBins" : "etaBins"], log = state.effVar === "pt";
      const xc = centers(b, log);
      chart(el, {
        xlog: log, xmin: b[0], xmax: b[b.length - 1], xticks: log ? [1, 2, 5, 10, 20, 50, 100] : null, dodge: 4,
        xlabel: log ? "truth pT [GeV]" : "truth η", ylabel: "efficiency [%]", pct: true,
        title: `Efficiency, ${state.effSel === "tail" ? "tail" : "no-tail"} primaries`,
        series: cfgs.map(c => { const d = DATA.curves[c.id][`${state.effSel}_${state.effVar}`]; return { id: c.id, label: c.label, pts: xc.map((x, i) => ({ x, y: d.e[i], err: d.err[i] })) }; }),
        tip: (s, p) => `${s.label}: ${(100 * p.y).toFixed(2)} ± ${(100 * p.err).toFixed(2)} %`,
      });
    },
    fake(el) {
      const b = DATA[state.fakeVar === "pt" ? "ptBins" : "etaBins"], log = state.fakeVar === "pt";
      const xc = centers(b, log);
      chart(el, {
        xlog: log, xmin: b[0], xmax: b[b.length - 1], xticks: log ? [1, 2, 5, 10, 20, 50, 100] : null, dodge: 4, ymin: 0,
        xlabel: log ? "reco pT [GeV]" : "reco η", ylabel: "fake rate [%]", pct: true, title: "Fake rate of the output tracks",
        series: cfgs.map(c => { const d = DATA.curves[c.id][`fake_${state.fakeVar}`]; return { id: c.id, label: c.label, pts: xc.map((x, i) => ({ x, y: d.e[i], err: d.err[i] })) }; }),
        tip: (s, p) => `${s.label}: ${(100 * p.y).toFixed(3)} ± ${(100 * p.err).toFixed(3)} %`,
      });
    },
    res(el) {
      const mm = state.resMetric;
      const names = { d0_q68_um: "d0 residual q68 [µm]", z0_q68_um: "z0 residual q68 [µm]", phi_q68_mrad: "φ residual q68 [mrad]", theta_q68_mrad: "θ residual q68 [mrad]", qop_rel_q68: "q/p relative residual q68", pull_eQOP_q68: "q/p pull q68", pull_eLOC0_q68: "d0 pull q68", pull_eQOP_gt5: "fraction |q/p pull| > 5", pull_eLOC0_gt5: "fraction |d0 pull| > 5" };
      chart(el, {
        xmin: -0.5, xmax: 1.5, xticks: [0, 1], xfmt: v => v === 0 ? "tail" : "no tail", dodge: 14, height: 280,
        xlabel: "matched tracks, split by the truth tail flag", ylabel: names[mm], title: names[mm],
        series: cfgs.map(c => ({ id: c.id, label: c.label, r: 6, pts: [{ x: 0, y: DATA.summary[c.id].res.tail[mm] }, { x: 1, y: DATA.summary[c.id].res.core[mm] }] })),
        tip: (s, p) => `${s.label}: ${fmt(p.y, 4)}`,
      });
    },
    dist(el) {
      const k = state.dist, b = DATA[k === "d0_tail" ? "d0Bins" : "pullBins"];
      chart(el, {
        ylog: true, xmin: b[0], xmax: b[b.length - 1], yfloor: 1e-6,
        xlabel: k === "d0_tail" ? "d0 residual [µm] (overflow in the edge bins)" : (k === "pullqop_tail" ? "q/p pull" : "d0 pull") + " (overflow in the edge bins)",
        ylabel: "density", title: "Matched tail tracks",
        series: cfgs.map(c => ({ id: c.id, label: c.label, kind: "step", pts: DATA.curves[c.id][k].map((y, i) => ({ x0: b[i], x1: b[i + 1], y })) })),
        tip: (s, p) => `${s.label}: ${fmt(p.y, 5)} at ${((p.x0 + p.x1) / 2).toFixed(2)}`,
      });
    },
    pv(el) {
      const b = DATA.linBins, k = state.pv;
      const t = { track_all: "Track p-value, all tracks", track_tail: "Track p-value, matched tail tracks", track_core: "Track p-value, matched no-tail tracks", state_all: "State p-value, all tracks", state_tail: "State p-value, matched tail tracks", state_core: "State p-value, matched no-tail tracks" };
      chart(el, {
        ylog: true, xmin: 0, xmax: 1, ref: 1, yfloor: 0.1, xlabel: "p-value", ylabel: "density (uniform = 1)", title: t[k],
        series: cfgs.map(c => ({ id: c.id, label: c.label, kind: "step", pts: DATA.curves[c.id][`p_${k}`].map((y, i) => ({ x0: b[i], x1: b[i + 1], y })) })),
        tip: (s, p) => `${s.label}: ${fmt(p.y, 3)} in [${p.x0.toFixed(3)}, ${p.x1.toFixed(3)}]`,
      });
    },
    pvlog(el) {
      const b = DATA.logBins.map(v => Math.pow(10, v)), k = state.pvLog;
      chart(el, {
        xlog: true, ylog: true, xmin: 1e-12, xmax: 1, yfloor: 1e-6, xlabel: "p-value (underflow at 1e-12)", ylabel: "fraction per bin",
        title: k === "track_all" ? "Track p-value, all tracks" : "State p-value, all tracks",
        series: cfgs.map(c => ({ id: c.id, label: c.label, kind: "step", pts: DATA.curves[c.id][`plog_${k}`].map((y, i) => ({ x0: b[i], x1: b[i + 1], y })) })),
        tip: (s, p) => `${s.label}: ${fmt(p.y, 6)} in [${p.x0.toExponential(0)}, ${p.x1.toExponential(0)}]`,
      });
    },
    cpu(el) {
      const T = DATA.timing, ids = cfgs.map(c => c.id).filter(id => T[id]);
      const series = ids.map((id, i) => ({ id, label: label(id), r: 6, pts: [{ x: i, y: T[id].reduce((a, b) => a + b, 0) / T[id].length }] }));
      ids.forEach((id, i) => series.push({ id, label: label(id) + " run", r: 3, color: "var(--muted)", pts: T[id].map(v => ({ x: i + 0.18, y: v })) }));
      chart(el, {
        xmin: -0.6, xmax: ids.length - 0.4, xticks: ids.map((_, i) => i), xfmt: v => label(ids[v]).replace(" 15/25", "").replace(" 49/100", " 49"), height: 300,
        xlabel: "configuration (single runs to the right of each mean)", ylabel: "CKF time [s / event]", title: "TrackFindingAlgorithm, single thread, 20 events per run",
        series, tip: (s, p) => `${s.label}: ${p.y.toFixed(3)} s/event`,
      });
    },
    model(el) {
      const M = DATA.model; if (!M) return;
      chart(el, {
        ylog: true, xmin: -15, xmax: 15, yfloor: 1e-6, ymin: 1e-6, xlabel: "projected angle / Highland θ0", ylabel: "density", title: "Scattering at 2 % X0 (Si)",
        series: [
          { id: "m1", always: true, label: "Fatras general mixture", kind: "step", color: "var(--c-base15)", pts: M.x.map((x, i) => ({ x0: x - 0.05, x1: x + 0.05, y: M.sampled[i] })) },
          { id: "m2", always: true, label: "two-Gaussian tail model", kind: "line", color: "var(--c-base49)", pts: M.x.map((x, i) => ({ x, y: M.fit[i] })) },
          { id: "m3", always: true, label: "Highland Gaussian (KF core)", kind: "line", dash: "4 3", width: 1.5, color: "var(--muted)", pts: M.x.map((x, i) => ({ x, y: M.hl[i] })) },
        ],
        tip: (s, p) => `${s.label}: ${fmt(p.y, 6)}`,
      });
    },
    modeltable(el) {
      const M = DATA.model; if (!M) return;
      el.innerHTML = `<div class="tablewrap"><table><thead><tr><th>x / X0</th>${M.ts.map(t => `<th>${(100 * t).toFixed(1)} %</th>`).join("")}</tr></thead><tbody>
        <tr><td>tail weight ε</td>${M.eps.map(v => `<td>${v.toFixed(4)}</td>`).join("")}</tr>
        <tr><td>tail width k [Highland]</td>${M.k.map(v => `<td>${v.toFixed(2)}</td>`).join("")}</tr></tbody></table></div>`;
    },
    summary(el) {
      const S = DATA.summary;
      const rows = [
        ["Efficiency, all primaries [%]", s => 100 * s.eff_all, 2, "max"],
        ["Efficiency, tail primaries [%]", s => 100 * s.eff_tail, 2, "max", s => 100 * s.eff_tail_err],
        ["Efficiency, no-tail primaries [%]", s => 100 * s.eff_core, 2, "max"],
        ["Fake rate [%]", s => 100 * s.fake_rate, 3, "min"],
        ["Tracks / event", s => s.tracks_per_event, 1, null],
        ["Tail-accepted states / event, all branches", s => s.tail_states_per_event || 0, 0, null],
        ["Measurements / matched tail track", s => s.nmeas_tail, 2, "max"],
        ["d0 residual q68, tail [µm]", s => s.res.tail.d0_q68_um, 1, "min"],
        ["q/p rel. residual q68, tail [%]", s => 100 * s.res.tail.qop_rel_q68, 2, "min"],
        ["q/p pull q68, tail", s => s.res.tail.pull_eQOP_q68, 3, "min"],
        ["|q/p pull| > 5, tail [%]", s => 100 * s.res.tail.pull_eQOP_gt5, 2, "min"],
        ["q/p pull q68, no tail", s => s.res.core.pull_eQOP_q68, 3, "min"],
        ["Tracks with p < 1e-3 [%]", s => 100 * s["frac_track_p_lt_1e-3"], 2, "min"],
        ["Non-seed states with selection p < 1e-3 [%]", s => 100 * s["frac_state_p_lt_1e-3"], 2, null],
        ["CKF time, 1 thread [s / event]", s => s.ckf_s_per_event, 3, "min"],
      ];
      const shown = cfgs.filter(c => visible.has(c.id));
      let h = `<div class="tablewrap"><table><thead><tr><th>Metric</th>${shown.map(c => `<th><span class="sw" style="background:${color(c.id)}"></span>${c.label}</th>`).join("")}</tr></thead><tbody>`;
      rows.forEach(([name, f, d, best, err]) => {
        const vals = shown.map(c => f(S[c.id]));
        const ok = vals.filter(v => v != null && isFinite(v));
        const b = best === "max" ? Math.max(...ok) : best === "min" ? Math.min(...ok) : null;
        h += `<tr><td>${name}</td>${shown.map((c, i) => { const v = vals[i]; const e = err ? err(S[c.id]) : null;
          return `<td class="${b != null && v === b ? "best" : ""}">${v == null || !isFinite(v) ? "–" : v.toFixed(d)}${e ? ` ± ${e.toFixed(d)}` : ""}</td>`; }).join("")}</tr>`;
      });
      el.innerHTML = h + "</tbody></table></div>";
    },
  };

  document.querySelectorAll(".seg").forEach(seg => {
    const key = seg.dataset.state;
    seg.querySelectorAll("button").forEach(b => {
      b.setAttribute("aria-pressed", b.dataset.v === state[key]);
      b.addEventListener("click", () => {
        state[key] = b.dataset.v;
        seg.querySelectorAll("button").forEach(x => x.setAttribute("aria-pressed", x === b));
        redraw();
      });
    });
  });

  function redraw() {
    document.querySelectorAll("[data-chart]").forEach(el => { const f = draws[el.dataset.chart]; if (f) f(el); });
  }
  redraw();
  requestAnimationFrame(redraw);
  let rt = null;
  window.addEventListener("resize", () => { clearTimeout(rt); rt = setTimeout(redraw, 150); });
})();
</script>
"""

DESCRIPTIONS = {
    "base15": ("No tail treatment", "Gaussian CKF with the ODD default cuts: chi2 15 to accept a measurement, 25 to keep it as an outlier. The prediction uses the Highland scattering only. This is the reference for all candidates."),
    "base25": ("No tail treatment", "As baseline 15/25, but with a looser cut of 25/50. It accepts more hits after a large scatter, but the update keeps the core covariance."),
    "base35": ("No tail treatment", "As baseline 25/50, with the cut 35/70."),
    "base49": ("No tail treatment", "As baseline 25/50, with the cut 49/100. This is the inflated cut, close to the 7σ / 10σ of the ATLAS ITk ACTS pass."),
    "retry15": ("Tail treatment at 15/25", "Selects with the core covariance C first. If that gives only a hole or an outlier, it selects again with C + D, where D is the tail covariance of the material since the last hit. The Kalman update uses C + D, so the track can bend at the scatter."),
    "mix15": ("Tail treatment at 15/25", "Selects once with the chi2 of a two-component prediction: the core C with weight 1 − ε, and the tail C + D with weight ε. The cut keeps its meaning for small residuals. The update uses C + w D, where w is the posterior weight of the tail for that hit."),
    "branch15": ("Tail treatment at 15/25", "As retry, but the hole or outlier of the first selection is also kept as a second branch. The branch stopper and the ambiguity resolution choose between the two."),
    "selonly15": ("Tail treatment at 15/25", "As retry, but the update uses the core covariance C. The tail only widens the selection window, so the fit must absorb the kink with the other parameters."),
}
ORDER = ["base15", "base25", "base35", "base49", "retry15", "mix15", "branch15", "selonly15"]
export["configs"].sort(key=lambda c: ORDER.index(c["id"]))
for c in export["configs"]:
    c["group"], c["desc"] = DESCRIPTIONS[c["id"]]

meta = export["meta"]
for k, v in {
    "%EVENTS%": str(meta["events"]),
    "%TAILFRAC%": f"{100 * meta['tailFraction']:.1f} %",
    "%NPRIM%": f"{meta['nPrimaries']:,}".replace(",", " "),
    "%RATIO%": f"{meta['ratio']:g}",
    "%RHOMIN%": f"{meta['rhoMin']:g}",
}.items():
    content = content.replace(k, v)
missing = [w for w in content.split("%") if w.isupper() and len(w) > 3]
if missing:
    print("unfilled placeholders:", missing)

data = json.dumps(export, default=float, allow_nan=True)
html = TEMPLATE.replace("%CONTENT%", content).replace("%DATA%", data)
open(out, "w").write(html)
print(f"wrote {out}: {len(html)/1024:.0f} kB")
