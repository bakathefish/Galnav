"use strict";
// GalNav web demo frontend. Talks only to this app's own /api/* endpoints.

const $ = (id) => document.getElementById(id);
const state = { frames: [], selected: new Set(), focus: null, busy: false };

function cssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

function toast(msg) {
  const t = document.createElement("div");
  t.className = "toast";
  t.textContent = msg;
  $("toasts").appendChild(t);
  setTimeout(() => t.remove(), 6000);
}

async function api(path, opts) {
  const res = await fetch(path, opts);
  const ct = res.headers.get("content-type") || "";
  if (!ct.includes("application/json")) return res;
  return res.json();
}

function fieldTag(field) {
  if (field === "Proxima") return '<span class="tag prox">Proxima</span>';
  if (field === "Wolf 359") return '<span class="tag wolf">Wolf 359</span>';
  return '<span class="tag up">uploaded</span>';
}

function ageOf(ids) {
  const ages = state.frames.filter((f) => ids.includes(f.id)).map((f) => f.obs_age_yr);
  if (!ages.length) return null;
  return ages.reduce((a, b) => a + b, 0) / ages.length;
}

function renderGallery() {
  const g = $("gallery");
  g.innerHTML = "";
  for (const f of state.frames) {
    const sel = state.selected.has(f.id);
    const el = document.createElement("button");
    el.className = "frame" + (sel ? " sel" : "") + (state.focus === f.id ? " focus" : "");
    el.setAttribute("aria-pressed", sel ? "true" : "false");
    const age = $("age").value || "4.31";
    const radius = $("radius").value || "120";
    el.innerHTML =
      `<img loading="lazy" alt="" src="/api/image?id=${f.id}&age=${age}&radius=${radius}&thumb=1">` +
      `<span class="meta"><span class="fname">${f.name}</span><br>${fieldTag(f.field)}</span>` +
      `<input class="ck" type="checkbox" tabindex="-1" ${sel ? "checked" : ""} aria-hidden="true">`;
    el.addEventListener("click", () => toggleFrame(f.id));
    g.appendChild(el);
  }
}

function toggleFrame(id) {
  if (state.selected.has(id)) state.selected.delete(id);
  else state.selected.add(id);
  state.focus = id;
  syncAge();
  renderGallery();
  updatePreview();
}

function syncAge() {
  const a = ageOf([...state.selected]);
  if (a !== null) $("age").value = a.toFixed(2);
}

function updatePreview() {
  const wrap = $("imgwrap");
  if (!state.focus) {
    wrap.innerHTML = '<div class="hint" id="preview-hint">Select a frame to see its ' +
      "detected stars (cyan circles) and identified nearby stars (amber crosses).</div>";
    $("caption").textContent = "";
    return;
  }
  const age = $("age").value || "4.31";
  const radius = $("radius").value || "120";
  const f = state.frames.find((x) => x.id === state.focus);
  wrap.innerHTML = `<img alt="frame ${f.name}" src="/api/image?id=${state.focus}&age=${age}&radius=${radius}&t=${Date.now()}">`;
  $("caption").textContent = `${f.name} - ${f.field} field - cyan = detected star, amber = identified nearby star`;
}

function setBusy(on) {
  state.busy = on;
  for (const id of ["locate", "estimate", "preset-2", "preset-12"]) $(id).disabled = on;
}

async function locate() {
  const ids = [...state.selected];
  if (ids.length === 0) { toast("Select at least one frame first."); return; }
  setBusy(true);
  $("results").innerHTML = '<div class="resultcard"><span class="spin"></span>Locating...</div>';
  try {
    const body = JSON.stringify({
      ids, age: parseFloat($("age").value), radius: parseFloat($("radius").value),
      rv: parseFloat($("rv").value || "0"),
    });
    const r = await api("/api/locate", { method: "POST", body });
    renderLocate(r);
  } catch (e) { toast("Locate failed: " + e); $("results").innerHTML = ""; }
  finally { setBusy(false); }
}

function renderLocate(r) {
  if (!r.ok) {
    $("results").innerHTML = `<div class="resultcard"><div class="pos">${r.message}</div></div>`;
    return;
  }
  const x = r.x_au.map((v) => v.toFixed(3)).join(", ");
  const ell = r.ellipsoid_au.map((v) => v.toFixed(3)).join(" / ");
  const miss = r.miss_au === null || r.miss_au === undefined
    ? '<div><div class="k">miss</div><div class="v">n/a (not the NH set)</div></div>'
    : `<div><div class="k">miss vs JPL truth</div><div class="v cyan">${r.miss_au.toFixed(3)} au</div></div>`;
  const lines = r.lines.map(
    (l) => `<span class="sn">${l.star_name}</span> in ${l.image} &mdash; residual ${l.resid_arcsec}"`
  ).join("<br>");
  $("results").innerHTML =
    `<div class="resultcard">
       <div class="k mono" style="color:var(--faint);letter-spacing:.1em">SPACECRAFT POSITION</div>
       <div class="big-r">|r| = ${r.r_au.toFixed(2)} au</div>
       <div class="pos">x = [${x}] au &nbsp;(${r.r_pc.toExponential(3)} pc)</div>
       <div class="kv">
         ${miss}
         <div><div class="k">1-sigma ellipsoid</div><div class="v">${ell} au</div></div>
         <div><div class="k">chi2</div><div class="v">${r.chi2.toExponential(2)}</div></div>
         <div><div class="k">lines / stars</div><div class="v">${r.n_lines} / ${r.distinct_stars}</div></div>
       </div>
       <div class="linelist">${lines}</div>
     </div>`;
}

async function estimateAge() {
  const ids = [...state.selected];
  if (ids.length === 0) { toast("Select at least one frame first."); return; }
  setBusy(true);
  $("results").innerHTML = '<div class="resultcard"><span class="spin"></span>Scanning ages...</div>';
  try {
    const body = JSON.stringify({
      ids, radius: parseFloat($("radius").value), rv: parseFloat($("rv").value || "0"),
      min: parseFloat($("amin").value), max: parseFloat($("amax").value),
      step: parseFloat($("astep").value),
    });
    const r = await api("/api/estimate_age", { method: "POST", body });
    renderAge(r);
  } catch (e) { toast("Age estimate failed: " + e); $("results").innerHTML = ""; }
  finally { setBusy(false); }
}

function renderAge(r) {
  if (!r.ok) {
    $("results").innerHTML = `<div class="resultcard"><div class="pos">${r.message}</div></div>`;
    return;
  }
  const sig = r.sigma_age_yr === null ? "n/a" : "± " + r.sigma_age_yr.toFixed(3);
  const truth = r.truth_yr === null ? "" : ` &nbsp;vs true ${r.truth_yr.toFixed(3)} yr`;
  const note = r.note ? `<div class="linelist">${r.note}</div>` : "";
  $("results").innerHTML =
    `<div class="resultcard">
       <div class="k mono" style="color:var(--faint);letter-spacing:.1em">CATALOG AGE FROM IMAGE GEOMETRY</div>
       <div class="big-r">${r.age_hat_yr.toFixed(3)} ${sig} yr</div>
       <div class="pos">chi2-vs-age scan${truth}</div>
       <div class="agebox"><canvas id="curve" width="900" height="200"></canvas></div>
       ${note}
     </div>`;
  drawCurve(r);
}

function drawCurve(r) {
  const c = $("curve"), ctx = c.getContext("2d");
  const W = c.width, H = c.height, pad = 34;
  ctx.clearRect(0, 0, W, H);
  const all = r.ages.map((a, i) => [a, r.chi2s[i]]).filter((p) => p[1] !== null && isFinite(p[1]));
  if (all.length < 2) return;
  // Draw only the informative bowl around the minimum. FAR from the minimum the
  // fix uses a different set of matched stars, so chi2 jumps discontinuously in a
  // sawtooth that is NOT a smooth continuation of the same chi-squared -- drawing
  // a line through it misleads. Every point stays in r.chi2s (returned arrays are
  // unchanged); we just clip the polyline to the contiguous run around the
  // minimum where chi2 stays within 30x the minimum (absolute floor 30 so a
  // near-zero minimum still shows a few points). On the 12-frame default scan
  // this draws ages 4.00-5.00 around the 4.29 yr vertex and drops the match-set
  // cliffs at ~2 and ~3.75 yr; if no clear bowl exists it falls back to all pts.
  const ymn = Math.min(...all.map((p) => p[1]));
  const ceil = ymn + Math.max(30 * ymn, 30);
  let lo = all.reduce((m, p, i) => (p[1] < all[m][1] ? i : m), 0), hi = lo;
  while (lo > 0 && all[lo - 1][1] <= ceil) lo--;
  while (hi < all.length - 1 && all[hi + 1][1] <= ceil) hi++;
  const pts = hi - lo >= 1 ? all.slice(lo, hi + 1) : all;
  const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]);
  const xmin = Math.min(...xs), xmax = Math.max(...xs);
  const ymin = Math.min(...ys), ymax = Math.max(...ys);
  const X = (x) => pad + (x - xmin) / (xmax - xmin || 1) * (W - 2 * pad);
  const Y = (y) => H - pad - (y - ymin) / (ymax - ymin || 1) * (H - 2 * pad);
  const cyan = cssVar("--cyan") || "#3fcbef", amber = cssVar("--amber") || "#f2b444",
    line = cssVar("--line") || "#263248", dim = cssVar("--dim") || "#93a6bf";
  // axes
  ctx.strokeStyle = line; ctx.lineWidth = 1;
  ctx.beginPath(); ctx.moveTo(pad, H - pad); ctx.lineTo(W - pad, H - pad); ctx.stroke();
  // curve
  ctx.strokeStyle = cyan; ctx.lineWidth = 2; ctx.beginPath();
  pts.forEach((p, i) => { const x = X(p[0]), y = Y(p[1]); i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); });
  ctx.stroke();
  // best-fit marker
  ctx.strokeStyle = amber; ctx.lineWidth = 1.5; ctx.setLineDash([4, 4]);
  ctx.beginPath(); ctx.moveTo(X(r.age_hat_yr), pad - 6); ctx.lineTo(X(r.age_hat_yr), H - pad); ctx.stroke();
  ctx.setLineDash([]);
  ctx.fillStyle = amber; ctx.font = "12px ui-monospace,monospace";
  ctx.fillText(r.age_hat_yr.toFixed(2) + " yr", X(r.age_hat_yr) + 5, pad + 6);
  ctx.fillStyle = dim; ctx.font = "11px ui-monospace,monospace";
  ctx.fillText("age (yr) →", W - pad - 70, H - pad + 22);
  ctx.save(); ctx.translate(12, H / 2); ctx.rotate(-Math.PI / 2);
  ctx.fillText("chi2", 0, 0); ctx.restore();
}

async function upload(file) {
  setBusy(true);
  try {
    const fd = new FormData(); fd.append("file", file);
    const key = $("apikey").value.trim();
    const opts = { method: "POST", body: fd };
    if (key) opts.headers = { "X-Api-Key": key };
    const r = await api("/api/upload", opts);
    if (!r.ok) { toast(r.message || "upload failed"); return; }
    await loadFrames();
    state.selected.add(r.id); state.focus = r.id;
    renderGallery(); updatePreview();
    toast("Added " + r.name);
  } catch (e) { toast("Upload failed: " + e); }
  finally { setBusy(false); }
}

async function loadFrames() {
  const frames = await api("/api/frames");
  state.frames = frames;
  renderGallery();
}

function selectPreset(ids) {
  state.selected = new Set(ids);
  state.focus = ids[0];
  $("age").value = (ageOf(ids) ?? 4.31).toFixed(2);
  renderGallery(); updatePreview();
}

function init() {
  $("preset-2").addEventListener("click", () => selectPreset(["f0", "f6"]));
  $("preset-12").addEventListener("click", () =>
    selectPreset(["f0", "f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9", "f10", "f11"]));
  $("clear-sel").addEventListener("click", () => {
    state.selected.clear(); state.focus = null; renderGallery(); updatePreview();
    $("results").innerHTML = "";
  });
  $("locate").addEventListener("click", locate);
  $("estimate").addEventListener("click", estimateAge);
  $("age").addEventListener("change", () => { renderGallery(); updatePreview(); });
  $("radius").addEventListener("change", () => { renderGallery(); updatePreview(); });
  $("file").addEventListener("change", (e) => { if (e.target.files[0]) upload(e.target.files[0]); });
  loadFrames();
}
document.addEventListener("DOMContentLoaded", init);
