# round_manager.py
"""
RoundManager — Stochastic Traffic Parameter Controller
=======================================================
Now level-aware: level_config parameters override base values.

Models in use:
  1. Poisson / Exponential inter-arrival  (spawner.py)
  2. Nagel-Schreckenberg CA               (vehicle.py)
  3. Truncated-Normal speed, lane-dep.    (get_speed_sample)
  4. Bernoulli lane activation            (get_lane_activation_probs)
  5. Weighted categorical vehicle type    (get_vehicle_weights)
  6. Log-Normal gap acceptance            (logger.py)
"""

import json, os, random, math

HIGHSCORE_FILE = "highscores.json"


def _load_hs():
    if os.path.exists(HIGHSCORE_FILE):
        with open(HIGHSCORE_FILE) as f:
            return json.load(f)
    return {"Badrul": 0, "Mrittika": 0}

def _save_hs(data):
    with open(HIGHSCORE_FILE, "w") as f:
        json.dump(data, f)


def weighted_choice(options, weights):
    total, r, cum = sum(weights), random.uniform(0, sum(weights)), 0
    for opt, w in zip(options, weights):
        cum += w
        if r <= cum:
            return opt
    return options[-1]


def truncated_normal_speed(mean, std, lo, hi):
    for _ in range(20):
        v = random.gauss(mean, std)
        if lo <= v <= hi:
            return v
    return max(lo, min(hi, mean))


class RoundManager:
    def __init__(self, character_name="", level_cfg=None):
        self.character_name = character_name
        self.current_round  = 1
        self.wins           = 0
        self.losses         = 0
        self.score          = 0
        self.new_highscore  = False

        self._hs     = _load_hs()
        self.high_score = self._hs.get(character_name, 0)

        # Level config — if None use flat defaults
        self.level_cfg = level_cfg or {}

        # Base spawn timing
        self.base_spawn_rate = 40
        self.min_spawn_rate  = 15

        # ── Non-Homogeneous Poisson Process session clock ─────────────
        self.session_frame = 0          # incremented externally each frame
        self.session_duration = 18000   # 5 min at 60 fps — full λ(t) cycle

    # ── Level parameter helpers ──────────────────────────────────────────
    @property
    def _lambda_mult(self):
        return self.level_cfg.get("lambda_mult", 1.0)

    @property
    def _speed_mult(self):
        return self.level_cfg.get("speed_mult", 1.0)

    @property
    def _nasch_p_slow(self):
        return self.level_cfg.get("nasch_p_slow", 0.15)

    @property
    def _bidir_prob(self):
        return self.level_cfg.get("bidir_prob_mid", 0.40)

    @property
    def _vehicle_mix(self):
        return self.level_cfg.get("vehicle_mix", None)

    # ── Score ────────────────────────────────────────────────────────────
    def _update_score(self, delta):
        self.score = max(0, self.score + delta)
        if self.score > self.high_score:
            self.high_score    = self.score
            self.new_highscore = True
            self._hs[self.character_name] = self.high_score
            _save_hs(self._hs)

    def record_win(self):
        self.wins += 1
        self.current_round += 1
        self._update_score(10 + self.current_round * 2)

    def record_loss(self):
        self.losses += 1
        self.current_round += 1
        self._update_score(-3)

    # ── Poisson mean inter-arrival ───────────────────────────────────────
    def get_spawn_frequency(self) -> float:
        base = max(self.min_spawn_rate,
                   self.base_spawn_rate - (self.current_round * 3))
        return base / self._lambda_mult

    # ── Truncated-normal speed, lane-dependent ───────────────────────────
    def get_speed_sample(self, vtype: str, lane: int = None) -> float:
        base_ranges = {
            "car":        (3.0, 6.0),
            "motorcycle": (5.0, 9.0),
            "bus":        (2.0, 4.0),
            "truck":      (2.0, 4.0),
            "cng":        (2.0, 4.5),
        }
        lo, hi      = base_ranges.get(vtype, (3.0, 6.0))
        round_boost = (self.current_round - 1) * 0.20 * self._speed_mult

        if lane == 3:       # near — residential slow
            mean = lo + (hi - lo) * 0.30 + round_boost * 0.60
            std  = 0.50 + (self.current_round - 1) * 0.03
        elif lane == 1:     # far — highway fast
            mean = lo + (hi - lo) * 0.75 + round_boost
            std  = 0.90 + (self.current_round - 1) * 0.06
        else:               # middle — bimodal chaos
            if random.random() < 0.5:
                mean = lo + (hi - lo) * 0.25 + round_boost * 0.70
            else:
                mean = lo + (hi - lo) * 0.75 + round_boost
            std = 1.20 + (self.current_round - 1) * 0.07

        new_hi = (hi + round_boost) * self._speed_mult
        return truncated_normal_speed(mean * self._speed_mult, std, lo, new_hi)

    # ── Bernoulli lane activation ─────────────────────────────────────────
    def get_lane_activation_probs(self) -> list:
        r = self.current_round
        lm = self._lambda_mult
        p_near   = min(0.92, (0.50 + r * 0.05) * lm)
        p_middle = min(0.85, (0.15 + r * 0.08) * lm)
        p_far    = min(0.80, (0.10 + r * 0.07) * lm)
        return [p_near, p_middle, p_far]

    # ── Weighted categorical vehicle type ────────────────────────────────
    def get_vehicle_weights(self) -> dict:
        if self._vehicle_mix:
            return dict(self._vehicle_mix)
        r = self.current_round
        return {
            "car":        max(1.0, 8.0 - r * 0.5),
            "motorcycle": min(6.0, 0.5 + r * 0.6),
            "bus":        min(5.0, r * 0.4),
            "truck":      min(4.0, r * 0.3),
            "cng":        min(3.0, r * 0.3),
        }

    # ── NaSch p_slow ─────────────────────────────
    def get_nasch_p_slow(self, vtype: str) -> float:
        base = {
            "car": 0.10, "motorcycle": 0.08,
            "bus": 0.15, "truck": 0.18, "cng": 0.20,
        }
        return max(0.03, base.get(vtype, 0.12) * (self._nasch_p_slow / 0.15))

    # ── Dynamic headway gap ───────────────────────────────────────────────
    def get_spawn_gap(self) -> int:
        return max(65, 150 - self.current_round * 7)

    # ── Middle-lane bidirectional probability ─────────────────────────────
    def get_middle_bidirectional_prob(self) -> float:
        base = self._bidir_prob
        return min(0.95, base + self.current_round * 0.04)

    # ── Non-Homogeneous Poisson Process  λ(t) ────────────────────────────
    def get_rush_hour_lambda_mult(self) -> float:
        tau = min(1.0, self.session_frame / max(1, self.session_duration))
        morning = 0.85 * math.exp(-((tau - 0.20) ** 2) / (2 * 0.06 ** 2))
        evening = 1.00 * math.exp(-((tau - 0.72) ** 2) / (2 * 0.05 ** 2))
        return 0.40 + morning + evening

    def get_rush_phase(self) -> tuple:
        mult = self.get_rush_hour_lambda_mult()
        intensity = min(1.0, (mult - 0.40) / 1.00)

        if intensity < 0.20:
            label = "OFF-PEAK"
        elif intensity < 0.45:
            label = "BUILDING"
        elif intensity < 0.70:
            label = "RUSH HOUR"
        elif intensity < 0.88:
            label = "PEAK RUSH"
        else:
            label = "⚠ GRIDLOCK"
        return label, intensity

    def tick_session(self):
        self.session_frame += 1

    # ── Legacy compat ─────────────────────────────────────────────────────
    def get_lane_weights(self):
        r = self.current_round
        return [max(1.0, 6.0-r*0.4), min(5.0, 0.5+r*0.5), min(5.0, 0.5+r*0.4)]

    def get_traffic_speed_multiplier(self):
        return (1.0 + self.current_round * 0.05) * self._speed_mult

    def get_difficulty_label(self):
        return self.level_cfg.get("difficulty",
               ["EASY","EASY","MEDIUM","MEDIUM","HARD","HARD","CHAOS"][
                   min(6, self.current_round // 2)])