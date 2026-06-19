# Software Setup 
This file details how to set up and install the software dependencies needed to run the game.  

Following is the list of hardware we will be using for this project.  
 This guide will be focusing on the Raspberry Pi 4 Model B and Multiplay setup.
| Item | Qty | Remarks |
| --- | --- | --- |
| BU03-Kit UWB modules | 8 | 6 anchors and 2 tags. |
| Raspberry Pi 4 Model B | 2 | 1 rPi for running game code, and another for receiving UWB data through UART.  |
| Multiplay | - | For synchronised audio feedback |
| Physical button | 1 | Connected to game rPi so it can take in the button input. |
| Jumper wires | 2 | Soldered to the button and connected to rPi GPIO 27 |
## First inital boot
1. Update the Raspberry Pi.
```
sudo apt update
sudo apt upgrade
```
If this fails, set the date and time on the Raspberry Pi before trying again.
```
sudo date -s 'YYYY-MM-DD HH:MM:SS'
```
2. Enable SSH
To enable SSH, type:
```
sudo raspi-config
```
3. Enable VNC (Virtual Network Computing)
```

```

## Multiplay

Open Multiplay>Files>Preferences  
![multiplayPrefss](images/MultiplayPref.png)  
Then, open OSC Control and set the port to the corresponding port number while also enabling Control (Incoming).
![multiplayOSCss](images/multiplayOSC.png)
