import time
from pythonosc import udp_client

# ───────── CONFIGURE THIS ─────────
GMA3_IP = "192.168.254.48"   # Server IP add
GMA3_PORT = 2000 # Server OSC port num
GMA3_ADDR = "/gma3/cmd" # For grandMA command line to receive message
# ──────────────────────────────────

# Function for Sending OSC Messages
def send_message(address: str, message: str):
    try:
        client = udp_client.SimpleUDPClient(GMA3_IP, GMA3_PORT)
        client.send_message(address, message) # To send message in the terminal
        print(f"Sent: {message}")
    except Exception as e:
        print(f"Message not sent: {e}") # if there is any error

def trigger_sequence(seq_id):
    # This sends the command: Go+ Sequence 5
    command = f"Go+ Sequence {seq_id}"
    
    print(f"Triggering: {command}")
    # Try both common addresses just in case
    send_message(GMA3_ADDR, command)
    send_message(GMA3_ADDR, command)

# Example: Run Sequence 1
trigger_sequence(3)