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
CURRENT_QUESTION = 1
DEFAULT_PORT = 5005

TAG_COLORS = ["#ff5252", "#42a5f5", "#66bb6a", "#ffb74d", "#ab47bc", "#26a69a", "#ec407a", "#bdbdbd", "#9c27b0", "#00bcd4"]

def setup_question_zones():
    colors = ["#ffff00", "#00ff95", "#ff9900", "#00e1ff"]
    ZONE_RADIUS = 0.80 
    
    # 1 Zone per Question (Questions 1 through 4)
    question_list = [
        {"center": (5.4, 2.7), "radius": ZONE_RADIUS, "min_radius": 0.10, "color": colors[0], "label": "Question 1 Zone", "active": True, "question": 1},
        {"center": (6.7, 3.9), "radius": ZONE_RADIUS, "min_radius": 0.10, "color": colors[1], "label": "Question 2 Zone", "active": True, "question": 2},
        {"center": (2.1, 4.9), "radius": ZONE_RADIUS, "min_radius": 0.10, "color": colors[2], "label": "Question 3 Zone", "active": True, "question": 3},
        {"center": (5.6, 6.5), "radius": ZONE_RADIUS, "min_radius": 0.10, "color": colors[3], "label": "Question 4 Zone", "active": True, "question": 4},
    ]
    return question_list

Ghosts = setup_question_zones()

def ptInGhost(point, ghost):
    if point is None: return False
    px, py = point; zx, zy = ghost["center"]; r = ghost["radius"] + GhostHitTol
    return ((px - zx)**2 + (py - zy)**2) <= (r * r)