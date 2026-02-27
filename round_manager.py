# round_manager.py
"""
RoundManager — Stochastic Traffic Parameter Controller
=======================================================
Controls three probability models that govern traffic behaviour:

  1. Truncated-Normal speed distributions — now lane-dependent
     ─────────────────────────────────────────────────────────
     Each lane has its own (mean, std) pair reflecting real-world
     characteristics:
       Near  lane  : residential / slow  → low mean, tight σ
       Middle lane : chaotic urban mix   → bimodal (slow trucks + fast bikes)
       Far   lane  : highway-style flow  → high mean, moderate σ

  2. Bernoulli lane activation probabilities
     ────────────────────────────────────────
     get_lane_activation_probs() returns [p_near, p_middle, p_far].
     Spawner flips an independent Bernoulli coin per lane per arrival
     event.  Probabilities scale upward with round number to simulate
     congestion onset.

  3. All existing models (weighted categorical vehicle type, shrinking
     headway gap, Poisson mean arrival rate) are preserved unchanged.
"""

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
    Models realistic speed variance — most vehicles cluster near the mean,
    occasional fast/slow outliers exist but cannot exceed physical limits.
    Up to 20 rejection attempts; falls back to clamped mean on failure.
    """
    for _ in range(20):
        v = random.gauss(mean, std)
        if lo <= v <= hi:
            return v
    return max(lo, min(hi, mean))


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

    # ── Spawn timing (mean of the Poisson process) ───────────────────────
    def get_spawn_frequency(self) -> float:
        """
        Mean inter-arrival time in frames.
        Used by Spawner as E[T] = 1/λ for the Exponential distribution.
        """
        return float(max(self.min_spawn_rate,
                         self.base_spawn_rate - (self.current_round * 3)))

    # ── Lane-dependent speed (truncated normal) ──────────────────────────
    def get_speed_sample(self, vtype: str, lane: int = None) -> float:
        """
        Sample a vehicle speed from a truncated-normal distribution whose
        parameters depend on BOTH vehicle type AND lane:

          Lane 3 (near)   → residential character; low mean, tight σ
          Lane 2 (middle) → chaotic urban mix; bimodal approximated by
                            randomly selecting a low or high cluster
          Lane 1 (far)    → highway-style; high mean, moderate σ

        Mean and hi-bound shift upward each round (round_boost).
        """
        base_ranges = {
            "car":        (3.0, 6.0),
            "motorcycle": (5.0, 9.0),
            "bus":        (2.0, 4.0),
            "truck":      (2.0, 4.0),
        }
        lo, hi      = base_ranges.get(vtype, (3.0, 6.0))
        round_boost = (self.current_round - 1) * 0.25

        if lane == 3:      # ── Near lane: slow residential ───────────────
            mean = lo + (hi - lo) * 0.30 + round_boost * 0.60
            std  = 0.50 + (self.current_round - 1) * 0.03

        elif lane == 1:    # ── Far lane: highway-style ───────────────────
            mean = lo + (hi - lo) * 0.75 + round_boost
            std  = 0.90 + (self.current_round - 1) * 0.06

        else:              # ── Middle lane: chaotic bimodal ──────────────
            # Bimodal: 50 % from a slow cluster, 50 % from a fast cluster.
            # This approximates a mixture of heavy vehicles and motorcycles.
            if random.random() < 0.5:
                mean = lo + (hi - lo) * 0.25 + round_boost * 0.70   # slow peak
            else:
                mean = lo + (hi - lo) * 0.75 + round_boost           # fast peak
            std = 1.20 + (self.current_round - 1) * 0.07

        new_hi = hi + round_boost
        return truncated_normal_speed(mean, std, lo, new_hi)

    # ── Bernoulli lane activation probabilities ──────────────────────────
    def get_lane_activation_probs(self) -> list[float]:
        """
        Returns [p_near, p_middle, p_far].

        Each value is the independent Bernoulli probability that a given
        lane will spawn a vehicle at the current arrival event.

        Round 1 : near lane is reliably active; middle and far are rare.
        Round 8+: all three lanes are almost always active — full chaos.
        """
        r = self.current_round
        p_near   = min(0.90, 0.50 + r * 0.05)
        p_middle = min(0.80, 0.15 + r * 0.08)
        p_far    = min(0.75, 0.10 + r * 0.07)
        return [p_near, p_middle, p_far]

    # ── Vehicle type weights (weighted categorical) ───────────────────────
    def get_vehicle_weights(self) -> dict:
        """
        Round 1 : mostly cars, rare heavy vehicles.
        Round 5+: buses/trucks common, motorcycles swarm.
        """
        r = self.current_round
        return {
            "car":        max(1.0, 8.0 - r * 0.5),
            "motorcycle": min(6.0, 0.5 + r * 0.6),
            "bus":        min(5.0, r * 0.4),
            "truck":      min(4.0, r * 0.3),
        }

    # ── Lane weights (kept for legacy callers; Bernoulli model is primary) ─
    def get_lane_weights(self) -> list[float]:
        r = self.current_round
        return [
            max(1.0, 6.0 - r * 0.4),   # near
            min(5.0, 0.5 + r * 0.5),   # middle
            min(5.0, 0.5 + r * 0.4),   # far
        ]

    # ── Dynamic headway gap ──────────────────────────────────────────────
    def get_spawn_gap(self) -> int:
        """
        Minimum pixel gap between spawned vehicles.  Decreases each round
        to simulate higher traffic intensity (Poisson-style headway reduction).
        Floored at 70 px so vehicles do not overlap on spawn.
        """
        return max(70, 150 - self.current_round * 8)

    # ── Middle lane chaos probability ────────────────────────────────────
    def get_middle_bidirectional_prob(self) -> float:
        return min(0.9, 0.2 + self.current_round * 0.07)

    # ── Speed multiplier (vehicle.update compatibility) ──────────────────
    def get_traffic_speed_multiplier(self) -> float:
        return 1.0 + (self.current_round * 0.05)

    # ── Difficulty label ─────────────────────────────────────────────────
    def get_difficulty_label(self) -> str:
        r = self.current_round
        if r <= 2:  return "EASY"
        if r <= 4:  return "MEDIUM"
        if r <= 7:  return "HARD"
        return "CHAOS"