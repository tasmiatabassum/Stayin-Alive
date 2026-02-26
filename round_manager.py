# round_manager.py

class RoundManager:
    def __init__(self):
        self.current_round = 1
        self.wins = 0
        self.losses = 0
        
        # Difficulty parameters that scale up
        self.base_spawn_rate = 40  # Start relatively easy
        self.min_spawn_rate = 15   # Maximum chaos

    def record_win(self):
        self.wins += 1
        self.current_round += 1
        print(f"--- ROUND {self.current_round} START ---")

    def record_loss(self):
        self.losses += 1
        self.current_round += 1
        print(f"--- ROUND {self.current_round} START ---")

    def get_spawn_frequency(self):
        # Every round, the spawn rate gets 3 frames faster, until it hits the max chaos limit
        current_rate = self.base_spawn_rate - (self.current_round * 3)
        return max(self.min_spawn_rate, current_rate)

    def get_traffic_speed_multiplier(self):
        # Every round, cars get 5% faster
        return 1.0 + (self.current_round * 0.05)