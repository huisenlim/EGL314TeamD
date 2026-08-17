# lighting.py
import threading
from pythonosc import udp_client

# ───────── GMA3 NETWORK CONFIGURATION ─────────
GMA3_IP = "192.168.254.252"   # Replace with your grandMA3 console IP
GMA3_PORT = 8080             # Default grandMA3 inbound OSC port
GMA3_ADDR = "/gma3/cmd"
# ─────────────────────────────────────────────

QUESTION_SEQUENCES = {
    1: {"question_seq": 93, "success_seq": 86},
    2: {"question_seq": 94, "success_seq": 87},
    3: {"question_seq": 95, "success_seq": 88},
    4: {"question_seq": 96, "success_seq": 89},
}

# Timed Cue Configurations: (delay_seconds, cue_number)
QUESTION_CUE_TIMINGS = {
    1: [(6.0, 1), (10.0, 2), (14.0, 3), (18.0, 4)],
    2: [(7.0, 1), (11.0, 2), (14.0, 3), (17.0, 4)],
    3: [(6.0, 1), (10.0, 2), (13.0, 3), (16.0, 4)],
    4: [(10.0, 1), (13.0, 2), (18.0, 3), (21.0, 4)],
}

STARTUP_SEQUENCE = 100
NO_BUTTON_SEQUENCE = 97
FINAL_DIMMER_SEQUENCE = 102 
TUTORIAL_SEQUENCE = 91
FINAL_MACRO = 15

# List to keep track of active cue timers so we can cancel them if YES is pressed early
active_cue_timers = []

try:
    client = udp_client.SimpleUDPClient(GMA3_IP, GMA3_PORT)
    print(f"[LIGHTING] Connected to grandMA3 at {GMA3_IP}:{GMA3_PORT}")
except Exception as e:
    client = None
    print(f"[LIGHTING ERROR] Failed to initialize OSC client: {e}")

def send_command(cmd_string: str):
    """Sends a raw command string to the grandMA3 command line."""
    if client:
        try:
            client.send_message(GMA3_ADDR, cmd_string)
        except Exception as err:
            print(f"[LIGHTING ERROR] Network send failed: {err}")

def cancel_active_cue_timers():
    """Cancels any pending timed cues for question sequences."""
    global active_cue_timers
    for timer in active_cue_timers:
        if timer.is_alive():
            timer.cancel()
    active_cue_timers.clear()

def trigger_initial_startup_light():
    """Runs Cue 2 on Sequence 100 upon application launch."""
    print("[LIGHTING] App Launched: Triggering Cue 2 on Sequence 100...")
    send_command(f"Go+ Cue 2 Sequence {STARTUP_SEQUENCE}")

def stop_startup_light():
    """Turns OFF Sequence 100 when START GAME is pressed."""
    print("[LIGHTING] Start Game Pressed: Turning OFF Sequence 100...")
    send_command(f"Off Sequence {STARTUP_SEQUENCE}")

def trigger_no_button_sequence():
    """Plays Sequence 97 for 5 seconds when NO is pressed, then turns it off."""
    print("[LIGHTING] NO Button Pressed: Triggering Sequence 97 for 5 seconds...")
    send_command(f"Go+ Sequence {NO_BUTTON_SEQUENCE}")
    
    # Schedule automatic OFF after 5 seconds
    threading.Timer(5.0, _stop_no_button_sequence).start()

def _stop_no_button_sequence():
    """Helper timer callback to turn OFF Sequence 97."""
    print("[LIGHTING] 5s elapsed: Turning OFF Sequence 97...")
    send_command(f"Off Sequence {NO_BUTTON_SEQUENCE}")

def start_tutorial_lighting():
    """Turns ON Sequence 91 when START TUTORIAL is pressed."""
    print(f"[LIGHTING] Start Tutorial Pressed: Turning ON Sequence {TUTORIAL_SEQUENCE}...")
    send_command(f"Go+ Sequence {TUTORIAL_SEQUENCE}")

def stop_tutorial_lighting():
    """Turns OFF Sequence 91 when START GAME is pressed."""
    print(f"[LIGHTING] Turning OFF Sequence {TUTORIAL_SEQUENCE}...")
    send_command(f"Off Sequence {TUTORIAL_SEQUENCE}")

def _trigger_cue(cue_num: int, seq_num: int):
    """Helper callback to send Go+ Cue X Sequence Y to GMA3."""
    print(f"[LIGHTING] Triggering Cue {cue_num} on Sequence {seq_num}")
    send_command(f"Go+ Cue {cue_num} Sequence {seq_num}")

def start_question_lighting(q_num: int):
    """
    Triggers the initial sequence (93-96) and schedules 
    timed Cue 1, 2, 3, 4 commands for the given question.
    """
    cancel_active_cue_timers()  # Clear old timers
    
    seq_info = QUESTION_SEQUENCES.get(q_num)
    if not seq_info:
        return
        
    seq_num = seq_info["question_seq"]
    send_command(f"Go+ Sequence {seq_num}")
    
    # Schedule timed cue triggers
    timings = QUESTION_CUE_TIMINGS.get(q_num, [])
    for delay, cue in timings:
        timer = threading.Timer(delay, _trigger_cue, args=(cue, seq_num))
        active_cue_timers.append(timer)
        timer.start()
        
    print(f"[LIGHTING] Started Question {q_num} (Seq {seq_num}) with timed cues.")

def trigger_question_success_light(q_num: int, audio_controller=None):
    """
    Cancels pending intro cues, turns OFF question sequence (93-96), 
    and runs corresponding success sequence (86-89).
    """
    cancel_active_cue_timers()  # Stop any intro cues from firing late
    
    seq_info = QUESTION_SEQUENCES.get(q_num)
    if seq_info:
        send_command(f"Off Sequence {seq_info['question_seq']}")
        send_command(f"Go+ Sequence {seq_info['success_seq']}")

    # --- Special Transition Logic for Question 4 / Sequence 89 ---
    if q_num == 4:
        print("[LIGHTING] Q4 Cleared: Seq 89 active! Playing Track 34 Marker 22...")
        send_command("Go+ Sequence 101")
        
        # Step 1: Play Track 34 Marker 22 when Sequence 89 starts
        if audio_controller:
            audio_controller.play_yes_q1_to_q3()

        # Step 2: Hold for 9s before triggering Cue 9 on Sequence 102
        threading.Timer(9.0, _q4_fade_seq102, args=(audio_controller,)).start()

def _q4_fade_seq102(audio_controller=None):
    print("[LIGHTING] 9s elapsed: Triggering Cue 9 on Sequence 102 & Playing Track 6 Marker 23 (11s)...")
    send_command(f"Go+ Cue 9 Sequence {FINAL_DIMMER_SEQUENCE}")
    
    # Play Track 6 Marker 23 for 11s when Seq 102 Cue 9 triggers
    if audio_controller:
        audio_controller.play_seq102_fade_audio()
        
    # Step 3: Timer for 11s (when Marker 23 finishes) -> Turn OFF Seq 89, execute Macro 15 & Track 36 Marker 24
    threading.Timer(11.0, _q4_delayed_macro15_transition, args=(audio_controller,)).start()

def _q4_delayed_macro15_transition(audio_controller=None):
    """Helper timer callback: Turns OFF Seq 89, runs Macro 15 via 'Go', and triggers Track 36 Marker 24."""
    print(f"[LIGHTING] 11s elapsed! Turning OFF Seq 89 and executing Macro {FINAL_MACRO}...")
    send_command("Off Sequence 89")
    send_command(f"Go Macro {FINAL_MACRO}")
    
    if audio_controller:
        audio_controller.play_seq90_audio()

def handle_continue_lighting(q_num: int):
    """Turns OFF the current success sequence (86/87/88) when continuing."""
    seq_info = QUESTION_SEQUENCES.get(q_num)
    if seq_info:
        send_command(f"Off Sequence {seq_info['success_seq']}")

def end_game_lighting_cleanup():
    """End Game Action: Cancels active timers and triggers Cue 9 on Sequence 102."""
    cancel_active_cue_timers()
    print("[LIGHTING] End Game Pressed: Triggering Cue 9 on Sequence 102...")
    send_command(f"Go+ Cue 9 Sequence {FINAL_DIMMER_SEQUENCE}")