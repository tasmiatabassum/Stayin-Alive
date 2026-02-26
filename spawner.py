import random
from vehicle import Vehicle
from config import *


class Spawner:
    def __init__(self, round_manager):
        self.vehicles = []
        self.spawn_timer = 0
        self.min_spawn_gap = 150
        self.rm = round_manager

    def update(self):
        self.spawn_timer += 1

        if self.spawn_timer > self.rm.get_spawn_frequency():
            self.attempt_spawn()
            self.spawn_timer = 0

        for v in self.vehicles:
            v.update(self.vehicles, self.rm.get_traffic_speed_multiplier())

        self.vehicles = [v for v in self.vehicles if -200 < v.rect.x < SCREEN_WIDTH + 200]

    def attempt_spawn(self):
        lane_choice = random.choice([1, 2, 3])
        sub_lane_choice = random.choice([0, 1])

        target_y = 0
        target_direction_left = True

        if lane_choice == 1:
            target_y = FAR_LANE_Y
            target_direction_left = False
        elif lane_choice == 2:
            target_y = MIDDLE_LANE_Y
            target_direction_left = random.choice([True, False])
        elif lane_choice == 3:
            target_y = NEAR_LANE_Y
            target_direction_left = True

        if self.is_lane_clear(target_y, sub_lane_choice, target_direction_left):
            self.vehicles.append(Vehicle(target_y, target_direction_left, sub_lane_choice))

    def is_lane_clear(self, lane_y, sub_lane, is_moving_left):
        for v in self.vehicles:
            if abs(v.rect.y - lane_y) < 100 and v.sub_lane == sub_lane:
                if is_moving_left:
                    if v.rect.x > SCREEN_WIDTH - self.min_spawn_gap: return False
                else:
                    if v.rect.x < self.min_spawn_gap: return False
        return True

    def draw(self, screen):
        for v in self.vehicles:
            v.draw(screen)
