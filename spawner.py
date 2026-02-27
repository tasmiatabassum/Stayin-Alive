# spawner.py
import random
from vehicle import Vehicle
from config import *
from round_manager import weighted_choice


class Spawner:
    def __init__(self, round_manager):
        self.vehicles    = []
        self.spawn_timer = 0
        self.rm          = round_manager

    def update(self):
        self.spawn_timer += 1
        if self.spawn_timer > self.rm.get_spawn_frequency():
            self.attempt_spawn()
            self.spawn_timer = 0

        multiplier = self.rm.get_traffic_speed_multiplier()
        for v in self.vehicles:
            v.update(self.vehicles, multiplier)

        self.vehicles = [v for v in self.vehicles
                         if -200 < v.rect.x < SCREEN_WIDTH + 200]

    def attempt_spawn(self):
        # ── Weighted categorical: lane selection ─────────────────────────
        lane_weights = self.rm.get_lane_weights()   # [near, middle, far]
        lane_choice  = weighted_choice([3, 2, 1], lane_weights)

        sub_lane_choice = random.choice([0, 1])

        # ── Direction logic per lane ─────────────────────────────────────
        if lane_choice == 1:       # Far lane — always rightward
            target_y   = FAR_LANE_Y
            go_left    = False

        elif lane_choice == 2:     # Middle lane — bidirectional probability
            target_y   = MIDDLE_LANE_Y
            bidir_prob = self.rm.get_middle_bidirectional_prob()
            go_left    = random.random() < bidir_prob

        else:                      # Near lane — always leftward
            target_y   = NEAR_LANE_Y
            go_left    = True

        # ── Weighted categorical: vehicle type ───────────────────────────
        type_weights_dict = self.rm.get_vehicle_weights()
        vtypes   = list(type_weights_dict.keys())
        vweights = list(type_weights_dict.values())
        vtype    = weighted_choice(vtypes, vweights)

        # ── Dynamic headway gap ──────────────────────────────────────────
        spawn_gap = self.rm.get_spawn_gap()

        if self.is_lane_clear(target_y, sub_lane_choice, go_left, spawn_gap):
            # Pass vtype and speed sample into Vehicle
            speed = self.rm.get_speed_sample(vtype)
            self.vehicles.append(
                Vehicle(target_y, go_left, sub_lane_choice,
                        vtype=vtype, speed_override=speed)
            )

    def is_lane_clear(self, lane_y, sub_lane, is_moving_left, gap):
        for v in self.vehicles:
            if abs(v.rect.y - lane_y) < 100 and v.sub_lane == sub_lane:
                if is_moving_left:
                    if v.rect.x > SCREEN_WIDTH - gap: return False
                else:
                    if v.rect.x < gap: return False
        return True

    def draw(self, screen):
        for v in self.vehicles:
            v.draw(screen)