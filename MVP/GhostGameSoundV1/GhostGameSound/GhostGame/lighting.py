# lighting.py
from pythonosc import udp_client

# ───────── GMA3 NETWORK CONFIGURATION ─────────
GMA3_IP = "192.168.254.252"   # Replace with your grandMA3 console/laptop IP address
GMA3_PORT = 8080             # Default grandMA3 inbound OSC port
GMA3_ADDR = "/gma3/cmd"
# ─────────────────────────────────────────────

# Mapped Sequence IDs
FINAL_GHOST_SEQUENCE = 35   # grandMA3 Sequence ID for Wave 3 Final Boss
GAME_OVER_SEQUENCE   = 36   # grandMA3 Sequence ID for Game Completion / Win

GHOST_SEQUENCES = {
    0: 31,  # Ghost 0 (Bob)
    1: 32,  # Ghost 1 (Stewart)
    2: 37,  # Ghost 2 (Tim)
    3: 34,  # Ghost 3 (Kevin)
    4: 29,  # Ghost 4 (Carl)
    5: 33,  # Ghost 5 (Dave)
}

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

def trigger_cue(seq_id: int, cue_id: float):
    """Triggers a specific Cue inside a grandMA3 Sequence."""
    send_command(f"Goto Cue {cue_id} Sequence {seq_id}")

def set_ghost_light(ghost_index: int, turn_on: bool):
    """Triggers or turns off the specific Sequence mapped to a ghost."""
    seq_id = GHOST_SEQUENCES.get(ghost_index)
    if seq_id is not None:
        if turn_on:
            send_command(f"Go+ Sequence {seq_id}")
        else:
            send_command(f"Off Sequence {seq_id}")

# ───────── WAVE & GAME STATE SEQUENCES ─────────
def trigger_final_ghost_light():
    """Triggers the lighting sequence for the Wave 3 Final Boss."""
    send_command(f"Go+ Sequence {FINAL_GHOST_SEQUENCE}")

def trigger_game_finish_light():
    """
    Kills the final boss sequence and all mapped ghost sequences,
    then triggers the game completion sequence.
    """
    # 1. Kills the Final Boss sequence explicitly
    send_command(f"Off Sequence {FINAL_GHOST_SEQUENCE}")
    
    # 2. Ensures all standard ghost sequences are off
    for seq_id in GHOST_SEQUENCES.values():
        send_command(f"Off Sequence {seq_id}")
        
    # 3. Triggers the Victory / Game Over Sequence
    send_command(f"Go+ Sequence {GAME_OVER_SEQUENCE}")