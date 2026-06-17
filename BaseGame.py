"""
game.py  —  OSC Receiver + Trilateration + Kalman Filter + Visualizer
======================================================================
Runs on the "game" Pi that drives the display.

Listens for OSC messages sent by uart.py:
    /distances  <tag_id:int> <d0:float> ... <d7:float>

For each incoming frame it:
  1. Runs multilateration (trilaterate_2d) to get a raw (x, y) position.
  2. Smooths it through a per-tag Kalman2D filter.
  3. Updates a live Tkinter / matplotlib visualizer (identical to the
     original viewer).

Run:
    python3 game.py --tags 2
    python3 game.py --tags 2 --port 5005 --windowed
"""

import argparse
import pygame
import csv
import sys
import threading
#import RPi.GPIO as GPIO
import socket
import time
import tkinter as tk
from tkinter import ttk
from dataclasses import dataclass, field

import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt #plt is an alias for pyplot package
import matplotlib.patches as mpatches
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from pythonosc import dispatcher as osc_dispatcher
from pythonosc import osc_server

# ---------------------------------------------------------------------------
# Anchor layout and view config  (must match uart.py)
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
# Ghosts
# ---------------------------------------------------------------------------
GhostHitTol = 0.0 #hit tolerance

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

beepLvl = [
    {
        "lv4": 0,
        "lv3": 0.25,
        "lv2": 0.5,
        "lv1": 0.75
     }
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
# Trilateration (linear least-squares multilateration — no numpy needed)
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

# ---------------------------------------------------------------------------
# Ghost detection
# ---------------------------------------------------------------------------
def ptInGhost(point, ghost):
    if point is None:
        return False

    px, py = point
    zx, zy = ghost["center"]
    r = ghost["radius"] + GhostHitTol

    dx = px - zx
    dy = py - zy   # calculates tag dist from center of ghost

    return (dx * dx + dy * dy) <= (r * r)  # checks if tag is in ghost
# ---------------------------------------------------------------------------
# Ghost distance beep sect
# ---------------------------------------------------------------------------
def send_message(mpIP, mpPort, Message):

  try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    MESSAGE = bytes(Message, 'UTF-8')
    sock.sendto(MESSAGE, (mpIP, mpPort))
    sock.close()
    print(f'messsage sent: {Message}')
  except:
    print(f'message not sent: {Message}')


if __name__ == "__main__":
# UDP_IP is target IP address
  mpIP = "192.168.254.173" #Local Host Address
  mpPORT = 5005
  beepL1 = "/cue/1/go" # Trigger Cue 1
  beepL2 = "/cue/2/go" # Trigger Cue 2
  beepL3 = "/cue/3/go" # Trigger Cue 3
  beepL4 = "/cue/4/go" # Trigger Cue 4
  stopcue = "/cue/stop"

send_message(mpIP, mpPORT, beepL4)

def ptFromGhost(point, ghost, beep):
    if point is None:
        return False

    px, py = point
    zx, zy = ghost["center"]
    beep4 = ghost["radius"] + beep["lv4"]
    beep3 = ghost["radius"] + beep["lv3"]
    beep2 = ghost["radius"] + beep["lv2"]
    beep1 = ghost["radius"] + beep["lv1"]

    dx = px - zx
    dy = py - zy   # calculates tag dist from center of ghost

    if (dx * dx + dy * dy) <= (beep4 * beep4):
        send_message(mpIP, mpPORT, beepL4)
    elif (dx * dx + dy * dy) <= (beep3 * beep3):
        send_message(mpIP, mpPORT, beepL3)
    elif (dx * dx + dy * dy) <= (beep2 * beep2):
        send_message(mpIP, mpPORT, beepL2)
    elif (dx * dx + dy * dy) <= (beep1 * beep1):
        send_message(mpIP, mpPORT, beepL1)
    else:
        send_message(mpIP, mpPORT, beepL1)

# ---------------------------------------------------------------------------
# Kalman filter (position + velocity, 2-D)
# ---------------------------------------------------------------------------
class Kalman2D:
    def __init__(self, dt=0.10, q=0.12, r=1.1):
        self.dt = dt    # distance travelled prediction
        self.q  = q     # process noise
        self.r  = r     # measurement noise
        self.state = [0.0, 0.0, 0.0, 0.0]
        self.P = [[1.0, 0, 0, 0], [0, 1.0, 0, 0],
                [0, 0, 1.0, 0], [0, 0, 0, 1.0]]
        self.initialized = False

    def predict(self):     # Prediction based on velocity
        if not self.initialized:      # If not initialised, return self. (no prediction required to be carried out) exit early.
            return
        self.state[0] += self.state[2] * self.dt      # vx * dt = distance travelled in x
        self.state[1] += self.state[3] * self.dt      # vy * dt = distance travelled in y
        for i in range(4):
            self.P[i][i] += self.q     # 'p' is uncertainty. this function is increasing the uncertainty of the prediction. (higher more uncertain)


    def update(self, mx, my):
        if not self.initialized:       # If not initialised, return the given x and y distance valuie. (no prediction carried out)
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
# Per-tag state and shared state container
# ---------------------------------------------------------------------------
@dataclass
# Stores per-tag information
class TagState:
    last_distances: list = field(default_factory=lambda: [0.0] * 8)
    raw_position:   tuple = None    # unfiltered (x, y) position from triangulation
    filt_position:  tuple = None    # Kalman-filtered (x, y) position
    last_update:    float = 0.0     # Timestamp
    kalman: Kalman2D = field(default_factory=Kalman2D)   # Kalman filter instance
    ghosts_inside: set = field(default_factory=set)  # store ghost radii for each tag individually, and when new tag is added, default set is empty 

# Thread-safe container for all tags
class SharedState:
    def __init__(self, n_tags):
        self.n_tags = n_tags
        self.tags   = [TagState() for _ in range(n_tags)]
        self.row_color_index = list(range(n_tags))
        self.lock   = threading.Lock()
        self.frame_count = 0
        self.start_time  = time.time()
        self.stop = False

# ---------------------------------------------------------------------------
# OSC handler — called from the OSC server thread for every /distances message
# ---------------------------------------------------------------------------
def make_osc_handler(state: SharedState, anchor_ids, anchor_positions_list,
                    csv_writer=None):
    def handle_distances(address, *args):
        # args = [tag_id, d0, d1, ..., d7]
        if len(args) < 9:
            print(f"[osc] malformed message (got {len(args)} args)")
            return

        tag_id    = int(args[0])
        distances = [float(v) for v in args[1:9]]

        if tag_id >= state.n_tags:
            return   # ignore tags beyond what we're tracking

        tag = state.tags[tag_id]

        # Trilateration
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

                # --- ghost detection(per tag) ---

                current_ghosts = set()                            # checks ghosts tht are occupied by tags

                for zi, ghost in enumerate(Ghosts):                # checking each ghost
                    if ptInGhost(tag.filt_position, ghost):   # takes tag position and check if tag is in ghost
                        current_ghosts.add(zi)                    # stores ghost id if tag is in the ghost

                entered = current_ghosts - tag.ghosts_inside       # comparing tag positions so see if it entered a new ghost
                exited  = tag.ghosts_inside - current_ghosts

                for zi in entered:
                    print(f"Tag {tag_id} ENTERED "
                        f"{Ghosts[zi]['label']}")

                for zi in exited:
                    print(f"Tag {tag_id} EXITED "
                        f"{Ghosts[zi]['label']}")

                tag.ghosts_inside = current_ghosts
            else:
                tag.kalman.predict()
            state.frame_count += 1
            #csv_color_idx = state.row_color_index[tag_id]

    return handle_distances


# ---------------------------------------------------------------------------
# Viewer  (Tkinter + matplotlib — identical to original viewer3_annotated.py)
# ---------------------------------------------------------------------------
class ViewerApp:
    def __init__(self, root, state: SharedState, show_circles, fullscreen):
        self.root         = root
        self.state        = state
        self.show_circles = show_circles
        self.anchor_ids   = sorted(ANCHORS.keys())
        self.n_anchors    = len(self.anchor_ids)

        root.title("BU03 Live Tracker — game.py")
        root.configure(bg="#000000")

        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        root.grid_rowconfigure(0, weight=5)
        root.grid_rowconfigure(1, weight=1)
        root.grid_columnconfigure(0, weight=1)

        # --- matplotlib plot (top) ---
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
        self.ax_plot.set_xlabel("X (m)")
        self.ax_plot.set_ylabel("Y (m)")
        self.ax_plot.grid(True, alpha=0.2)
        self.ax_plot.set_title("UWB Live Tracker — press Q to quit")
        self.ax_plot.set_facecolor("#000000")

        for aid, (ax_x, ax_y) in ANCHORS.items():
            self.ax_plot.plot(ax_x, ax_y, marker="^", markersize=14,
                            color="#ffeb3b", markeredgecolor="white")
            self.ax_plot.annotate(f"A{aid}", (ax_x, ax_y),
                                textcoords="offset points",
                                xytext=(8, 8), color="#ffeb3b", fontsize=11)
        # --- ghost visual ---
        for ghost in Ghosts:
            cx, cy = ghost["center"]

            circle = mpatches.Circle(
                (cx, cy),
                ghost["radius"],
                fill=False,
                linewidth=3,
                linestyle="-.",
                edgecolor=ghost["color"],
                alpha=0.9,
            )

            self.ax_plot.add_patch(circle)

            # ghost label
            self.ax_plot.text(
                cx,
                cy,
                ghost["label"],
                color=ghost["color"],
                fontsize=11,
                ha="center",
                va="center",
                weight="bold",
            )

        self.row_dots = []
        self.row_circles_per_anchor = [[None] * self.n_anchors
                                    for _ in range(state.n_tags)]
        for i in range(state.n_tags):
            dot, = self.ax_plot.plot([], [], marker="o", markersize=10,
                                    color=TAG_COLORS[i],
                                    markeredgecolor="white", linewidth=0)
            self.row_dots.append(dot)

        self.hud = self.ax_plot.text(
            0.02, 0.98, "", transform=self.ax_plot.transAxes,
            va="top", ha="left", color="white",
            fontsize=10, family="monospace",
            bbox=dict(facecolor="black", alpha=0.5, edgecolor="none"),
        )

        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        # --- table with dropdowns (bottom) ---
        table_frame = tk.Frame(root, bg="#000000")
        table_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

        headers = ["Tag ID", "X (m)", "Y (m)", "Color"]
        for col, label in enumerate(headers):
            lbl = tk.Label(
                table_frame, text=label,
                bg="#222222", fg="white",
                font=("Helvetica", 13, "bold"),
                padx=8, pady=6, relief="solid", borderwidth=1,
            )
            lbl.grid(row=0, column=col, sticky="nsew")

        for col in range(4):
            table_frame.grid_columnconfigure(col, weight=1, uniform="cols")

        self.id_labels    = []
        self.x_labels     = []
        self.y_labels     = []
        self.color_combos = []
        self.color_swatches = []

        for r in range(state.n_tags):
            id_lbl = tk.Label(
                table_frame, text=f"T{r}",
                bg="#111111", fg=TAG_COLORS[r],
                font=("Helvetica", 14, "bold"),
                padx=8, pady=6, relief="solid", borderwidth=1,
            )
            id_lbl.grid(row=r + 1, column=0, sticky="nsew")
            self.id_labels.append(id_lbl)

            x_lbl = tk.Label(
                table_frame, text="—",
                bg="#111111", fg="white",
                font=("Courier", 13),
                padx=8, pady=6, relief="solid", borderwidth=1,
            )
            x_lbl.grid(row=r + 1, column=1, sticky="nsew")
            self.x_labels.append(x_lbl)

            y_lbl = tk.Label(
                table_frame, text="—",
                bg="#111111", fg="white",
                font=("Courier", 13),
                padx=8, pady=6, relief="solid", borderwidth=1,
            )
            y_lbl.grid(row=r + 1, column=2, sticky="nsew")
            self.y_labels.append(y_lbl)

            color_cell = tk.Frame(
                table_frame, bg="#111111",
                relief="solid", borderwidth=1,
            )
            color_cell.grid(row=r + 1, column=3, sticky="nsew")

            swatch = tk.Frame(color_cell, bg=TAG_COLORS[r], width=24, height=24)
            swatch.pack(side="left", padx=8, pady=6)
            swatch.pack_propagate(False)
            self.color_swatches.append(swatch)

            combo = ttk.Combobox(
                color_cell, values=COLOR_NAMES,
                state="readonly", width=10,
                font=("Helvetica", 12),
            )
            combo.set(COLOR_NAMES[r])
            combo.pack(side="left", padx=4, pady=6)
            combo.bind("<<ComboboxSelected>>",
                    lambda event, row=r: self.on_color_changed(row))
            self.color_combos.append(combo)

        root.bind("<KeyPress-q>", lambda e: self.shutdown())
        root.bind("<KeyPress-Q>", lambda e: self.shutdown())
        root.bind("<Escape>",     lambda e: self.shutdown())
        root.protocol("WM_DELETE_WINDOW", self.shutdown)

        if fullscreen:
            try:
                root.attributes("-fullscreen", True)
            except tk.TclError as e:
                print(f"[warn] could not enter fullscreen: {e}")

        self.root.after(100, self.update_loop)

    # --- color dropdown logic ---
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

        names = [COLOR_NAMES[i] for i in snapshot]
        if other_row is not None:
            print(f"Row {row} -> {chosen_name}; row {other_row} swapped to "
                f"{names[other_row]}.")
        else:
            print(f"Row {row} -> {chosen_name}.")
        self.sync_color_widgets(snapshot)

    def sync_color_widgets(self, color_indices):
        for r, ci in enumerate(color_indices):
            self.color_combos[r].set(COLOR_NAMES[ci])
            self.color_swatches[r].configure(bg=TAG_COLORS[ci])
            self.id_labels[r].configure(fg=TAG_COLORS[ci])

    # --- main display refresh (called every ~66 ms from Tk event loop) ---
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
                })
            total         = self.state.frame_count
            elapsed       = time.time() - self.state.start_time
            color_indices = list(self.state.row_color_index)

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
                    circ = mpatches.Circle((cx, cy), d, fill=False,
                                        color=color, alpha=0.25, linewidth=1)
                    self.ax_plot.add_patch(circ)
                    self.row_circles_per_anchor[row][slot] = circ

        for r, ci in enumerate(color_indices):
            if self.color_swatches[r].cget("bg") != TAG_COLORS[ci]:
                self.color_swatches[r].configure(bg=TAG_COLORS[ci])
            if self.color_combos[r].get() != COLOR_NAMES[ci]:
                self.color_combos[r].set(COLOR_NAMES[ci])

        rate   = total / elapsed if elapsed > 0 else 0
        active = sum(1 for s in snapshot
                    if s["filt"] is not None and now - s["last"] < 1.0)
        colors_str = " ".join(
            f"T{i}={COLOR_NAMES[color_indices[i]]}"
            for i in range(self.state.n_tags)
        )
        self.hud.set_text(
            f"frames: {total}\n"
            f"rate:   {rate:5.1f} Hz\n"
            f"active: {active}/{self.state.n_tags}\n"
            f"colors: {colors_str}"
        )

        self.canvas.draw_idle()
        self.root.after(66, self.update_loop)

    def shutdown(self):
        self.state.stop = True
        try:
            self.root.destroy()
        except tk.TclError:
            pass


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(
        description="Receive UWB distances via OSC, trilaterate, and visualize.")
    ap.add_argument("--tags", type=int, default=2,
                    help="Number of active tags (1..8). Default: 2.")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT,
                    help=f"UDP port to listen on. Default: {DEFAULT_PORT}")
    ap.add_argument("--csv", type=str, default=None,
                    help="If set, log per-frame data to this CSV file.")
    ap.add_argument("--no-circles", action="store_true",
                    help="Hide distance circles (faster rendering).")
    ap.add_argument("--windowed", action="store_true",
                    help="Don't enter fullscreen mode.")
    args = ap.parse_args()

    if not 1 <= args.tags <= 8:
        print("--tags must be between 1 and 8")
        sys.exit(1)

    state = SharedState(n_tags=args.tags)
    for tag in state.tags:
        tag.kalman.dt = 0.10

    anchor_ids             = sorted(ANCHORS.keys())
    anchor_positions_list  = [ANCHORS[i] for i in anchor_ids]

    # Optional CSV
    csv_file   = None
    csv_writer = None
    if args.csv:
        csv_file   = open(args.csv, "w", newline="")
        csv_writer = csv.writer(csv_file)
        header  = ["timestamp", "tag_id", "color"]
        header += [f"d{i}_m" for i in anchor_ids]
        header += ["raw_x", "raw_y", "filt_x", "filt_y"]
        csv_writer.writerow(header)

    # Build OSC dispatcher and start server thread
    disp = osc_dispatcher.Dispatcher()
    handler = make_osc_handler(state, anchor_ids, anchor_positions_list,
                            csv_writer)
    disp.map("/distances", handler)

    server = osc_server.ThreadingOSCUDPServer(("0.0.0.0", args.port), disp)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    print(f"[game] Listening for OSC on UDP port {args.port}")
    print(f"[game] Tracking {args.tags} tag(s)")
    print(f"[game] Anchors: {ANCHORS}")
    print(f"[game] View bounds: {VIEW_BOUNDS}")
    if args.csv:
        print(f"[game] Logging to: {args.csv}")
    print("[game] Press Q in the window to quit.\n")

    root = tk.Tk()
    app  = ViewerApp(root, state,
                    show_circles=not args.no_circles,
                    fullscreen=not args.windowed)

    try:
        root.mainloop()
    except KeyboardInterrupt:
        pass
    finally:
        state.stop = True
        server.shutdown()
        time.sleep(0.3)
        if csv_file:
            csv_file.close()
            print(f"[game] Wrote {args.csv}")


if __name__ == "__main__":
    main()
