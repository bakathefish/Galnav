"""tkinter shell for the GalNav demo. This module is the THIN, un-unit-tested
UI layer: every piece of physics lives in the testable modules (platesolve,
centroids, locate, age, fitsmeta) and this file only wires buttons to them and
draws results.

Importing this module must NEVER open a window or require a display -- all
tkinter/matplotlib-Tk objects are created inside App.__init__, which runs only
from main(). `import gui.app` is therefore safe in a headless test.

Run:  python -m gui.app
"""

import os
import queue
import threading
from pathlib import Path

import numpy as np

from gui.age import estimate_age
from gui.centroids import find_centroids
from gui.fitsmeta import age_yr_since_j2016, observation_jd
from gui.locate import (
    LineOfPosition,
    fix_position,
    identify_in_frame,
    load_aged_catalog,
    measured_direction,
)
from gui.platesolve import fits_header_solution, solve_image

REPO_ROOT = Path(__file__).resolve().parent.parent
CATALOG_CSV = REPO_ROOT / "data" / "gaia_dr3_nav_subset.csv"

# Hand labels for the two stars the demo dataset features.
STAR_NAMES = {
    5853498713190525696: "Proxima Cen",
    3864972938605115520: "Wolf 359",
}


def load_grayscale(path):
    """Load a FITS/PNG/JPG image as a 2-D float array (row=y, col=x).

    path: image path. FITS uses the first 2-D HDU; PNG/JPG go through
        matplotlib.pyplot.imread and are averaged to grayscale.
    Returns: (H, W) float ndarray.
    """
    path = str(path)
    if path.lower().endswith((".fits", ".fit", ".fts")):
        from astropy.io import fits

        with fits.open(path) as hdul:
            for hdu in hdul:
                if hdu.data is not None and np.ndim(hdu.data) >= 2:
                    arr = np.asarray(hdu.data, dtype=float)
                    while arr.ndim > 2:  # collapse any leading cube axes
                        arr = arr[0]
                    return arr
        raise ValueError(f"{path}: no 2-D image HDU")
    import matplotlib.pyplot as plt

    arr = np.asarray(plt.imread(path), dtype=float)
    if arr.ndim == 3:
        arr = arr[..., :3].mean(axis=2)
    return arr


class App:
    """The single-window demo application. Constructed only by main()."""

    def __init__(self, root):
        import tkinter as tk
        from tkinter import ttk
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        from matplotlib.figure import Figure

        self.tk = tk
        self.root = root
        root.title("GalNav - starlight + pulsar navigation demo")

        # Per-image state: list of dicts {path, name, plate, status, image}.
        self.images = []
        self._queue = queue.Queue()
        self._busy = False

        left = ttk.Frame(root, padding=8)
        left.grid(row=0, column=0, sticky="ns")
        right = ttk.Frame(root, padding=4)
        right.grid(row=0, column=1, sticky="nsew")
        root.columnconfigure(1, weight=1)
        root.rowconfigure(0, weight=1)

        r = 0
        ttk.Button(left, text="Add image(s)...", command=self.add_images).grid(
            row=r, column=0, columnspan=2, sticky="ew", pady=2
        )
        r += 1
        self.listbox = tk.Listbox(left, width=42, height=8)
        self.listbox.grid(row=r, column=0, columnspan=2, sticky="ew", pady=2)
        self.listbox.bind("<<ListboxSelect>>", lambda e: self.redraw())
        r += 1
        ttk.Button(left, text="Solve fields", command=self.solve_fields).grid(
            row=r, column=0, columnspan=2, sticky="ew", pady=2
        )
        r += 1

        self.age_var = tk.StringVar(value="0.00")
        self.rv_var = tk.StringVar(value="0.0")
        self.radius_var = tk.StringVar(value="120")
        self.apikey_var = tk.StringVar(
            value=os.environ.get("ASTROMETRY_NET_API_KEY", "")
        )
        self.age_min_var = tk.StringVar(value="0")
        self.age_max_var = tk.StringVar(value="25")
        self.age_step_var = tk.StringVar(value="0.25")

        def labeled(text, var, **kw):
            nonlocal r
            ttk.Label(left, text=text).grid(row=r, column=0, sticky="w")
            ent = (
                ttk.Spinbox(left, textvariable=var, width=12, **kw)
                if kw
                else (ttk.Entry(left, textvariable=var, width=14))
            )
            ent.grid(row=r, column=1, sticky="ew", pady=1)
            r += 1
            return ent

        labeled(
            "Catalog age (yr since J2016.0)",
            self.age_var,
            from_=0.0,
            to=1000.0,
            increment=0.01,
        )
        labeled("RV fill (km/s)", self.rv_var, from_=-500.0, to=500.0, increment=0.1)
        labeled(
            "Match radius (arcsec)",
            self.radius_var,
            from_=1.0,
            to=3600.0,
            increment=1.0,
        )
        ttk.Label(left, text="nova API key").grid(row=r, column=0, sticky="w")
        ttk.Entry(left, textvariable=self.apikey_var, width=14, show="*").grid(
            row=r, column=1, sticky="ew", pady=1
        )
        r += 1
        ttk.Button(left, text="Locate spacecraft", command=self.locate).grid(
            row=r, column=0, columnspan=2, sticky="ew", pady=(8, 2)
        )
        r += 1
        ttk.Label(left, text="Age scan min / max / step").grid(
            row=r, column=0, columnspan=2, sticky="w"
        )
        r += 1
        scan = ttk.Frame(left)
        scan.grid(row=r, column=0, columnspan=2, sticky="ew")
        ttk.Entry(scan, textvariable=self.age_min_var, width=5).grid(row=0, column=0)
        ttk.Entry(scan, textvariable=self.age_max_var, width=5).grid(row=0, column=1)
        ttk.Entry(scan, textvariable=self.age_step_var, width=5).grid(row=0, column=2)
        r += 1
        ttk.Button(left, text="Estimate catalog age", command=self.estimate_age).grid(
            row=r, column=0, columnspan=2, sticky="ew", pady=2
        )
        r += 1
        self.results = tk.Text(left, width=44, height=16, wrap="word")
        self.results.grid(row=r, column=0, columnspan=2, sticky="nsew", pady=4)
        self.results.configure(state="disabled")

        self.fig = Figure(figsize=(6, 6))
        gs = self.fig.add_gridspec(3, 1)
        self.ax_img = self.fig.add_subplot(gs[0:2, 0])
        self.ax_chi = self.fig.add_subplot(gs[2, 0])
        self.canvas = FigureCanvasTkAgg(self.fig, master=right)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        self._clear_axes()
        self.canvas.draw()
        self.root.after(120, self._drain_queue)

    # --- helpers ------------------------------------------------------------
    def _log(self, text):
        self.results.configure(state="normal")
        self.results.insert("end", text + "\n")
        self.results.see("end")
        self.results.configure(state="disabled")

    def _clear_axes(self):
        self.ax_img.clear()
        self.ax_chi.clear()
        self.ax_img.set_title("image (log stretch)")
        self.ax_chi.set_title("chi2 vs catalog age")
        self.ax_chi.set_xlabel("age (yr)")

    def _selected_index(self):
        sel = self.listbox.curselection()
        return sel[0] if sel else (0 if self.images else None)

    def _refresh_list(self):
        self.listbox.delete(0, "end")
        for im in self.images:
            self.listbox.insert("end", f"{im['name']}  [{im['status']}]")

    # --- actions ------------------------------------------------------------
    def add_images(self):
        from tkinter import filedialog

        paths = filedialog.askopenfilenames(
            title="Select star-field image(s)",
            filetypes=[
                ("Images", "*.fits *.fit *.fts *.png *.jpg *.jpeg"),
                ("All files", "*.*"),
            ],
        )
        for p in paths:
            try:
                image = load_grayscale(p)
            except Exception as exc:  # noqa: BLE001
                self._log(f"could not read {Path(p).name}: {exc}")
                continue
            jd = (
                observation_jd(p)
                if str(p).lower().endswith((".fits", ".fit", ".fts"))
                else None
            )
            self.images.append(
                dict(
                    path=p,
                    name=Path(p).name,
                    plate=None,
                    status="unsolved",
                    image=image,
                    obs_jd=jd,
                )
            )
        # Prefill age from the first FITS with a time key.
        for im in self.images:
            if im.get("obs_jd"):
                self.age_var.set(f"{age_yr_since_j2016(im['obs_jd']):.2f}")
                break
        self._refresh_list()
        self.redraw()

    def solve_fields(self):
        if self._busy or not self.images:
            return
        self._busy = True
        api_key = self.apikey_var.get().strip() or None
        todo = [im for im in self.images if im["plate"] is None]
        self._log(f"solving {len(todo)} field(s)...")

        def worker():
            for im in todo:
                try:
                    plate = solve_image(im["path"], api_key=api_key)
                    self._queue.put(("solved", im, plate))
                except Exception as exc:  # noqa: BLE001
                    self._queue.put(("solve_error", im, str(exc)))
            self._queue.put(("solve_done", None, None))

        threading.Thread(target=worker, daemon=True).start()

    def _drain_queue(self):
        try:
            while True:
                kind, im, payload = self._queue.get_nowait()
                if kind == "solved":
                    im["plate"] = payload
                    im["status"] = payload.source
                    self._log(f"{im['name']}: solved ({payload.source})")
                elif kind == "solve_error":
                    im["status"] = "solve failed"
                    self._log(f"{im['name']}: {payload}")
                elif kind == "solve_done":
                    self._busy = False
                elif kind == "text":
                    self._log(payload)
                elif kind == "age_curve":
                    self._draw_chi(payload)
                self._refresh_list()
                self.redraw()
        except queue.Empty:
            pass
        self.root.after(120, self._drain_queue)

    def _collect_lines(self, age_yr, radius):
        """Build lines of position across all solved images at a catalog age."""
        lines = []
        for im in self.images:
            if im["plate"] is None:
                continue
            rv = float(self.rv_var.get() or 0.0)
            cat = load_aged_catalog(CATALOG_CSV, age_yr, rv_fill_kms=rv)
            centroids = find_centroids(im["image"])
            matches = identify_in_frame(
                im["plate"],
                centroids["xy"],
                cat["positions_au"],
                match_radius_arcsec=radius,
            )
            for m in matches:
                si = m["star_index"]
                direction = measured_direction(
                    im["plate"], centroids["xy"][m["centroid_index"]]
                )
                lines.append(
                    LineOfPosition(
                        star_pos_au=cat["positions_au"][si],
                        direction_unit=direction,
                        star_source_id=int(cat["source_id"][si]),
                        sep_arcsec=m["sep_arcsec"],
                        image_name=im["name"],
                    )
                )
        return lines

    def locate(self):
        try:
            age = float(self.age_var.get())
            radius = float(self.radius_var.get())
        except ValueError:
            self._log("age and match radius must be numbers")
            return
        lines = self._collect_lines(age, radius)
        self._log(f"\nLocate at age {age:.2f} yr: {len(lines)} line(s) of position")
        for ln in lines:
            name = STAR_NAMES.get(ln.star_source_id, str(ln.star_source_id))
            self._log(f'  {name} in {ln.image_name} (residual {ln.sep_arcsec:.1f}")')
        try:
            fix = fix_position(lines, rmssig_arcsec=0.44)
        except ValueError as exc:
            self._log(f"  cannot fix: {exc}")
            return
        x = fix["x_au"]
        r = float(np.linalg.norm(x))
        self._log(
            f"  position = [{x[0]:.3f}, {x[1]:.3f}, {x[2]:.3f}] au\n"
            f"  |r| = {r:.3f} au = {r / 206264.806:.3e} pc\n"
            f"  1-sigma ellipsoid = {np.round(fix['ellipsoid_au'], 3)} au\n"
            f"  chi2 = {fix['chi2']:.3e}, distinct stars = {fix['distinct_stars']}"
        )

    def estimate_age(self):
        if self._busy or not self.images:
            return
        try:
            lo = float(self.age_min_var.get())
            hi = float(self.age_max_var.get())
            step = float(self.age_step_var.get())
            radius = float(self.radius_var.get())
        except ValueError:
            self._log("age scan fields must be numbers")
            return
        grid = np.arange(lo, hi + 1e-9, step)
        self._busy = True
        self._queue.put(("text", None, f"\nEstimating age over {lo}..{hi} yr..."))

        def worker():
            try:
                res = estimate_age(
                    lambda a: self._collect_lines(a, radius),
                    grid,
                    rmssig_arcsec=0.44,
                )
                self._queue.put(
                    (
                        "text",
                        None,
                        f"  age_hat = {res['age_hat_yr']:.3f} +/- "
                        f"{res['sigma_age_yr']:.3f} yr",
                    )
                )
                truth = [
                    age_yr_since_j2016(im["obs_jd"])
                    for im in self.images
                    if im.get("obs_jd")
                ]
                if truth:
                    self._queue.put(
                        ("text", None, f"  FITS truth (mean) = {np.mean(truth):.3f} yr")
                    )
                self._queue.put(("age_curve", None, res))
            except Exception as exc:  # noqa: BLE001
                self._queue.put(("text", None, f"  age estimate failed: {exc}"))
            self._queue.put(("solve_done", None, None))

        threading.Thread(target=worker, daemon=True).start()

    # --- drawing ------------------------------------------------------------
    def _draw_chi(self, res):
        self.ax_chi.clear()
        self.ax_chi.plot(res["ages"], res["chi2s"], "-o", ms=3)
        self.ax_chi.axvline(res["age_hat_yr"], color="tab:red", lw=1)
        self.ax_chi.set_title(
            f"chi2 vs age: {res['age_hat_yr']:.2f} +/- {res['sigma_age_yr']:.2f} yr"
        )
        self.ax_chi.set_xlabel("age (yr)")
        self.canvas.draw()

    def redraw(self):
        idx = self._selected_index()
        self.ax_img.clear()
        self.ax_img.set_title("image (log stretch)")
        if idx is None or idx >= len(self.images):
            self.canvas.draw()
            return
        im = self.images[idx]
        img = im["image"]
        bg = np.median(img)
        self.ax_img.imshow(
            np.log1p(np.clip(img - bg, 0, None)), origin="lower", cmap="gray"
        )
        centroids = find_centroids(img)
        xy = centroids["xy"]
        if xy.shape[0]:
            self.ax_img.scatter(
                xy[:, 0],
                xy[:, 1],
                s=40,
                facecolors="none",
                edgecolors="tab:cyan",
                linewidths=0.8,
            )
        if im["plate"] is not None:
            try:
                age = float(self.age_var.get())
                radius = float(self.radius_var.get())
                rv = float(self.rv_var.get() or 0.0)
            except ValueError:
                age, radius, rv = 0.0, 120.0, 0.0
            cat = load_aged_catalog(CATALOG_CSV, age, rv_fill_kms=rv)
            matches = identify_in_frame(im["plate"], xy, cat["positions_au"], radius)
            for m in matches:
                sid = int(cat["source_id"][m["star_index"]])
                cx, cy = xy[m["centroid_index"]]
                self.ax_img.plot(cx, cy, "+", color="tab:orange", ms=12, mew=2)
                label = STAR_NAMES.get(sid, str(sid))
                self.ax_img.annotate(
                    label,
                    (cx, cy),
                    color="tab:orange",
                    fontsize=8,
                    xytext=(5, 5),
                    textcoords="offset points",
                )
        self.ax_img.set_title(f"{im['name']} [{im['status']}]")
        self.canvas.draw()


def main():
    """Open the demo window and run the tkinter main loop."""
    import tkinter as tk

    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
