# game_logic.py
import random

ANCHORS = {
    0: (0.0, 0.0),
    1: (0.0, 3.9),
    2: (0.0, 8.16),
    3: (9.5, 8.14),
    4: (9.5, 3.8),
    5: (9.5, 0.0),
}

VIEW_BOUNDS = (-1.50, 12.0, -1.50, 12.0)
GhostHitTol = 0.25  
CURRENT_WAVE = 1
DEFAULT_PORT = 5005
BUTTON_PIN = 18

TAG_COLORS = ["#ff5252", "#42a5f5", "#66bb6a", "#ffb74d", "#ab47bc", "#26a69a", "#ec407a", "#bdbdbd", "#9c27b0", "#00bcd4"]

def setup_wave_ghosts():
    names = ["Bob", "Stewart", "Tim", "Kevin", "Carl", "Dave", "Jerry"]
    colors = ["#ffff00", "#00ff95", "#ff9900", "#00e1ff", "#f088f0", "#ff007f", "#fc9090"]
    ZONE_RADIUS = 0.80 
    
    ghosts_list = [
        {"center": (2.5, 6.0), "radius": ZONE_RADIUS, "min_radius": 0.10, "color": colors[0], "label": names[0], "active": True, "wave": 1},
        {"center": (7.0, 6.0), "radius": ZONE_RADIUS, "min_radius": 0.10, "color": colors[1], "label": names[1], "active": True, "wave": 1},
        {"center": (4.75, 3.5), "radius": ZONE_RADIUS, "min_radius": 0.10, "color": colors[2], "label": names[2], "active": True, "wave": 1},
        {"center": (2.5, 2.5), "radius": ZONE_RADIUS, "min_radius": 0.10, "color": colors[3], "label": names[3], "active": True, "wave": 2},
        {"center": (7.0, 2.5), "radius": ZONE_RADIUS, "min_radius": 0.10, "color": colors[4], "label": names[4], "active": True, "wave": 2},
        {"center": (4.75, 6.0), "radius": ZONE_RADIUS, "min_radius": 0.10, "color": colors[5], "label": names[5], "active": True, "wave": 2},
    ]
    
    # Generate random static coordinates for Wave 3 (Jerry)
    while True:
        rand_x = random.uniform(1.0, 8.5)
        rand_y = random.uniform(1.0, 7.0)
        too_close = False
        for existing in ghosts_list:
            ex, ey = existing["center"]
            if (rand_x - ex)**2 + (rand_y - ey)**2 < (1.80 ** 2):
                too_close = True
                break
        if not too_close:
            break

    ghosts_list.append({
        "center": (rand_x, rand_y),
        "radius": ZONE_RADIUS, 
        "min_radius": 0.10, 
        "color": colors[6], 
        "label": names[6], 
        "active": True, 
        "wave": 3
    })
    return ghosts_list

Ghosts = setup_wave_ghosts()

def ptInGhost(point, ghost):
    if point is None: return False
    px, py = point; zx, zy = ghost["center"]; r = ghost["radius"] + GhostHitTol
    return ((px - zx)**2 + (py - zy)**2) <= (r * r)