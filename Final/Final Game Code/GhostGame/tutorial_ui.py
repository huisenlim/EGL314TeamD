# tutorial_ui.py
import tkinter as tk

class TutorialSystem:
    def __init__(self, parent_frame, on_complete_callback):
        self.frame = parent_frame
        self.on_complete = on_complete_callback
        self.current_step = 0

        self.steps = [
            {
                "title": "GHOST HUNTING 101 !!",
                "subtitle": "Get ready to master the art of ghost hunting!",
                "body": "ARE YOU UP FOR IT ?\n\nIf you are, grab your device and HAPPY HUNTING !!\n\n",
                "color": "#42a5f5"
            },
            {
                "title": "HOW TO HUNT: STEP 1",
                "subtitle": "Identify the Containment Fields",
                "body": "In the zone, there are Ghosts roaming around.\n\nWalk towards them.\n\nYour goal is to enter their containment fields.\n\nOnce you're in position, press your device's button to dispel the ghosts !!!",
                "color": "#ffeb3b"
            },
            {
                "title": "HOW TO HUNT: STEP 2",
                "subtitle": "Using Your Device",
                "body": "Take note: when your detector starts beeping, you’re getting closer!\n\nThe beeping gets <SUCCESSFUL> faster and more urgent the closer you get to a ghost's containment field.\n\nOnce you're in position, press your device's button to dispel the ghosts !!!",
                "color": "#ffff00"
            },
            {
                "title": "HOW TO HUNT: STEP 3",
                "subtitle": "Systems nominal, filter arrays steady\n\n",
                "body": "Now without my help, keep moving around to figure out where the rest of the ghosts are!\n\nTry it out below — walk to a ghost, listen for the beeping, and press the button to dispel it.\n\nBefore we begin the official HUNT, ARE YOU READY ?\n\nClick below to Start Hunting !!\n\n",
                "color": "#66bb6a"
            }
        ]

        self.build_ui()
        self.frame.bind("<Configure>", self.on_resize)
        self.show_step(0)

    def build_ui(self):
        self.inner_box = tk.LabelFrame(
            self.frame,
            text=" INSTRUCTION CONTROL MODULE ",
            bg="#0d0d0d", fg="#ffffff", font=("Helvetica", 11, "bold"),
            bd=2, relief="groove", labelanchor="n"
        )
        self.inner_box.pack(fill="both", expand=True, padx=10, pady=10)

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
            font=("Helvetica", 24, "bold"), justify="center"
        )
        self.title_lbl.pack(pady=(10, 5), fill="x")

        self.sub_lbl = tk.Label(
            self.scroll_content, text="", bg="#0d0d0d", fg="#888888",
            font=("Helvetica", 16, "italic"), justify="center"
        )
        self.sub_lbl.pack(pady=(0, 10), fill="x")

        self.body_lbl = tk.Text(
            self.scroll_content, bg="#0d0d0d", fg="#dddddd",
            font=("Courier", 14, "bold"), wrap="word",
            bd=0, highlightthickness=0, height=12
        )
        self.body_lbl.pack(fill="both", expand=True, padx=15, pady=10)

        self.status_frame = tk.Frame(self.scroll_content, bg="#0d0d0d")
        self.status_frame.pack(fill="x", padx=15, pady=(0, 10))

        self.button_indicator = tk.Label(
            self.status_frame, text="● BUTTON: idle", bg="#0d0d0d", fg="#666666",
            font=("Courier", 14, "bold")
        )
        self.button_indicator.pack(side="left", padx=(0, 20))

        self.beeper_indicator = tk.Label(
            self.status_frame, text="♪ DETECTOR: silent", bg="#0d0d0d", fg="#666666",
            font=("Courier", 14, "bold")
        )
        self.beeper_indicator.pack(side="left")

        self.ghost_status_lbl = tk.Label(
            self.scroll_content, text="", bg="#0d0d0d", fg="#aaaaaa",
            font=("Courier", 14, "bold"), justify="center"
        )
        self.ghost_status_lbl.pack(pady=(0, 5), fill="x")

        self.control_frame = tk.Frame(self.inner_box, bg="#0d0d0d")
        self.control_frame.pack(side="bottom", fill="x", pady=10, padx=15)

        self.prev_btn = tk.Button(
            self.control_frame, text="< PREV STEP", bg="#1c1c1c", fg="#ffffff",
            font=("Helvetica", 14, "bold"), bd=1, relief="solid", padx=20, pady=8,
            command=self.prev_step
        )
        self.prev_btn.pack(side="left")

        self.next_btn = tk.Button(
            self.control_frame, text="NEXT STEP >", bg="#222222", fg="#ffffff",
            font=("Helvetica", 14, "bold"), bd=1, relief="solid", padx=30, pady=8,
            command=self.next_step
        )
        self.next_btn.pack(side="right")

    def on_resize(self, event):
        """ Dynamically adapts text wrapping according to frame size """
        new_width = max(300, event.width - 60)
        self.title_lbl.configure(wraplength=new_width)
        self.sub_lbl.configure(wraplength=new_width)
        self.ghost_status_lbl.configure(wraplength=new_width)

    def show_step(self, index):
        step = self.steps[index]
        self.title_lbl.configure(text=step["title"], fg=step["color"])
        self.sub_lbl.configure(text=step["subtitle"])

        self.body_lbl.configure(state="normal")
        self.body_lbl.delete("1.0", tk.END)

        raw_body_text = step["body"]
        self.body_lbl.insert(tk.END, raw_body_text)
        self.body_lbl.configure(state="disabled")

        self.root_update_calls()
        self.canvas.yview_moveto(0)

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

    def update_button_indicator(self, pressed):
        if pressed:
            self.button_indicator.configure(text="● BUTTON: PRESSED", fg="#00ff00")
        else:
            self.button_indicator.configure(text="● BUTTON: idle", fg="#666666")

    def update_ghost_status(self, remaining, total):
        if remaining == 0:
            self.ghost_status_lbl.configure(
                text=f"All {total} wave targets dispelled — nice work!", fg="#00ff00"
            )
        else:
            self.ghost_status_lbl.configure(
                text=f"Ghosts remaining: {remaining}/{total}", fg="#aaaaaa"
            )