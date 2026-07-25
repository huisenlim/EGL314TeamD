# reaper.py
import time
from pythonosc import udp_client

# ==============================================================================
# CONFIGURATION & NETWORK ADDRESSES
# ==============================================================================
REAPER_IP   = "192.168.254.12"
REAPER_PORT = 8000

LISA_IP     = "127.0.0.1"
LISA_PORT   = 8880

# Action IDs mapped to Markers in REAPER
MARKER_12_FAST = "/action/41252"  # Marker 12 (Fast Beep)
MARKER_14_SLOW = "/action/41254"  # Marker 14 (Slow Beep)
MARKER_15_KILL = "/action/41255"  # Marker 15 (Ghost Kill Alarm)
ACTION_PLAY    = "/action/1007"   # Transport Play
UNMUTE         = "/action/_RS4be7ebbc924f4393bc97948fd73296b4b32f1fef"  

# L-ISA Timecode Snapshot Targets (Formatted as "HH:MM:SS:FF")
LISA_TIME_KILL = "00:45:00:00"  # Ghost Kill Alarm
LISA_TIME_FAST = "00:45:30:00"  # Fastest Beeping
LISA_TIME_SLOW = "00:46:30:00"  # Slow Beeping

# Initialize OSC Clients
reaper_client = udp_client.SimpleUDPClient(REAPER_IP, REAPER_PORT)
lisa_client   = udp_client.SimpleUDPClient(LISA_IP, LISA_PORT)

# ==============================================================================
# BASE SEND MESSAGE HELPERS
# ==============================================================================
def send_reaper(address):
    """Sends OSC action message with payload value 1.0 to REAPER."""
    try:
        reaper_client.send_message(address, 1.0)
        print(f"[REAPER] Sent: {address}")
    except Exception as e:
        print("[REAPER ERROR] Send failed:", e)

def send_lisa(timecode_str):
    """Sends OSC snapshot timecode recall to L-ISA."""
    try:
        lisa_client.send_message("/lisa/snapshot/timecode", timecode_str)
        print(f"[L-ISA] Sent: {timecode_str}")
    except Exception as e:
        print("[L-ISA ERROR] Send failed:", e)

# ==============================================================================
# GAME EVENT TRIGGER FUNCTIONS
# ==============================================================================
def unmute():
    """Unmutes designated tracks in REAPER."""
    send_reaper(UNMUTE)

def slow_beep():
    """Triggers Marker 14 (Slow Beep) in REAPER & 00:46:30:00 in L-ISA."""
    send_reaper(MARKER_14_SLOW)
    send_reaper(ACTION_PLAY)
    send_lisa(LISA_TIME_SLOW)

def fast_beep():
    """Triggers Marker 12 (Fast Beep) in REAPER & 00:45:30:00 in L-ISA."""
    send_reaper(MARKER_12_FAST)
    send_reaper(ACTION_PLAY)
    send_lisa(LISA_TIME_FAST)

def ghost_hit():
    """Triggers Marker 15 (Ghost Kill Alarm) in REAPER & 00:45:00:00 in L-ISA."""
    send_reaper(MARKER_15_KILL)
    send_reaper(ACTION_PLAY)
    send_lisa(LISA_TIME_KILL)


# ==============================================================================
# REAPER & L-ISA CONTROLLER CLASS
# ==============================================================================
class ReaperController:
    """
    Receives proximity distance values from display.py and dispatches 
    corresponding triggers simultaneously to REAPER and L-ISA.
    """

    def __init__(self):
        self.last_beep_time = 0.0

    def trigger_alarm(self):
        """Triggers Marker 15 (Ghost Kill Alarm) & L-ISA snapshot 00:45:00:00."""
        ghost_hit()

    def update_proximity(self, min_distance):
        """
        Evaluates min_distance from display.py against distance thresholds:
        - <= 2.5m : Fast Beeping (interval: 0.25s)
        - <= 8.0m : Slow Beeping (interval: 1.0s)
        """
        now = time.time()

        if min_distance <= 1.0:
            if (now - self.last_beep_time) >= 0.25:
                fast_beep()
                self.last_beep_time = now
        elif min_distance <= 9.5:
            if (now - self.last_beep_time) >= 1.0:
                slow_beep()
                self.last_beep_time = now