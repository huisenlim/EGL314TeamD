#!/usr/bin/env python3
import argparse
import threading
import tkinter as tk

from pythonosc import dispatcher as osc_dispatcher
from pythonosc import osc_server

import game_logic
import lighting
from game_state import SharedState
from network import make_osc_handler
from display import ViewerApp

app = None

def repeat_current_question_intro():
    """Helper callback: Re-triggers current question intro audio and lighting cues after NO button finishes."""
    print(f"\n🔄 REPEATING INTRO for Question {game_logic.CURRENT_QUESTION}...")
    
    # Restart lighting sequence and cues
    lighting.start_question_lighting(game_logic.CURRENT_QUESTION)
    
    # Restart intro audio marker
    if app and hasattr(app, 'audio_controller'):
        if game_logic.CURRENT_QUESTION == 1:
            app.audio_controller.play_q1_intro()
        elif game_logic.CURRENT_QUESTION == 2:
            app.audio_controller.play_q2_intro()
        elif game_logic.CURRENT_QUESTION == 3:
            app.audio_controller.play_q3_intro()
        elif game_logic.CURRENT_QUESTION == 4:
            app.audio_controller.play_q4_intro()

def handle_tutorial_click():
    """Triggered when user clicks START TUTORIAL."""
    print("\n🎓 TUTORIAL STARTED: Turning ON Sequence 91...")
    lighting.start_tutorial_lighting()

def handle_start_click(state):
    """Triggered when user clicks START GAME."""
    with state.lock:
        state.game_active = True
        print("\n▶ GAME STARTED: Turning OFF Sequence 100 & 91, triggering Seq 93 & Track 6 Marker 20...")
        
        # Turn OFF startup sequence (100) and tutorial lighting (91)
        lighting.stop_startup_light()
        lighting.stop_tutorial_lighting()
        
        # Start Question 1 sequence (fires Seq 93 and schedules timed Cues 1-4)
        lighting.start_question_lighting(1)
        
        if app and hasattr(app, 'audio_controller'):
            app.audio_controller.play_q1_intro()

def handle_yes_click(state, root):
    """Triggered when user clicks YES."""
    with state.lock:
        if not state.game_won and state.game_active and not state.question_answered:
            hit_detected = False
            
            for tag_id, tag in enumerate(state.tags):
                if tag.filt_position is None:
                    continue
                
                for zi, ghost in enumerate(game_logic.Ghosts):
                    if ghost.get("active", True) and ghost.get("question") == game_logic.CURRENT_QUESTION:
                        if game_logic.ptInGhost(tag.filt_position, ghost):
                            print(f"\n✅ YES CONFIRMED: Tag {tag_id} in Question {game_logic.CURRENT_QUESTION} Zone!")
                            ghost["active"] = False
                            hit_detected = True

            if hit_detected:
                state.question_answered = True
                
                # Audio triggers for YES (Q1 - Q3 play Marker 22; Q4 handled in trigger_question_success_light)
                if app and hasattr(app, 'audio_controller'):
                    if game_logic.CURRENT_QUESTION < 4:
                        app.audio_controller.play_yes_q1_to_q3()
                
                # Turn OFF Question Sequence (93-96) & Run Success Sequence (86-89)
                audio_ctrl = app.audio_controller if (app and hasattr(app, 'audio_controller')) else None
                lighting.trigger_question_success_light(game_logic.CURRENT_QUESTION, audio_controller=audio_ctrl)

                if app:
                    if game_logic.CURRENT_QUESTION == 4:
                        state.game_won = True
                        root.after(0, app.show_end_game_state)
                    else:
                        root.after(0, app.show_continue_state)
            else:
                print(f"\n⚠️ ACTION DENIED: No tag inside Question {game_logic.CURRENT_QUESTION} Zone!")

def handle_no_click(state):
    """Triggered when user clicks NO."""
    print(f"\n❌ NO CLICKED: Playing Track 6 Marker 21 for 4s & Sequence 97 for 5s...")
    
    # Play Sequence 97 for 5 seconds on grandMA3
    lighting.trigger_no_button_sequence()
    
    # Play NO audio marker for 4s, then repeat the active question intro
    if app and hasattr(app, 'audio_controller'):
        app.audio_controller.play_no_button(on_finish_callback=repeat_current_question_intro)

def handle_continue_click(state, root):
    """Triggered when user clicks CONTINUE."""
    with state.lock:
        if state.question_answered and game_logic.CURRENT_QUESTION < 4:
            # Turn OFF current success sequence (86/87/88)
            lighting.handle_continue_lighting(game_logic.CURRENT_QUESTION)
            
            game_logic.CURRENT_QUESTION += 1
            state.question_answered = False
            print(f"\n➡️ CONTINUING: Moving to Question {game_logic.CURRENT_QUESTION}...")
            
            # Start Question Sequence for next Question (schedules Cues 1-4) & Play Audio
            lighting.start_question_lighting(game_logic.CURRENT_QUESTION)
            
            if app and hasattr(app, 'audio_controller'):
                if game_logic.CURRENT_QUESTION == 2:
                    app.audio_controller.play_q2_intro()
                elif game_logic.CURRENT_QUESTION == 3:
                    app.audio_controller.play_q3_intro()
                elif game_logic.CURRENT_QUESTION == 4:
                    app.audio_controller.play_q4_intro()
            
            if app: 
                root.after(0, app.reset_to_question_state)

def handle_end_game_click(state, root):
    """Triggered when user clicks END GAME."""
    print("\n🛑 END GAME: Stopping all audio, turning OFF Sequence 98, and exiting code...")
    
    # 1. Stop all REAPER audio immediately
    if app and hasattr(app, 'audio_controller'):
        app.audio_controller.stop_all_audio()

    # 2. Turn off lighting Sequence 98
    lighting.end_game_lighting_cleanup()
    
    if app:
        root.after(500, app.shutdown)

def main():
    global app
    ap = argparse.ArgumentParser()
    ap.add_argument("--tags", type=int, default=4)
    ap.add_argument("--port", type=int, default=game_logic.DEFAULT_PORT)
    ap.add_argument("--no-circles", action="store_true")
    ap.add_argument("--windowed", action="store_true")
    args = ap.parse_args()

    state = SharedState(n_tags=args.tags)
    state.game_active = False # Set game idle until START button is pressed
    
    for tag in state.tags:
        tag.kalman.dt = 0.10

    root = tk.Tk()

    anchor_ids = sorted(game_logic.ANCHORS.keys())
    anchor_positions_list = [game_logic.ANCHORS[i] for i in anchor_ids]
    
    disp = osc_dispatcher.Dispatcher()
    handler = make_osc_handler(state, anchor_ids, anchor_positions_list)
    disp.map("/distances", handler)

    server = osc_server.OSCUDPServer(("0.0.0.0", args.port), disp)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    print(f"[game] Interactive Arena online via port {args.port}")
    
    app = ViewerApp(
        root, state, 
        show_circles=not args.no_circles, 
        fullscreen=not args.windowed,
        on_tutorial_callback=handle_tutorial_click,
        on_start_callback=lambda: handle_start_click(state),
        on_yes_callback=lambda: handle_yes_click(state, root),
        on_no_callback=lambda: handle_no_click(state),
        on_continue_callback=lambda: handle_continue_click(state, root),
        on_end_game_callback=lambda: handle_end_game_click(state, root)
    )

    # 1. Unmute all REAPER tracks on startup (No audio is triggered until START GAME is pressed)
    if hasattr(app, 'audio_controller'):
        app.audio_controller.unmute_all_tracks()

    # 2. Trigger Cue 2 on Sequence 100 on initial code launch
    lighting.trigger_initial_startup_light()

    try: 
        root.mainloop()
    except KeyboardInterrupt: 
        pass
    finally:
        state.stop = True
        server.shutdown()
        print("[game] System shut down safely.")

if __name__ == "__main__":
    main()