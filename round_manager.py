# round_manager.py
import json
import os
import random
import math

HIGHSCORE_FILE = "highscores.json"


def _load_highscores():
    if os.path.exists(HIGHSCORE_FILE):
        with open(HIGHSCORE_FILE, "r") as f:
            return json.load(f)
    return {"Badrul": 0, "Mrittika": 0}


def _save_highscores(data):
    with open(HIGHSCORE_FILE, "w") as f:
        json.dump(data, f)


def weighted_choice(options, weights):
    """
    Weighted categorical distribution.
    options: list of values
    weights: list of non-negative floats (need not sum to 1)
    """
    total = sum(weights)
    r = random.uniform(0, total)
    cumulative = 0
    for opt, w in zip(options, weights):
        cumulative += w
        if r <= cumulative:
            return opt
    return options[-1]


def truncated_normal_speed(mean, std, lo, hi):
    """
    Sample from a normal distribution, rejecting values outside [lo, hi].
    Models realistic speed variance — most vehicles cluster near mean,
    occasional fast/slow outliers exist but can't exceed physical limits.
    """
    for _ in range(20):          # max rejection attempts
        v = random.gauss(mean, std)
        if lo <= v <= hi:
            return v
    return max(lo, min(hi, mean))  # fallback: clamp


class RoundManager:
    def __init__(self, character_name=""):
        self.current_round  = 1
        self.wins           = 0
        self.losses         = 0
        self.score          = 0
        self.character_name = character_name
        self.new_highscore  = False

        self._highscores = _load_highscores()
        self.high_score  = self._highscores.get(character_name, 0)

        self.base_spawn_rate = 40
        self.min_spawn_rate  = 15

    # ── Score ────────────────────────────────────────────────────────────
    def _update_score(self, delta):
        self.score = max(0, self.score + delta)
        if self.score > self.high_score:
            self.high_score    = self.score
            self.new_highscore = True
            self._highscores[self.character_name] = self.high_score
            _save_highscores(self._highscores)

    def record_win(self):
        self.wins += 1
        self.current_round += 1
        self._update_score(10 + self.current_round * 2)
        print(f"--- ROUND {self.current_round} | SCORE {self.score} ---")

    def record_loss(self):
        self.losses += 1
        self.current_round += 1
        self._update_score(-3)
        print(f"--- ROUND {self.current_round} | SCORE {self.score} (loss) ---")

    # ── Spawn timing ─────────────────────────────────────────────────────
    def get_spawn_frequency(self):
        return max(self.min_spawn_rate,
                   self.base_spawn_rate - (self.current_round * 3))

    # ── Speed (truncated normal) ─────────────────────────────────────────
    def get_speed_sample(self, vtype):
        """
        Returns a speed magnitude (always positive).
        Mean and std scale with round number.
        Each vehicle type has its own base range.
        """
        base_ranges = {
            "car":        (3.0, 6.0),
            "motorcycle": (5.0, 9.0),
            "bus":        (2.0, 4.0),
            "truck":      (2.0, 4.0),
        }
        lo, hi = base_ranges.get(vtype, (3.0, 6.0))
        # Mean shifts upward each round, std widens slightly
        round_boost = (self.current_round - 1) * 0.25
        mean = (lo + hi) / 2 + round_boost
        std  = 0.8 + (self.current_round - 1) * 0.05
        new_hi = hi + round_boost
        return truncated_normal_speed(mean, std, lo, new_hi)

    # ── Vehicle type weights (weighted categorical) ───────────────────────
    def get_vehicle_weights(self):
        """
        Round 1 : mostly cars, rare heavy vehicles.
        Round 5+: buses/trucks common, motorcycles swarm.
        Returns dict {vtype: weight}
        """
        r = self.current_round
        return {
            "car":        max(1.0, 8.0 - r * 0.5),
            "motorcycle": min(6.0, 0.5 + r * 0.6),
            "bus":        min(5.0, r * 0.4),
            "truck":      min(4.0, r * 0.3),
        }

    # ── Lane weights (weighted categorical) ──────────────────────────────
    def get_lane_weights(self):
        """
        Round 1 : near lane dominates (player starts near it).
        Round 5+: all three lanes equally dangerous.
        Returns [near_w, middle_w, far_w]
        """
        r = self.current_round
        near_w   = max(1.0, 6.0 - r * 0.4)
        middle_w = min(5.0, 0.5 + r * 0.5)
        far_w    = min(5.0, 0.5 + r * 0.4)
        return [near_w, middle_w, far_w]

    # ── Spawn gap (headway model) ─────────────────────────────────────────
    def get_spawn_gap(self):
        """
        Minimum pixel gap between spawned vehicles decreases each round,
        simulating higher traffic intensity (Poisson-style headway reduction).
        Floor at 70px so vehicles don't overlap on spawn.
        """
        return max(70, 150 - self.current_round * 8)

    # ── Middle lane chaos probability ────────────────────────────────────
    def get_middle_bidirectional_prob(self):
        """
        Probability that middle lane spawns traffic in BOTH directions
        (as opposed to a single dominant direction).
        Increases each round.
        """
        return min(0.9, 0.2 + self.current_round * 0.07)

    # ── Speed multiplier (kept for vehicle.update compatibility) ─────────
    def get_traffic_speed_multiplier(self):
        return 1.0 + (self.current_round * 0.05)

    # ── Human-readable summary for HUD/debug ─────────────────────────────
    def get_difficulty_label(self):
        r = self.current_round
        if r <= 2:  return "EASY"
        if r <= 4:  return "MEDIUM"
        if r <= 7:  return "HARD"
        return "CHAOS"