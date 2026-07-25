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

try:
    from gpiozero import Button
    HAS_GPIO = True
except (ImportError, RuntimeError):
    Button = None
    HAS_GPIO = False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tags", type=int, default=2)
    ap.add_argument("--port", type=int, default=game_logic.DEFAULT_PORT)
    ap.add_argument("--no-circles", action="store_true")
    ap.add_argument("--windowed", action="store_true")
    args = ap.parse_args()

    state = SharedState(n_tags=args.tags)
    for tag in state.tags:
        tag.kalman.dt = 0.10

    root = tk.Tk()

    def handle_button_event(state, is_pressed):
        with state.lock:
            state.button_pressed = is_pressed
            
            # Only trigger hit detection on button PRESS down
            if is_pressed and not state.game_won and not state.game_lost and state.timer_active:
                hit_detected = False
                
                # STEP 1: Process tag hit checks for current wave ghosts
                for tag_id, tag in enumerate(state.tags):
                    if tag.filt_position is None:
                        continue
                    
                    for zi, ghost in enumerate(game_logic.Ghosts):
                        if ghost.get("active", True) and ghost.get("wave") == game_logic.CURRENT_WAVE:
                            if game_logic.ptInGhost(tag.filt_position, ghost):
                                print(f"\n🎯 DISPELLED: Tag {tag_id} hit Wave {game_logic.CURRENT_WAVE} Ghost [{ghost['label']}]!")
                                ghost["active"] = False
                                hit_detected = True
                                
                                # Turn OFF the individual light for this dispelled ghost
                                lighting.set_ghost_light(zi, turn_on=False)

                # STEP 2: Evaluate Wave Progression & Audio / Lighting Triggers
                if hit_detected:
                    state.time_left += 30.0
                    
                    # Trigger Ghost Kill sound in Reaper & L-ISA
                    if hasattr(app, 'audio_controller'):
                        app.audio_controller.trigger_alarm()
                    
                    # Check if all ghosts in the CURRENT wave are dispelled
                    wave_cleared = all(
                        not g.get("active", True) 
                        for g in game_logic.Ghosts 
                        if g.get("wave") == game_logic.CURRENT_WAVE
                    )
                    
                    if wave_cleared:
                        if game_logic.CURRENT_WAVE < 4:
                            game_logic.CURRENT_WAVE += 1
                            print(f"\n🌊 WAVE CLEARED! Transitioning to Wave {game_logic.CURRENT_WAVE}...")
                            
                            # Trigger Sequence when reaching Wave 3 (Final Boss)
                            if game_logic.CURRENT_WAVE == 3:
                                lighting.trigger_final_ghost_light()

                            root.after(0, app.force_instant_ui_refresh)
                        else:
                            state.game_won = True
                            state.timer_active = False 
                            print("\n🏆 !!! WIN CONDITION ACHIEVED !!! All arena grid sectors cleared! 🏆")
                            
                            # Kills final boss light and triggers victory sequence
                            lighting.trigger_game_finish_light()

                            root.after(0, app.force_instant_ui_refresh)
                    else:
                        root.after(0, app.force_instant_ui_refresh)
                else:
                    # Penalty for pressing button without hitting a ghost
                    state.time_left -= 5.0

    physical_button = None
    if HAS_GPIO:
        try:
            physical_button = Button(game_logic.BUTTON_PIN, pull_up=True, bounce_time=0.2)
            physical_button.when_pressed = lambda: handle_button_event(state, True)
            physical_button.when_released = lambda: handle_button_event(state, False)
            print("\n[GPIO SYSTEM] gpiozero successfully bound to BCM 18.")
        except Exception as e:
            print(f"\n[CRITICAL ERROR] gpiozero failed: {e}")
    else:
        print("\n[GPIO NOT AVAILABLE] Running without local hardware button. Listening for remote OSC events or spacebar.\n")

    anchor_ids = sorted(game_logic.ANCHORS.keys())
    anchor_positions_list = [game_logic.ANCHORS[i] for i in anchor_ids]
    
    disp = osc_dispatcher.Dispatcher()
    handler = make_osc_handler(state, anchor_ids, anchor_positions_list)
    disp.map("/distances", handler)

    def handle_remote_button(address, *args):
        if len(args) > 0:
            is_pressed = bool(args[0])
            handle_button_event(state, is_pressed)

    disp.map("/button", handle_remote_button)

    server = osc_server.OSCUDPServer(("0.0.0.0", args.port), disp)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    print(f"[game] Dynamic network wave tracker online via port {args.port}")
    app = ViewerApp(root, state, show_circles=not args.no_circles, fullscreen=not args.windowed)

    root.bind("<space>", lambda e: handle_button_event(state, True))
    root.bind("<KeyRelease-space>", lambda e: handle_button_event(state, False))

    try: 
        root.mainloop()
    except KeyboardInterrupt: 
        pass
    finally:
        state.stop = True
        server.shutdown()
        if physical_button:
            physical_button.close()
        print("[game] Runtime hardware structures unmounted safely.")

if __name__ == "__main__":
    main()