# 314 Project Phantom MVP: Final Containment(Station 4)
An interactive and physical game of ghost hunting where player position determines real-time tracking with audio and visual cues to elimate the ghosts.

## Table of contents
1. [Project Overview](#1-Project-Overview)
2. [How The Game Works](#2-how-the-game-works)
3. [Game Setup](#3-game-setup)
*  3.1 [Real-Time Tracking Setup](#31-tag-and-anchor-setup)
*  3.2 [Button Setup](#32-button-setup)
*  3.3 [Gun Setup](#33-gun-setup)
4. [Software Setup](#4-software-setup)
*  4.1 [Audio](#41-audio-cues-setup)
*  4.2 [Lighting](#42-lighting-cues-setup)
5. [Conditions For The Game](#5-conditions-for-the-game)
*  5.1 [Win Conditions](#51-win-condition)
*  5.2 [Lose Conditions](#52-lose-condition)
6. [Final Outcome](#6-final-outcome)


### 1. Project Overview
An interactive, physical ghost-hunting experience where real-world player position drives a live game. Players carry UWB (ultra-wideband) location tags; the system trilaterates their position in an arena, checks it against "ghost" containment zones, and reacts in real time with a live arena visualization, dynamic stage lighting (grandMA3), and spatial audio (REAPER + L-ISA). Dispelling a ghost means physically walking into its zone and pressing a handheld button at the right moment.


### 2. How The Game Works


### 3. Game Setup


## 3.1 Tag and Anchor Setup


## 3.2 Button Setup



This section documents the physical trigger hardware (the "gun") and the game's lose condition — how they're wired together and how they behave in code.

---

## 1. Button Setup

The dispel trigger is a single momentary push button wired to the Raspberry Pi's GPIO, read continuously in the background and forwarded to the game laptop as an event.

## Wiring

| Pi Pin | Connection |
|---|---|
| GPIO 18 (BCM) | Button signal leg |
| GND | Button other leg |

The button is configured with an **internal pull-up**, so the pin reads HIGH when idle and LOW when pressed — `gpiozero` handles the inversion automatically.

```python
from gpiozero import Button

BUTTON_PIN = 18  # GPIO 18

button = Button(BUTTON_PIN, pull_up=True, bounce_time=0.2)
```

- `pull_up=True` — enables the internal pull-up resistor so no external resistor is needed
- `bounce_time=0.2` — 200ms software debounce, prevents a single physical press from registering as multiple rapid presses

## Event handling

`gpiozero` exposes clean press/release callbacks, which are bound to a small helper that sends an OSC message to the game laptop:

```python
def send_button_event(is_pressed: bool):
    print(f"[PI] Button {'PRESSED' if is_pressed else 'RELEASED'} -> Sending to Laptop")
    client.send_message("/button", 1 if is_pressed else 0)

button.when_pressed  = lambda: send_button_event(True)
button.when_released = lambda: send_button_event(False)
```

Every press/release is sent as an OSC message to `/button` with a payload of `1` (pressed) or `0` (released). On the laptop side, `main.py` listens for this address and only acts on the **press** edge (not release) to avoid double-triggering:

```python
disp.map("/button", handle_remote_button)
```

For development without a Pi, the laptop also binds the **spacebar** to the same event handler, so the whole game can be tested without any hardware attached.

---

## 3.3 Gun Setup

The "gun" is the handheld unit each player carries — it combines the **position tag** (UWB, reporting distance to anchors over UART) and the **dispel button** into one Raspberry Pi–driven transmitter. Its only job is to read hardware and forward everything to the game laptop over the network via OSC; it does no game logic itself.

## Components

- Raspberry Pi (or Pi Zero, depending on form factor)
- UWB tag module wired to the Pi's UART (`/dev/ttyS0` or `/dev/ttyUSB0`)
- Momentary push button on GPIO 18 (see [Button Setup](#1-button-setup))
- Wi-Fi connection to the same network as the game laptop

## Configuration

Before deploying a gun, set these constants at the top of `pi_transmitter.py`:

```python
LAPTOP_IP = "192.168.1.XXX"  # Game laptop's local IP address
PORT = 5005                  # Must match --port used when launching main.py

SERIAL_PORT = "/dev/ttyS0"   # Or /dev/ttyUSB0 for a USB-to-UART adapter
BAUD_RATE = 115200
BUTTON_PIN = 18
```

> ⚠️ `LAPTOP_IP` is a placeholder — it must be updated to the actual laptop IP before each session, since it can change between networks/venues.

### Runtime behavior

On startup, the gun opens a serial connection to the UWB tag and an OSC client pointed at the laptop:

```python
client = udp_client.SimpleUDPClient(LAPTOP_IP, PORT)
ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
ser.flushInput()
```

It then loops continuously:

1. **Reads a line from UART** whenever data is available — the tag reports distances as a CSV string: `tag_id, d0, d1, d2, d3, d4, d5`
2. **Validates the packet** — needs at least 7 comma-separated values (1 tag ID + 6 anchor distances) to match what `network.py` expects on the laptop side
3. **Converts and forwards** the values as a `/distances` OSC message; malformed lines are silently skipped
4. **Button presses/releases** fire independently and asynchronously via the `gpiozero` callbacks described above — they aren't tied to the UART polling loop, so the gun stays responsive even if UART data is delayed

```python
if len(parts) >= 7:
    try:
        osc_payload = [float(val) for val in parts]
        client.send_message("/distances", osc_payload)
    except ValueError:
        pass  # Skip corrupted lines
```

A short `time.sleep(0.01)` keeps the polling loop from pegging the CPU while still comfortably outpacing the 20Hz throttle applied on the receiving end (`network.py`).

## Multiple guns

Each gun just needs a unique `tag_id` embedded in its UART payload — the laptop auto-assigns each new physical tag ID to the next free UI "slot" the first time it's seen, so no per-gun code changes are required beyond flashing/wiring the tag itself.

---


## 4. Software Setup


### 4.1 Audio Cues Setup

### 4.2 Lighting Cues Setup


## 5. Conditions For The Game


### 5.1 Win Condition

### 5.2 Lose Condition
### 5.3 Lose Condition

The game is lost if the countdown timer reaches zero before every ghost in all three waves has been dispelled.

### Timer mechanics

The timer lives in shared game state and only starts counting once the tutorial is completed:

```python
self.time_left = 150.0       # 150-second countdown
self.timer_active = False    # Stays paused until tutorial is dismissed
```

Once active, `display.py`'s render loop decrements it every frame based on real elapsed time (not a fixed tick), so it stays accurate regardless of frame rate:

```python
if self.state.timer_active and not self.state.game_won and not self.state.game_lost:
    delta = now - self.state.last_time
    self.state.time_left -= delta
    self.state.last_time = now

    if self.state.time_left <= 0:
        self.state.time_left = 0
        self.state.game_lost = True
        self.state.timer_active = False
```

### What affects the clock

| Action | Effect |
|---|---|
| Dispelling a ghost (button press inside a zone) | **+30 seconds** |
| Pressing the button outside any active zone | **−5 seconds** (penalty for a wasted/wrong press) |

This means the timer isn't purely a countdown — good play actively buys more time, so the lose condition is really "run out of misses and time before clearing all ghosts."

### On loss

When `time_left` hits zero:

- `state.game_lost = True` and `state.timer_active = False` are set, freezing the game
- The arena canvas title updates immediately:
  ```python
  self.canvas.itemconfig(self.title_text, text="MISSION FAILED — OUT OF TIME!", fill="#ff0000")
  ```
- The same message/color is re-applied by `force_instant_ui_refresh()` if triggered from elsewhere, so the fail state is consistent no matter what path set it
- The timer HUD window turns red (`#ff5252`) once under 30 seconds remaining, giving players a visual warning before the loss actually happens:
  ```python
  timer_color = "#ff5252" if (self.state.time_left < 30.0 and self.state.timer_active) else "#00ffff"
  ```
- Once `game_lost` is `True`, `main.py`'s button handler stops processing hit detection entirely — further button presses have no effect on game state


## 6. Final Outcome
