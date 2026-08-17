# reaper.py
import threading
from pythonosc import udp_client

# ==============================================================================
# CONFIGURATION & NETWORK ADDRESSES
# ==============================================================================
REAPER_IP   = "192.168.254.12"
REAPER_PORT = 8000

# Action IDs mapped in REAPER
ACTION_PLAY       = "/action/1007"   # Transport: Play
ACTION_STOP       = "/action/1016"   # Transport: Stop (Stops all audio)
ACTION_UNMUTE_ALL = "/action/40339"  # Track: Unmute all tracks

# Marker Action Mappings (Track 6 for Intros, NO button, and Q4/Seq 102 fade)
MARKER_20_TRK6  = "/action/41260" # Q1 Intro (Track 6, Marker 20)
MARKER_21_TRK6  = "/action/41261" # NO Button (Track 6, Marker 21)
MARKER_22_TRK34 = "/action/41262" # YES Button Q1-Q3 & Q4 Seq 89 Start (Track 34, Marker 22)
MARKER_23_TRK6  = "/action/41263" # Seq 102 Fade (Track 6, Marker 23)
MARKER_24_TRK36 = "/action/41264" # Macro 15 Lighting Play (Track 36, Marker 24)
MARKER_25_TRK6  = "/action/41265" # Q2 Intro (Track 6, Marker 25)
MARKER_26_TRK6  = "/action/41266" # Q3 Intro (Track 6, Marker 26)
MARKER_27_TRK6  = "/action/41267" # Q4 Intro (Track 6, Marker 27)

# Marker 29 for Track 4
MARKER_29_TRK4 = "/action/41269"

# Initialize OSC Client
reaper_client = udp_client.SimpleUDPClient(REAPER_IP, REAPER_PORT)

def send_reaper(address):
    """Sends OSC action message to REAPER."""
    try:
        reaper_client.send_message(address, 1.0)
        print(f"[REAPER] Sent: {address}")
    except Exception as e:
        print("[REAPER ERROR] Send failed:", e)

class ReaperController:
    def __init__(self):
        self.marker_timer = None

    def _cancel_timer(self):
        if self.marker_timer and self.marker_timer.is_alive():
            self.marker_timer.cancel()
        self.marker_timer = None

    def unmute_all_tracks(self):
        """Unmutes all audio tracks in REAPER on code launch."""
        print("[REAPER] Unmuting all audio tracks...")
        send_reaper(ACTION_UNMUTE_ALL)

    def play_marker(self, marker_action):
        """Goes to specified marker and starts playback."""
        send_reaper(marker_action)
        send_reaper(ACTION_PLAY)

    def stop_all_audio(self):
        """Immediately stops all audio playback in REAPER."""
        self._cancel_timer()
        send_reaper(ACTION_STOP)

    def play_marker_29(self):
        """Plays Marker 29 on Track 4 upon code launch."""
        self._cancel_timer()
        print("[REAPER] Playing Marker 29 (Track 4)...")
        self.play_marker(MARKER_29_TRK4)

    def play_intro_then_marker_29(self, intro_marker_action, intro_duration_seconds):
        """
        Plays an intro marker (20, 25, 26, or 27 on Track 6), and automatically
        switches to Marker 29 on Track 4 after intro_duration_seconds finishes.
        """
        self._cancel_timer()
        print(f"[REAPER] Playing Track 6 intro {intro_marker_action} for {intro_duration_seconds}s...")
        self.play_marker(intro_marker_action)

        # Schedule automatic switch to Marker 29 on Track 4
        self.marker_timer = threading.Timer(
            intro_duration_seconds, 
            lambda: self.play_marker(MARKER_29_TRK4)
        )
        self.marker_timer.start()

    # --- Trigger Methods ---
    def play_q1_intro(self):
        # Marker 20 (Track 6) plays for 21.0s -> Marker 29 (Track 4)
        self.play_intro_then_marker_29(MARKER_20_TRK6, intro_duration_seconds=21.0)

    def play_q2_intro(self):
        # Marker 25 (Track 6) plays for 21.0s -> Marker 29 (Track 4)
        self.play_intro_then_marker_29(MARKER_25_TRK6, intro_duration_seconds=21.0)

    def play_q3_intro(self):
        # Marker 26 (Track 6) plays for 19.0s -> Marker 29 (Track 4)
        self.play_intro_then_marker_29(MARKER_26_TRK6, intro_duration_seconds=20.0)

    def play_q4_intro(self):
        # Marker 27 (Track 6) plays for 24.0s -> Marker 29 (Track 4)
        self.play_intro_then_marker_29(MARKER_27_TRK6, intro_duration_seconds=26.0)

    def play_no_button(self, on_finish_callback=None):
        """Plays Marker 21 (Track 6) for 4s, then triggers callback to repeat intro."""
        self._cancel_timer()
        print("[REAPER] Playing NO button Marker 21 (Track 6) for 4.0s...")
        self.play_marker(MARKER_21_TRK6)

        if on_finish_callback:
            self.marker_timer = threading.Timer(4.0, on_finish_callback)
            self.marker_timer.start()

    def play_yes_q1_to_q3(self):
        self._cancel_timer()
        self.play_marker(MARKER_22_TRK34)

    def play_seq102_fade_audio(self):
        """Plays Marker 23 (Track 6) during Sequence 102 fade off."""
        self._cancel_timer()
        self.play_marker(MARKER_23_TRK6)

    def play_seq90_audio(self):
        self._cancel_timer()
        self.play_marker(MARKER_24_TRK36)