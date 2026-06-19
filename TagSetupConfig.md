# Tag Configuration

Back to [README.md](README.md)

## How it works
The system operates in Two-Way Ranging (TWR) mode, allowing the tag to measure its distance from each anchor (on the orange boxes) without requiring clock synchronization.   
  
  
For each measurement cycle, the moving tag exchanges three timestamped UWB messages with each anchor:
```mermaid
graph LR
A[Tag]--message-->B[Anchor]
```
```mermaid
graph RL
C[Anchor]--reply-->D[Tag]
```
```mermaid
graph LR
E[Tag]--final-->F[Anchor]
```
From the timestamps captured, the tag converts it into a distance, and doing so against the 6 anchors gives the tag a vector distance.  
  
The calculated distance measurements are then output through its data UART connection to a Receiving Raspberry Pi like so:

```mermaid
graph TD
A[BU03 Anchor 0]--UART-->B[Receiver rPi]
C[BU03 Anchor 1] --> A
D[BU03 Anchor 2] --> A
E[BU03 Anchor 3] --> A
F[BU03 Anchor 4] --> A
G[BU03 Anchor 5] --> A
B --OSC--> H[Game rPi]
H --OSC--> I[Multiplay ]
```
The Receiver rPi then sends the raw UART data to the Game rPi using uart.py, which then uses the known coordinates of the anchors to perform multilateration to determine the player's real-time position within the game environment.   
  
To improve tracking accuracy, calibration offsets are applied to compensate for ranging errors, and a Kalman filter is used to smooth position data and reduce measurement noise.   

## Configuration of BU03 modules
For this project, we need 6 boards configured as anchors A00 through A05, and 1 board configured as a tag.

To configure each board, this was the workflow: 

Step 1: Verify UART link (bu03_detect.py)  
Step 2: Configure each board (bu03_multi_config.py)  
Step 3: Inspect a board's saved config (bu03_inspect.py)  
Step 4: Calibrate per-anchor offsets (viewer_calibrate.py)  
Step 5: Run the game (GamePOC.py)  

After configuring the anchors

View the step by step guide [**here**](https://github.com/huats-club/stage_tracking#step-1--verify-uart-link-bu03_detectpy).  

### Anchors and Tag IDs
During configuration, ensure that each UWB module has a Anchor/Tag ID.  
If you find that the tracking on the viewer is not working as expected, for example tags are jittery and stick to each other, double-check that they have unique IDs.

---
Back to [README.md](README.md)