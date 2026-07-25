#!/usr/bin/env python3
"""
tutorial.py  —  OSC Receiver + Trilateration + Kalman Filter + Visualizer + Tutorial
======================================================================================
Runs on the "game" Pi that drives the display.

Interactive tutorial mode: walks the player through the GHOST HUNTING 101 steps,
then drops them into a LIVE practice hunt using the real button (GPIO) and the
Multiplay proximity-beeping cues, exactly like the main game — but with NO timer
and NO win/lose conditions. Ghosts simply get dispelled when the button is
pressed while standing in their containment field.

Run:
    python3 tutorial.py --tags 2 --windowed
"""

import argparse
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk
from dataclasses import dataclass, field

import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import RPi.GPIO as GPIO

from pythonosc import dispatcher as osc_dispatcher
from pythonosc import osc_server
from pythonosc.udp_client import SimpleUDPClient

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

GhostHitTol = 0.08

# ---------------------------------------------------------------------------
# Ghosts Configuration
# ---------------------------------------------------------------------------
Ghosts = [
    {
        "center": (0.25, 0.5),
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
]

TAG_COLORS = [
    "#ff5252", "#42a5f5", "#66bb6a", "#ffb74d",
    "#ab47bc", "#26a69a", "#ec407a", "#bdbdbd",
]

COLOR_NAMES = [
    "red", "blue", "green", "orange",
    "purple", "teal", "pink", "gray",
]

DEFAULT_PORT = 5005

# ---------------------------------------------------------------------------
# Button Configuration
# ---------------------------------------------------------------------------
BUTTON_PIN = 27

# ---------------------------------------------------------------------------
# Multiplay Sound Cue Configuration
# ---------------------------------------------------------------------------
MULTIPLAY_IP   = "192.168.254.173"
MULTIPLAY_PORT = 5005

# Evaluated top-to-bottom; first threshold the player is WITHIN triggers that cue.
SOUND_CUE_THRESHOLDS = [
    (0.0,   "/cue/4/go"),   # right on the ghost
    (0.25,  "/cue/3/go"),   # very close
    (0.625, "/cue/2/go"),   # medium range
    (1.0,   "/cue/1/go"),   # far away
]


# ---------------------------------------------------------------------------
# Math & Logic Modules
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
    return (px - zx) ** 2 + (py - zy) ** 2 <= r * r


def dist_to_ghost(point, ghost):
    px, py = point
    gx, gy = ghost["center"]
    return ((px - gx) ** 2 + (py - gy) ** 2) ** 0.5


def nearest_ghost_distance(point):
    active = [g for g in Ghosts if g.get("active", True)]
    if not active or point is None:
        return float("inf")
    return min(dist_to_ghost(point, g) for g in active)


def cue_for_distance(distance):
    for threshold, address in SOUND_CUE_THRESHOLDS:
        if distance <= threshold:
            return address
    return None


# ---------------------------------------------------------------------------
# Multiplay Client
# ---------------------------------------------------------------------------
class MultiplayClient:
    def __init__(self, ip: str, port: int):
        self._client = SimpleUDPClient(ip, port)
        print(f"[multiplay] OSC client initialised → {ip}:{port}")

    def stop_all(self):
        try:
            self._client.send_message("/cue/all/stop", [])
            print("[multiplay] all cues stopped")
        except Exception as exc:
            print(f"[multiplay] stop_all failed: {exc}")

    def trigger(self, address: str):
        try:
            self._client.send_message("/cue/all/stop", [])
            self._client.send_message(address, [])
            print(f"[multiplay] stopped all → cue sent: {address}")
        except Exception as exc:
            print(f"[multiplay] send failed ({address}): {exc}")


# ---------------------------------------------------------------------------
# Kalman Filter
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


# ---------------------------------------------------------------------------
# Data Structures
# ---------------------------------------------------------------------------
@dataclass
class TagState:
    last_distances: list  = field(default_factory=lambda: [0.0] * 8)
    raw_position:   tuple = None
    filt_position:  tuple = None
    last_update:    float = 0.0
    kalman: Kalman2D       = field(default_factory=Kalman2D)
    ghosts_inside: set     = field(default_factory=set)
    last_cue: str          = None


class SharedState:
    def __init__(self, n_tags):
        self.n_tags          = n_tags
        self.tags            = [TagState() for _ in range(n_tags)]
        self.row_color_index = list(range(n_tags))
        self.lock            = threading.Lock()
        self.frame_count     = 0
        self.start_time      = time.time()
        self.stop            = False
        self.tutorial_active = True   # while True, button presses don't dispel ghosts
        self.button_pressed  = False
        self.all_dispelled   = False


# ---------------------------------------------------------------------------
# OSC Handler
# ---------------------------------------------------------------------------
def make_osc_handler(state: SharedState, anchor_ids, anchor_positions_list,
                      multiplay_client: MultiplayClient = None):
    def handle_distances(address, *args):
        if len(args) < 9 or state.stop:
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
            tag.last_update    = time.time()

            if raw_pos is not None:
                tag.kalman.predict()
                fx, fy = tag.kalman.update(raw_pos[0], raw_pos[1])
                tag.raw_position  = raw_pos
                tag.filt_position = (fx, fy)

                current_ghosts = set()
                for zi, ghost in enumerate(Ghosts):
                    if ghost.get("active", True) and ptInGhost(tag.filt_position, ghost):
                        current_ghosts.add(zi)

                tag.ghosts_inside = current_ghosts

                # Proximity beeping — runs throughout the tutorial so the
                # player can practice reading the detector cues
                if multiplay_client and not state.all_dispelled:
                    dist    = nearest_ghost_distance(tag.filt_position)
                    new_cue = cue_for_distance(dist)
                    if new_cue != tag.last_cue:
                        if new_cue:
                            multiplay_client.trigger(new_cue)
                        else:
                            multiplay_client.stop_all()
                        tag.last_cue = new_cue
            else:
                tag.kalman.predict()

            state.frame_count += 1

    return handle_distances


# ---------------------------------------------------------------------------
# Integrated Live Game Tutorial Panel
# ---------------------------------------------------------------------------
class TutorialSystem:
    def __init__(self, parent_frame, on_complete_callback):
        self.frame = parent_frame
        self.on_complete = on_complete_callback
        self.current_step = 0

        self.steps = [
            {
                "title": "GHOST HUNTING 101 !!",
                "subtitle": "Get ready to master the art of ghost hunting!",
                "body": "ARE YOU UP FOR IT ?\n\n"
                        "If you are, grab your device and HAPPY HUNTING !!\n\n",
                "color": "#42a5f5"
            },
            {
                "title": "HOW TO HUNT: STEP 1",
                "subtitle": "Identify the Containment Fields",
                "body": "In the zone, there are Ghosts roaming around.\n\n"
                        "Walk towards them.\n\n"
                        "Your goal is to enter their containment fields.\n\n"
                        "Once you're in position, press your device's button to dispel the ghosts !!!",
                "color": "#ffeb3b"
            },
            {
                "title": "HOW TO HUNT: STEP 2",
                "subtitle": "Using Your Device",
                "body": "Take note: when your detector starts beeping, you’re getting closer!\n\n"
                        "The beeping gets <SUCCESSFUL> faster and more urgent the closer you "
                        "get to a ghost's containment field.\n\n"
                        "Once you're in position, press your device's button to dispel the ghosts !!!",
                "color": "#ffff00"
            },
            {
                "title": "HOW TO HUNT: STEP 3",
                "subtitle": "Systems nominal, filter arrays steady\n\n",
                "body": "Now without my help, keep moving around to figure out where the rest of the ghosts are!\n\n"
                        "Try it out below — walk to a ghost, listen for the beeping, and press the "
                        "button to dispel it.\n\n"
                        "Before we begin the official HUNT, ARE YOU READY ?\n\n"
                        "Click below to Start Hunting !!\n\n",
                "color": "#66bb6a"
            }
        ]

        self.build_ui()
        self.show_step(0)

    def build_ui(self):
        self.inner_box = tk.LabelFrame(
            self.frame,
            text=" INSTRUCTION CONTROL MODULE ",
            bg="#0d0d0d", fg="#ffffff", font=("Helvetica", 11, "bold"),
            bd=2, relief="groove", labelanchor="n"
        )
        self.inner_box.pack(fill="both", expand=True, padx=15, pady=15)

        self.canvas = tk.Canvas(self.inner_box, bg="#0d0d0d", highlightthickness=0)
        self.scrollbar = tk.Scrollbar(self.inner_box, orient="vertical", command=self.canvas.yview)

        self.scroll_content = tk.Frame(self.canvas, bg="#0d0d0d")
        self.scroll_content.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas_frame_window = self.canvas.create_window((0, 0), window=self.scroll_content, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.bind('<Configure>', lambda event: self.canvas.itemconfig(self.canvas_frame_window, width=event.width))

        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="top", fill="both", expand=True, padx=10, pady=10)

        self.title_lbl = tk.Label(
            self.scroll_content, text="", bg="#0d0d0d", fg="#ffffff",
            font=("Helvetica", 48, "bold"), justify="center", wraplength=1400
        )
        self.title_lbl.pack(pady=(10, 5), fill="x")

        self.sub_lbl = tk.Label(
            self.scroll_content, text="", bg="#0d0d0d", fg="#888888",
            font=("Helvetica", 42, "italic"), justify="center", wraplength=1400
        )
        self.sub_lbl.pack(pady=(0, 10), fill="x")

        self.body_lbl = tk.Text(
            self.scroll_content, bg="#0d0d0d", fg="#dddddd",
            font=("Courier", 39, "bold"), wrap="word",
            bd=0, highlightthickness=0, height=22
        )
        self.body_lbl.pack(fill="both", expand=True, padx=15, pady=10)

        self.body_lbl.tag_config("ominous", foreground="#ff1111", font=("Courier", 42, "bold"))
        self.body_lbl.tag_config("success", foreground="#00ff00", font=("Courier", 39, "bold"))

        # --- Live Status Strip: shows button + beeper state during practice ---
        self.status_frame = tk.Frame(self.scroll_content, bg="#0d0d0d")
        self.status_frame.pack(fill="x", padx=15, pady=(0, 10))

        self.button_indicator = tk.Label(
            self.status_frame, text="● BUTTON: idle", bg="#0d0d0d", fg="#666666",
            font=("Courier", 36, "bold")
        )
        self.button_indicator.pack(side="left", padx=(0, 20))

        self.beeper_indicator = tk.Label(
            self.status_frame, text="♪ DETECTOR: silent", bg="#0d0d0d", fg="#666666",
            font=("Courier", 36, "bold")
        )
        self.beeper_indicator.pack(side="left")

        self.ghost_status_lbl = tk.Label(
            self.scroll_content, text="", bg="#0d0d0d", fg="#aaaaaa",
            font=("Courier", 33, "bold"), justify="center", wraplength=1400
        )
        self.ghost_status_lbl.pack(pady=(0, 5), fill="x")

        self.control_frame = tk.Frame(self.inner_box, bg="#0d0d0d")
        self.control_frame.pack(side="bottom", fill="x", pady=10, padx=15)

        # Swapped SKIP out for a context-aware PREV step button mapping
        self.prev_btn = tk.Button(
            self.control_frame, text="< PREV STEP", bg="#1c1c1c", fg="#ffffff",
            font=("Helvetica", 36, "bold"), bd=1, relief="solid", padx=36, pady=15,
            command=self.prev_step
        )
        self.prev_btn.pack(side="left")

        self.next_btn = tk.Button(
            self.control_frame, text="NEXT STEP >", bg="#222222", fg="#ffffff",
            font=("Helvetica", 39, "bold"), bd=1, relief="solid", padx=60, pady=18,
            command=self.next_step
        )
        self.next_btn.pack(side="right")

    def show_step(self, index):
        step = self.steps[index]
        self.title_lbl.configure(text=step["title"], fg=step["color"])
        self.sub_lbl.configure(text=step["subtitle"])

        self.body_lbl.configure(state="normal")
        self.body_lbl.delete("1.0", tk.END)

        raw_body_text = step["body"]

        if "<CRITICAL>" in raw_body_text or "<SUCCESSFUL>" in raw_body_text:
            if "<CRITICAL>" in raw_body_text:
                parts = raw_body_text.split("<CRITICAL>")
                before_critical = parts[0]
                after_critical = parts[1]

                if "<SUCCESSFUL>" in before_critical:
                    sub_parts = before_critical.split("<SUCCESSFUL>")
                    self.body_lbl.insert(tk.END, sub_parts[0])
                    self.body_lbl.insert(tk.END, "successful", "success")
                    self.body_lbl.insert(tk.END, sub_parts[1])
                else:
                    self.body_lbl.insert(tk.END, before_critical)

                self.body_lbl.insert(tk.END, "CRITICAL", "ominous")

                if "<SUCCESSFUL>" in after_critical:
                    sub_parts = after_critical.split("<SUCCESSFUL>")
                    self.body_lbl.insert(tk.END, sub_parts[0])
                    self.body_lbl.insert(tk.END, "successful", "success")
                    self.body_lbl.insert(tk.END, sub_parts[1])
                else:
                    self.body_lbl.insert(tk.END, after_critical)
            else:
                parts = raw_body_text.split("<SUCCESSFUL>")
                self.body_lbl.insert(tk.END, parts[0])
                self.body_lbl.insert(tk.END, "successful", "success")
                self.body_lbl.insert(tk.END, parts[1])
        else:
            self.body_lbl.insert(tk.END, raw_body_text)

        self.body_lbl.configure(state="disabled")

        self.root_update_calls()
        self.canvas.yview_moveto(0)

        # Context visual updates based on index boundaries
        if index == 0:
            self.prev_btn.configure(state="disabled", fg="#555555")
        else:
            self.prev_btn.configure(state="normal", fg="#ffffff")

        if index == len(self.steps) - 1:
            self.next_btn.configure(text="START HUNTING!", bg=step["color"], fg="#000000")
        else:
            self.next_btn.configure(text="NEXT STEP >", bg="#222222", fg="#ffffff")

    def root_update_calls(self):
        try:
            self.scroll_content.update_idletasks()
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        except Exception:
            pass

    def prev_step(self):
        if self.current_step > 0:
            self.current_step -= 1
            self.show_step(self.current_step)

    def next_step(self):
        if self.current_step < len(self.steps) - 1:
            self.current_step += 1
            self.show_step(self.current_step)
        else:
            self.finish()

    def finish(self):
        self.frame.destroy()
        self.on_complete()

    # --- Live status updates, called from ViewerApp.update_loop ---
    def update_button_indicator(self, pressed):
        if pressed:
            self.button_indicator.configure(text="● BUTTON: PRESSED", fg="#00ff00")
        else:
            self.button_indicator.configure(text="● BUTTON: idle", fg="#666666")

    def update_beeper_indicator(self, cue):
        if cue is None:
            self.beeper_indicator.configure(text="♪ DETECTOR: silent", fg="#666666")
        else:
            cue_labels = {
                "/cue/4/go": "♪ DETECTOR: ON TARGET!!",
                "/cue/3/go": "♪ DETECTOR: very close",
                "/cue/2/go": "♪ DETECTOR: getting closer",
                "/cue/1/go": "♪ DETECTOR: far away",
            }
            self.beeper_indicator.configure(text=cue_labels.get(cue, "♪ DETECTOR: active"), fg="#ffeb3b")

    def update_ghost_status(self, remaining, total):
        if remaining == 0:
            self.ghost_status_lbl.configure(
                text=f"All {total} practice ghosts dispelled — nice work!", fg="#00ff00"
            )
        else:
            self.ghost_status_lbl.configure(
                text=f"Ghosts remaining: {remaining}/{total}", fg="#aaaaaa"
            )


# ---------------------------------------------------------------------------
# Viewer (Tkinter + matplotlib)
# ---------------------------------------------------------------------------
class ViewerApp:
    def __init__(self, root, state: SharedState, show_circles, fullscreen,
                 multiplay_client: MultiplayClient = None):
        self.root         = root
        self.state        = state
        self.show_circles = show_circles
        self.multiplay    = multiplay_client
        self.anchor_ids   = sorted(ANCHORS.keys())
        self.n_anchors    = len(self.anchor_ids)

        root.title("BU03 Live Tracker & Guidance Module — TUTORIAL")
        root.configure(bg="#000000")

        root.grid_rowconfigure(0, weight=1)
        root.grid_columnconfigure(0, weight=5)
        root.grid_columnconfigure(1, weight=4)

        # --- LEFT PANEL: matplotlib tracking grid ---
        self.left_container = tk.Frame(root, bg="#000000")
        self.left_container.grid(row=0, column=0, sticky="nsew")

        self.left_container.grid_rowconfigure(0, weight=1)
        self.left_container.grid_rowconfigure(1, weight=0)
        self.left_container.grid_columnconfigure(0, weight=1)

        self.plot_frame = tk.Frame(self.left_container, bg="#000000")
        self.plot_frame.grid(row=0, column=0, sticky="nsew")

        plt.style.use("dark_background")
        self.fig = Figure(figsize=(16, 9))
        self.fig.patch.set_facecolor("#000000")
        self.ax_plot = self.fig.add_subplot(111)

        x_min, x_max, y_min, y_max = VIEW_BOUNDS
        self.ax_plot.set_xlim(x_min, x_max)
        self.ax_plot.set_ylim(y_min, y_max)

        self.ax_plot.set_aspect("equal")
        self.ax_plot.grid(True, alpha=0.15)
        self.ax_plot.set_facecolor("#000000")

        self.fig.subplots_adjust(left=0.12, right=0.88, top=0.9, bottom=0.1)

        for aid, (ax_x, ax_y) in ANCHORS.items():
            self.ax_plot.plot(ax_x, ax_y, marker="^", markersize=11, color="#ffeb3b")
            self.ax_plot.annotate(f"A{aid}", (ax_x, ax_y), textcoords="offset points", xytext=(5, 5), color="#ffeb3b", fontsize=9)

        self.ghost_circles = []
        self.ghost_labels  = []
        for ghost in Ghosts:
            cx, cy = ghost["center"]
            circle = plt.Circle((cx, cy), ghost["radius"], fill=False, linewidth=2, linestyle="-.", edgecolor=ghost["color"], alpha=0.8)
            self.ax_plot.add_patch(circle)
            label = self.ax_plot.text(cx, cy, ghost["label"], color=ghost["color"], fontsize=10, ha="center", va="center", weight="bold")
            self.ghost_circles.append(circle)
            self.ghost_labels.append(label)

        self.row_dots = []
        self.row_circles_per_anchor = [[None] * self.n_anchors for _ in range(state.n_tags)]
        for i in range(state.n_tags):
            dot, = self.ax_plot.plot([], [], marker="o", markersize=10, color=TAG_COLORS[i], markeredgecolor="white")
            self.row_dots.append(dot)

        self.hud = self.ax_plot.text(0.02, 0.98, "", transform=self.ax_plot.transAxes, va="top", ha="left", color="white", fontsize=9, family="monospace")

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.plot_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        # Legend / Data Table layout
        self.table_frame = tk.Frame(self.left_container, bg="#000000")
        self.table_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)

        headers = ["Tag ID", "X (m)", "Y (m)", "Color Assignment"]
        for col, label in enumerate(headers):
            lbl = tk.Label(self.table_frame, text=label, bg="#1a1a1a", fg="white", font=("Helvetica", 10, "bold"), relief="solid", borderwidth=1)
            lbl.grid(row=0, column=col, sticky="nsew")
        for col in range(4):
            self.table_frame.grid_columnconfigure(col, weight=1, uniform="cols")

        self.id_labels, self.x_labels, self.y_labels, self.color_combos, self.color_swatches = [], [], [], [], []

        for r in range(state.n_tags):
            id_lbl = tk.Label(self.table_frame, text=f"T{r}", bg="#0b0b0b", fg=TAG_COLORS[r], font=("Helvetica", 11, "bold"), relief="solid", borderwidth=1)
            id_lbl.grid(row=r + 1, column=0, sticky="nsew")
            self.id_labels.append(id_lbl)

            x_lbl = tk.Label(self.table_frame, text="—", bg="#0b0b0b", fg="white", font=("Courier", 11), relief="solid", borderwidth=1)
            x_lbl.grid(row=r + 1, column=1, sticky="nsew")
            self.x_labels.append(x_lbl)

            y_lbl = tk.Label(self.table_frame, text="—", bg="#0b0b0b", fg="white", font=("Courier", 11), relief="solid", borderwidth=1)
            y_lbl.grid(row=r + 1, column=2, sticky="nsew")
            self.y_labels.append(y_lbl)

            color_cell = tk.Frame(self.table_frame, bg="#0b0b0b", relief="solid", borderwidth=1)
            color_cell.grid(row=r + 1, column=3, sticky="nsew")

            swatch = tk.Frame(color_cell, bg=TAG_COLORS[r], width=16, height=16)
            swatch.pack(side="left", padx=5, pady=2)
            self.color_swatches.append(swatch)

            combo = ttk.Combobox(color_cell, values=COLOR_NAMES, state="readonly", width=8, font=("Helvetica", 10))
            combo.set(COLOR_NAMES[r])
            combo.pack(side="left", padx=2, pady=2)
            combo.bind("<<ComboboxSelected>>", lambda event, row=r: self.on_color_changed(row))
            self.color_combos.append(combo)

        # --- RIGHT PANEL: Interactive Tutorial Sidebar Area ---
        self.sidebar_panel = tk.Frame(root, bg="#0a0a0a", width=900, bd=1, relief="solid")
        self.sidebar_panel.grid(row=0, column=1, sticky="nsew")
        self.sidebar_panel.pack_propagate(False)

        self.tutorial_module = TutorialSystem(self.sidebar_panel, on_complete_callback=self.expand_view_format)
        self.tutorial_module.canvas.master.bind("<Configure>", lambda e: self.tutorial_module.root_update_calls())

        root.bind("<KeyPress-q>", lambda e: self.shutdown())
        root.bind("<KeyPress-Q>", lambda e: self.shutdown())
        root.bind("<Escape>",     lambda e: self.shutdown())
        root.protocol("WM_DELETE_WINDOW", self.shutdown)

        self.root.update_idletasks()
        self.root.after(100, self.update_loop)

    def expand_view_format(self):
        """Removes the sidebar, unlocks the aspect ratio, and stretches the plot to fill 100% of the screen."""
        self.sidebar_panel.grid_forget()
        self.left_container.grid_forget()
        self.left_container.pack(fill="both", expand=True)

        self.ax_plot.set_aspect("auto")
        self.fig.subplots_adjust(left=0.0, right=1.0, top=1.0, bottom=0.15)

        self.root.update_idletasks()
        self.canvas.draw_idle()
        self.root.update()
        print("[tutorial] Tutorial complete — handing off to live hunt view.")

    def on_color_changed(self, row):
        chosen_name = self.color_combos[row].get()
        try:
            chosen_idx = COLOR_NAMES.index(chosen_name)
        except ValueError:
            return
        with self.state.lock:
            current = self.state.row_color_index[row]
            if chosen_idx == current:
                return
            other_row = None
            for r, c in enumerate(self.state.row_color_index):
                if r != row and c == chosen_idx:
                    other_row = r
                    break
            self.state.row_color_index[row] = chosen_idx
            if other_row is not None:
                self.state.row_color_index[other_row] = current
            snapshot = list(self.state.row_color_index)

        self.sync_color_widgets(snapshot)

    def sync_color_widgets(self, color_indices):
        for r, ci in enumerate(color_indices):
            self.color_combos[r].set(COLOR_NAMES[ci])
            self.color_swatches[r].configure(bg=TAG_COLORS[ci])
            self.id_labels[r].configure(fg=TAG_COLORS[ci])

    def update_loop(self):
        if self.state.stop:
            return

        with self.state.lock:
            snapshot = []
            for tag in self.state.tags:
                snapshot.append({
                    "filt":  tag.filt_position,
                    "dists": list(tag.last_distances),
                    "last":  tag.last_update,
                    "cue":   tag.last_cue,
                })
            total         = self.state.frame_count
            elapsed       = time.time() - self.state.start_time
            color_indices = list(self.state.row_color_index)
            button_state  = self.state.button_pressed

        now = time.time()

        for row, snap in enumerate(snapshot):
            color_idx = color_indices[row]
            color     = TAG_COLORS[color_idx]
            pos       = snap["filt"]
            stale     = (now - snap["last"] > 1.0) if snap["last"] else True

            self.row_dots[row].set_color(color)
            self.row_dots[row].set_markerfacecolor(color)
            if pos is not None and not stale:
                self.row_dots[row].set_data([pos[0]], [pos[1]])
            else:
                self.row_dots[row].set_data([], [])

            self.id_labels[row].configure(fg=color)
            if pos is not None and not stale:
                self.x_labels[row].configure(text=f"{pos[0]:.3f}")
                self.y_labels[row].configure(text=f"{pos[1]:.3f}")
            else:
                self.x_labels[row].configure(text="—")
                self.y_labels[row].configure(text="—")

            if self.show_circles:
                for slot, aid in enumerate(self.anchor_ids):
                    old = self.row_circles_per_anchor[row][slot]
                    if old is not None:
                        old.remove()
                        self.row_circles_per_anchor[row][slot] = None
                    if stale:
                        continue
                    d = snap["dists"][aid] if aid < len(snap["dists"]) else 0
                    if d <= 0.05:
                        continue
                    cx, cy = ANCHORS[aid]
                    circ = plt.Circle((cx, cy), d, fill=False, color=color, alpha=0.15, linewidth=1)
                    self.ax_plot.add_patch(circ)
                    self.row_circles_per_anchor[row][slot] = circ

        # Hide circles/labels for dispelled ghosts
        for zi, ghost in enumerate(Ghosts):
            active = ghost.get("active", True)
            self.ghost_circles[zi].set_visible(active)
            self.ghost_labels[zi].set_visible(active)

        rate   = total / elapsed if elapsed > 0 else 0
        active = sum(1 for s in snapshot if s["filt"] is not None and now - s["last"] < 1.0)
        self.hud.set_text(f"Frames: {total}\nRate:   {rate:5.1f} Hz\nActive: {active}/{self.state.n_tags}")

        # Update tutorial sidebar live indicators (only while sidebar exists)
        try:
            if self.tutorial_module.frame.winfo_exists():
                self.tutorial_module.update_button_indicator(button_state)
                latest_cue = None
                for s in snapshot:
                    if s["cue"] is not None:
                        latest_cue = s["cue"]
                self.tutorial_module.update_beeper_indicator(latest_cue)
                remaining = sum(1 for g in Ghosts if g.get("active", True))
                self.tutorial_module.update_ghost_status(remaining, len(Ghosts))
        except tk.TclError:
            pass

        self.canvas.draw_idle()
        self.root.after(50, self.update_loop)

    def shutdown(self):
        self.state.stop = True
        try:
            self.root.destroy()
        except tk.TclError:
            pass


# ---------------------------------------------------------------------------
# Execution Pipeline
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tags",       type=int, default=2)
    ap.add_argument("--port",       type=int, default=DEFAULT_PORT)
    ap.add_argument("--no-circles", action="store_true")
    ap.add_argument("--windowed",   action="store_true")
    args = ap.parse_args()

    if not 1 <= args.tags <= 8:
        sys.exit("[error] --tags must be 1–8")

    state = SharedState(n_tags=args.tags)
    for tag in state.tags:
        tag.kalman.dt = 0.10

    # GPIO button — used to dispel ghosts during the practice hunt
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    def pin_edge_callback(channel):
        is_pressed = not GPIO.input(channel)
        with state.lock:
            state.button_pressed = is_pressed

            if not is_pressed:
                return

            for tag_id, tag in enumerate(state.tags):
                if tag.filt_position is None:
                    continue
                for ghost in Ghosts:
                    if ghost.get("active", True) and ptInGhost(tag.filt_position, ghost):
                        print(f"\n🎯 HIT! Tag {tag_id} dispelled {ghost['label']}!")
                        ghost["active"] = False

            if all(not g.get("active", True) for g in Ghosts):
                state.all_dispelled = True
                print("\n✅ All practice ghosts dispelled — tutorial hunt complete!")

    GPIO.add_event_detect(BUTTON_PIN, GPIO.BOTH, callback=pin_edge_callback, bouncetime=200)

    anchor_ids            = sorted(ANCHORS.keys())
    anchor_positions_list = [ANCHORS[i] for i in anchor_ids]

    multiplay = MultiplayClient(MULTIPLAY_IP, MULTIPLAY_PORT)

    disp    = osc_dispatcher.Dispatcher()
    handler = make_osc_handler(state, anchor_ids, anchor_positions_list,
                                multiplay_client=multiplay)
    disp.map("/distances", handler)

    server        = osc_server.ThreadingOSCUDPServer(("0.0.0.0", args.port), disp)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    print(f"[tutorial] OSC server listening on port {args.port}")

    root = tk.Tk()
    if not args.windowed:
        try:
            root.attributes("-fullscreen", True)
        except tk.TclError:
            pass

    ViewerApp(root, state,
              show_circles=not args.no_circles,
              fullscreen=not args.windowed,
              multiplay_client=multiplay)

    try:
        root.mainloop()
    except KeyboardInterrupt:
        pass
    finally:
        state.stop = True
        if multiplay:
            multiplay.stop_all()
        server.shutdown()
        GPIO.cleanup()
        print("[tutorial] Shutdown complete.")


if __name__ == "__main__":
    main()