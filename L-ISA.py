# Huats 2023 oscstarterkit
# This python script demonstrate OSC control on Raspberry Pi to L-ISA 
# Controller adjusting pan value by 0.3 on Source 1
from pythonosc import udp_client

def send_message(receiver_ip, receiver_port, address, message):
  try:
    # Create an OSC client to send messages
    client = udp_client.SimpleUDPClient(receiver_ip, receiver_port)

    # Send an OSC message to the receiver
    client.send_message(address, message)

    print("Message sent successfully.")
  except:
    print("Message not sent")

# FOR INFO: IP address and port of the receiving Raspberry Pi
PI_A_ADDR = "192.168.254.72"    # wlan ip
PORT = 8880



addr = "/ext/src/1/p"
msg = float(0.5)

addr = "/ext/src/1/d"     
msg = float(0.5)      

addr = "/ext/src/1/send/1"   
msg = float(0.5)            


# PAN
send_message(PI_A_ADDR, PORT, "/ext/src/1/p", 0.5)

# DEPTH
send_message(PI_A_ADDR, PORT, "/ext/src/1/d", 0.5)

# FX SEND
send_message(PI_A_ADDR, PORT, "/ext/src/1/send/1", 0.5)