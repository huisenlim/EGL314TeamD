# display.py
import time
import math
import tkinter as tk
import game_logic
import tutorial_ui 
import lighting 
from reaper import ReaperController

class ViewerApp:
    def __init__(self, root, state, show_circles, fullscreen):
        self.root = root
        self.state = state
        self.show_circles = show_circles
        
        self.audio_controller = ReaperController()
        
        self.LIGHTING_SEQUENCE_ID = 1
        self.CUE_GREEN_WASH = 1.0
        
        # Configure Main Window for 1920x1080 target resolution
        self.root.title("Sequential Wave Tracker Field (Arena View)")
        self.root.geometry("1920x1080")
        self.root.configure(bg="#000000")
        
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=5) 
        self.root.grid_columnconfigure(1, weight=4) 
        
        self.game_frame = tk.Frame(self.root, bg="#000000")
        self.game_frame.grid(row=0, column=0, sticky="nsew")
        self.game_frame.grid_rowconfigure(0, weight=1)
        self.game_frame.grid_columnconfigure(0, weight=1)
        
        self.canvas_width = 800
        self.canvas_height = 800
        self.x_min, self.x_max, self.y_min, self.y_max = game_logic.VIEW_BOUNDS
        self.scale_x = self.canvas_width / (self.x_max - self.x_min)
        self.scale_y = self.canvas_height / (self.y_max - self.y_min)

        self.canvas = tk.Canvas(self.game_frame, width=self.canvas_width, height=self.canvas_height, bg="#000000", highlightthickness=0)
        self.canvas.grid(row=0, column=0, pady=10)
        
        table_frame = tk.Frame(self.game_frame, bg="#000000")
        table_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        
        for col, label in enumerate(["Slot / Phys ID", "X (m)", "Y (m)", "Color Matrix"]):
            lbl = tk.Label(table_frame, text=label, bg="#222222", fg="white", font=("Helvetica", 13, "bold"), padx=8, pady=6, relief="solid", borderwidth=1)
            lbl.grid(row=0, column=col, sticky="nsew")
        for col in range(4): table_frame.grid_columnconfigure(col, weight=1, uniform="cols")

        self.id_labels, self.x_labels, self.y_labels = [], [], []
        for r in range(state.n_tags):
            id_lbl = tk.Label(table_frame, text=f"Slot {r} (—)", bg="#111111", fg=game_logic.TAG_COLORS[r], font=("Helvetica", 14, "bold"), padx=8, pady=6, relief="solid", borderwidth=1)
            id_lbl.grid(row=r + 1, column=0, sticky="nsew")
            self.id_labels.append(id_lbl)
            
            x_lbl = tk.Label(table_frame, text="—", bg="#111111", fg="white", font=("Courier", 13), padx=8, pady=6, relief="solid", borderwidth=1)
            x_lbl.grid(row=r + 1, column=1, sticky="nsew")
            self.x_labels.append(x_lbl)
            
            y_lbl = tk.Label(table_frame, text="—", bg="#111111", fg="white", font=("Courier", 13), padx=8, pady=6, relief="solid", borderwidth=1)
            y_lbl.grid(row=r + 1, column=2, sticky="nsew")
            self.y_labels.append(y_lbl)
            
            swatch = tk.Frame(table_frame, bg=game_logic.TAG_COLORS[r], width=24, height=24)
            swatch.grid(row=r + 1, column=3, padx=8, pady=6)

        self.ghost_items = {} 
        self.tag_dots = []
        self.title_text = None
        self.ui_update_counter = 0 
        self.active_lit_ghosts = set()

        self.build_static_arena_layout()
        self.render_active_wave_shapes()
        
        # Embedded Tutorial Panel
        self.sidebar_panel = tk.Frame(self.root, bg="#0a0a0a", bd=1, relief="solid")
        self.sidebar_panel.grid(row=0, column=1, sticky="nsew")
        
        self.tutorial_module = tutorial_ui.TutorialSystem(
            self.sidebar_panel, 
            on_complete_callback=self.expand_view_format
        )

        # Separate Floating Timer Window
        self.timer_win = tk.Toplevel(self.root)
        self.timer_win.title("Game Controller & Timer HUD")
        self.timer_win.geometry("500x350+50+50")
        self.timer_win.configure(bg="#0a0a0a")
        
        self.timer_label = tk.Label(
            self.timer_win, text="READY", font=("Courier", 22, "bold"),
            bg="#0a0a0a", fg="#00ffff", justify="left", padx=20, pady=20
        )
        self.timer_label.pack(fill="both", expand=True)

        self.root.bind("<Escape>", lambda e: self.shutdown())
        self.root.protocol("WM_DELETE_WINDOW", self.shutdown)
        self.timer_win.protocol("WM_DELETE_WINDOW", self.shutdown)
        
        if fullscreen:
            try: self.root.attributes("-fullscreen", True)
            except tk.TclError: pass
            
        self.root.after(60, self.update_loop)

    def expand_view_format(self):
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=0)
        
        with self.state.lock:
            self.state.timer_active = True
            self.state.last_time = time.time()
            
        lighting.trigger_cue(self.LIGHTING_SEQUENCE_ID, self.CUE_GREEN_WASH)
        self.root.update_idletasks()

    def cx(self, x):
        return (x - self.x_min) * self.scale_x

    def cy(self, y):
        return self.canvas_height - ((y - self.y_min) * self.scale_y)

    def build_static_arena_layout(self):
        for i in range(int(self.x_min), int(self.x_max) + 1):
            px = self.cx(i)
            self.canvas.create_line(px, 0, px, self.canvas_height, fill="#222222", dash=(2, 4))
        for i in range(int(self.y_min), int(self.y_max) + 1):
            py = self.cy(i)
            self.canvas.create_line(0, py, self.canvas_width, py, fill="#222222", dash=(2, 4))

        for aid, (ax_x, ax_y) in game_logic.ANCHORS.items():
            px, py = self.cx(ax_x), self.cy(ax_y)
            self.canvas.create_polygon(px, py-10, px-10, py+10, px+10, py+10, fill="#ffeb3b", outline="white")
            self.canvas.create_text(px + 15, py + 15, text=f"A{aid}", fill="#ffeb3b", font=("Helvetica", 11))

        for i in range(self.state.n_tags):
            dot = self.canvas.create_oval(-20, -20, -20, -20, fill=game_logic.TAG_COLORS[i], outline="white", width=2)
            self.tag_dots.append(dot)

        self.title_text = self.canvas.create_text(self.canvas_width/2, 30, anchor="n", fill="#00ffff", font=("Helvetica", 14, "bold"), text="")

    def render_active_wave_shapes(self):
        for items in self.ghost_items.values():
            for item in items:
                self.canvas.delete(item)
        self.ghost_items.clear()
        
        for zi, ghost in enumerate(game_logic.Ghosts):
            if ghost.get("active", True) and ghost.get("wave") == game_logic.CURRENT_WAVE:
                px, py = self.cx(ghost["center"][0]), self.cy(ghost["center"][1])
                pr = ghost["radius"] * self.scale_x 
                
                circle = self.canvas.create_oval(px-pr, py-pr, px+pr, py+pr, outline=ghost["color"], width=3, dash=(6, 4))
                txt = self.canvas.create_text(px, py, text=ghost["label"], fill=ghost["color"], font=("Helvetica", 12, "bold"))
                self.ghost_items[zi] = (circle, txt)
                
        self.canvas.itemconfig(self.title_text, text=f"ACTIVE STAGE: WAVE {game_logic.CURRENT_WAVE} — Clear all targets!", fill="#00ffff")

    def force_instant_ui_refresh(self):
        self.render_active_wave_shapes()
        with self.state.lock:
            if self.state.game_won:
                self.canvas.itemconfig(self.title_text, text="GAME OVER — AREA CLEARED! YOU WIN!", fill="#00ff00")
            elif self.state.game_lost:
                self.canvas.itemconfig(self.title_text, text="MISSION FAILED — OUT OF TIME!", fill="#ff0000")

    def update_loop(self):
        if self.state.stop: return
        
        now = time.time()
        self.ui_update_counter += 1
        update_text_elements = (self.ui_update_counter % 8 == 0)

        with self.state.lock:
            if self.state.timer_active and not self.state.game_won and not self.state.game_lost:
                delta = now - self.state.last_time
                self.state.time_left -= delta
                self.state.last_time = now
                
                if self.state.time_left <= 0:
                    self.state.time_left = 0
                    self.state.game_lost = True
                    self.state.timer_active = False
                    self.canvas.itemconfig(self.title_text, text="MISSION FAILED — OUT OF TIME!", fill="#ff0000")

            snapshot = [{"filt": t.filt_position, "last": t.last_update} for t in self.state.tags]
            total = self.state.frame_count
            elapsed = time.time() - self.state.start_time
            phys_ids = list(self.state.row_color_index)
            btn_pressed = self.state.button_pressed
            time_left_str = f"{max(0.0, self.state.time_left):.1f}s"

        current_lit_ghosts = set()
        min_dist_to_ghost = float('inf')

        for row, snap in enumerate(snapshot):
            pos = snap["filt"]
            stale = (now - snap["last"] > 1.0) if snap["last"] else True
            
            if pos and not stale:
                px, py = self.cx(pos[0]), self.cy(pos[1])
                self.canvas.coords(self.tag_dots[row], px-8, py-8, px+8, py+8)
                
                for zi, ghost in enumerate(game_logic.Ghosts):
                    if ghost.get("active", True) and ghost.get("wave") == game_logic.CURRENT_WAVE:
                        gx, gy = ghost["center"]
                        dist = math.hypot(pos[0] - gx, pos[1] - gy)
                        
                        if dist < min_dist_to_ghost:
                            min_dist_to_ghost = dist
                            
                        if game_logic.ptInGhost(pos, ghost):
                            current_lit_ghosts.add(zi)
            else:
                self.canvas.coords(self.tag_dots[row], -20, -20, -20, -20)
                
            if update_text_elements:
                p_id = phys_ids[row]
                self.id_labels[row].configure(text=f"Slot {row} (ID: {p_id})" if p_id != -1 else f"Slot {row} (—)")
                if pos and not stale:
                    self.x_labels[row].configure(text=f"{pos[0]:.3f}")
                    self.y_labels[row].configure(text=f"{pos[1]:.3f}")
                else:
                    self.x_labels[row].configure(text="—")
                    self.y_labels[row].configure(text="—")

        if self.state.timer_active and not self.state.game_won and not self.state.game_lost:
            self.audio_controller.update_proximity(min_dist_to_ghost)

        if self.state.timer_active:
            for zi in current_lit_ghosts - self.active_lit_ghosts:
                lighting.set_ghost_light(zi, turn_on=True)
            for zi in self.active_lit_ghosts - current_lit_ghosts:
                lighting.set_ghost_light(zi, turn_on=False)
            self.active_lit_ghosts = current_lit_ghosts

        if update_text_elements:
            try:
                if hasattr(self, 'tutorial_module') and self.tutorial_module.frame.winfo_exists():
                    self.tutorial_module.update_button_indicator(btn_pressed)
                    active_ghosts = [g for g in game_logic.Ghosts if g.get("wave") == game_logic.CURRENT_WAVE and g.get("active", True)]
                    remaining_count = len(active_ghosts)
                    total_wave_count = sum(1 for g in game_logic.Ghosts if g.get("wave") == game_logic.CURRENT_WAVE)
                    self.tutorial_module.update_ghost_status(remaining_count, total_wave_count)
            except tk.TclError:
                pass 

            rate = total / elapsed if elapsed > 0 else 0
            active = sum(1 for s in snapshot if s["filt"] is not None and now - s["last"] < 1.0)
            
            hud_str = (
                f"Time Left:  {time_left_str}\n"
                f"Wave Track: {game_logic.CURRENT_WAVE}/3\n"
                f"Rate:       {rate:5.1f} Hz\n"
                f"Active:     {active}/{self.state.n_tags}\n"
                f"Pin 18:     {'PRESSED' if btn_pressed else 'OPEN'}"
            )
            
            # Update dedicated timer HUD window
            if self.timer_win.winfo_exists():
                timer_color = "#ff5252" if (self.state.time_left < 30.0 and self.state.timer_active) else "#00ffff"
                self.timer_label.configure(text=hud_str, fg=timer_color)
        
        self.root.after(60, self.update_loop)

    def shutdown(self):
        self.state.stop = True
        for zi in list(self.active_lit_ghosts):
            lighting.set_ghost_light(zi, turn_on=False)
        try: self.timer_win.destroy()
        except tk.TclError: pass
        try: self.root.destroy()
        except tk.TclError: pass