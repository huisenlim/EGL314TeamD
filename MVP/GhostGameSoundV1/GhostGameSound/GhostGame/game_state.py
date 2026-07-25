# game_state.py
import time
import threading
from dataclasses import dataclass, field
from trilateration import Kalman2D

@dataclass
class TagState:
    last_distances: list = field(default_factory=lambda: [0.0] * 8)
    raw_position: tuple = None
    filt_position: tuple = None
    last_update: float = 0.0
    kalman: Kalman2D = field(default_factory=Kalman2D)
    ghosts_inside: set = field(default_factory=set)

class SharedState:
    def __init__(self, n_tags):
        self.n_tags = n_tags
        self.tags = [TagState() for _ in range(n_tags)]
        self.row_color_index = [-1] * n_tags
        self.lock = threading.Lock()
        
        # System tracking
        self.frame_count = 0
        self.start_time = time.time()
        self.last_time = time.time() 
        self.stop = False
        self.button_pressed = False
        
        # Game mechanics
        self.game_won = False
        self.game_lost = False
        
        # Countdown Timer (150 seconds)
        self.time_left = 150.0 
        self.timer_active = False # Timer stays paused until the tutorial is dismissed