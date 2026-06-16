# This python script can be used to control Multiplay 3 software
# For more infomation, please refer to 
# http://da-share.com/help/multiplay3/OSC-Control-Cue-Actions.html
import socket

def send_message(IP, Port, Message):

  try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    MESSAGE = bytes(Message, 'UTF-8')
    sock.sendto(MESSAGE, (IP, Port))
    sock.close()
    print(f'messsage sent: {Message}')
  except:
    print(f'message not sent: {Message}')


if __name__ == "__main__":
# UDP_IP is target IP address
  IP = "192.168.254.173" #Local Host Address
  PORT = 5005
  message = "/cue/1/go" # Trigger Cue 1

  send_message(IP, PORT, message)