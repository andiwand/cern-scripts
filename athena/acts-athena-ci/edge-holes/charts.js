// Inline SVG charts (edge-hole note; from the GBTS vs CKF note): binned lines with error bars and stacked bars, per panel edges.
// Needs const CH = {figs, notes}; panel col "L" shown, "D" folded into a details block.
const NS = "http://www.w3.org/2000/svg";
const el = (n, a, p) => { const e = document.createElementNS(NS, n); for (const k in a) e.setAttribute(k, a[k]); if (p) p.appendChild(e); return e; };
function nice(m) { const p = Math.pow(10, Math.floor(Math.log10(m)) - 1); for (const s of [1, 2, 2.5, 5, 10, 20, 25, 50, 100]) if (m / (s * p) <= 6) return s * p; return 100 * p; }
const fmt = (v, u) => v == null ? "–" : (u === "%" ? (Math.abs(v) < 10 ? v.toFixed(2) : v.toFixed(1)) + "%" : Math.abs(v) >= 100 ? v.toFixed(0) : v.toFixed(1));
const bin = (p, i) => `${p.edges[i]}–${p.edges[i + 1]}`;
function chart(host, p) {
  const box = document.createElement("div"); box.className = "chart"; host.appendChild(box);
  box.innerHTML = `<div class="ct">${p.title}</div><div class="legend">` + p.series.map(s => `<span><i style="background:var(${s.color})"></i>${s.label}</span>`).join("") + "</div>";
  const tip = document.createElement("div"); tip.className = "tip"; tip.hidden = true; box.appendChild(tip);
  const nb = p.edges.length - 1, W = 460, H = 250, l = 50, r = 8, t = 8, b = 34, pw = W - l - r, ph = H - t - b, bw = pw / nb;
  const unit = p.unit || p.ylabel;
  let hi = p.ymax, lo = p.ymin ?? 0;
  if (hi == null) {
    hi = 0;
    if (p.kind === "stack") for (let i = 0; i < nb; i++) hi = Math.max(hi, p.series.reduce((a, s) => a + (s.v[i] || 0), 0));
    else for (const s of p.series) s.v.forEach((v, i) => { if (v != null) hi = Math.max(hi, v + (s.e ? s.e[i] || 0 : 0)); });
    const st = nice(hi * 1.1 || 1); hi = Math.ceil(hi * 1.1 / st) * st || 1;
  }
  const y = v => t + ph * (1 - (Math.max(lo, Math.min(hi, v)) - lo) / (hi - lo));
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, width: "100%", role: "img", "aria-label": p.title, style: "font-size:11px;fill:var(--fg-2)" }, box);
  const step = nice(hi - lo);
  for (let v = Math.ceil(lo / step) * step; v <= hi + 1e-9; v += step) {
    el("line", { x1: l, x2: W - r, y1: y(v), y2: y(v), stroke: Math.abs(v) < 1e-9 ? "var(--axis)" : "var(--grid)" }, svg);
    const tx = el("text", { x: l - 6, y: y(v) + 4, "text-anchor": "end" }, svg); tx.textContent = +v.toFixed(2) + (unit === "%" ? "%" : "");
  }
  const every = nb > 12 ? 2 : 1;
  for (let i = 0; i <= nb; i += every) { const tx = el("text", { x: l + i * bw, y: H - b + 15, "text-anchor": "middle" }, svg); tx.textContent = p.edges[i]; }
  const xl = el("text", { x: l + pw / 2, y: H - 4, "text-anchor": "middle" }, svg); xl.textContent = p.xlabel;
  if (p.kind === "stack") {
    for (let i = 0; i < nb; i++) {
      let acc = 0;
      p.series.forEach(s => {
        const v = s.v[i]; if (!v) return;
        const y0 = y(acc), y1 = y(acc + v); acc += v;
        el("rect", { x: l + i * bw + 2, y: y1, width: bw - 4, height: Math.max(0, y0 - y1 - 1), fill: `var(${s.color})`, rx: 1.5 }, svg);
      });
    }
  } else {
    const ns = p.series.length, off = k => (k - (ns - 1) / 2) * Math.min(4, bw / (ns + 1));
    p.series.forEach((s, k) => {
      let d = "";
      s.v.forEach((v, i) => { if (v == null) return; const X = l + (i + 0.5) * bw + off(k); d += (d && s.v[i - 1] != null ? "L" : "M") + X + " " + y(v); });
      el("path", { d, fill: "none", stroke: `var(${s.color})`, "stroke-width": 2, "stroke-linejoin": "round" }, svg);
      s.v.forEach((v, i) => {
        if (v == null) return; const X = l + (i + 0.5) * bw + off(k);
        if (s.e && s.e[i]) el("line", { x1: X, x2: X, y1: y(v - s.e[i]), y2: y(v + s.e[i]), stroke: `var(${s.color})`, "stroke-width": 1.5 }, svg);
        el("circle", { cx: X, cy: y(v), r: 3.2, fill: `var(${s.color})`, stroke: "var(--surface)", "stroke-width": 1.5 }, svg);
      });
    });
  }
  for (let i = 0; i < nb; i++) {
    const hit = el("rect", { x: l + i * bw, y: t, width: bw, height: ph, fill: "transparent" }, svg);
    const rows = p.series.map(s => `<i style="display:inline-block;width:8px;height:8px;border-radius:2px;margin-right:4px;background:var(${s.color})"></i>${s.label}: ${fmt(s.v[i], unit)}` +
      (s.e && s.e[i] != null ? ` ± ${fmt(s.e[i], unit)}` : "") + (s.n && s.n[i] != null ? ` <span style="opacity:.7">(n ${s.n[i]})</span>` : ""));
    const html = `${bin(p, i)}` + (p.n ? ` · ${p.n[i]} ${p.nlabel}` : "") + "<br>" + rows.join("<br>");
    hit.addEventListener("mousemove", ev => {
      tip.innerHTML = html; tip.hidden = false; const R = box.getBoundingClientRect();
      tip.style.left = Math.max(2, Math.min(ev.clientX - R.left + 12, R.width - tip.offsetWidth - 4)) + "px";
      tip.style.top = Math.max(ev.clientY - R.top - tip.offsetHeight - 8, 2) + "px";
    });
    hit.addEventListener("mouseleave", () => tip.hidden = true);
  }
}
function table(p) {
  const unit = p.unit || p.ylabel, nb = p.edges.length - 1, rows = [];
  const head = (p.n ? `<th class=n>${p.nlabel}</th>` : "") + p.series.map(s => `<th class=n>${s.label}</th>`).join("");
  for (let i = 0; i < nb; i++) {
    if (!p.series.some(s => s.v[i] != null)) continue;
    rows.push(`<tr><td>${bin(p, i)}</td>` + (p.n ? `<td class=n>${p.n[i]}</td>` : "") + p.series.map(s => `<td class=n>${fmt(s.v[i], unit)}${s.e && s.e[i] != null ? " ± " + fmt(s.e[i], unit) : ""}</td>`).join("") + "</tr>");
  }
  return `<h4>${p.title}</h4><div class="tw"><table><thead><tr><th>${p.x === "pt" ? "pT [GeV]" : p.x === "d0" ? "|d0| [mm]" : "|η|"}</th>${head}</tr></thead><tbody>${rows.join("")}</tbody></table></div>`;
}
document.querySelectorAll(".plot").forEach(host => {
  const name = host.dataset.plot, F = CH.figs[name];
  const g = document.createElement("div"); g.className = "grid2"; host.appendChild(g);
  F.filter(p => p.col !== "D").forEach(p => chart(g, p));
  const dd = F.filter(p => p.col === "D");
  if (dd.length) {
    const d = document.createElement("details"); d.innerHTML = "<summary>" + ((CH.more || {})[name] || "More panels") + "</summary>";
    const g2 = document.createElement("div"); g2.className = "grid2"; d.appendChild(g2); dd.forEach(p => chart(g2, p)); host.appendChild(d);
  }
  const note = document.createElement("p"); note.className = "cap"; note.textContent = CH.notes[name] || ""; host.appendChild(note);
  const d = document.createElement("details"); d.innerHTML = "<summary>Values per bin</summary>" + F.map(table).join(""); host.appendChild(d);
});
