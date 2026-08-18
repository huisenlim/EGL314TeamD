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

```python
# ───────── GMA3 NETWORK CONFIGURATION ─────────
GMA3_IP = "192.168.254.252"   # Replace with your grandMA3 console IP
GMA3_PORT = 8080             # Default grandMA3 inbound OSC port
GMA3_ADDR = "/gma3/cmd"
# ─────────────────────────────────────────────
```

```python
try:
    client = udp_client.SimpleUDPClient(GMA3_IP, GMA3_PORT)
    print(f"[LIGHTING] Connected to grandMA3 at {GMA3_IP}:{GMA3_PORT}")
except Exception as e:
    client = None
    print(f"[LIGHTING ERROR] Failed to initialize OSC client: {e}")
```

To execute these actions on the console, a helper function converts string commands into raw OSC messages:
```python
def send_command(cmd_string: str):
    """Sends a raw command string to the grandMA3 command line."""
    if client:
        try:
            client.send_message(GMA3_ADDR, cmd_string)
        except Exception as err:
            print(f"[LIGHTING ERROR] Network send failed: {err}")
```
### 4.3 Lighting Setup Checklist
Use this checklist to verify that all Open Sound Control (OSC) commands from the Python game server are successfully reaching the grandMA3 console and triggering the correct sequences.

## 1. Network & Initialization
- [ ] **Network Connection:** Verify the grandMA3 console is set to IP `192.168.254.252` and listening for OSC on UDP port `8080`.
- [ ] **Application Launch:** Run `python main.py`. 
  - *Expected Console Action:* Triggers `Go+ Cue 2 Sequence 100`.
  - *Visual Check:* Baseline environmental startup lighting is active.

## 2. UI & Pre-Game States
- [ ] **Tutorial Mode:** Click **START TUTORIAL**.
  - *Expected Console Action:* Triggers `Go+ Sequence 91`.
- [ ] **Game Start Initialization:** Click **START GAME**.
  - *Expected Console Action:* Sends `Off Sequence 100` and `Off Sequence 91`.
  - *Expected Console Action:* Immediately triggers `Go+ Sequence 93` (Question 1 Intro).

## 3. Question Intros & Timed Cues
- [ ] **Staggered Cues (Stage 1):** While Question 1 is active, do not press any buttons for 20 seconds.
  - *Expected Console Action:* Automatically triggers Cues 1, 2, 3, and 4 on Sequence `93` at the 6s, 10s, 14s, and 18s marks.

## 4. Game Action Responses
- [ ] **Lose Condition (NO Button):** Click **NO**.
  - *Expected Console Action:* Triggers `Go+ Sequence 97`.
  - *Expected Console Action:* Wait exactly 5 seconds; system should automatically send `Off Sequence 97`.
- [ ] **Win Condition (YES Button):** Physically enter the Question 1 zone and click **YES**.
  - *Expected Console Action:* Turns `Off Sequence 93`.
  - *Expected Console Action:* Triggers Success `Go+ Sequence 86`.
- [ ] **Stage Progression (CONTINUE Button):** Click **CONTINUE**.
  - *Expected Console Action:* Turns `Off Sequence 86`.
  - *Expected Console Action:* Triggers the next stage intro `Go+ Sequence 94`.

## 5. Final Boss Sequence (Question 4)
- [ ] **Boss Win Trigger:** Reach Question 4, enter the zone, and click **YES**.
  - *Expected Console Action:* Turns `Off Sequence 96`.
  - *Expected Console Action:* Triggers `Go+ Sequence 89` and `Go+ Sequence 101` simultaneously.
- [ ] **Boss Fade (9s Delay):** Wait 9 seconds after the boss win.
  - *Expected Console Action:* System automatically triggers `Go+ Cue 9 Sequence 102`.
- [ ] **Boss Conclusion (11s Delay):** Wait another 11 seconds (20s total).
  - *Expected Console Action:* Turns `Off Sequence 89`.
  - *Expected Console Action:* Executes `Go Macro 15`.

## 6. System Shutdown
- [ ] **End Game:** Click the **END GAME** button.
  - *Expected Console Action:* Pending timers are cancelled.
  - *Expected Console Action:* Triggers `Go+ Cue 9 Sequence 102` to bring the arena to its final resting state.
     
  
### 4.4 grandMA3 OSC Configuration Guide
To allow the Python game server to communicate with the grandMA3 console, you must configure the console to receive incoming Open Sound Control (OSC) network commands. 

### 1. Network Session Verification
Before configuring OSC, ensure your console or onPC software is active within a network session.
*   Navigate to the **Network** menu.
*   Verify that your station is actively in a session (indicated by the green highlight in the station list).

<img width="1918" height="1017" alt="OSC LIGHT NETWORK SESSION" src="https://github.com/user-attachments/assets/5f7154fa-003b-46d6-a53f-fe77d5e3b432" />


### 2. OSC In & Out Configuration
The core communication settings are established in the OSC Input/Output menu.

Navigate to the **In & Out** menu and select the **OSC** tab on the left sidebar.

Configure the global OSC settings at the top of the screen:
*   **Interface:** Select the network interface that matches your local network IP (e.g., `Wi-Fi (192.168.254.252)`).
*   **Enable Output:** Ensure this button is toggled ON (highlighted in yellow).
*   **Enable Input:** Ensure this button is toggled ON (highlighted in yellow) to allow the console to listen for commands.

### 3. OSC Data Setup
Create a new OSC Data row (e.g., `OSCData 1`) in the main window and apply the following specific configuration parameters:

*   **Destination IP:** `192.168.254.252`
*   **Mode:** `UDP`
*   **Port:** `8080` (This must match the `GMA3_PORT` defined in your Python script)
*   **Prefix:** `gma3` (This acts as the root address block for incoming commands)

Ensure the following command toggles are enabled for this data row:
*   **Receive:** `Yes`
*   **Send:** `Yes`
*   **Receive Command:** `Yes` (Crucial for allowing remote execution of macros and sequences)
*   **Send Command:** `Yes`



<img width="1918" height="1027" alt="OSC LIGHT" src="https://github.com/user-attachments/assets/5fec0cc7-f408-4843-bda4-3da3d611d717" />








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
The game dynamically triggers specific grandMA3 sequences and timed cues based on player actions and UI events.

System Startup
When the application first launches, it triggers a baseline environmental lighting state.
```python
def trigger_initial_startup_light():
    """Runs Cue 2 on Sequence 100 upon application launch."""
    print("[LIGHTING] App Launched: Triggering Cue 2 on Sequence 100...")
    send_command(f"Go+ Cue 2 Sequence {STARTUP_SEQUENCE}")
```

#### Question & Success Sequences
Each of the 4 progressive game questions utilizes a dedicated introductory sequence and a corresponding success sequence upon clearance:
*   **Question 1:** Intro Sequence `93` ➔ Success Sequence `86`.
*   **Question 2:** Intro Sequence `94` ➔ Success Sequence `87`.
*   **Question 3:** Intro Sequence `95` ➔ Success Sequence `88`.
*   **Question 4 (Boss Stage):** Intro Sequence `96` ➔ Success Sequence `89`.

  
When a player physically enters an active Question Zone and successfully clicks YES, the system turns off the introductory sequence and fires a success sequence. 
```python
def trigger_question_success_light(q_num: int, audio_controller=None):
    """
    Cancels pending intro cues, turns OFF question sequence (93-96), 
    and runs corresponding success sequence (86-89).
    """
    cancel_active_cue_timers()  # Stop any intro cues from firing late
    
    seq_info = QUESTION_SEQUENCES.get(q_num)
    if seq_info:
        send_command(f"Off Sequence {seq_info['question_seq']}")
        send_command(f"Go+ Sequence {seq_info['success_seq']}")
```


### 5.2 Lose Condition
Players will only lose when they get the answer wrong but they can try again until they get it right.
#### Audio Part

#### Lighting Part
## ❌ Lose Condition (Incorrect Action)

A lose or incorrect condition occurs when a player clicks the **NO** button on the game dashboard. This is used to indicate an incorrect answer or action, temporarily halting the current hunt.

When the **NO** button is clicked, the system triggers `trigger_no_button_sequence()`:
*   **Trigger:** The system sends a `Go+ Sequence 97` command to the grandMA3 console.
*   **Duration:** This sequence plays a specific error lighting state for exactly 5 seconds.
*   **Reset:** A background thread automatically sends an `Off Sequence 97` command after the 5 seconds have elapsed. Following this, the audio and lighting intros for the current question are automatically repeated so the player can try again.


```python
def trigger_no_button_sequence():
    """Plays Sequence 97 for 5 seconds when NO is pressed, then turns it off."""
    print("[LIGHTING] NO Button Pressed: Triggering Sequence 97 for 5 seconds...")
    send_command(f"Go+ Sequence {NO_BUTTON_SEQUENCE}")
    
    # Schedule automatic OFF after 5 seconds
    threading.Timer(5.0, _stop_no_button_sequence).start()

def _stop_no_button_sequence():
    """Helper timer callback to turn OFF Sequence 97."""
    print("[LIGHTING] 5s elapsed: Turning OFF Sequence 97...")
    send_command(f"Off Sequence {NO_BUTTON_SEQUENCE}")
```


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

### 👑 Final Boss Win (Question 4)
Defeating the final ghost (Question 4) triggers a specialized, multi-phase grandMA3 lighting transition to signify the end of the game:
1.  **Initial Clear:** Turns OFF Sequence `96`, triggers Success Sequence `89`, and simultaneously fires Sequence `101`.
2.  **9-Second Delay:** The system waits 9 seconds before automatically triggering Cue 9 on Sequence `102` (Final Dimmer fade).
3.  **11-Second Delay:** After 11 more seconds, the system turns OFF Sequence `89` and executes Macro `15` to conclude the visual experience.

For the final boss stage (Question 4), a special delayed lighting and audio transition sequence is triggered using threading.
```python
    # --- Special Transition Logic for Question 4 / Sequence 89 ---
    if q_num == 4:
        print("[LIGHTING] Q4 Cleared: Seq 89 active! Playing Track 34 Marker 22...")
        send_command("Go+ Sequence 101")
        
        # Step 1: Play Track 34 Marker 22 when Sequence 89 starts
        if audio_controller:
            audio_controller.play_yes_q1_to_q3()

        # Step 2: Hold for 9s before triggering Cue 9 on Sequence 102
        threading.Timer(9.0, _q4_fade_seq102, args=(audio_controller,)).start()
```
### Cleanup Utilities
*   **`cancel_active_cue_timers()`:** A safety utility that iterates through `active_cue_timers` and stops them, ensuring overlapping button presses don't cause late-firing cues.
*   **`end_game_lighting_cleanup()`:** Safely shuts down pending timers and triggers Cue 9 on Sequence `102` to dim the physical arena when the game session fully terminates.
