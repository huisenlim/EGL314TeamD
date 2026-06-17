#!/usr/bin/env python3
"""
game.py  —  OSC Receiver + Trilateration + Kalman Filter + Visualizer + Hardware Button
======================================================================================
Runs on the "game" Pi driving the display. Tracks tags, updates ghost zones,
and handles win conditions when a physical arcade button is hit inside a zone.

Run:
    python3 game.py --tags 2 --windowed
"""

import argparse
import csv
import sys
import threading
import RPi.GPIO as GPIO
import time
import tkinter as tk
from tkinter import ttk
from dataclasses import dataclass, field

import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from pythonosc import dispatcher as osc_dispatcher
from pythonosc import osc_server

# ---------------------------------------------------------------------------
# Anchor layout and view config
# ---------------------------------------------------------------------------
ANCHORS = {
    0: (0.0, 0.0),
    1: (0.0, 0.50),
    2: (0.0, 1.0),
    3: (1.0, 1.0),
    4: (1.0, 0.50),
    5: (1.0, 0.0),
}

VIEW_BOUNDS = (-0.50, 1.50, -0.50, 1.50)

# ---------------------------------------------------------------------------
# Ghosts Configuration
# ---------------------------------------------------------------------------
GhostHitTol = 0.0  # hit tolerance

Ghosts = [
    {
        "center": (0.25, 0.625),
        "radius": 0.15,
        "min_radius": 0.10,
        "color": "#ffff00",
        "label": "Bob",
        "active": True,
    },
    {
        "center": (0.75, 1.0),
        "radius": 0.15,
        "min_radius": 0.10,
        "color": "#fff700",
        "label": "Stewart",
        "active": True,
    },
    {
        "center": (0.75, 0.25),
        "radius": 0.15,
        "min_radius": 0.10,
        "color": "#fff700",
        "label": "Kevin",
        "active": True,
    },
]

TAG_COLORS = [
    "#ff5252", "#42a5f5", "#66bb6a", "#ffb74d",
    "#ab47bc", "#26a69a", "#ec407a", "#bdbdbd",
]

COLOR_NAMES = [
    "red", "blue", "green", "orange",
    "purple", "teal", "pink", "gray",
]

DEFAULT_PORT = 5005   # UDP port to listen on


# ---------------------------------------------------------------------------
# Trilateration Core Logic
# ---------------------------------------------------------------------------
def trilaterate_2d(anchor_positions, distances):
    valid = [(p[0], p[1], d) for p, d in zip(anchor_positions, distances)
            if p is not None and 0.05 < d < 50.0]
    if len(valid) < 3:
        return None

    xr, yr, rr = valid[-1]
    A, b = [], []
    for xi, yi, ri in valid[:-1]:
        A.append((2 * (xi - xr), 2 * (yi - yr)))
        b.append(ri**2 - rr**2 - xi**2 + xr**2 - yi**2 + yr**2)
    if len(A) < 2:
        return None

    m00 = sum(ax * ax for ax, ay in A)
    m01 = sum(ax * ay for ax, ay in A)
    m11 = sum(ay * ay for ax, ay in A)
    v0  = sum(ax * bi for (ax, ay), bi in zip(A, b))
    v1  = sum(ay * bi for (ax, ay), bi in zip(A, b))

    det = m00 * m11 - m01 * m01
    if abs(det) < 1e-9:
        return None

    x = -(v0 * m11 - v1 * m01) / det
    y = -(m00 * v1 - m01 * v0) / det
    return x, y

def ptInGhost(point, ghost):
    if point is None:
        return False
    px, py = point
    zx, zy = ghost["center"]
    r = ghost["radius"] + GhostHitTol
    dx = px - zx
    dy = py - zy
    return (dx * dx + dy * dy) <= (r * r)


# ---------------------------------------------------------------------------
# Kalman Filter Tracking Processing
# ---------------------------------------------------------------------------
class Kalman2D:
    def __init__(self, dt=0.10, q=0.12, r=1.1):
        self.dt = dt
        self.q  = q
        self.r  = r
        self.state = [0.0, 0.0, 0.0, 0.0]
        self.P = [[1.0, 0, 0, 0], [0, 1.0, 0, 0],
                [0, 0, 1.0, 0], [0, 0, 0, 1.0]]
        self.initialized = False

    def predict(self):
        if not self.initialized:
            return
        self.state[0] += self.state[2] * self.dt
        self.state[1] += self.state[3] * self.dt
        for i in range(4):
            self.P[i][i] += self.q

    def update(self, mx, my):
        if not self.initialized:
            self.state = [mx, my, 0.0, 0.0]
            self.initialized = True
            return mx, my
        Kx = self.P[0][0] / (self.P[0][0] + self.r)
        Ky = self.P[1][1] / (self.P[1][1] + self.r)
        old_x, old_y = self.state[0], self.state[1]
        self.state[0] += Kx * (mx - self.state[0])
        self.state[1] += Ky * (my - self.state[1])
        self.state[2] = (self.state[0] - old_x) / self.dt
        self.state[3] = (self.state[1] - old_y) / self.dt
        self.P[0][0] *= (1 - Kx)
        self.P[1][1] *= (1 - Ky)
        return self.state[0], self.state[1]


@dataclass
class TagState:
    last_distances: list = field(default_factory=lambda: [0.0] * 8)
    raw_position:   tuple = None
    filt_position:  tuple = None
    last_update:    float = 0.0
    kalman: Kalman2D = field(default_factory=Kalman2D)
    ghosts_inside: set = field(default_factory=set)


class SharedState:
    def __init__(self, n_tags):
        self.n_tags = n_tags
        self.tags   = [TagState() for _ in range(n_tags)]
        self.row_color_index = list(range(n_tags))
        self.lock   = threading.Lock()
        self.frame_count = 0
        self.start_time  = time.time()
        self.stop = False
        self.game_won = False
        self.button_pressed = False  # Track live hardware button state


# ---------------------------------------------------------------------------
# OSC Handler & Main Gameplay Decision Matrix
# ---------------------------------------------------------------------------
def make_osc_handler(state: SharedState, anchor_ids, anchor_positions_list, csv_writer=None):
    def handle_distances(address, *args):
        if len(args) < 9 or state.game_won or state.stop:
            return

        tag_id    = int(args[0])
        distances = [float(v) for v in args[1:9]]

        if tag_id >= state.n_tags:
            return

        tag = state.tags[tag_id]
        dists_for_trilat = [distances[i] for i in anchor_ids]
        raw_pos = trilaterate_2d(anchor_positions_list, dists_for_trilat)

        with state.lock:
            tag.last_distances = distances
            tag.last_update = time.time()
            if raw_pos is not None:
                tag.kalman.predict()
                fx, fy = tag.kalman.update(raw_pos[0], raw_pos[1])
                tag.raw_position  = raw_pos
                tag.filt_position = (fx, fy)

                # --- GAME LOGIC MATRIX ---
                current_ghosts = set()

                for zi, ghost in enumerate(Ghosts):
                    if ghost.get("active", True):
                        if ptInGhost(tag.filt_position, ghost):
                            current_ghosts.add(zi)

                tag.ghosts_inside = {zi for zi in current_ghosts if Ghosts[zi]["active"]}

                for zi, ghost in enumerate(Ghosts):
                    if ghost.get("active", True):
                        is_in_zone = ptInGhost(tag.filt_position, ghost)

                        # Condition 1: Button is pressed AND tag is inside the ghost zone
                        if state.button_pressed and is_in_zone:
                            print(f"\n=== SUCCESS === Tag {tag_id} dispelled Ghost: {ghost['label']}!")
                            ghost["active"] = False

                        # Condition 2: Button is pressed AND tag is NOT inside the ghost zone
                        elif state.button_pressed and not is_in_zone:
                            pass # Ghost remains unaffected 

                        # Condition 3: Button is NOT pressed AND tag is inside the ghost zone
                        elif not state.button_pressed and is_in_zone:
                            current_ghosts.add(zi) # Ghost remains, mark as occupying zone

                tag.ghosts_inside = {zi for zi in current_ghosts if Ghosts[zi]["active"]}

                # Check for Win Condition (Are all ghosts turned off?)
                if all(not g.get("active", True) for g in Ghosts):
                    state.game_won = True
                    print("\n🏆 !!! CONGRATS!!! U WIN!!! ALL GHOSTS CLEARED!!! 🏆")

            else:
                tag.kalman.predict()
            state.frame_count += 1

    return handle_distances


# ---------------------------------------------------------------------------
# UI Visualizer Component (Tkinter Dashboard + Matplotlib Grid)
# ---------------------------------------------------------------------------
class ViewerApp:
    def __init__(self, root, state: SharedState, show_circles, fullscreen):
        self.root         = root
        self.state        = state
        self.show_circles = show_circles
        self.anchor_ids   = sorted(ANCHORS.keys())
        self.n_anchors    = len(self.anchor_ids)

        root.title("UWB Target Tracker")
        root.configure(bg="#000000")

        root.grid_rowconfigure(0, weight=5)
        root.grid_rowconfigure(1, weight=1)
        root.grid_columnconfigure(0, weight=1)

        plot_frame = tk.Frame(root, bg="#000000")
        plot_frame.grid(row=0, column=0, sticky="nsew")

        plt.style.use("dark_background")
        self.fig = Figure(figsize=(14, 8))
        self.fig.patch.set_facecolor("#000000")
        self.ax_plot = self.fig.add_subplot(111)

        x_min, x_max, y_min, y_max = VIEW_BOUNDS
        self.ax_plot.set_xlim(x_min, x_max)
        self.ax_plot.set_ylim(y_min, y_max)
        self.ax_plot.set_aspect("equal")
        self.ax_plot.grid(True, alpha=0.2)
        self.ax_plot.set_title("UWB Active Tracking Field", color="white", fontsize=14)
        self.ax_plot.set_facecolor("#000000")

        # Static Anchor Layout Mapping
        for aid, (ax_x, ax_y) in ANCHORS.items():
            self.ax_plot.plot(ax_x, ax_y, marker="^", markersize=14, color="#ffeb3b", markeredgecolor="white")
            self.ax_plot.annotate(f"A{aid}", (ax_x, ax_y), textcoords="offset points", xytext=(8, 8), color="#ffeb3b", fontsize=11)

        # Dynamic Ghost Object Handles Initialization
        self.ghost_patches = {}
        for zi, ghost in enumerate(Ghosts):
            cx, cy = ghost["center"]
            circle = mpatches.Circle((cx, cy), ghost["radius"], fill=False, linewidth=3, linestyle="-.", edgecolor=ghost["color"], alpha=0.9)
            self.ax_plot.add_patch(circle)
            txt = self.ax_plot.text(cx, cy, ghost["label"], color=ghost["color"], fontsize=11, ha="center", va="center", weight="bold")
            self.ghost_patches[zi] = (circle, txt)

        self.row_dots = []
        self.row_circles_per_anchor = [[None] * self.n_anchors for _ in range(state.n_tags)]
        for i in range(state.n_tags):
            dot, = self.ax_plot.plot([], [], marker="o", markersize=10, color=TAG_COLORS[i], markeredgecolor="white", linewidth=0)
            self.row_dots.append(dot)

        self.hud = self.ax_plot.text(0.02, 0.98, "", transform=self.ax_plot.transAxes, va="top", ha="left", color="white",
                                    fontsize=10, family="monospace", bbox=dict(facecolor="black", alpha=0.5, edgecolor="none"))

        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        # Bottom Monitoring Dashboard Data Table
        table_frame = tk.Frame(root, bg="#000000")
        table_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

        headers = ["Tag ID", "X (m)", "Y (m)", "Color Assignment"]
        for col, label in enumerate(headers):
            lbl = tk.Label(table_frame, text=label, bg="#222222", fg="white", font=("Helvetica", 13, "bold"), padx=8, pady=6, relief="solid", borderwidth=1)
            lbl.grid(row=0, column=col, sticky="nsew")

        for col in range(4):
            table_frame.grid_columnconfigure(col, weight=1, uniform="cols")

        self.id_labels, self.x_labels, self.y_labels, self.color_combos, self.color_swatches = [], [], [], [], []

        for r in range(state.n_tags):
            id_lbl = tk.Label(table_frame, text=f"T{r}", bg="#111111", fg=TAG_COLORS[r], font=("Helvetica", 14, "bold"), padx=8, pady=6, relief="solid", borderwidth=1)
            id_lbl.grid(row=r + 1, column=0, sticky="nsew")
            self.id_labels.append(id_lbl)

            x_lbl = tk.Label(table_frame, text="—", bg="#111111", fg="white", font=("Courier", 13), padx=8, pady=6, relief="solid", borderwidth=1)
            x_lbl.grid(row=r + 1, column=1, sticky="nsew")
            self.x_labels.append(x_lbl)

            y_lbl = tk.Label(table_frame, text="—", bg="#111111", fg="white", font=("Courier", 13), padx=8, pady=6, relief="solid", borderwidth=1)
            y_lbl.grid(row=r + 1, column=2, sticky="nsew")
            self.y_labels.append(y_lbl)

            color_cell = tk.Frame(table_frame, bg="#111111", relief="solid", borderwidth=1)
            color_cell.grid(row=r + 1, column=3, sticky="nsew")

            swatch = tk.Frame(color_cell, bg=TAG_COLORS[r], width=24, height=24)
            swatch.pack(side="left", padx=8, pady=6)
            self.color_swatches.append(swatch)

            combo = ttk.Combobox(color_cell, values=COLOR_NAMES, state="readonly", width=10, font=("Helvetica", 12))
            combo.set(COLOR_NAMES[r])
            combo.pack(side="left", padx=4, pady=6)
            self.color_combos.append(combo)

        root.bind("<KeyPress-q>", lambda e: self.shutdown())
        root.bind("<KeyPress-Q>", lambda e: self.shutdown())
        root.bind("<Escape>",     lambda e: self.shutdown())
        root.protocol("WM_DELETE_WINDOW", self.shutdown)

        if fullscreen:
            try: root.attributes("-fullscreen", True)
            except tk.TclError: pass

        self.root.after(30, self.update_loop)

    def update_loop(self):
        if self.state.stop:
            return

        # Check and handle active visual drop modifications
        for zi, ghost in enumerate(Ghosts):
            if not ghost.get("active", True) and zi in self.ghost_patches:
                circle, txt = self.ghost_patches[zi]
                try:
                    circle.remove()
                    txt.remove()
                except ValueError:
                    pass
                del self.ghost_patches[zi]

        with self.state.lock:
            if self.state.game_won:
                self.ax_plot.set_title("GAME OVER — AREA CLEARED! YOU WIN!", color="#00ff00", fontsize=16, weight="bold")
            
            snapshot = [{"filt": t.filt_position, "dists": list(t.last_distances), "last": t.last_update} for t in self.state.tags]
            total, elapsed, color_indices = self.state.frame_count, time.time() - self.state.start_time, list(self.state.row_color_index)

        now = time.time()
        for row, snap in enumerate(snapshot):
            color = TAG_COLORS[color_indices[row]]
            pos, stale = snap["filt"], (now - snap["last"] > 1.0) if snap["last"] else True

            self.row_dots[row].set_color(color)
            self.row_dots[row].set_markerfacecolor(color)
            self.row_dots[row].set_data([pos[0]] if pos and not stale else [], [pos[1]] if pos and not stale else [])

            if pos and not stale:
                self.x_labels[row].configure(text=f"{pos[0]:.3f}")
                self.y_labels[row].configure(text=f"{pos[1]:.3f}")
            else:
                self.x_labels[row].configure(text="—")
                self.y_labels[row].configure(text="—")

            if self.show_circles:
                for slot, aid in enumerate(self.anchor_ids):
                    old = self.row_circles_per_anchor[row][slot]
                    if old: old.remove(); self.row_circles_per_anchor[row][slot] = None
                    if stale: continue
                    d = snap["dists"][aid] if aid < len(snap["dists"]) else 0
                    if d <= 0.05: continue
                    cx, cy = ANCHORS[aid]
                    circ = mpatches.Circle((cx, cy), d, fill=False, color=color, alpha=0.25, linewidth=1)
                    self.ax_plot.add_patch(circ)
                    self.row_circles_per_anchor[row][slot] = circ

        rate = total / elapsed if elapsed > 0 else 0
        active = sum(1 for s in snapshot if s["filt"] is not None and now - s["last"] < 1.0)
        self.hud.set_text(f"frames: {total}\nrate:   {rate:5.1f} Hz\nactive: {active}/{self.state.n_tags}\nButton Pin 27: {'PRESSED' if self.state.button_pressed else 'OPEN'}")

        self.canvas.draw_idle()
        self.root.after(66, self.update_loop)

    def shutdown(self):
        self.state.stop = True
        try: self.root.destroy()
        except tk.TclError: pass


# ---------------------------------------------------------------------------
# Hardware & Server Pipeline Execution Initialization
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tags", type=int, default=2, help="Number of active tags (1..8).")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT, help="UDP port.")
    ap.add_argument("--no-circles", action="store_true", help="Hide distance circles.")
    ap.add_argument("--windowed", action="store_true", help="Don't enter fullscreen mode.")
    args = ap.parse_args()

    if not 1 <= args.tags <= 8:
        sys.exit("[error] --tags entry range bounds violated")

    state = SharedState(n_tags=args.tags)
    for tag in state.tags:
        tag.kalman.dt = 0.10

    # --- RPi.GPIO EDGE DETECT INTERRUPT CALL REGISTER ---
    BUTTON_PIN = 27
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    def pin_edge_callback(channel):
        is_pressed = not GPIO.input(channel)
        with state.lock:
            state.button_pressed = is_pressed

            # --- FORCE IMMEDIATE DEACTIVATION ON PRESS ---
            if is_pressed:
                for tag_id, tag in enumerate(state.tags):
                    if tag.filt_position is None:
                        continue
                    
                    for zi, ghost in enumerate(Ghosts):
                        if ghost.get("active", True):
                            # Check if this tag is inside this ghost right now
                            if ptInGhost(tag.filt_position, ghost):
                                print(f"\n🎯 HIT! Tag {tag_id} dispelled {ghost['label']}!")
                                ghost["active"] = False

    # 200ms software bounce filter mapping 
    GPIO.add_event_detect(BUTTON_PIN, GPIO.FALLING, callback=pin_edge_callback, bouncetime=200)

    anchor_ids = sorted(ANCHORS.keys())
    anchor_positions_list = [ANCHORS[i] for i in anchor_ids]

    disp = osc_dispatcher.Dispatcher()
    handler = make_osc_handler(state, anchor_ids, anchor_positions_list)
    disp.map("/distances", handler)

    server = osc_server.ThreadingOSCUDPServer(("0.0.0.0", args.port), disp)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    print(f"[game] Operational server online listening on port {args.port}")

    root = tk.Tk()
    app = ViewerApp(root, state, show_circles=not args.no_circles, fullscreen=not args.windowed)

    try:
        root.mainloop()
    except KeyboardInterrupt:
        pass
    finally:
        state.stop = True
        server.shutdown()
        GPIO.cleanup()
        print("[game] System core execution pipelines deactivated safely.")

if __name__ == "__main__":
    main()