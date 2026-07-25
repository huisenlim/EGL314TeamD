# Game tutorial code
# Tutorial System Documentation

## Overview

The `tutorial.py` program serves as an interactive training module for the Ghost Hunting Game. It combines UWB positioning, real-time player tracking, audio guidance, button interaction, and a graphical user interface to teach players how to play the game before entering the main hunt.

The tutorial introduces players to the ghost hunting mechanics through a series of instructional screens and then transitions into a live practice session where players can locate and dispel ghosts using the same equipment and controls as the actual game. Unlike the main game, the tutorial does not include a countdown timer or win/lose conditions.

Back to [README.md](README.md)

---

## System Components

The tutorial system consists of the following major modules:

### 1. UWB Position Tracking

The system receives distance measurements from the BU03 UWB tracking system through OSC (Open Sound Control) messages.

The anchor locations are defined in the `ANCHORS` dictionary:

```python
ANCHORS = {
    0: (0.0, 0.0),
    1: (0.0, 0.50),
    2: (0.0, 1.0),
    3: (1.0, 1.0),
    4: (1.0, 0.50),
    5: (1.0, 0.0),
}
```

Each anchor has a fixed coordinate within the play area. Distance measurements from these anchors are used to determine the player's position.

---

### 2. Trilateration

The function `trilaterate_2d()` calculates the player's position using the measured distances from multiple anchors.

```python
def trilaterate_2d(anchor_positions, distances):
```

The algorithm:

1. Receives distance measurements from the anchors.
2. Uses least-squares multilateration.
3. Calculates the estimated X and Y coordinates of the player.

At least three valid anchors are required to calculate a position.

---

### 3. Kalman Filter

Raw UWB measurements may contain noise and fluctuations.

The `Kalman2D` class smooths the calculated position data.

```python
class Kalman2D:
```

The filter performs:

* Prediction of future position
* Correction using new measurements
* Velocity estimation
* Noise reduction

This produces smoother player movement on the tracking display.

---

## Ghost System

The tutorial contains two practice ghosts.

```python
Ghosts = [
    {
        "center": (0.25, 0.5),
        ...
    },
    {
        "center": (0.75, 1.0),
        ...
    }
]
```

Each ghost contains:

| Parameter  | Purpose                        |
| ---------- | ------------------------------ |
| center     | Ghost location                 |
| radius     | Detection radius               |
| min_radius | Minimum visual size            |
| color      | Display colour                 |
| label      | Ghost name                     |
| active     | Whether ghost is still present |

---

### Ghost Detection

The function:

```python
def ptInGhost(point, ghost):
```

checks whether the player is inside a ghost's containment field.

The player's position is compared with the ghost's centre point.

If the player is within:

```
ghost radius + hit tolerance
```

the function returns `True`.

---

## Audio Guidance System

To help players locate ghosts without relying solely on the screen, proximity-based sound cues are used.

### Sound Cue Thresholds

```python
SOUND_CUE_THRESHOLDS = [
    (0.0, "/cue/4/go"),
    (0.25, "/cue/3/go"),
    (0.625, "/cue/2/go"),
    (1.0, "/cue/1/go"),
]
```

The cue played depends on the distance between the player and the nearest active ghost.

| Distance     | Cue   |
| ------------ | ----- |
| On target    | Cue 4 |
| Very close   | Cue 3 |
| Medium range | Cue 2 |
| Far away     | Cue 1 |

As the player approaches a ghost, the beeping frequency increases.

---

### Multiplay Integration

The `MultiplayClient` class sends OSC commands to Multiplay.

```python
class MultiplayClient:
```

Functions include:

#### stop_all()

Stops all currently playing audio cues.

```python
stop_all()
```

#### trigger()

Stops any existing cue and starts the requested cue.

```python
trigger(address)
```

This ensures only one proximity sound is active at any time.

---

## Button Input System

A physical button connected to Raspberry Pi GPIO 27 is used to dispel ghosts.

```python
BUTTON_PIN = 27
```

The GPIO library monitors button state changes.

```python
GPIO.add_event_detect(...)
```

When pressed:

1. The system checks the player's current position.
2. Determines whether the player is inside a ghost containment field.
3. If successful, the ghost is removed from the game.

---

## OSC Communication

The tutorial receives live tracking data using OSC.

### OSC Handler

```python
make_osc_handler(...)
```

The handler:

1. Receives distance measurements.
2. Performs trilateration.
3. Applies Kalman filtering.
4. Updates player position.
5. Updates ghost detection.
6. Controls proximity audio cues.

---

## User Interface

The graphical interface is built using:

* Tkinter
* Matplotlib

### Left Panel

Displays:

* Anchor locations
* Ghost locations
* Player position
* Tracking circles
* Position data table

### Right Panel

Displays tutorial instructions.

The tutorial consists of four steps:

1. Introduction
2. Understanding containment fields
3. Understanding detector beeps
4. Practice hunt

After completion, the tutorial panel is removed and the tracking display expands to full screen.

---

## Practice Hunt

After completing the instructional pages, the player enters a live practice hunt.

Features available:

* Real-time tracking
* Ghost detection
* Button interaction
* Audio guidance

Features disabled:

* Countdown timer
* Score tracking
* Win/Lose conditions

Players can freely practise locating and dispelling ghosts.

---

## Program Flow

1. Initialise GPIO button input.
2. Start OSC server.
3. Initialise Multiplay connection.
4. Launch graphical interface.
5. Receive UWB distance data.
6. Perform trilateration.
7. Apply Kalman filtering.
8. Update player position.
9. Generate proximity sound cues.
10. Detect ghost interactions.
11. Remove ghosts when successfully dispelled.
12. Shut down safely when the application closes.

This tutorial system provides players with a guided introduction to the Ghost Hunting Game while allowing them to practise the core mechanics using the actual hardware and tracking system before starting the main gameplay experience.

---
Back to [README.md](README.md)