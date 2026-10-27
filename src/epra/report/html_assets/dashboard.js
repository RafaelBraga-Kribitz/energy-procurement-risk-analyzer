/* EPRA HTML dashboard twin (ADR-022): vanilla JS, inline SVG, no dependencies.
   Draws every chart from the JSON embedded by epra.report.html_dashboard. Labels come
   from data, so all text goes through textContent, never innerHTML. */
(function () {
  "use strict";
  var D = JSON.parse(document.getElementById("epra-data").textContent);
  var NS = "http://www.w3.org/2000/svg";
  var LABEL = {};
  D.strategies.forEach(function (s) { LABEL[s.id] = s.label; });
  var IDS = D.strategies.map(function (s) { return s.id; });
  var MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  var state = { year: "all", variant: "unconditional", metric: "cost", page: null };
  var tip = document.getElementById("tip");
  var live = document.getElementById("live");

  /* ---- RP-703 formatters (mirror of epra.report.format) ---- */
  function nf(v, d) {
    return v.toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });
  }
  function fmtM(v, d) { return "€" + nf(v / 1e6, d === undefined ? 2 : d) + " M"; }
  function fmtEur(v) { return "€" + nf(Math.round(v), 0); }
  function fmtMwh(v) { return nf(v, 1) + " EUR/MWh"; }
  function fmtInt(v) { return nf(Math.round(v), 0); }
  function sv(id) { return "var(--s-" + id + ")"; }
  function monthLabel(m) { return MONTHS[+m.slice(5, 7) - 1] + " " + m.slice(0, 4); }
  function mDecimals(ticks) {
    var step = ticks.length > 1 ? Math.abs(ticks[1] - ticks[0]) : 1e6;
    return step >= 1e6 ? 0 : step >= 1e5 ? 1 : 2;
  }

  /* ---- SVG helpers ---- */
  function el(tag, attrs, parent) {
    var e = document.createElementNS(NS, tag);
    for (var k in attrs) { if (Object.prototype.hasOwnProperty.call(attrs, k)) e.setAttribute(k, attrs[k]); }
    if (parent) parent.appendChild(e);
    return e;
  }
  function text(parent, x, y, s, attrs) {
    var a = { x: x, y: y };
    for (var k in attrs || {}) { a[k] = attrs[k]; }
    var t = el("text", a, parent);
    t.textContent = s;
    return t;
  }
  var ctx = document.createElement("canvas").getContext("2d");
  function tw(s, size, weight) {
    ctx.font = (weight || 400) + " " + (size || 12) + "px -apple-system,'Segoe UI',Inter,Roboto,sans-serif";
    return ctx.measureText(s).width;
  }
  function lin(d0, d1, r0, r1) {
    var k = (r1 - r0) / ((d1 - d0) || 1);
    return function (v) { return r0 + (v - d0) * k; };
  }
  function niceTicks(lo, hi, n) {
    if (!isFinite(lo) || !isFinite(hi)) { lo = 0; hi = 1; }
    if (hi === lo) { hi = lo + 1; }
    var raw = (hi - lo) / n, mag = Math.pow(10, Math.floor(Math.log10(raw))), e = raw / mag;
    var step = (e >= 7.5 ? 10 : e >= 3.5 ? 5 : e >= 1.5 ? 2 : 1) * mag;
    var a = Math.floor(lo / step + 1e-9), b = Math.ceil(hi / step - 1e-9), out = [];
    for (var i = a; i <= b; i++) { out.push(i * step); }
    return out;
  }
  function maxOf(a) { return a.reduce(function (m, v) { return v != null && v > m ? v : m; }, -Infinity); }
  function minOf(a) { return a.reduce(function (m, v) { return v != null && v < m ? v : m; }, Infinity); }
  function plot(id) { return document.getElementById("plot-" + id); }
  function frame(host, o) {
    host.replaceChildren();
    var w = Math.max(240, Math.floor(host.clientWidth));
    var h = typeof o.height === "function" ? o.height(w) : o.height;
    var svg = el("svg", { width: w, height: h, viewBox: "0 0 " + w + " " + h, role: "img",
      "aria-label": o.label }, host);
    svg.style.width = "100%";
    host.setAttribute("role", "group");
    host.setAttribute("aria-label", o.label + ". Focus and use the arrow keys to read values.");
    return { host: host, svg: svg, w: w, h: h, m: o.m };
  }
  function yAxis(f, y, ticks, fmt) {
    ticks.forEach(function (t) {
      var yy = Math.round(y(t)) + 0.5;
      el("line", { x1: f.m.l, x2: f.w - f.m.r, y1: yy, y2: yy, "class": "grid-l" }, f.svg);
      text(f.svg, f.m.l - 8, yy + 4, fmt(t), { "text-anchor": "end" });
    });
  }
  function xBase(f, yy) {
    el("line", { x1: f.m.l, x2: f.w - f.m.r, y1: Math.round(yy) + 0.5, y2: Math.round(yy) + 0.5,
      "class": "axis-l" }, f.svg);
  }
  function monthAxis(f, months, x) {
    var yb = f.h - f.m.b;
    if (months.length <= 24) {
      var per = months.length > 1 ? x(1) - x(0) : 60, step = Math.max(1, Math.ceil(38 / per));
      months.forEach(function (m, i) {
        if (i % step) return;
        var lbl = months.length <= 12 ? MONTHS[+m.slice(5, 7) - 1] : MONTHS[+m.slice(5, 7) - 1] + " " + m.slice(2, 4);
        text(f.svg, x(i), yb + 17, lbl, { "text-anchor": "middle" });
      });
      return;
    }
    var perYear = (x(1) - x(0)) * 12, ystep = Math.max(1, Math.ceil(44 / perYear));
    months.forEach(function (m, i) {
      if (m.slice(5) !== "01" || (+m.slice(0, 4)) % ystep) return;
      el("line", { x1: x(i), x2: x(i), y1: yb, y2: yb + 4, "class": "axis-l" }, f.svg);
      text(f.svg, x(i), yb + 17, m.slice(0, 4), { "text-anchor": "middle" });
    });
  }
  function legend(id, items, box) {
    var L = document.getElementById("legend-" + id);
    if (!L) return;
    L.replaceChildren();
    if (items.length < 2) return;
    items.forEach(function (it) {
      var s = document.createElement("span"), i = document.createElement("i");
      if (box) i.className = "box";
      i.style.background = it.color;
      s.appendChild(i);
      s.appendChild(document.createTextNode(it.label));
      L.appendChild(s);
    });
  }

  /* ---- tooltip + keyboard layer: tooltips enhance, the data tables carry every value ---- */
  function showTip(f, px, py, title, rows) {
    tip.replaceChildren();
    var h = document.createElement("div");
    h.className = "tt-h";
    h.textContent = title;
    tip.appendChild(h);
    rows.forEach(function (r) {
      var row = document.createElement("div"), i = document.createElement("i");
      var v = document.createElement("strong"), l = document.createElement("span");
      row.className = "tt-r";
      i.style.background = r.color || "transparent";
      v.textContent = r.value;
      l.textContent = r.label;
      row.appendChild(i); row.appendChild(v); row.appendChild(l);
      tip.appendChild(row);
    });
    tip.hidden = false;
    var rect = f.svg.getBoundingClientRect(), s = rect.width / f.w;
    var vw = document.documentElement.clientWidth, width = tip.offsetWidth;
    var left = rect.left + window.scrollX + px * s + 14;
    if (left + width > window.scrollX + vw - 8) left = rect.left + window.scrollX + px * s - width - 14;
    left = Math.max(window.scrollX + 8, left);
    tip.style.left = left + "px";
    tip.style.top = (rect.top + window.scrollY + py * s - 12) + "px";
  }
  function interact(f, stops, opts) {
    var idx = -1, hot = null, cross = null;
    if (opts.crosshair) {
      cross = el("line", { "class": "cross", y1: f.m.t, y2: f.h - f.m.b, visibility: "hidden" }, f.svg);
    }
    el("rect", { x: 0, y: 0, width: f.w, height: f.h, fill: "transparent" }, f.svg);
    function pick(i, announce) {
      if (i < 0 || i >= stops.length) return;
      idx = i;
      var s = stops[i];
      if (cross) {
        cross.setAttribute("x1", s.x); cross.setAttribute("x2", s.x);
        cross.setAttribute("visibility", "visible");
      }
      if (hot) hot.classList.remove("hot");
      hot = s.mark || null;
      if (hot) hot.classList.add("hot");
      showTip(f, s.x, s.y, s.title, s.rows);
      if (announce) {
        live.textContent = s.title + ": " + s.rows.map(function (r) { return r.label + " " + r.value; }).join(", ");
      }
    }
    function clear() {
      if (cross) cross.setAttribute("visibility", "hidden");
      if (hot) hot.classList.remove("hot");
      hot = null;
      tip.hidden = true;
    }
    function nearest(ev) {
      var r = f.svg.getBoundingClientRect(), k = f.w / r.width;
      var px = (ev.clientX - r.left) * k, py = (ev.clientY - r.top) * k, best = 0, bd = Infinity;
      stops.forEach(function (s, i) {
        var d = opts.xy ? Math.hypot(s.x - px, s.y - py) : Math.abs(s.x - px);
        if (d < bd) { bd = d; best = i; }
      });
      return best;
    }
    f.svg.addEventListener("pointermove", function (ev) { pick(nearest(ev), false); });
    f.svg.addEventListener("pointerleave", clear);
    f.host.tabIndex = 0;
    f.host.onkeydown = function (ev) {
      var k = ev.key, j = null;
      if (k === "ArrowRight" || k === "ArrowDown") j = Math.min(stops.length - 1, idx + 1);
      else if (k === "ArrowLeft" || k === "ArrowUp") j = Math.max(0, idx - 1);
      else if (k === "Home") j = 0;
      else if (k === "End") j = stops.length - 1;
      else if (k === "Escape") { clear(); return; }
      if (j !== null) { ev.preventDefault(); pick(j, true); }
    };
    f.host.onfocus = function () { pick(idx < 0 ? 0 : idx, true); };
    f.host.onblur = clear;
  }

  /* ---- chart forms ---- */
  function columns(host, o) {
    var yt = niceTicks(Math.min(0, minOf(o.values)), Math.max(0, maxOf(o.values)), 5);
    var lw = maxOf(yt.map(function (t) { return tw(o.fmtAxis(t, yt)); })) + 14;
    var f = frame(host, { height: o.height, label: o.label,
      m: { t: o.valueLabels ? 24 : 10, r: 8, b: o.sub ? 62 : 28, l: lw } });
    var y = lin(yt[0], yt[yt.length - 1], f.h - f.m.b, f.m.t);
    yAxis(f, y, yt, function (t) { return o.fmtAxis(t, yt); });
    var n = o.values.length, band = (f.w - f.m.l - f.m.r) / n;
    var bw = Math.max(1, Math.min(o.maxBar || 24, band - 2));
    var widest = maxOf(o.cats.map(function (c) { return c ? tw(c) : 0; }));
    var step = Math.max(1, Math.ceil((widest + 10) / band)), stops = [];
    o.values.forEach(function (v, i) {
      var cx = f.m.l + band * (i + 0.5), top = y(Math.max(0, v)), y0 = y(0);
      var r = el("rect", { x: cx - bw / 2, y: Math.min(top, y(Math.min(0, v))), width: bw,
        height: Math.max(0, Math.abs(y(v) - y0)) }, f.svg);
      r.style.fill = o.colors[i];
      if (o.valueLabels) text(f.svg, cx, top - 7, o.fmtVal(v), { "text-anchor": "middle", "class": "lbl" });
      if (o.cats[i] && (o.denseCats || (n - 1 - i) % step === 0)) {
        text(f.svg, cx, f.h - f.m.b + 17, o.cats[i], { "text-anchor": "middle" });
      }
      if (o.sub) wrapLabel(f.svg, cx, f.h - f.m.b + 34, o.sub[i], band - 6);
      stops.push({ x: cx, y: top, mark: r, title: o.tipTitle(i), rows: o.tipRows(i) });
    });
    xBase(f, y(0));
    interact(f, stops, {});
  }

  function wrapLabel(svg, x, y, s, maxW) {
    var words = s.split(" "), lines = [""];
    words.forEach(function (w) {
      var cur = lines[lines.length - 1], next = cur ? cur + " " + w : w;
      if (tw(next) <= maxW || !cur) lines[lines.length - 1] = next;
      else lines.push(w);
    });
    if (lines.length > 2 || lines.some(function (l) { return tw(l) > maxW; })) return;
    lines.forEach(function (l, k) { text(svg, x, y + k * 15, l, { "text-anchor": "middle" }); });
  }

  function placeLabels(items, minGap, lo, hi) {
    items.sort(function (a, b) { return a.y - b.y; });
    for (var i = 1; i < items.length; i++) {
      if (items[i].ly < items[i - 1].ly + minGap) items[i].ly = items[i - 1].ly + minGap;
    }
    var over = items.length ? items[items.length - 1].ly - hi : 0;
    if (over > 0) {
      items.forEach(function (it) { it.ly -= over; });
      for (var j = items.length - 2; j >= 0; j--) {
        if (items[j].ly > items[j + 1].ly - minGap) items[j].ly = items[j + 1].ly - minGap;
      }
    }
    items.forEach(function (it) { it.ly = Math.max(lo, it.ly); });
    return items;
  }

  function lines(host, o) {
    var all = [];
    o.series.forEach(function (s) { all = all.concat(s.values.filter(function (v) { return v != null; })); });
    var lo = minOf(all), hi = maxOf(all);
    if (o.fromZero || o.zero) { lo = Math.min(0, lo); hi = Math.max(0, hi); }
    if (o.domain) { lo = o.domain[0]; hi = Math.max(o.domain[1], hi); }
    var yt = niceTicks(lo, hi, 5);
    var lw = maxOf(yt.map(function (t) { return tw(o.fmtAxis(t, yt)); })) + 14;
    var width = Math.max(240, Math.floor(host.clientWidth)), ends = !!o.endLabels && width >= 560;
    var endW = 0;
    if (ends) {
      endW = maxOf(o.series.map(function (s) {
        return tw(s.label, 12, 600) + tw(" " + o.fmtEnd(s.values[s.values.length - 1]));
      })) + 26;
    }
    var f = frame(host, { height: o.height, label: o.label, m: { t: 12, r: ends ? endW : 14, b: 28, l: lw } });
    var n = o.months.length, x = lin(0, Math.max(1, n - 1), f.m.l, f.w - f.m.r);
    var y = lin(yt[0], yt[yt.length - 1], f.h - f.m.b, f.m.t);
    yAxis(f, y, yt, function (t) { return o.fmtAxis(t, yt); });
    xBase(f, f.h - f.m.b);
    monthAxis(f, o.months, x);
    if (o.zero && yt[0] < 0) {
      el("line", { x1: f.m.l, x2: f.w - f.m.r, y1: Math.round(y(0)) + 0.5, y2: Math.round(y(0)) + 0.5,
        "class": "ref" }, f.svg);
    }
    o.series.forEach(function (s) {
      var d = "", pen = false;
      s.values.forEach(function (v, i) {
        if (v == null) { pen = false; return; }
        d += (pen ? "L" : "M") + x(i).toFixed(1) + "," + y(v).toFixed(1);
        pen = true;
      });
      var p = el("path", { d: d, fill: "none", "stroke-width": 2, "stroke-linejoin": "round",
        "stroke-linecap": "round" }, f.svg);
      p.style.stroke = s.color;
      if (n === 1) {
        var c1 = el("circle", { cx: x(0), cy: y(s.values[0]), r: 4 }, f.svg);
        c1.style.fill = s.color;
      }
    });
    if (ends) {
      var items = o.series.map(function (s) {
        var v = s.values[n - 1];
        return { s: s, v: v, y: y(v), ly: y(v) };
      });
      placeLabels(items, 16, f.m.t + 4, f.h - f.m.b);
      var xe = x(n - 1);
      items.forEach(function (it) {
        var dot = el("circle", { cx: xe, cy: it.y, r: 4, "stroke-width": 2 }, f.svg);
        dot.style.fill = it.s.color;
        dot.style.stroke = "var(--surface-2)";
        el("line", { x1: xe + 6, y1: it.y, x2: xe + 14, y2: it.ly, "class": "leader" }, f.svg);
        var t = text(f.svg, xe + 18, it.ly + 4, it.s.label, { "class": "lbl" });
        var ts = el("tspan", {}, t);
        ts.textContent = " " + o.fmtEnd(it.v);
        ts.setAttribute("class", "val");
        ts.style.fontWeight = "400";
        ts.style.fill = "var(--ink-2)";
      });
    }
    var stops = o.months.map(function (m, i) {
      var rows = o.series.map(function (s) {
        return { color: s.color, label: s.label, v: s.values[i],
          value: s.values[i] == null ? "–" : o.fmtVal(s.values[i]) };
      });
      rows.sort(function (a, b) { return (b.v == null ? -Infinity : b.v) - (a.v == null ? -Infinity : a.v); });
      var top = maxOf(rows.map(function (r) { return r.v; }));
      return { x: x(i), y: isFinite(top) ? y(top) : f.m.t, title: monthLabel(m), rows: rows };
    });
    interact(f, stops, { crosshair: true });
  }

  function ranges(host, rows, label) {
    var lo = minOf(rows.map(function (r) { return r.p5; })), hi = maxOf(rows.map(function (r) { return r.p95; }));
    var xt = niceTicks(lo, hi, 4);
    var lw = maxOf(rows.map(function (r) { return tw(r.label, 12, 600); })) + 16, rowH = 36;
    var f = frame(host, { height: rows.length * rowH + 40, label: label, m: { t: 8, r: 20, b: 30, l: lw } });
    var x = lin(xt[0], xt[xt.length - 1], f.m.l, f.w - f.m.r), d = mDecimals(xt), stops = [];
    var tstep = Math.max(1, Math.ceil((tw(fmtM(xt[xt.length - 1], d)) + 12) / ((f.w - f.m.l - f.m.r) / Math.max(1, xt.length - 1))));
    xt.forEach(function (t, i) {
      var xx = Math.round(x(t)) + 0.5;
      el("line", { x1: xx, x2: xx, y1: f.m.t, y2: f.h - f.m.b, "class": "grid-l" }, f.svg);
      if (i % tstep === 0) text(f.svg, xx, f.h - f.m.b + 18, fmtM(t, d), { "text-anchor": "middle" });
    });
    xBase(f, f.h - f.m.b);
    rows.forEach(function (r, i) {
      var cy = f.m.t + rowH * (i + 0.5);
      text(f.svg, f.m.l - 10, cy + 4, r.label, { "text-anchor": "end", "class": "lbl" });
      var ln = el("line", { x1: x(r.p5), x2: x(r.p95), y1: cy, y2: cy, "stroke-width": 2 }, f.svg);
      ln.style.stroke = r.color;
      [r.p5, r.p95].forEach(function (v) {
        var tk = el("line", { x1: x(v), x2: x(v), y1: cy - 6, y2: cy + 6, "stroke-width": 2 }, f.svg);
        tk.style.stroke = r.color;
      });
      var dot = el("circle", { cx: x(r.p50), cy: cy, r: 5, "stroke-width": 2 }, f.svg);
      dot.style.fill = r.color;
      dot.style.stroke = "var(--surface-2)";
      stops.push({ x: x(r.p50), y: cy, mark: dot, title: r.label, rows: [
        { label: "P95", value: fmtM(r.p95) }, { label: "P50", value: fmtM(r.p50) },
        { label: "P5", value: fmtM(r.p5) }, { label: "mean", value: fmtM(r.mean) }] });
    });
    interact(f, stops, { xy: true });
  }

  function scatter(host, pts, label) {
    var xs = pts.map(function (p) { return p.x; }), ys = pts.map(function (p) { return p.y; });
    var px = (maxOf(xs) - minOf(xs)) * 0.08 || 1e5, py = (maxOf(ys) - minOf(ys)) * 0.08 || 1e5;
    var xt = niceTicks(minOf(xs) - px, maxOf(xs) + px, 4), yt = niceTicks(minOf(ys) - py, maxOf(ys) + py, 4);
    var dx = mDecimals(xt), dy = mDecimals(yt);
    var lw = maxOf(yt.map(function (t) { return tw(fmtM(t, dy)); })) + 14;
    var f = frame(host, { height: function (w) { return Math.max(240, Math.min(320, w * 0.6)); },
      label: label, m: { t: 22, r: 18, b: 44, l: lw } });
    var x = lin(xt[0], xt[xt.length - 1], f.m.l, f.w - f.m.r), y = lin(yt[0], yt[yt.length - 1], f.h - f.m.b, f.m.t);
    yAxis(f, y, yt, function (t) { return fmtM(t, dy); });
    var tstep = Math.max(1, Math.ceil((tw(fmtM(xt[xt.length - 1], dx)) + 12) / ((f.w - f.m.l - f.m.r) / Math.max(1, xt.length - 1))));
    xt.forEach(function (t, i) {
      if (i % tstep === 0) text(f.svg, x(t), f.h - f.m.b + 18, fmtM(t, dx), { "text-anchor": "middle" });
    });
    xBase(f, f.h - f.m.b);
    text(f.svg, f.w - f.m.r, f.h - 6, "Mean 12-month cost →", { "text-anchor": "end" });
    text(f.svg, f.m.l - lw + 2, 12, "↑ P95 (bad case)", {});
    var items = pts.map(function (p) { return { p: p, y: y(p.y), ly: y(p.y) + 4 }; });
    placeLabels(items, 15, f.m.t + 4, f.h - f.m.b);
    var stops = [];
    items.forEach(function (it) {
      var cx = x(it.p.x), wlab = tw(it.p.label, 12, 600), right = cx + 10 + wlab < f.w - 2;
      var lx = right ? cx + 10 : cx - 10;
      if (Math.abs(it.ly - 4 - it.y) > 3) {
        el("line", { x1: cx + (right ? 5 : -5), y1: it.y, x2: lx + (right ? -2 : 2), y2: it.ly - 4, "class": "leader" }, f.svg);
      }
      text(f.svg, lx, it.ly, it.p.label, { "class": "lbl", "text-anchor": right ? "start" : "end" });
    });
    pts.forEach(function (p) {
      var c = el("circle", { cx: x(p.x), cy: y(p.y), r: 5, "stroke-width": 2 }, f.svg);
      c.style.fill = p.color;
      c.style.stroke = "var(--surface-2)";
      stops.push({ x: x(p.x), y: y(p.y), mark: c, title: p.label,
        rows: [{ label: "mean", value: fmtM(p.x) }, { label: "P95", value: fmtM(p.y) }] });
    });
    interact(f, stops, { xy: true });
  }

  function histograms(container, r) {
    container.replaceChildren();
    var ymax = 0, nb = 0, bw = 1e5;
    IDS.forEach(function (id) {
      if (!r.hist[id]) return;
      ymax = Math.max(ymax, maxOf(r.hist[id]));
      nb = Math.max(nb, r.hist[id].length);
    });
    var x0 = r.bin_lo * bw, x1 = (r.bin_lo + nb) * bw, xt = niceTicks(x0, x1, 4), d = mDecimals(xt);
    var yt = niceTicks(0, ymax, 2);
    IDS.forEach(function (id) {
      if (!r.hist[id]) return;
      var box = document.createElement("div"), h4 = document.createElement("h4"), sw = document.createElement("i");
      var host = document.createElement("div");
      box.className = "mini";
      sw.style.background = sv(id);
      h4.appendChild(sw);
      h4.appendChild(document.createTextNode(LABEL[id]));
      host.className = "plot";
      box.appendChild(h4);
      box.appendChild(host);
      container.appendChild(box);
      var lw = maxOf(yt.map(function (t) { return tw(fmtInt(t)); })) + 12;
      var f = frame(host, { height: 150, label: "Paths per cost bin, " + LABEL[id], m: { t: 16, r: 10, b: 26, l: lw } });
      var x = lin(xt[0], xt[xt.length - 1], f.m.l, f.w - f.m.r), y = lin(0, yt[yt.length - 1], f.h - f.m.b, f.m.t);
      yAxis(f, y, yt, fmtInt);
      var tstep = Math.max(1, Math.ceil((tw(fmtM(xt[xt.length - 1], d)) + 10) / ((f.w - f.m.l - f.m.r) / Math.max(1, xt.length - 1))));
      xt.forEach(function (t, i) {
        if (i % tstep === 0) text(f.svg, x(t), f.h - f.m.b + 17, fmtM(t, d), { "text-anchor": "middle" });
      });
      var stops = [];
      r.hist[id].forEach(function (c, i) {
        var a = (r.bin_lo + i) * bw, xa = x(a), xb = x(a + bw);
        var rect = el("rect", { x: xa + 1, y: y(c), width: Math.max(0.5, xb - xa - 2), height: Math.max(0, y(0) - y(c)) }, f.svg);
        rect.style.fill = sv(id);
        stops.push({ x: (xa + xb) / 2, y: y(c), mark: rect, title: fmtM(a) + " to " + fmtM(a + bw),
          rows: [{ label: "paths", value: fmtInt(c) }] });
      });
      xBase(f, y(0));
      var p95 = r.stats[id].p95, xp = Math.round(x(p95)) + 0.5;
      el("line", { x1: xp, x2: xp, y1: f.m.t - 4, y2: f.h - f.m.b, "class": "ref" }, f.svg);
      var right = xp + 6 + tw("P95 " + fmtM(p95)) < f.w;
      text(f.svg, right ? xp + 4 : xp - 4, f.m.t - 4, "P95 " + fmtM(p95), { "text-anchor": right ? "start" : "end" });
      interact(f, stops, {});
    });
  }

  /* ---- pages ---- */
  function hTwo(w) { return Math.round(Math.max(230, Math.min(320, w * 0.55))); }
  function hWide(w) { return Math.round(Math.max(230, Math.min(340, w * 0.3))); }
  function mAxis(t, ticks) { return fmtM(t, mDecimals(ticks)); }

  function drawHeadline() {
    var w = D.wrong, top = 0;
    w.forEach(function (r, i) { if (r.gap > w[top].gap) top = i; });
    columns(plot("wrong"), {
      cats: w.map(function (r) { return String(r.year); }), values: w.map(function (r) { return r.gap; }),
      colors: w.map(function (r, i) { return i === top ? "var(--hl)" : "var(--sc-ac)"; }),
      valueLabels: true, fmtVal: function (v) { return fmtM(v); }, fmtAxis: mAxis, height: hTwo,
      sub: w.map(function (r) { return LABEL[r.worst]; }), denseCats: true,
      label: "Column chart: cost of the wrong strategy per year in euros",
      tipTitle: function (i) { return String(w[i].year); },
      tipRows: function (i) {
        return [{ value: fmtM(w[i].gap), label: "dearest minus cheapest" },
          { value: LABEL[w[i].worst], label: "dearest" }, { value: LABEL[w[i].best], label: "cheapest" }];
      } });
  }

  function drawMarket() {
    var mk = D.market, idx = [];
    mk.months.forEach(function (m, i) { if (state.year === "all" || m.slice(0, 4) === state.year) idx.push(i); });
    var months = idx.map(function (i) { return mk.months[i]; });
    function pick(a) { return idx.map(function (i) { return a[i]; }); }
    lines(plot("price"), { months: months, height: hWide, fromZero: true,
      series: [{ label: "Peak", values: pick(mk.peak), color: "var(--sc-ac)" },
        { label: "Base", values: pick(mk.base), color: "var(--hl)" }],
      fmtVal: fmtMwh, fmtAxis: function (t) { return nf(t, 0); }, fmtEnd: function (v) { return nf(v, 1); },
      endLabels: true, label: "Line chart: monthly Austrian day-ahead base and peak price in EUR/MWh" });
    legend("price", [{ label: "Base", color: "var(--hl)" }, { label: "Peak", color: "var(--sc-ac)" }]);
    var hiIdx = 0;
    mk.neg_hours.forEach(function (v, i) { if (v > mk.neg_hours[hiIdx]) hiIdx = i; });
    columns(plot("neg"), { cats: mk.neg_years.map(function (y, i) { return String(y) + (mk.neg_partial[i] ? "*" : ""); }),
      values: mk.neg_hours, height: hTwo,
      colors: mk.neg_years.map(function (y, i) {
        var on = state.year === "all" ? i === hiIdx : String(y) === state.year;
        return on ? "var(--hl)" : "var(--sc-ac)";
      }),
      valueLabels: true, fmtVal: fmtInt, fmtAxis: function (t) { return fmtInt(t); },
      label: "Column chart: hours with a negative price per year",
      tipTitle: function (i) { return String(mk.neg_years[i]) + (mk.neg_partial[i] ? " (partial year)" : ""); },
      tipRows: function (i) { return [{ value: fmtInt(mk.neg_hours[i]) + " hours", label: "negative price" }]; } });
    lines(plot("spread"), { months: months, height: hTwo, zero: true,
      series: [{ label: "AT − DE-LU", values: pick(mk.spread), color: "var(--hl)" }],
      fmtVal: fmtMwh, fmtAxis: function (t) { return nf(t, 0); }, fmtEnd: function (v) { return nf(v, 1); },
      label: "Line chart: monthly AT minus DE-LU day-ahead spread in EUR/MWh" });
  }

  function drawStrategies() {
    var cum = D.cumulative;
    lines(plot("cum"), { months: cum.months, height: function (w) { return Math.round(Math.max(260, Math.min(380, w * 0.34))); },
      fromZero: true, endLabels: true,
      series: IDS.map(function (id) { return { label: LABEL[id], values: cum.series[id], color: sv(id) }; }),
      fmtVal: function (v) { return fmtM(v); }, fmtEnd: function (v) { return fmtM(v); }, fmtAxis: mAxis,
      label: "Line chart: cumulative energy cost per strategy since January 2021 in euros" });
    legend("cum", IDS.map(function (id) { return { label: LABEL[id], color: sv(id) }; }));
  }

  function drawRisk() {
    var r = D.risk[state.variant];
    if (!r) return;
    var rows = IDS.filter(function (id) { return r.stats[id]; }).map(function (id) {
      var s = r.stats[id];
      return { label: LABEL[id], color: sv(id), p5: s.p5, p50: s.p50, p95: s.p95, mean: s.mean };
    });
    ranges(plot("range"), rows, "Range chart: P5 to P95 of the simulated next-12-month cost per strategy");
    scatter(plot("scatter"), IDS.filter(function (id) { return r.stats[id]; }).map(function (id) {
      return { label: LABEL[id], color: sv(id), x: r.stats[id].mean, y: r.stats[id].p95 };
    }), "Scatter chart: mean versus P95 of the simulated next-12-month cost per strategy");
    histograms(document.getElementById("plot-hist"), r);
    document.querySelectorAll("details[data-variant]").forEach(function (d) {
      d.hidden = d.getAttribute("data-variant") !== state.variant;
    });
  }

  function drawDq() {
    var dq = D.dq;
    lines(plot("cov"), { months: dq.months, height: hWide, domain: [dq.axis_min, 100],
      series: [{ label: "Coverage", values: dq.coverage, color: "var(--hl)" }],
      fmtVal: function (v) { return nf(v, 2) + "%"; }, fmtAxis: function (t, ticks) {
        var st = ticks.length > 1 ? ticks[1] - ticks[0] : 1;
        return nf(t, st >= 1 ? 0 : st >= 0.1 ? 1 : 2) + "%";
      }, label: "Line chart: monthly Austrian price coverage in percent of expected hours" });
    columns(plot("pt15"), { cats: dq.months.map(function (m) { return m.slice(5) === "01" ? m.slice(0, 4) : ""; }),
      values: dq.pt15m, colors: dq.pt15m.map(function () { return "var(--hl)"; }), height: hWide,
      fmtVal: fmtInt, fmtAxis: function (t) { return fmtInt(t); }, maxBar: 12,
      label: "Column chart: hours per month built from 15-minute quarters",
      tipTitle: function (i) { return monthLabel(dq.months[i]); },
      tipRows: function (i) { return [{ value: fmtInt(dq.pt15m[i]) + " hours", label: "from 15-min quarters" }]; } });
  }

  var DRAW = { headline: drawHeadline, market: drawMarket, strategies: drawStrategies, risk: drawRisk,
    "data-quality": drawDq };

  /* ---- tabs (WAI-ARIA tabs pattern), controls, theme ---- */
  var tabs = Array.prototype.slice.call(document.querySelectorAll("[role=tab]"));
  function activate(id, focus) {
    tabs.forEach(function (t) {
      var on = t.id === "tab-" + id;
      t.setAttribute("aria-selected", on ? "true" : "false");
      t.tabIndex = on ? 0 : -1;
      document.getElementById(t.getAttribute("aria-controls")).hidden = !on;
      if (on && focus) t.focus();
    });
    state.page = id;
    if (location.hash !== "#" + id) {
      try { history.replaceState(null, "", "#" + id); } catch (e) { location.hash = id; }
    }
    tip.hidden = true;
    DRAW[id]();
  }
  tabs.forEach(function (t, i) {
    t.addEventListener("click", function () { activate(t.id.slice(4)); });
    t.addEventListener("keydown", function (ev) {
      var j = null;
      if (ev.key === "ArrowRight") j = (i + 1) % tabs.length;
      else if (ev.key === "ArrowLeft") j = (i - 1 + tabs.length) % tabs.length;
      else if (ev.key === "Home") j = 0;
      else if (ev.key === "End") j = tabs.length - 1;
      if (j !== null) { ev.preventDefault(); activate(tabs[j].id.slice(4), true); }
    });
  });
  window.addEventListener("hashchange", function () {
    var id = location.hash.slice(1);
    if (DRAW[id] && id !== state.page) activate(id);
  });
  document.getElementById("market-year").addEventListener("change", function (ev) {
    state.year = ev.target.value;
    drawMarket();
  });
  document.querySelectorAll("[data-metric].seg").forEach(function (b) {
    b.addEventListener("click", function () {
      state.metric = b.getAttribute("data-metric");
      document.querySelectorAll("[data-metric].seg").forEach(function (o) {
        o.setAttribute("aria-pressed", o === b ? "true" : "false");
      });
      document.querySelectorAll("#panel-strategies table.matrix").forEach(function (t) {
        t.hidden = t.getAttribute("data-metric") !== state.metric;
      });
    });
  });
  document.querySelectorAll("#panel-strategies table.matrix").forEach(function (t) {
    t.hidden = t.getAttribute("data-metric") !== state.metric;
  });
  document.querySelectorAll("[data-variant].seg").forEach(function (b) {
    b.addEventListener("click", function () {
      state.variant = b.getAttribute("data-variant");
      document.querySelectorAll("[data-variant].seg").forEach(function (o) {
        o.setAttribute("aria-pressed", o === b ? "true" : "false");
      });
      drawRisk();
    });
  });
  var THEMES = ["auto", "light", "dark"], themeBtn = document.getElementById("theme");
  function setTheme(t) {
    if (t === "auto") document.documentElement.removeAttribute("data-theme");
    else document.documentElement.setAttribute("data-theme", t);
    themeBtn.textContent = "Theme: " + t;
    themeBtn.setAttribute("aria-label", "Colour theme: " + (t === "auto" ? "automatic" : t));
    try { localStorage.setItem("epra-theme", t); } catch (e) { /* storage unavailable */ }
  }
  themeBtn.addEventListener("click", function () {
    var cur = document.documentElement.getAttribute("data-theme") || "auto";
    setTheme(THEMES[(THEMES.indexOf(cur) + 1) % THEMES.length]);
  });
  try { var saved = localStorage.getItem("epra-theme"); if (saved && saved !== "auto") setTheme(saved); } catch (e) { /* none */ }
  var lastW = 0, timer = null;
  window.addEventListener("resize", function () {
    clearTimeout(timer);
    timer = setTimeout(function () {
      var w = document.documentElement.clientWidth;
      if (w !== lastW) { lastW = w; DRAW[state.page](); }
    }, 120);
  });
  var start = location.hash.slice(1);
  lastW = document.documentElement.clientWidth;
  activate(DRAW[start] ? start : tabs[0].id.slice(4));
})();
