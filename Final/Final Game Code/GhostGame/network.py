# network.py
import time
from trilateration import trilaterate_2d

def make_osc_handler(state, anchor_ids, anchor_positions_list, csv_writer=None):
    
    # --- FAST LOCAL TRACKER TO PREVENT LAG ---
    packet_throttle = {} 
    
    def handle_distances(address, *args):
        # Silently ignore bad packets or if game is over
        if len(args) < 7 or state.stop: 
            return
        
        raw_tag_id = int(args[0])
        
        # --- THE LAG KILLER (UDP Buffer Clearer) ---
        # If less than 0.05 seconds (50ms) has passed since this tag's last packet, drop it!
        # This caps processing at 20 FPS, preventing the Pi's memory from clogging.
        now = time.time()
        if raw_tag_id in packet_throttle:
            if now - packet_throttle[raw_tag_id] < 0.05:
                return
        packet_throttle[raw_tag_id] = now
        
        distances = [float(v) for v in args[1:]]
        
        # 1. Grab ID safely
        with state.lock:
            if raw_tag_id not in state.row_color_index:
                assigned = False
                for idx in range(state.n_tags):
                    if state.row_color_index[idx] == -1:
                        state.row_color_index[idx] = raw_tag_id
                        assigned = True
                        print(f"[OSC NETWORK] Mapped physical Tag {raw_tag_id} to UI Index {idx}")
                        break
                if not assigned:
                    return
            tag_id = state.row_color_index.index(raw_tag_id)
                
        # 2. DO THE HEAVY MATH OUTSIDE THE LOCK SO THE GAME DOESN'T FREEZE!
        valid_distances = [distances[i] for i in anchor_ids if i < len(distances)]
        raw_pos = trilaterate_2d(anchor_positions_list, valid_distances)
        
        # 3. Quickly save the result back into memory
        with state.lock:
            tag = state.tags[tag_id]
            padded_dists = distances + [0.0] * (8 - len(distances))
            tag.last_distances = padded_dists[:8]
            tag.last_update = time.time()
            
            if raw_pos is not None:
                tag.kalman.predict()
                fx, fy = tag.kalman.update(raw_pos[0], raw_pos[1])
                tag.raw_position, tag.filt_position = raw_pos, (fx, fy)
            else:
                tag.kalman.predict()
            state.frame_count += 1
            
    return handle_distances