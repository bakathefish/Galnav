# GUI: the pipeline walk + the live OpenSpace bridge

**What this is.** Two layers that turn the demo from "a button that prints an
answer" into "watch the navigation happen." First, six chained webpages
(`gui/web/pipeline-1-raw.html` … `pipeline-6-fix.html`) walk the pipeline one
stage per page — raw image, centroid detection, star identification, measured
angles, lines of position, the fix — each fetching the stage's REAL numbers
from the new `/api/pipeline` endpoint and showing the math beside them.
Second, `gui/openspace_link.py` pushes each stage's geometry into a RUNNING
OpenSpace planetarium ([OpenSpace] in citations; protocol facts under
[OpenSpace API]), so the booth show is the actual measurement appearing in the
actual sky. Nothing computes in OpenSpace; it only displays.

**The honest degenerate case, made visible.** One image holding one nearby
star cannot fix a point — `fix_position` refuses, as it always has. Page 6
now SHOWS why instead of only saying so: the response carries `mode:"line"`
plus the drawable ray from `locate.line_of_position_summary` (anchor at the
star, unit ray toward the observer, fan-out in arcsec when two same-star
frames merge), the page headline reads "a line, not a point," and an *add a
second image* link re-runs the walk with two frames. One image with TWO
distinct nearby stars in frame is a full fix and always was — the frame count
never mattered, the distinct-star count did; the wide-pair synthetic test in
`test_locate.py` pins that with a measured 6.8 au recovery at |r| = 329 au.

**The wire, tiny-by-tiny.** The bridge speaks the Server module's TCP socket
(port 4681, `openspace.cfg` default; localhost pre-allowed). Each message is
one newline-terminated JSON object. Three facts were learned ONLY by driving
a live OpenSpace 0.22.0 on this box (2026-07-20) — the offline fake-server
tests could not have caught any of them:

1. **The apiHandshake is mandatory.** The first message on every connection
   must be `{"type":"apiHandshake","apiVersion":{"major":1,"minor":0,
   "patch":0}}` — the same first-thing-on-connect the official
   openspace-api-js client sends (`src/api.ts`, `_sendHandshake`). Without
   it, EVERY topic message is rejected with `Unexpected error Unsupported
   API version` and nothing executes. The first diagnosis (a wrong
   `shouldBeSynchronized` flag) was a MISREAD of engine log lines that quote
   the offending payload — the "executions" being counted were the rejection
   lines themselves. Corrected by checking that the marker string appears in
   a clean log line, not inside an error that echoes our own message.
2. **The linger is load-bearing.** OpenSpace's per-connection reader thread
   enqueues messages as it pulls them off the socket; a FIN immediately
   after `sendall` races that thread and the message dies unparsed.
   Measured: instant close → 0/2 delivered; any hold ≥ 50 ms → 9/9 (50 /
   250 / 750 ms trials). `run_lua` holds the socket 0.25 s (5× margin) and
   pauses 0.2 s between handshake and script so the version state is set
   before the script arrives.
3. **The camera API.** `openspace.pathnavigation` is nil on 0.22 ("attempt
   to call a nil value"). `openspace.navigation.flyTo(id, 4.0)` completes
   ("Reached target") but PRESERVES the camera-to-target distance — flying
   from Earth it arrived 6.54 light-hours (≈ 47 au) from an 8×10⁹ m marker,
   which subtends nothing — and flyTo has no height control (a third number
   → "Duration cannot be specified twice"; an options table → "Expected type
   'Boolean or Number'"). The working call is
   `openspace.navigation.setNavigationState{Anchor="GalNavLiveFix",
   Position={6e10,0,0}}`: exact, instant, and 6×10¹⁰ m happens to frame the
   amber fix sphere WITH the cyan truth sphere 5.8×10¹⁰ m (0.387 au) beside
   it — the miss story in a single view, screenshot-verified.

**Idempotency.** Every stage push is prefixed by a guarded clear
(`hasSceneGraphNode` + `pcall`) of all `GalNavLive*` nodes, so re-pushing a
stage or switching stages never raises a duplicate-identifier error. All
frame conversion reuses `gui.openspace_export.icrs_au_to_galactic_m` — the
Hipparcos rotation already verified against astropy to a measured 0.025
arcsec definition floor (journal/gui-openspace.md).

**End-to-end proof (this box, 2026-07-20).** OpenSpace 0.22.0 installed
(full 9.9 GB release), engine driven through the real webapp HTTP endpoints:
stars stage placed the Proxima + Wolf 359 markers, lines stage drew all 12
LORRI lines of position (their near-parallel bundling IS the narrow-field
geometry), fix stage landed the camera on amber fix + cyan truth + white
0.387 au miss line (focus "GalNav fix", 60,000,000 km readout, PathNavigator
"Reached target"). In-engine screenshots taken after every stage via
`openspace.takeScreenshot()` (they land in a dated SUBFOLDER of
`user/screenshots/` — another live-only fact).

**Tests** (`tests_gui/test_openspace_link.py`, 19, all offline): wire
framing including handshake-first against an in-process fake TCP server; the
linger pinned by measuring payload-to-FIN wall time; galactic-metre
positions present with raw-au absent (the classic wrong-frame bug); clear
prefix; endpoint = anchor − (|anchor|+100 au)·direction checked numerically
through the rotation; camera move present, pcall-guarded, anchored to the
fix; every identifier `GalNavLive`-prefixed. Plus webapp endpoint tests
(status shape, per-stage payloads with the link mocked, one-star LOP
behavior, the honest not-running message) and static source-hook tests for
all six pages served through the real static route.

**Honest limits.** The pushed markers are single-epoch statements, exactly
like the exporter's (park the booth clock near the frame epochs when telling
the miss story). If OpenSpace is upgraded, the apiHandshake version, the
navigation call signatures and the reply-frame shape below are the first
things to re-verify; the tests name the expected failure modes.

**Re-measured 2026-07-21: the reply channel WORKS — pushes are now
execution-confirmed.** The 2026-07-20 note here said the `return:true` reply
channel closed the probe connections without data on 0.22; re-probing against
the same live 0.22.0 build (fresh boot, handshake in place) shows it answers
reliably, so that finding is superseded (the earlier probes most plausibly ran
before the engine finished coming up). Measured on this box, 2026-07-21:

- `{"script": s, "return": true}` → ONE newline-framed reply AFTER the chunk
  executes: `{"payload":{"1":<return value>},"topic":<our topic>}` — a 3-line
  chunk ending `return x+y` replied `{"1":42.0}`, so a trailing sentinel
  proves the WHOLE chunk ran.
- A FAILING chunk (both `error("boom")` and a syntax error measured) still
  replies, with payload `{}` — execution failure is distinguishable from a
  dropped message.
- `return:false` stays silent (0 bytes in 1.5 s) — fire-and-forget confirmed.

`gui/openspace_link.run_lua_confirmed` builds on this: it appends `return 1`
to every push and maps the reply to `confirmed` / `failed` / `sent` / `down`;
`_os_push` and the panel note surface exactly those words. Waiting for the
reply also holds the socket open past the reader-thread race, so the blind
0.25 s linger is subsumed by the read. Live-verified end-to-end 2026-07-21:
stars/fix/clear pushes over HTTP all `confirmed`, and
`openspace.hasSceneGraphNode("GalNavLiveFix")` interrogated true after the
fix push and false after clear — the engine's own scene graph as witness.
run_lua (fire-and-forget) remains for anything that needs no receipt.
