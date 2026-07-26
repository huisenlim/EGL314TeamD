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
### Audio Cue Setup

The Ghost Game uses REAPER to provide real-time audio cues based on the player's distance from a ghost. The `reaper.py` file communicates with REAPER using OSC commands and triggers different audio markers depending on the player's proximity.

Three main audio tracks are used for the proximity warning system:

- **Track 12 – Fast Beep:** Used when the player is very close to the ghost.
- **Track 13 – Medium Beep:** Used when the player is at a medium distance from the ghost.
- **Track 14 – Slow Beep:** Used when the player is further away from the ghost.

The `reaper.py` file assigns OSC actions to each of these audio cues. Track 12 is triggered using the fast beep marker, Track 13 is triggered using the medium beep marker, and Track 14 is triggered using the slow beep marker. :contentReference[oaicite:0]{index=0}

The audio cue is selected automatically based on the player's minimum distance from the ghost. When the player is further away, a slow beep is triggered. As the player gets closer, the system changes to a medium and then fast beep. The warning interval also becomes shorter, causing the beeps to occur more frequently as the player approaches the ghost. :contentReference[oaicite:1]{index=1} :contentReference[oaicite:2]{index=2}

The proximity levels are configured as follows:

| Distance from Ghost | Audio Cue | Track |
|---|---|---|
| More than 5 m and up to 8 m | Slow Beep | Track 14 |
| More than 2.5 m and up to 5 m | Medium Beep | Track 13 |
| More than 1 m and up to 2.5 m | Fast Beep | Track 12 |
| 1 m or less | Critical Fast Beep | Track 12 |

This creates a dynamic warning system where the audio becomes faster and more frequent as the player approaches the ghost. When the player reaches the critical distance or successfully interacts with the ghost, a separate ghost-hit audio cue can also be triggered.

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


# 6. Final Outcome








 📋 Final Setup & Outcome Summary — Ghost Hunting Game

A wrap-up summary of the complete game setup, how a session plays out end-to-end, and the two possible final outcomes.

---

## 1. Setup Overview

| Layer | Component | Status |
|---|---|---|
| **Positioning hardware** | 6× fixed UWB anchors + per-player UWB tags | Configured via `game_logic.ANCHORS` |
| **Player device ("gun")** | Raspberry Pi + UWB tag (UART) + push button (GPIO 18) | `pi_transmitter.py` |
| **Network transport** | OSC over UDP, Pi → Laptop | Port `5005` (`--port`) |
| **Position engine** | Trilateration + Kalman filter | `network.py`, `trilateration.py` |
| **Game engine** | Wave/ghost state, hit detection, timer | `game_logic.py`, `game_state.py`, `main.py` |
| **Spectator display** | Live arena map, tag table, timer HUD, tutorial | `display.py`, `tutorial_ui.py` |
| **Lighting** | grandMA3 via OSC | `lighting.py` |
| **Audio** | REAPER + L-ISA via OSC | `reaper.py` |

**End-to-end flow:** UWB tags measure distance → Pi reads UART + button, forwards via OSC → laptop trilaterates position → game logic checks position against active ghost zones → display updates live → button press attempts a dispel → lighting + audio react → timer and wave state update → repeat until win or loss.

---

## 2. Session Flow (Start to Finish)

1. **Launch** — `main.py` starts the OSC server, opens the arena display, and waits
2. **Tutorial** — players complete the 4-step onboarding panel; timer stays paused (`timer_active = False`) until this finishes
3. **Hunt begins** — timer starts at `150.0s`, green "wash" lighting cue fires
4. **Wave 1 → 2 → 3** — players track ghosts via proximity beeping, walk into zones, and press the button to dispel; each successful dispel is `+30s`, each wasted press is `−5s`
5. **Round ends** — either all 3 waves are cleared (**win**) or the timer hits `0` first (**loss**)

---

## 3. Final Outcomes

### 🏆 Win
- Fires when the **last ghost of wave 3** is dispelled
- `game_won = True`, timer stops instantly at whatever time remains
- `lighting.trigger_game_finish_light()` clears all ghost/boss sequences and triggers the **Victory** cue on grandMA3
- Arena title switches to green: `"GAME OVER — AREA CLEARED! YOU WIN!"`

### ☠️ Loss
- Fires when `time_left` reaches `0` before all waves are cleared
- `game_lost = True`, timer freezes at `0.0`
- Arena title switches to red: `"MISSION FAILED — OUT OF TIME!"`
- **No lighting or audio cue currently fires on loss** — this is the one asymmetry between the two outcomes

### After either outcome
- Button presses stop affecting the game (`handle_button_event` checks `not game_won and not game_lost`)
- The arena title and timer HUD simply freeze on-screen showing final state — there is no dedicated results/summary screen
- No stats are persisted anywhere (no logging of waves cleared, hit/miss counts, or time remaining/overrun)
- Returning to a fresh round currently requires restarting the app — `game_won`, `game_lost`, `time_left`, and ghost `active` flags are not reset in-session

---

## 4. Setup Checklist

Use this to confirm a venue is ready before a session:

- [ ] All 6 anchor coordinates in `game_logic.ANCHORS` match the physical arena
- [ ] `VIEW_BOUNDS` in `game_logic.py` covers the full playable area
- [ ] Each gun's `LAPTOP_IP` in `pi_transmitter.py` points to the current laptop IP
- [ ] `--port` on the laptop matches `PORT` in every gun's config
- [ ] `GMA3_IP` / `GMA3_PORT` in `lighting.py` reachable, and `GHOST_SEQUENCES` / `FINAL_GHOST_SEQUENCE` / `GAME_OVER_SEQUENCE` match the grandMA3 show file
- [ ] `REAPER_IP` / `LISA_IP` in `reaper.py` reachable, and marker/action IDs match the current REAPER project
- [ ] Buttons debounced and tested on all guns (`bounce_time=0.2`)
- [ ] Tutorial content reviewed and up to date (`tutorial_ui.py`)
- [ ] `--tags` set to the correct number of players for the session

---
