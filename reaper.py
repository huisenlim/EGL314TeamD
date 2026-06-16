from pythonosc import udp_client
import time

def send_message(receiver_ip, receiver_port, address, message):
	try:
		client = udp_client.SimpleUDPClient(receiver_ip, receiver_port)

		client.send_message(address, message)

		print("Message sent successfully.")
	except:
		print("Message not sent")

PI_A_ADDR = "192.168.254.48"		# wlan ip 192.168.171.1, 48
PORT = 2000

mkr1 = "/action/40161" # Marker 1
mkr2 = "/action/40162" # Marker 2
mkr3 = "/action/40163" # Marker 3
mkr4 = "/action/40164" # Marker 4
mkr7 = "/action/40167" # Marker 7
mkr8 = "/action/40168" # Marker 8
play = "/action/1007" # Play
pause = "/action/1008" # Pause
playstop = "/action/40044" # Play Pause toggle

msg = float(1) 

def c1():
    send_message(PI_A_ADDR, PORT, mkr7, msg)
    send_message(PI_A_ADDR, PORT, play, msg)
	
def c2():
    send_message(PI_A_ADDR, PORT, mkr8, msg)
    send_message(PI_A_ADDR, PORT, play, msg)

c1()
time.sleep(20)
send_message(PI_A_ADDR, PORT, pause, msg)
time.sleep(5)
c2()
time.sleep(5)
send_message(PI_A_ADDR, PORT, pause, msg)