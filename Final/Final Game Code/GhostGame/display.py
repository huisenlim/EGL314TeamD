import time
import math
import tkinter as tk
import game_logic
import lighting 
from reaper import ReaperController

class ViewerApp:
    def __init__(self, root, state, show_circles, fullscreen, 
                 on_tutorial_callback=None,
                 on_start_callback=None, on_yes_callback=None, 
                 on_no_callback=None, on_continue_callback=None, 
                 on_end_game_callback=None):
        self.root = root
        self.state = state
        self.show_circles = show_circles
        self.on_tutorial_callback = on_tutorial_callback
        self.on_start_callback = on_start_callback
        self.on_yes_callback = on_yes_callback
        self.on_no_callback = on_no_callback
        self.on_continue_callback = on_continue_callback
        self.on_end_game_callback = on_end_game_callback
        
        self.audio_controller = ReaperController()
        
        # Configure Main Window
        self.root.title("Interactive Question Arena Tracker")
        self.root.geometry("1920x1080")
        self.root.configure(bg="#000000")
        
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1) 
        
        self.game_frame = tk.Frame(self.root, bg="#000000")
        self.game_frame.grid(row=0, column=0, sticky="nsew")
        self.game_frame.grid_rowconfigure(0, weight=1)
        self.game_frame.grid_columnconfigure(0, weight=1)
        
        self.canvas_width = 850
        self.canvas_height = 700
        self.x_min, self.x_max, self.y_min, self.y_max = game_logic.VIEW_BOUNDS
        self.scale_x = self.canvas_width / (self.x_max - self.x_min)
        self.scale_y = self.canvas_height / (self.y_max - self.y_min)

        self.canvas = tk.Canvas(self.game_frame, width=self.canvas_width, height=self.canvas_height, bg="#000000", highlightthickness=0)
        self.canvas.grid(row=0, column=0, pady=5)
        
        # ───────── ON-SCREEN ACTION BUTTON CONTROLS ─────────
        self.btn_control_frame = tk.Frame(self.game_frame, bg="#000000")
        self.btn_control_frame.grid(row=1, column=0, pady=5)

        self.tutorial_btn = tk.Button(
            self.btn_control_frame, text="🎓 START TUTORIAL", bg="#ab47bc", fg="white",
            font=("Helvetica", 18, "bold"), width=16, height=1, relief="raised", bd=3,
            command=self.trigger_tutorial
        )
        self.tutorial_btn.pack(side="left", padx=15)

        self.start_btn = tk.Button(
            self.btn_control_frame, text="▶ START GAME", bg="#ff9800", fg="white",
            font=("Helvetica", 18, "bold"), width=16, height=1, relief="raised", bd=3,
            command=self.trigger_start
        )
        self.start_btn.pack(side="left", padx=15)

        self.yes_btn = tk.Button(
            self.btn_control_frame, text="✔ YES", bg="#2e7d32", fg="white",
            font=("Helvetica", 18, "bold"), width=12, height=1, relief="raised", bd=3,
            command=self.trigger_yes
        )

        self.no_btn = tk.Button(
            self.btn_control_frame, text="✖ NO", bg="#c62828", fg="white",
            font=("Helvetica", 18, "bold"), width=12, height=1, relief="raised", bd=3,
            command=self.trigger_no
        )

        self.continue_btn = tk.Button(
            self.btn_control_frame, text="CONTINUE ➔", bg="#0288d1", fg="white",
            font=("Helvetica", 18, "bold"), width=16, height=1, relief="raised", bd=3,
            command=self.trigger_continue
        )

        self.end_game_btn = tk.Button(
            self.btn_control_frame, text="🛑 END GAME", bg="#d32f2f", fg="white",
            font=("Helvetica", 18, "bold"), width=16, height=1, relief="raised", bd=3,
            command=self.trigger_end_game
        )
        # ──────────────────────────────────────────────────────
        
        table_frame = tk.Frame(self.game_frame, bg="#000000")
        table_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)
        
        for col, label in enumerate(["Slot / Phys ID", "X (m)", "Y (m)", "Color Matrix"]):
            lbl = tk.Label(table_frame, text=label, bg="#222222", fg="white", font=("Helvetica", 11, "bold"), padx=4, pady=2, relief="solid", borderwidth=1)
            lbl.grid(row=0, column=col, sticky="nsew")
        for col in range(4): table_frame.grid_columnconfigure(col, weight=1, uniform="cols")

        self.id_labels, self.x_labels, self.y_labels = [], [], []
        
        # Display rows for up to 6 tags/anchors
        for r in range(state.n_tags):
            color = game_logic.TAG_COLORS[r % len(game_logic.TAG_COLORS)]
            
            id_lbl = tk.Label(table_frame, text=f"Slot {r} (—)", bg="#111111", fg=color, font=("Helvetica", 11, "bold"), padx=4, pady=2, relief="solid", borderwidth=1)
            id_lbl.grid(row=r + 1, column=0, sticky="nsew")
            self.id_labels.append(id_lbl)
            
            x_lbl = tk.Label(table_frame, text="—", bg="#111111", fg="white", font=("Courier", 11), padx=4, pady=2, relief="solid", borderwidth=1)
            x_lbl.grid(row=r + 1, column=1, sticky="nsew")
            self.x_labels.append(x_lbl)
            
            y_lbl = tk.Label(table_frame, text="—", bg="#111111", fg="white", font=("Courier", 11), padx=4, pady=2, relief="solid", borderwidth=1)
            y_lbl.grid(row=r + 1, column=2, sticky="nsew")
            self.y_labels.append(y_lbl)
            
            swatch = tk.Frame(table_frame, bg=color, width=16, height=16)
            swatch.grid(row=r + 1, column=3, padx=4, pady=2)

        self.ghost_items = {} 
        self.tag_dots = []
        self.title_text = None
        self.ui_update_counter = 0 
        self.active_lit_ghosts = set()

        self.build_static_arena_layout()
        self.canvas.itemconfig(self.title_text, text="PRESS 'START TUTORIAL' OR 'START GAME'", fill="#ff9800")

        self.root.bind("<Escape>", lambda e: self.shutdown())
        self.root.protocol("WM_DELETE_WINDOW", self.shutdown)
        
        if fullscreen:
            try: self.root.attributes("-fullscreen", True)
            except tk.TclError: pass
            
        self.root.after(60, self.update_loop)

    def trigger_tutorial(self):
        self.canvas.itemconfig(self.title_text, text="TUTORIAL MODE ACTIVE", fill="#ab47bc")
        if self.on_tutorial_callback:
            self.on_tutorial_callback()

    def trigger_start(self):
        self.tutorial_btn.pack_forget()
        self.start_btn.pack_forget()
        self.yes_btn.pack(side="left", padx=20)
        self.no_btn.pack(side="left", padx=20)
        self.render_active_wave_shapes()
        if self.on_start_callback:
            self.on_start_callback()

    def trigger_yes(self):
        if self.on_yes_callback:
            self.on_yes_callback()

    def trigger_no(self):
        if self.on_no_callback:
            self.on_no_callback()

    def trigger_continue(self):
        if self.on_continue_callback:
            self.on_continue_callback()

    def trigger_end_game(self):
        if self.on_end_game_callback:
            self.on_end_game_callback()

    def show_continue_state(self):
        """Hides YES/NO buttons and displays the CONTINUE button."""
        self.yes_btn.pack_forget()
        self.no_btn.pack_forget()
        self.continue_btn.pack(side="left", padx=20)
        self.canvas.itemconfig(self.title_text, text=f"QUESTION {game_logic.CURRENT_QUESTION} CLEARED! PRESS CONTINUE", fill="#00ff00")

    def show_end_game_state(self):
        """Hides YES/NO/CONTINUE buttons and displays the END GAME button."""
        self.yes_btn.pack_forget()
        self.no_btn.pack_forget()
        self.continue_btn.pack_forget()
        self.end_game_btn.pack(side="left", padx=20)
        self.canvas.itemconfig(self.title_text, text="GAME COMPLETE! ALL QUESTIONS CLEARED! PRESS END GAME TO EXIT", fill="#00ff00")

    def reset_to_question_state(self):
        """Hides CONTINUE button and brings back YES/NO buttons for the next question."""
        self.continue_btn.pack_forget()
        self.yes_btn.pack(side="left", padx=20)
        self.no_btn.pack(side="left", padx=20)
        self.render_active_wave_shapes()

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
            self.canvas.create_text(px + 15, py + 15, text=f"A{aid}", fill="#ffeb3b", font=("Helvetica", 11, "bold"))

        for i in range(self.state.n_tags):
            color = game_logic.TAG_COLORS[i % len(game_logic.TAG_COLORS)]
            dot = self.canvas.create_oval(-20, -20, -20, -20, fill=color, outline="white", width=2)
            self.tag_dots.append(dot)

        self.title_text = self.canvas.create_text(self.canvas_width/2, 25, anchor="n", fill="#00ffff", font=("Helvetica", 15, "bold"), text="")

    def render_active_wave_shapes(self):
        for items in self.ghost_items.values():
            for item in items:
                self.canvas.delete(item)
        self.ghost_items.clear()
        
        for zi, ghost in enumerate(game_logic.Ghosts):
            if ghost.get("active", True) and ghost.get("question") == game_logic.CURRENT_QUESTION:
                px, py = self.cx(ghost["center"][0]), self.cy(ghost["center"][1])
                pr = ghost["radius"] * self.scale_x 
                
                circle = self.canvas.create_oval(px-pr, py-pr, px+pr, py+pr, outline=ghost["color"], width=3, dash=(6, 4))
                txt = self.canvas.create_text(px, py, text=ghost["label"], fill=ghost["color"], font=("Helvetica", 12, "bold"))
                self.ghost_items[zi] = (circle, txt)
                
        self.canvas.itemconfig(self.title_text, text=f"ACTIVE STAGE: QUESTION {game_logic.CURRENT_QUESTION} / 4 — Navigate to Zone!", fill="#00ffff")

    def update_loop(self):
        if self.state.stop: return
        
        now = time.time()
        self.ui_update_counter += 1
        update_text_elements = (self.ui_update_counter % 8 == 0)

        with self.state.lock:
            snapshot = [{"filt": t.filt_position, "last": t.last_update} for t in self.state.tags]
            phys_ids = list(self.state.row_color_index)

        current_lit_ghosts = set()
        min_dist_to_ghost = float('inf')

        for row, snap in enumerate(snapshot):
            pos = snap["filt"]
            stale = (now - snap["last"] > 1.0) if snap["last"] else True
            
            if pos and not stale:
                px, py = self.cx(pos[0]), self.cy(pos[1])
                self.canvas.coords(self.tag_dots[row], px-8, py-8, px+8, py+8)
                
                for zi, ghost in enumerate(game_logic.Ghosts):
                    if ghost.get("active", True) and ghost.get("question") == game_logic.CURRENT_QUESTION:
                        gx, gy = ghost["center"]
                        dist = math.hypot(pos[0] - gx, pos[1] - gy)
                        
                        if dist < min_dist_to_ghost:
                            min_dist_to_ghost = dist
                            
                        if game_logic.ptInGhost(pos, ghost):
                            current_lit_ghosts.add(zi)
            else:
                self.canvas.coords(self.tag_dots[row], -20, -20, -20, -20)
                
            if update_text_elements:
                p_id = phys_ids[row] if row < len(phys_ids) else -1
                self.id_labels[row].configure(text=f"Slot {row} (ID: {p_id})" if p_id != -1 else f"Slot {row} (—)")
                if pos and not stale:
                    self.x_labels[row].configure(text=f"{pos[0]:.3f}")
                    self.y_labels[row].configure(text=f"{pos[1]:.3f}")
                else:
                    self.x_labels[row].configure(text="—")
                    self.y_labels[row].configure(text="—")

        if self.state.game_active and not self.state.game_won:
            self.audio_controller.update_proximity(min_dist_to_ghost)

        self.root.after(60, self.update_loop)

    def shutdown(self):
        self.state.stop = True
        try: self.root.destroy()
        except tk.TclError: pass