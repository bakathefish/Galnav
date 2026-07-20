"use strict";
// GalNav web demo frontend. Talks only to this app's own /api/* endpoints.

const $ = (id) => document.getElementById(id);
// order = selection history (most recent LAST): focus always derives from it,
// so deselecting a frame can hand focus to the previously selected one.
// ageMode: "auto" follows the selected frames; "manual" = the user typed an
// age and selection changes must not stomp it.
const state = {
  frames: [],
  selected: new Set(),
  order: [],
  focus: null,
  busy: false,
  ageMode: "auto",
};

function cssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

// HTML-escape any server-supplied string before it goes into innerHTML. A file
// named `<img src=x onerror=alert(1)>.fits` would otherwise execute (stored/DOM
// XSS on this booth machine). Escapes the five HTML-significant characters,
// which also makes it safe inside a double-quoted attribute. Plain names should
// prefer .textContent; this is for the template-literal innerHTML paths.
const esc = (s) =>
  String(s ?? "").replace(
    /[&<>"']/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );

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
    const age = encodeURIComponent($("age").value || "4.31");
    const radius = encodeURIComponent($("radius").value || "120");
    const fid = encodeURIComponent(f.id);
    el.innerHTML =
      `<img loading="lazy" alt="" data-fid="${fid}" src="/api/image?id=${fid}&age=${age}&radius=${radius}&thumb=1">` +
      `<span class="meta"><span class="fname">${esc(f.name)}</span><br>${fieldTag(f.field)}</span>` +
      `<input class="ck" type="checkbox" tabindex="-1" ${sel ? "checked" : ""} aria-hidden="true">`;
    el.addEventListener("click", () => toggleFrame(f.id));
    if (f.id.startsWith("up_")) {
      // Only UPLOADS (ids up_<n>) get the remove control; demo frames get none.
      const rm = document.createElement("span");
      rm.className = "rm";
      rm.title = "Remove this upload";
      rm.setAttribute("role", "button");
      rm.textContent = "×";
      rm.addEventListener("click", (ev) => {
        ev.stopPropagation();
        removeUpload(f.id);
      });
      el.appendChild(rm);
    }
    g.appendChild(el);
  }
}

// --- selection (order-tracked so focus can follow honestly) -----------------
function selectId(id) {
  state.selected.add(id);
  state.order = state.order.filter((x) => x !== id);
  state.order.push(id);
  state.focus = id;
}

function deselectId(id) {
  state.selected.delete(id);
  state.order = state.order.filter((x) => x !== id);
  // Focus moves to the most recently selected REMAINING frame, or null: the
  // preview goes honestly empty instead of showing the frame just deselected
  // (the old focus/selected desync bug).
  state.focus = state.order.length ? state.order[state.order.length - 1] : null;
}

function toggleFrame(id) {
  if (state.selected.has(id)) deselectId(id);
  else selectId(id);
  syncAge();
  renderGallery();
  updatePreview();
}

// --- age auto/manual ---------------------------------------------------------
function setAgeMode(mode) {
  state.ageMode = mode;
  const badge = $("age-mode");
  if (badge) badge.textContent = mode;
  const reset = $("age-auto");
  if (reset) reset.hidden = mode === "auto";
  if (mode === "auto") {
    syncAge();
    refreshImages();
  }
}

function syncAge() {
  if (state.ageMode !== "auto") return; // manual: never stomp a typed age
  const a = ageOf([...state.selected]);
  if (a !== null) $("age").value = a.toFixed(2);
}

function updatePreview() {
  updateWalkLink(); // keep the step-through link on the current selection
  const wrap = $("imgwrap");
  if (!state.focus) {
    wrap.innerHTML = '<div class="hint" id="preview-hint">Select a frame to see its ' +
      "detected stars (cyan circles) and identified nearby stars (amber crosses).</div>";
    $("caption").textContent = "";
    return;
  }
  const age = encodeURIComponent($("age").value || "4.31");
  const radius = encodeURIComponent($("radius").value || "120");
  const f = state.frames.find((x) => x.id === state.focus);
  wrap.innerHTML = `<img alt="frame ${esc(f.name)}" src="/api/image?id=${encodeURIComponent(state.focus)}&age=${age}&radius=${radius}&t=${Date.now()}">`;
  $("caption").textContent = `${f.name} - ${f.field} field - cyan = detected star, amber = identified nearby star`;
}

// Update ONLY the <img> srcs (gallery thumbs + preview) when age/radius change.
// No renderGallery() teardown per keystroke: the thumbnails stay in place and
// just re-request with the new query params.
function refreshImages() {
  const age = encodeURIComponent($("age").value || "4.31");
  const radius = encodeURIComponent($("radius").value || "120");
  for (const img of document.querySelectorAll("#gallery img[data-fid]")) {
    img.src = `/api/image?id=${img.dataset.fid}&age=${age}&radius=${radius}&thumb=1`;
  }
  updatePreview();
}

function debounce(fn, wait) {
  let t = null;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), wait);
  };
}
const refreshImagesDebounced = debounce(refreshImages, 400);

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
  const warn = r.warning ? `<div class="warnbar">${esc(r.warning)}</div>` : "";
  if (!r.ok) {
    if (r.mode === "line" && r.lop) {
      // One usable nearby star: not a failure, a LINE of position (do.txt 9).
      renderLineOfPosition(r, warn);
      return;
    }
    $("results").innerHTML = `<div class="resultcard">${warn}<div class="pos">${esc(r.message)}</div></div>`;
    hideFixButton();
    return;
  }
  const x = r.x_au.map((v) => v.toFixed(3)).join(", ");
  const ell = r.ellipsoid_au.map((v) => v.toFixed(3)).join(" / ");
  const miss = r.miss_au === null || r.miss_au === undefined
    ? '<div><div class="k">miss</div><div class="v">n/a (not the NH set)</div></div>'
    : `<div><div class="k">miss vs JPL truth</div><div class="v cyan">${r.miss_au.toFixed(3)} au</div></div>`;
  const lines = r.lines.map(
    (l) => `<span class="sn">${esc(l.star_name)}</span> in ${esc(l.image)} &mdash; residual ${Number(l.resid_arcsec)}"`
  ).join("<br>");
  $("results").innerHTML =
    `<div class="resultcard">
       ${warn}
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
  // A point fix exists: offer to push it into OpenSpace, and refresh the walk
  // link so the step-through opens on this exact selection.
  revealFixButton();
  updateWalkLink();
}

// One nearby star pins the camera to a LINE of position, not a point. The card
// says so honestly (do.txt item 9). No 3-D wiring here: the viewer is moving to
// OpenSpace, and line-of-position display there lands in a later wave.
function renderLineOfPosition(r, warn) {
  const lop = r.lop;
  const name = lop.star_name || "one nearby star";
  const spread =
    r.n_lines > 1 && lop.residual_spread_arcsec !== null && lop.residual_spread_arcsec !== undefined
      ? `<div><div class="k">spread between sightings</div><div class="v">${Number(lop.residual_spread_arcsec).toFixed(2)}&Prime;</div></div>`
      : "";
  $("results").innerHTML =
    `<div class="resultcard">
       ${warn}
       <div class="k mono" style="color:var(--faint);letter-spacing:.1em">LINE OF POSITION</div>
       <div class="big-r">a line, not a point</div>
       <div class="pos">One nearby star (${esc(name)}) fixes you to a line of position through
         space, not a single point. Add a frame with a second, different nearby star and
         Locate again to pin the 3-D position.</div>
       <div class="kv">
         <div><div class="k">star</div><div class="v">${esc(name)}</div></div>
         <div><div class="k">lines</div><div class="v">${r.n_lines}</div></div>
         ${spread}
       </div>
     </div>`;
  // A line is not a point fix, so no "show the fix" button; but the line CAN be
  // drawn in OpenSpace from pipeline page 6, and the walk link stays current.
  hideFixButton();
  updateWalkLink();
}

// --- OpenSpace panel (the pipeline's live viewer) ---------------------------
// The old spacekit iframe view is retired from this flow; OpenSpace is now THE
// viewer. A status chip reflects whether a local OpenSpace is reachable, the
// walk link steps through the pipeline pages carrying the current selection, and
// after a successful Locate the fix can be pushed straight into OpenSpace.
async function openspaceStatus() {
  const chip = $("os-chip");
  if (!chip) return;
  let r;
  try {
    r = await api("/api/openspace/status");
  } catch (e) {
    return; // old server without the endpoint: leave the chip as-is
  }
  if (!r || r.ok !== true) return;
  if (r.running) {
    chip.dataset.state = "up";
    chip.textContent = "OpenSpace connected";
  } else {
    chip.dataset.state = "down";
    chip.textContent = "OpenSpace not running";
  }
}

// The step-through link carries the current selection so the pipeline pages
// open on exactly the frames the user has chosen (or the demo default).
function currentWalkQuery() {
  const ids = [...state.selected];
  const q = new URLSearchParams();
  if (ids.length) q.set("ids", ids.join(","));
  q.set("age", $("age").value || "4.31");
  q.set("radius", $("radius").value || "120");
  return q.toString();
}

function updateWalkLink() {
  const a = $("walk-link");
  if (a) a.href = "/static/pipeline-1-raw.html?" + currentWalkQuery();
}

function revealFixButton() {
  const b = $("os-show-fix");
  if (!b) return;
  b.hidden = false;
  b.onclick = () => showInOpenSpace("fix");
}

function hideFixButton() {
  const b = $("os-show-fix");
  if (b) b.hidden = true;
}

// Push a pipeline stage ("stars"|"lines"|"fix"|"clear") into a running
// OpenSpace. Honest when OpenSpace is not running: the response says so and the
// note line shows it, no fake success.
async function showInOpenSpace(stage) {
  const ids = [...state.selected];
  const note = $("os-note");
  const body = JSON.stringify({
    stage, ids, age: parseFloat($("age").value),
    radius: parseFloat($("radius").value), rv: parseFloat($("rv").value || "0"),
  });
  try {
    const r = await api("/api/openspace/show", { method: "POST", body });
    if (r.ok) {
      if (note) note.textContent = r.note || "Pushed to OpenSpace.";
      toast("Pushed to OpenSpace.");
    } else {
      if (note) note.textContent = r.message || "OpenSpace push failed.";
      toast(r.message || "OpenSpace push failed.");
    }
    openspaceStatus();
  } catch (e) {
    toast("OpenSpace push failed: " + e);
  }
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
  hideFixButton();  // age result is not a position fix
  if (!r.ok) {
    $("results").innerHTML = `<div class="resultcard"><div class="pos">${esc(r.message)}</div></div>`;
    return;
  }
  const sig = r.sigma_age_yr === null ? "" : " ± " + r.sigma_age_yr.toFixed(2);
  const mode = r.mode === "single-star drift"
    ? "single-star drift dating" : "position-fit χ² scan";
  const best = r.best_sep_arcsec ? ` · best separation ${r.best_sep_arcsec.toFixed(2)}″` : "";
  const truth = (r.truth_yr === null || r.truth_yr === undefined) ? ""
    : ` &nbsp;vs true ${(2016 + r.truth_yr).toFixed(2)}`;
  const note = r.note ? `<div class="linelist">${esc(r.note)}</div>` : "";
  // Show the calendar YEAR headline (lands harder than "-62.7 yr"); age below.
  const year = (r.year_hat === null || r.year_hat === undefined) ? null : r.year_hat;
  const yearLine = year === null ? "" :
    `<div class="big-r">${year.toFixed(1)}</div>
     <div class="pos">estimated year the image was taken${truth}</div>`;
  $("results").innerHTML =
    `<div class="resultcard">
       <div class="k mono" style="color:var(--faint);letter-spacing:.1em">IMAGE EPOCH FROM STAR MOTION</div>
       ${yearLine}
       <div class="pos">age ${r.age_hat_yr.toFixed(2)}${sig} yr since J2016.0 · ${mode}${best}</div>
       <div class="agebox"><canvas id="curve" width="900" height="200"></canvas></div>
       ${note}
     </div>`;
  drawCurve(r, r.curve_label || "chi2");
}

function drawCurve(r, ylabel) {
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
  ctx.fillText(ylabel || "chi2", 0, 0); ctx.restore();
}

// --- upload ------------------------------------------------------------------
const UPLOAD_STAGES = ["Solving field…", "Identifying stars…", "Locating…"];

// Upload ONE file. Returns {ok, name, message, id, duplicate, srvName} and
// never throws. Progress goes to the stage box with a per-file prefix
// ("2/5 img.fits — Solving field…") while the possibly-slow solve runs.
async function uploadOne(file, prefix) {
  const stage = $("upload-stage");
  stage.hidden = false;
  stage.className = "upload-stage busy";
  stage.innerHTML = '<span class="spin"></span><span id="stage-text"></span>';
  const label = (s) => {
    const t = $("stage-text");
    if (t) t.textContent = `${prefix}${s}`;
  };
  label(UPLOAD_STAGES[0]);
  let i = 0;
  const timer = setInterval(() => {
    i = (i + 1) % UPLOAD_STAGES.length;
    label(UPLOAD_STAGES[i]);
  }, 1200);
  try {
    const fd = new FormData();
    fd.append("file", file);
    const key = $("apikey").value.trim();
    const opts = { method: "POST", body: fd };
    if (key) opts.headers = { "X-Api-Key": key };
    const r = await api("/api/upload", opts);
    return {
      ok: !!r.ok,
      name: file.name,
      message: r.message || "",
      id: r.id,
      duplicate: !!r.duplicate,
      srvName: r.name,
    };
  } catch (e) {
    return { ok: false, name: file.name, message: String(e), duplicate: false };
  } finally {
    clearInterval(timer);
  }
}

// Sequential multi-upload: EVERY file is attempted (one bad file never aborts
// the rest), each success lands selected+focused, and an honest summary --
// counts plus per-file failure reasons -- ends up in the stage box.
async function uploadMany(files) {
  setBusy(true);
  const stage = $("upload-stage");
  const okNames = [], dupNames = [], failed = [];
  try {
    for (let n = 0; n < files.length; n++) {
      const file = files[n];
      const prefix = files.length > 1 ? `${n + 1}/${files.length} ${file.name} — ` : "";
      const r = await uploadOne(file, prefix);
      if (r.duplicate) {
        // Identical bytes are already in the gallery: select the existing
        // record instead of stacking a copy.
        dupNames.push(r.name);
        toast(`“${r.name}” already uploaded — selected the existing copy.`);
        if (r.id) selectId(r.id);
        continue;
      }
      if (!r.ok) {
        failed.push(r);
        continue;
      }
      okNames.push(r.srvName || r.name);
      if (r.id) selectId(r.id);
    }
    await loadFrames(); // re-renders the gallery with the new selection state
    updatePreview();
    if (failed.length === 0 && okNames.length === 1 && dupNames.length === 0) {
      stage.className = "upload-stage ok";
      stage.textContent = `Solved — added “${okNames[0]}”. Select it (plus one more nearby-star frame) and click Locate.`;
      return;
    }
    const parts = [];
    if (okNames.length) parts.push(`${okNames.length} uploaded`);
    if (dupNames.length) parts.push(`${dupNames.length} already uploaded`);
    if (failed.length) {
      const why = failed.map((f) => `${f.name} (${f.message || "failed"})`).join("; ");
      parts.push(`${failed.length} failed: ${why}`);
    }
    stage.hidden = false;
    stage.className = failed.length ? "upload-stage err" : "upload-stage ok";
    stage.textContent = parts.join(" · ") || "Nothing to upload.";
  } finally {
    setBusy(false);
  }
}

// Remove an uploaded frame server-side (the endpoint refuses demo ids), then
// drop it from selection AND focus so gallery/preview cannot desync.
async function removeUpload(id) {
  try {
    const r = await api("/api/remove_upload", {
      method: "POST",
      body: JSON.stringify({ id }),
    });
    if (!r.ok) {
      toast(r.message || "Could not remove that upload.");
      return;
    }
  } catch (e) {
    toast("Remove failed: " + e);
    return;
  }
  deselectId(id); // focus falls back to the last-selected remaining frame
  await loadFrames();
  updatePreview();
}

async function loadFrames() {
  const frames = await api("/api/frames");
  state.frames = frames;
  renderGallery();
}

// --- solver messaging (do.txt item 6) ----------------------------------------
// The page ships with static "install the blind solver" hints. When the local
// WSL astrometry.net is actually installed (wsl_solver && wsl_config), those
// three hints swap to an installed-state line; the install instructions stay
// rendered only while the solver is absent.
async function solverStatus() {
  let r;
  try {
    r = await api("/api/solver_status");
  } catch (e) {
    return; // old server without the endpoint: leave install hints as-is
  }
  if (!r || r.ok !== true) return; // 404 JSON from an old server: leave install hints as-is
  if (!(r.wsl_solver && r.wsl_config)) return; // absent: keep install instructions
  const line = `Blind solver: astrometry.net installed locally (WSL, ${r.index_files} narrow-field indexes)`;
  const fmt = $("solver-hint-formats");
  if (fmt) fmt.textContent = "FITS / PNG / JPG — several at once is fine. A FITS with a WCS solves instantly; raw photos are blind-solved locally.";
  const inst = $("solver-hint-install");
  if (inst) inst.textContent = line + ". No API key needed; the nova key below is an optional online fallback.";
  const how = $("solver-hint-how");
  if (how) how.textContent = line + " — a raw photo with no embedded WCS solves offline.";
}

function selectPreset(ids) {
  state.selected = new Set(ids);
  // A preset selects everything "at once" with the FIRST frame focused, so the
  // history is stored most-recent-last ending on ids[0].
  state.order = [...ids].reverse();
  state.focus = ids[0];
  syncAge(); // auto mode follows the selection; manual is never stomped
  renderGallery();
  updatePreview();
}

function init() {
  $("preset-2").addEventListener("click", () => selectPreset(["f0", "f6"]));
  $("preset-12").addEventListener("click", () =>
    selectPreset(["f0", "f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9", "f10", "f11"]));
  $("clear-sel").addEventListener("click", () => {
    state.selected.clear(); state.order = []; state.focus = null;
    renderGallery(); updatePreview();
    $("results").innerHTML = ""; hideFixButton();
  });
  $("locate").addEventListener("click", locate);
  $("estimate").addEventListener("click", estimateAge);
  // Typing an age is an explicit override: enter manual mode so selection
  // changes stop stomping it. Edits refresh only the <img> srcs, debounced.
  $("age").addEventListener("input", () => {
    setAgeMode("manual");
    refreshImagesDebounced();
  });
  $("age-auto").addEventListener("click", () => setAgeMode("auto"));
  $("radius").addEventListener("input", refreshImagesDebounced);
  $("file").addEventListener("change", (e) => {
    const files = [...e.target.files];
    // ALWAYS clear the input so re-selecting the SAME file fires change again
    // (the "upload looks frozen" bug) -- reset on success AND failure alike.
    e.target.value = "";
    if (files.length) uploadMany(files);
  });
  loadFrames();
  solverStatus();
  openspaceStatus();
  updateWalkLink();
}
document.addEventListener("DOMContentLoaded", init);
