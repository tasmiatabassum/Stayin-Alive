# spawner.py
"""
Spawner — Traffic Arrival Model
================================
Stochastic models in use:

1.  Non-Homogeneous Poisson Process (NHPP) arrivals
    ------------------------------------------------
    The arrival rate λ(t) now varies over the session to simulate
    Dhaka's morning rush hour.  The intensity function is a mixture
    of two Gaussian bumps (onset and peak) that produce a natural
    ramp-up, plateau, then taper pattern.

        λ(t) = λ_base(round) × I(t)

    where I(t) is a normalised intensity curve in [0.25, 2.0] and
    t is the session time in seconds.

    This replaces the earlier homogeneous Poisson process while keeping
    the Exponential inter-arrival draw as the per-step mechanism:

        T_next ~ Exp(λ(t))

2.  Bernoulli Lane Activation  (unchanged)
    ----------------------------------------
    Each lane independently activates per arrival event.

3.  Rain friction multiplier
    -------------------------
    When EnvironmentManager reports rain, the NaSch p_slow for every
    spawned vehicle is scaled up via vehicle_p_slow_mult.  This is
    stored on each Vehicle as p_slow_extra and read in vehicle._nasch_step.
"""

import random
import math
from vehicle import Vehicle
from config import *
from round_manager import weighted_choice


# ── NHPP intensity curve ────────────────────────────────────────────────
# Two Gaussian peaks centred at t=90s (early rush) and t=240s (full rush)
_RUSH_PEAKS  = [(90,  60, 1.2),   # (centre_s, sigma_s, amplitude)
                (240, 90, 2.0)]
_BASE_I      = 0.25                # minimum intensity (off-peak)

def _nhpp_intensity(t_seconds: float) -> float:
    """
    Normalised intensity I(t) ∈ [_BASE_I, ~2.0].
    Peaks model morning rush hour onset and peak congestion.
    """
    val = _BASE_I
    for mu, sigma, amp in _RUSH_PEAKS:
        val += amp * math.exp(-0.5 * ((t_seconds - mu) / sigma) ** 2)
    return val


class Spawner:
    def __init__(self, round_manager, env_manager=None):
        self.vehicles      = []
        self.rm            = round_manager
        self._env          = env_manager   # EnvironmentManager or None
        self._frame        = 0
        self._session_time = 0.0           # seconds since game start
        self._fps          = FPS
        self._next_spawn   = self._sample_interarrival()

    # ── NHPP inter-arrival time ─────────────────────────────────────────
    def _sample_interarrival(self) -> float:
        """
        Draw T ~ Exp(λ(t)) where λ(t) incorporates the rush-hour curve.
        Mean inter-arrival = base_mean / I(t).
        """
        base_mean = self.rm.get_spawn_frequency()      # frames (from round)
        intensity  = _nhpp_intensity(self._session_time)
        mean_frames = max(8.0, base_mean / intensity)  # clamp to prevent collapse
        lam         = 1.0 / mean_frames
        return random.expovariate(lam)

    # ── Main update ─────────────────────────────────────────────────────
    def update(self):
        self._frame         += 1
        self._session_time   = self._frame / self._fps

        if self._frame >= self._next_spawn:
            self.attempt_spawn()
            self._frame      = 0
            self._next_spawn = self._sample_interarrival()

        # Rain multiplier for NaSch p_slow
        p_slow_mult = (self._env.vehicle_p_slow_mult
                       if self._env is not None else 1.0)

        multiplier = self.rm.get_traffic_speed_multiplier()
        for v in self.vehicles:
            v.update(self.vehicles, multiplier, p_slow_mult)

        # Cull off-screen vehicles
        self.vehicles = [v for v in self.vehicles
                         if -200 < v.rect.x < SCREEN_WIDTH + 200]

    # ── Bernoulli lane activation ────────────────────────────────────────
    def attempt_spawn(self):
        lane_probs = self.rm.get_lane_activation_probs()

        lane_defs = [
            (3, NEAR_LANE_Y,    True),
            (2, MIDDLE_LANE_Y,  None),
            (1, FAR_LANE_Y,     False),
        ]

        for (lane_id, target_y, fixed_left), p_lane in zip(lane_defs, lane_probs):
            if random.random() > p_lane:
                continue

            sub_lane = random.choice([0, 1])

            if fixed_left is None:
                bidir   = self.rm.get_middle_bidirectional_prob()
                go_left = random.random() < bidir
            else:
                go_left = fixed_left

            tw    = self.rm.get_vehicle_weights()
            vtype = weighted_choice(list(tw.keys()), list(tw.values()))

            spawn_gap = self.rm.get_spawn_gap()

            if self.is_lane_clear(target_y, sub_lane, go_left, spawn_gap):
                speed = self.rm.get_speed_sample(vtype, lane_id)
                self.vehicles.append(
                    Vehicle(target_y, go_left, sub_lane,
                            vtype=vtype, speed_override=speed)
                )

    # ── Headway guard ───────────────────────────────────────────────────
    def is_lane_clear(self, lane_y, sub_lane, is_moving_left, gap) -> bool:
        for v in self.vehicles:
            if abs(v.rect.y - lane_y) < 100 and v.sub_lane == sub_lane:
                if is_moving_left:
                    if v.rect.x > SCREEN_WIDTH - gap:
                        return False
                else:
                    if v.rect.x < gap:
                        return False
        return True

    def draw(self, screen):
        for v in self.vehicles:
            v.draw(screen)