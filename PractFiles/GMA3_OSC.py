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

# Math Function to convert Values to Command line Values to GMA3 Values e.g. pan; -315 = 0 = -315, pan; 315 = 65535 = 315
def GMA3_Value_Converter(y, y_min, y_max, x_min=0, x_max=65535):
    y = max(min(y, y_max), y_min)  # clamp y
    return int(round((y - y_min) * (x_max - x_min) / (y_max - y_min) + x_min))

# Function to set the attribute parameters easier
def set_attribute(fixture: str, attribute: str, value: float, y_min: float, y_max: float):
    """
    Sends an OSC command to control a fixture attribute in GMA3.

    fixture   = "Fixture 1" (or any valid GMA3 selection string)
    attribute = "pan" / "tilt"
    value     = user-friendly value (scaled to GMA3's range)
    y_min     = minimum expected value for the attribute (e.g. -270) Click on Min to know
    y_max     = maximum expected value for the attribute (e.g. 270) Click on Max to know
    """

    # Convert to GMA3 absolute value
    gma_value = GMA3_Value_Converter(value, y_min, y_max)

    # Send Messages
    send_message(GMA3_ADDR, fixture)
    send_message(GMA3_ADDR, f"Attribute '{attribute}' At Absolute Decimal16 {gma_value}")
 
# Main Program
if __name__ == "__main__":
    set_attribute("Fixture 1", "tilt", 90, -135, 135)
    set_attribute("Fixture 4", "tilt", 90, -135, 135)


    """
    the last 2 values are the max and min rotation of the patched light
    THATS ALL 
    """

def dim_fixture(fixture_id, brightness):
    """
    fixture_id: The ID of the light (int)
    brightness: 0 to 100 (int)
    """
    # This creates the string: "Fixture 1 At 75"
    command = f"Fixture {fixture_id} At {brightness}"
    
    print(f"Sending: {command}")
    
    # Send the string to the GrandMA command line address
    send_message(GMA3_ADDR, command)

# Usage: Dim Fixture #2 to 20% brightness
dim_fixture(2, 20)


def trigger_sequence(seq_id):
    # This sends the command: Go+ Sequence 5
    command = f"Go+ Sequence {seq_id}"
    
    print(f"Triggering: {command}")
    # Try both common addresses just in case
    send_message(GMA3_ADDR, command)
    send_message(GMA3_ADDR, command)

# Example: Run Sequence 1
trigger_sequence(3)