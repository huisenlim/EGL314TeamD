import time
import serial
from gpiozero import Button
from pythonosc import udp_client

# ───────── CONFIGURATION ─────────
LAPTOP_IP = "192.168.1.XXX"  # Change this to your Laptop's Local IP address
PORT = 5005                  # Matches DEFAULT_PORT in main.py

SERIAL_PORT = "/dev/ttyS0"   # Or '/dev/ttyUSB0' if using a USB-to-UART adapter
BAUD_RATE = 115200
BUTTON_PIN = 18              # GPIO 18
# ─────────────────────────────────

# Initialize OSC Client to send packets to Laptop
client = udp_client.SimpleUDPClient(LAPTOP_IP, PORT)

# Initialize Hardware Button
button = Button(BUTTON_PIN, pull_up=True, bounce_time=0.2)

def send_button_event(is_pressed: bool):
    print(f"[PI] Button {'PRESSED' if is_pressed else 'RELEASED'} -> Sending to Laptop")
    client.send_message("/button", 1 if is_pressed else 0)

button.when_pressed = lambda: send_button_event(True)
button.when_released = lambda: send_button_event(False)

print(f"[PI TRANSMITTER] Operational. Forwarding UART & Button to {LAPTOP_IP}:{PORT}")

try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
    ser.flushInput()
    
    while True:
        if ser.in_waiting > 0:
            # Read line from UART
            raw_line = ser.readline().decode('utf-8', errors='ignore').strip()
            
            # Assuming UART string is CSV formatted: "tag_id, d0, d1, d2, d3, d4, d5"
            parts = raw_line.split(',')
            
            # network.py requires at least 7 arguments (1 ID + 6 Anchor Distances)
            if len(parts) >= 7:
                try:
                    osc_payload = [float(val) for val in parts]
                    client.send_message("/distances", osc_payload)
                except ValueError:
                    pass  # Skip corrupted lines
                    
        time.sleep(0.01)

except Exception as e:
    print(f"[ERROR] Failed to read UART: {e}")