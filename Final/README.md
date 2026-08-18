# EGL314 Project Phantom MVP: The Final Showdown (Station 4)
An interactive and physical game of ghost hunting where player need to answer question, when they answer correctly, they are one step closer to restore the energy to kill the final ghost(bossman).

## Table of Content
1. [Project Overview](#1-Project-Overview)
2. [How The Game Works](#2-how-the-game-works)
3. [Game Setup](#3-game-setup)
*  3.1 [Equipment](#31-equipment-used)
4. [Software Setup](#4-software-setup)
*  4.1 [Audio](#41-audio-cues-setup)
*  4.2 [Visual](#42-lighting-cues-setup)
5. [Conditions For The Game](#5-conditions-for-the-game)
*  5.1 [Win Conditions](#51-win-condition)
*  5.2 [Lose Conditions](#52-lose-condition)
6. [Final Outcome](#6-final-outcome)



## 1. Project Overview
This station consists of players if they are paying attention to the trainers(host). Players have to answer 4 questions, after one correct answer the energy will be restored slowly until the last question is answered correctly, they will be able to defeat the final ghosts(bossman). The system tracks participants across defined arena zones and synchronizes stage lighting and multi-track audio to deliver a guided 4-question interactive game.

This is bossman:)
<img width="1280" height="960" alt="bossman" src="https://github.com/huisenlim/EGL314TeamD/blob/main/Final/images/bossman.jpg" />


## 2. How The Game Works
The game is a synchronized spatial tracking and show automation system where trainees(players) have to answer the correct answer, trainers then will place a pillar in one of the option that the trainees(players) want and see if it is in the zone(correct option), if yes it will move on to the next question, if not players will have another try until they get correct. The Python engine processes real-time hardware positioning and coordinates stage lighting (grandMA3) and dynamic audio cues (REAPER) over Open Sound Control (OSC).

---

### **1. Zone Collision & Hit Detection**

* **Zone Radius Evaluation (`game_logic.py`)**:
Uses Euclidean distance to determine whether a smoothed tag coordinate $(px, py)$ falls within the active question's zone center $(zx, zy)$:


```python
def ptInGhost(point, ghost):
    if point is None: return False
    px, py = point; zx, zy = ghost["center"]; r = ghost["radius"] + GhostHitTol
    return ((px - zx)**2 + (py - zy)**2) <= (r * r)

```
To detect if tag is in zone.
<img width="1280" height="960" alt="tag in zone" src="https://github.com/huisenlim/EGL314TeamD/blob/main/Final/UI%20images/Question%202.jpg" />


---

### **2. Game Lifecycle & Show Automation**

* **Application Launch (`main.py`)**:
Unmutes all audio tracks in REAPER and sends grandMA3 to standby Cue 2 on Sequence 100:


```python
if hasattr(app, 'audio_controller'):
    app.audio_controller.unmute_all_tracks()

lighting.trigger_initial_startup_light()

```
When launch the code, there is a main staging light for when the trainers are first talking about how the game works.

* **Start Game Execution (`main.py`)**:
Turns off startup/tutorial lights, triggers Question 1 lights (Seq 93) with timed cues, and starts Track 6 Marker 20 intro audio:


```python
lighting.stop_startup_light()
lighting.stop_tutorial_lighting()

lighting.start_question_lighting(1)

if app and hasattr(app, 'audio_controller'):
    app.audio_controller.play_q1_intro()

```
When first run the code.
<img width="1280" height="960" alt="first run" src="https://github.com/huisenlim/EGL314TeamD/blob/main/Final/UI%20images/First%20run.jpg" />


* **Timed Lighting Cues (`lighting.py`)**:
Schedules dynamic cue progression across sequences 93–96:


```python
seq_num = seq_info["question_seq"]
send_command(f"Go+ Sequence {seq_num}")

timings = QUESTION_CUE_TIMINGS.get(q_num, [])
for delay, cue in timings:
    timer = threading.Timer(delay, _trigger_cue, args=(cue, seq_num))
    active_cue_timers.append(timer)
    timer.start()

```


* **Intro-to-Ambient Audio Transition (`reaper.py`)**:
Plays the intro on Track 6 and automatically switches to Track 4 Marker 29 background audio once the intro duration finishes:


```python
self.play_marker(intro_marker_action)

self.marker_timer = threading.Timer(
    intro_duration_seconds, 
    lambda: self.play_marker(MARKER_29_TRK4)
)
self.marker_timer.start()

```
When pressed start game question 1 will be played audio and lighting will sync together when the bossman is saying the options. It will be the same until the last question is played.

This is Q1.
<img width="1280" height="960" alt="Question1" src="https://github.com/huisenlim/EGL314TeamD/blob/main/Final/UI%20images/Question%201.jpg" />

This is Q2.
<img width="1280" height="960" alt="Question2" src="https://github.com/huisenlim/EGL314TeamD/blob/main/Final/UI%20images/Question%202.jpg" />

This is Q3.
<img width="1280" height="960" alt="Question3" src="https://github.com/huisenlim/EGL314TeamD/blob/main/Final/UI%20images/Question%203.jpg" />

This is Q4.
<img width="1280" height="960" alt="Question4" src="https://github.com/huisenlim/EGL314TeamD/blob/main/Final/UI%20images/Question%204.jpg" />


---

### **3. Submissions: YES and NO Logic**

* **Standard YES (`main.py`)**:
Validates if a tag is inside the physical question zone before triggering success:


```python
for zi, ghost in enumerate(game_logic.Ghosts):
    if ghost.get("active", True) and ghost.get("question") == game_logic.CURRENT_QUESTION:
        if game_logic.ptInGhost(tag.filt_position, ghost):
            ghost["active"] = False
            hit_detected = True

if hit_detected:
    state.question_answered = True
    if app and hasattr(app, 'audio_controller') and game_logic.CURRENT_QUESTION < 4:
        app.audio_controller.play_yes_q1_to_q3()
    lighting.trigger_question_success_light(game_logic.CURRENT_QUESTION, audio_controller=audio_ctrl)

```
When tag is in the zone(correct answer), lightings will turn green and audio will play a "correct" sound when yes button is pressed.

* **NO Button & Auto-Retry Loop (`main.py` & `reaper.py`)**:
Triggers lighting Sequence 97 for 5s and plays Track 6 Marker 21 for 4s before automatically restarting the active question intro:

```python
# main.py
lighting.trigger_no_button_sequence()
if app and hasattr(app, 'audio_controller'):
    app.audio_controller.play_no_button(on_finish_callback=repeat_current_question_intro)

# reaper.py
def play_no_button(self, on_finish_callback=None):
    self._cancel_timer()
    self.play_marker(MARKER_21_TRK6)
    if on_finish_callback:
        self.marker_timer = threading.Timer(4.0, on_finish_callback)
        self.marker_timer.start()

```
When tag is not in the zone(correct answer), lightings will turn red and audio will play a "laughing" sound coming out of the bossman and audio will replay the question when no button is pressed.

This is the yes and no button.
<img width="1280" height="960" alt="button" src="https://github.com/huisenlim/EGL314TeamD/blob/main/Final/UI%20images/Question%201.jpg" />


---

### **4. Question 4 Finale Sequence (`lighting.py`)**

* **Multi-Stage Automated Finale**:
Fires Track 34 Marker 22 and Sequences 89 & 101, triggers Sequence 102 Cue 9 and Track 6 Marker 23 after 9 seconds, and executes grandMA3 `Go Macro 15` with Track 36 Marker 24 after 11 seconds:


```python
if q_num == 4:
    send_command("Go+ Sequence 101")
    if audio_controller:
        audio_controller.play_yes_q1_to_q3()
    threading.Timer(9.0, _q4_fade_seq102, args=(audio_controller,)).start()

def _q4_fade_seq102(audio_controller=None):
    send_command(f"Go+ Cue 9 Sequence {FINAL_DIMMER_SEQUENCE}")
    if audio_controller:
        audio_controller.play_seq102_fade_audio()
    threading.Timer(11.0, _q4_delayed_macro15_transition, args=(audio_controller,)).start()

def _q4_delayed_macro15_transition(audio_controller=None):
    send_command("Off Sequence 89")
    send_command(f"Go Macro {FINAL_MACRO}")
    if audio_controller:
        audio_controller.play_seq90_audio()

```
Once final question is correct audio will play a dialouge coming from bossman after that the bossman will fade away and victory lights will be cued.

---

### **5. End Game Cleanup (`main.py` & `lighting.py`)**

* **Safe System Teardown**:
Stops all active audio transport in REAPER and sends grandMA3 to Cue 9 on Sequence 102:


```python
# main.py
if app and hasattr(app, 'audio_controller'):
    app.audio_controller.stop_all_audio()

lighting.end_game_lighting_cleanup()

# lighting.py
def end_game_lighting_cleanup():
    cancel_active_cue_timers()
    send_command(f"Go+ Cue 9 Sequence {FINAL_DIMMER_SEQUENCE}")

```
Once end game button is pressed, it will stop all cues both lighting and audio.

This is the end game button.
<img width="1280" height="960" alt="End Game" src="https://github.com/huisenlim/EGL314TeamD/blob/main/Final/UI%20images/End%20Game.jpg" />


---

## 3. Game Setup
### 3.1 Equipment used


## 4. Software Setup
For software both audio and lighting need to sync with each other to obtain the perfect game.
### 4.1 Audio Cues Setup

### 4.2 Lighting Cues Setup
The lighting module is responsible for sending Open Sound Control (OSC) commands directly to a grandMA3 console. It manages the visual atmosphere of the Interactive Question Arena by triggering specific light sequences, timed cues, and macros dynamically based on the active game state.

## Network Configuration
The module uses Python's `pythonosc.udp_client` to establish a one-way UDP connection with the grandMA3 console. 
*   **Console IP:** `192.168.254.252`
*   **Target Port:** `8080` (Default grandMA3 inbound OSC port)
*   **Command Address:** `/gma3/cmd`


## 5. Conditions For The Game
When playing a trivia question game, there is always a correct and wrong answer.

### 5.1 Win Condition
To win the game, players must answer all 4 question correctly in order to defeat the final ghost(bossman).
#### Audio Part

#### Lighting Part
Sequence & Cue Mappings
Specific grandMA3 sequences are mapped to global game events:
*   **Startup State:** Sequence `100` (automatically triggers Cue 2 upon application launch).
*   **Tutorial Mode:** Sequence `91`.
*   **Incorrect Action (NO Button):** Sequence `97` (plays for exactly 5 seconds before a background thread automatically turns it off).
*   **End Game / Final Dimmer:** Sequence `102` (specifically Cue 9).

### Question & Success Sequences
Each of the 4 progressive game questions utilizes a dedicated introductory sequence and a corresponding success sequence upon clearance:
*   **Question 1:** Intro Sequence `93` ➔ Success Sequence `86`.
*   **Question 2:** Intro Sequence `94` ➔ Success Sequence `87`.
*   **Question 3:** Intro Sequence `95` ➔ Success Sequence `88`.
*   **Question 4 (Boss Stage):** Intro Sequence `96` ➔ Success Sequence `89`.

### 5.2 Lose Condition
Players will only lose when they get the answer wrong but they can try again until they get it right.
#### Audio Part

#### Lighting Part


## 6. Final Outcome
After defeating the final ghost(bossman), victory is served and trainees would be able to obtain their license to become a trainer.
#### Audio Part

#### Lighting Part
## Core Logic & Functions

## `start_question_lighting(q_num)`
Clears any active lighting timers to prevent cue overlap, activates the target question's intro sequence, and schedules the staggered timed cues required for that specific question.

## `trigger_question_success_light(q_num, audio_controller)`
Executed when players successfully conquer a containment field. It cancels any pending intro cues, turns off the active question sequence, and immediately activates the corresponding success sequence. 

### The Boss Transition Logic (Question 4)
When Question 4 is cleared, the system executes a complex, threaded chain of audio-visual events to conclude the hunt:
1.  **Phase 1:** Sequence `101` fires, accompanied by Track 34 Marker 22 audio playback.
2.  **Phase 2 (9s Delay):** The system triggers Cue 9 on Sequence `102` (Final Dimmer) while simultaneously triggering the track fade-out audio marker.
3.  **Phase 3 (11s Delay):** Once the audio fade finishes, Sequence `89` is turned off, Macro `15` is executed, and the final concluding audio marker plays.

### Cleanup Utilities
*   **`cancel_active_cue_timers()`:** A safety utility that iterates through `active_cue_timers` and stops them, ensuring overlapping button presses don't cause late-firing cues.
*   **`end_game_lighting_cleanup()`:** Safely shuts down pending timers and triggers Cue 9 on Sequence `102` to dim the physical arena when the game session fully terminates.
