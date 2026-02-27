# spawner.py
"""
Spawner — Traffic Arrival Model
================================
Two stochastic upgrades over the original fixed-timer approach:

1.  Poisson Process arrivals
    -------------------------
    Real traffic arrivals are memoryless and independent: a Poisson process
    with rate λ (vehicles/frame).  The waiting time between successive
    arrivals follows an Exponential distribution with mean 1/λ.  We draw
    each inter-arrival gap with random.expovariate(λ), giving bursty,
    realistic spacing — sometimes three cars arrive close together,
    sometimes a long gap opens up.

        T_next ~ Exp(λ)    where  λ = 1 / get_spawn_frequency()

2.  Bernoulli Lane Activation
    --------------------------
    At each arrival event, every lane independently "activates" with its
    own probability p_lane (from round_manager.get_lane_activation_probs).
    This models stochastic congestion onset: near-lane traffic is always
    present early, while far and middle lanes gradually become active.
    Multiple lanes can spawn in a single arrival event, reflecting
    correlated bursts seen in real urban traffic.
"""

import random
from vehicle import Vehicle
from config import *
from round_manager import weighted_choice


class Spawner:
    def __init__(self, round_manager):
        self.vehicles    = []
        self.rm          = round_manager
        self._frame      = 0
        # Draw the first inter-arrival time immediately
        self._next_spawn = self._sample_interarrival()

    # ── Poisson inter-arrival time ──────────────────────────────────────
    def _sample_interarrival(self) -> float:
        """
        Sample the waiting time until the next vehicle arrival event.
        Uses the Exponential distribution — the waiting-time distribution
        of a homogeneous Poisson process.

            T ~ Exp(λ),  E[T] = 1/λ = get_spawn_frequency() frames
        """
        mean_frames = self.rm.get_spawn_frequency()   # scalar > 0
        lam         = 1.0 / mean_frames               # rate parameter
        return random.expovariate(lam)                # frames until next event

    # ── Main update ─────────────────────────────────────────────────────
    def update(self):
        self._frame += 1

        if self._frame >= self._next_spawn:
            self.attempt_spawn()
            self._frame      = 0
            self._next_spawn = self._sample_interarrival()   # re-draw gap

        multiplier = self.rm.get_traffic_speed_multiplier()
        for v in self.vehicles:
            v.update(self.vehicles, multiplier)

        # Cull off-screen vehicles
        self.vehicles = [v for v in self.vehicles
                         if -200 < v.rect.x < SCREEN_WIDTH + 200]

    # ── Bernoulli lane activation ────────────────────────────────────────
    def attempt_spawn(self):
        """
        For each lane, independently flip a Bernoulli coin with lane-specific
        probability p_lane (from round_manager).  Each active lane spawns one
        vehicle, so 0–3 vehicles can appear per arrival event.

        Lane layout (lane_id, y-constant, default direction):
            lane 3 → NEAR_LANE_Y,   always leftward
            lane 2 → MIDDLE_LANE_Y, bidirectional
            lane 1 → FAR_LANE_Y,    always rightward
        """
        lane_probs = self.rm.get_lane_activation_probs()  # [near_p, middle_p, far_p]

        lane_defs = [
            (3, NEAR_LANE_Y,    True),   # (lane_id, y, go_left)
            (2, MIDDLE_LANE_Y,  None),   # direction determined by bidir probability
            (1, FAR_LANE_Y,     False),
        ]

        for (lane_id, target_y, fixed_left), p_lane in zip(lane_defs, lane_probs):

            # ── Bernoulli trial ──────────────────────────────────────────
            if random.random() > p_lane:
                continue   # this lane is not active this event

            sub_lane = random.choice([0, 1])

            # Direction
            if fixed_left is None:           # middle lane: probabilistic
                bidir = self.rm.get_middle_bidirectional_prob()
                go_left = random.random() < bidir
            else:
                go_left = fixed_left

            # ── Weighted categorical: vehicle type ───────────────────────
            tw     = self.rm.get_vehicle_weights()
            vtype  = weighted_choice(list(tw.keys()), list(tw.values()))

            # ── Dynamic headway guard ────────────────────────────────────
            spawn_gap = self.rm.get_spawn_gap()

            if self.is_lane_clear(target_y, sub_lane, go_left, spawn_gap):
                # Lane-dependent truncated-normal speed
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