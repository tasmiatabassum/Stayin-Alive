# pedestrian.py
import pygame
import math
from config import *

class Pedestrian:
    def __init__(self, character_data):
        # Spawn on the near-side footpath, centred horizontally
        spawn_y = COMPOUND_Y - character_data["height"] - 10
        self.rect = pygame.Rect(SCREEN_WIDTH // 2, spawn_y,
                                character_data["width"], character_data["height"])
        self.color = character_data["color"]
        self.name = character_data["name"]

        self.accel = character_data["accel"]
        self.friction = character_data["friction"]
        self.max_speed = character_data["max_speed"]

        self.true_x = float(self.rect.x)
        self.true_y = float(self.rect.y)

        self.vel_x = 0.0
        self.vel_y = 0.0

        self.dash_power = character_data["dash_power"]
        self.dash_max_cooldown = character_data["dash_cooldown"]
        self.current_dash_cooldown = 0

        # Bottom clamp: keep player on the near footpath (not into compound)
        self._bottom_clamp = COMPOUND_Y - character_data["height"]

    def move(self, keys):
        if self.current_dash_cooldown > 0:
            self.current_dash_cooldown -= 1

        if keys[pygame.K_UP]:    self.vel_y -= self.accel
        if keys[pygame.K_DOWN]:  self.vel_y += self.accel
        if keys[pygame.K_LEFT]:  self.vel_x -= self.accel
        if keys[pygame.K_RIGHT]: self.vel_x += self.accel

        dashed = False
        if keys[pygame.K_SPACE] and self.current_dash_cooldown == 0:
            if self.vel_y < 0:   self.vel_y -= self.dash_power
            elif self.vel_y > 0: self.vel_y += self.dash_power
            elif self.vel_x < 0: self.vel_x -= self.dash_power
            elif self.vel_x > 0: self.vel_x += self.dash_power
            else:                self.vel_y -= self.dash_power
            self.current_dash_cooldown = self.dash_max_cooldown
            dashed = True

        if self.current_dash_cooldown < self.dash_max_cooldown - 10:
            self.vel_x = max(-self.max_speed, min(self.max_speed, self.vel_x))
            self.vel_y = max(-self.max_speed, min(self.max_speed, self.vel_y))

        self.vel_x *= self.friction
        self.vel_y *= self.friction

        self.true_x += self.vel_x
        self.true_y += self.vel_y

        # Clamp: can't go below near footpath (into compound)
        if self.true_y > self._bottom_clamp:
            self.true_y = self._bottom_clamp
            self.vel_y = 0
        if self.true_x < 0:
            self.true_x = 0
            self.vel_x = 0
        if self.true_x > SCREEN_WIDTH - self.rect.width:
            self.true_x = SCREEN_WIDTH - self.rect.width
            self.vel_x = 0

        self.rect.x = int(self.true_x)
        self.rect.y = int(self.true_y)

        return dashed

    def reset_position(self):
        self.rect.y = COMPOUND_Y - self.rect.height - 10
        self.rect.x = SCREEN_WIDTH // 2
        self.true_x = float(self.rect.x)
        self.true_y = float(self.rect.y)
        self.vel_x = 0
        self.vel_y = 0

    def draw(self, screen):
        # --- Body ---
        pygame.draw.rect(screen, self.color, self.rect, border_radius=5)

        # --- Directional arrow ---
        speed = math.hypot(self.vel_x, self.vel_y)
        if speed > 0.5:
            cx = self.rect.centerx
            cy = self.rect.centery
            nx = self.vel_x / speed
            ny = self.vel_y / speed
            arrow_len = 10
            tip_x = cx + nx * arrow_len
            tip_y = cy + ny * arrow_len
            wing = 5
            wx = -ny * wing
            wy =  nx * wing
            base_x = cx - nx * 4
            base_y = cy - ny * 4
            arrow_pts = [
                (tip_x, tip_y),
                (base_x + wx, base_y + wy),
                (base_x - wx, base_y - wy),
            ]
            arrow_color = tuple(max(0, c - 80) for c in self.color)
            pygame.draw.polygon(screen, arrow_color, arrow_pts)

        # --- Dash cooldown bar ---
        if self.current_dash_cooldown > 0:
            bar_w = self.rect.width
            fill = (self.dash_max_cooldown - self.current_dash_cooldown) / self.dash_max_cooldown
            pygame.draw.rect(screen, (255, 0, 0),
                             (self.rect.x, self.rect.y - 10, bar_w, 4))
            pygame.draw.rect(screen, (0, 255, 0),
                             (self.rect.x, self.rect.y - 10, int(bar_w * fill), 4))