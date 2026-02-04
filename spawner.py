# spawner.py
import random
from vehicle import Vehicle
from config import *


class Spawner:
    def __init__(self):
        self.vehicles = []
        self.spawn_timer = 0
        self.min_spawn_gap = 150  # Minimum pixels between cars

    def update(self):
        self.spawn_timer += 1

        # Try to spawn frequently (every 30 frames)
        if self.spawn_timer > 30:
            self.attempt_spawn()
            self.spawn_timer = 0

        # PASS THE LIST HERE!
        # This allows every car to see every other car
        for v in self.vehicles:
            v.update(self.vehicles)

        # Clean up off-screen cars
        self.vehicles = [v for v in self.vehicles if -200 < v.rect.x < SCREEN_WIDTH + 200]

    def attempt_spawn(self):
        lane_choice = random.choice([1, 2, 3])
        # Randomly pick Top Row (0) or Bottom Row (1)
        sub_lane_choice = random.choice([0, 1])

        target_y = 0
        target_direction_left = True

        if lane_choice == 1:  # Far Lane
            target_y = FAR_LANE_Y
            target_direction_left = False
        elif lane_choice == 2:  # Middle Lane
            target_y = MIDDLE_LANE_Y
            target_direction_left = random.choice([True, False])
        elif lane_choice == 3:  # Near Lane
            target_y = NEAR_LANE_Y
            target_direction_left = True

        # Check if the specific SUB-LANE is clear
        if self.is_lane_clear(target_y, sub_lane_choice, target_direction_left):
            self.vehicles.append(Vehicle(target_y, target_direction_left, sub_lane_choice))

    def is_lane_clear(self, lane_y, sub_lane, is_moving_left):
        for v in self.vehicles:
            # Must check Lane Y AND Sub-Lane
            if abs(v.rect.y - lane_y) < 100 and v.sub_lane == sub_lane:
                if is_moving_left:
                    if v.rect.x > SCREEN_WIDTH - self.min_spawn_gap: return False
                else:
                    if v.rect.x < self.min_spawn_gap: return False
        return True

    def draw(self, screen):
        for v in self.vehicles:
            v.draw(screen)