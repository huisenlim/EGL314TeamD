from pythonosc import udp_client
import time

def send_message(receiver_ip, receiver_port, address, message):
	try:
		client = udp_client.SimpleUDPClient(receiver_ip, receiver_port)

		client.send_message(address, message)

		print("Message sent successfully.")
	except:
		print("Message not sent")

PI_A_ADDR = "192.168.254.12"		# wlan ip 192.168.171.1, 48
PORT = 8000

mkr1 = "/action/40161" # Marker 1
mkr2 = "/action/40162" # Marker 2
mkr3 = "/action/40163" # Marker 3
mkr4 = "/action/40164" # Marker 4
mkr7 = "/action/40167" # Marker 7
mkr8 = "/action/40168" # Marker 8
play = "/action/1007" # Play
pause = "/action/1008" # Pause
playstop = "/action/40044" # Play Pause toggle
cust1 = "/action/_631b3e8487885e4ca41e36bf474b840f"
cust2 = "/action/_b14658efff2869488742ab2f27a44845"
cust3 = "/action/_d0abf1a60bea24439898fd2d159db2a9"
cust4 = "/action/_aa9d630d29046f4bb441abee7a7010a4"

msg = float(1) 

def c1():
    send_message(PI_A_ADDR, PORT, cust1, msg)
	
def c2():
    send_message(PI_A_ADDR, PORT, cust2, msg)

def c3():
    send_message(PI_A_ADDR, PORT, cust3, msg)
    
def c4():
    send_message(PI_A_ADDR, PORT, cust4, msg)

#time.sleep(60)
send_message(PI_A_ADDR, PORT, pause, msg)