# vehicle.py
import pygame
import random
from config import *


class Vehicle:
    def __init__(self, lane_y, direction_left=True, sub_lane=0):
        self.lane_y = lane_y
        self.direction_left = direction_left
        self.sub_lane = sub_lane

        y_offset = SUB_LANE_OFFSET_0 if self.sub_lane == 0 else SUB_LANE_OFFSET_1
        self.rect = pygame.Rect(0, lane_y + y_offset, 80, 50)

        if self.direction_left:
            self.rect.x = SCREEN_WIDTH + 50
            self.base_speed = random.randint(3, 6) * -1
            self.color = (200, 50, 50)
        else:
            self.rect.x = -100
            self.base_speed = random.randint(3, 6)
            self.color = (50, 100, 200)

        self.current_speed = self.base_speed
        self.switch_cooldown = 0

    def update(self, all_vehicles, speed_multiplier=1.0):  # <-- multiplier added
        self.current_speed = self.base_speed * speed_multiplier  # <-- applied here
        self.switch_cooldown = max(0, self.switch_cooldown - 1)

        if self.lane_y == MIDDLE_LANE_Y:
            self.check_head_on(all_vehicles)

        self.maintain_distance(all_vehicles)

        self.rect.x += int(self.current_speed)

    def check_head_on(self, all_vehicles):
        if self.switch_cooldown > 0:
            return

        for other in all_vehicles:
            if (other.lane_y == self.lane_y and
                    other.sub_lane == self.sub_lane and
                    other.direction_left != self.direction_left):

                distance = other.rect.x - self.rect.x
                danger = False
                if self.direction_left:
                    if -200 < distance < 0: danger = True
                else:
                    if 0 < distance < 200: danger = True

                if danger:
                    self.attempt_lane_switch(all_vehicles)
                    break

    def attempt_lane_switch(self, all_vehicles):
        target_sub_lane = 1 - self.sub_lane
        target_y_offset = SUB_LANE_OFFSET_0 if target_sub_lane == 0 else SUB_LANE_OFFSET_1
        target_rect = self.rect.copy()
        target_rect.y = self.lane_y + target_y_offset

        is_clear = True
        for v in all_vehicles:
            if v.rect.colliderect(target_rect):
                is_clear = False
                break

        if is_clear:
            self.sub_lane = target_sub_lane
            self.rect.y = self.lane_y + target_y_offset
            self.switch_cooldown = 60

    def maintain_distance(self, all_vehicles):
        for other in all_vehicles:
            if other != self and other.lane_y == self.lane_y and other.sub_lane == self.sub_lane:
                if other.direction_left == self.direction_left:
                    distance = other.rect.x - self.rect.x
                    if self.direction_left and -150 < distance < -10:
                        self.current_speed = max(self.current_speed, other.current_speed)
                    elif not self.direction_left and 10 < distance < 150:
                        self.current_speed = min(self.current_speed, other.current_speed)

    def draw(self, screen):
        pygame.draw.rect(screen, self.color, self.rect)
        if self.lane_y == MIDDLE_LANE_Y:
            pygame.draw.rect(screen, (255, 255, 0), (self.rect.centerx, self.rect.centery, 5, 5))
