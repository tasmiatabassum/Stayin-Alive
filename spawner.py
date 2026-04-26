# spawner.py
import random
from vehicle import Vehicle
from config import *
from round_manager import weighted_choice


class Spawner:
    def __init__(self, round_manager, env_manager=None):
        self.vehicles = []
        self.rm = round_manager
        self._env = env_manager
        self._frame = 0
        self._next_spawn = self._sample_interarrival()

    # ── NHPP inter-arrival time ─────────────────────────────────────────
    def _sample_interarrival(self) -> float:
        base_mean = self.rm.get_spawn_frequency()  # round-based mean
        nhpp_mult = self.rm.get_rush_hour_lambda_mult()  # time-varying ∈[0.4,1.4]
        mean_frames = max(5.0, base_mean / nhpp_mult)  # effective mean, floored
        lam = 1.0 / mean_frames
        return random.expovariate(lam)

    # ── Main update ─────────────────────────────────────────────────────
    def update(self):
        self._frame += 1

        if self._frame >= self._next_spawn:
            self.attempt_spawn()
            self._frame = 0
            self._next_spawn = self._sample_interarrival()  # re-draw gap

        # EnvironmentManager Rain Hook
        p_slow_mult = (self._env.vehicle_p_slow_mult if self._env is not None else 1.0)
        multiplier = self.rm.get_traffic_speed_multiplier()

        for v in self.vehicles:
            v.update(self.vehicles, multiplier, p_slow_mult)

        # Cull off-screen vehicles
        self.vehicles = [v for v in self.vehicles
                         if -200 < v.rect.x < SCREEN_WIDTH + 200]

    # ── Bernoulli lane activation ────────────────────────────────────────
    def attempt_spawn(self):
        lane_probs = self.rm.get_lane_activation_probs()  # [near_p, middle_p, far_p]

        lane_defs = [
            (3, NEAR_LANE_Y, True),
            (2, MIDDLE_LANE_Y, None),
            (1, FAR_LANE_Y, False),
        ]

        for (lane_id, target_y, fixed_left), p_lane in zip(lane_defs, lane_probs):
            if random.random() > p_lane:
                continue

            sub_lane = random.choice([0, 1])

            if fixed_left is None:
                bidir = self.rm.get_middle_bidirectional_prob()
                go_left = random.random() < bidir
            else:
                go_left = fixed_left

            tw = self.rm.get_vehicle_weights()
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