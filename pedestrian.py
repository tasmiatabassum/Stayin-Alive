# pedestrian.py
import pygame
import math
import os
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

        # ─── Sprite Animation Setup ──────────────────────────────────────────
        self.frames = []
        self.is_animated = False

        # Dynamically load the 4 walking frames based on the character's name
        for i in range(1, 5):
            filename = f"{self.name.lower()}_{i}.png"
            if os.path.exists(filename):
                try:
                    img = pygame.image.load(filename).convert_alpha()
                    # Scale exactly to the width/height defined in characters.py
                    img = pygame.transform.scale(img, (character_data["width"], character_data["height"]))
                    self.frames.append(img)
                except Exception as e:
                    print(f"Warning: Could not load {filename}: {e}")

        # If all 4 frames loaded successfully, enable animation
        if len(self.frames) == 4:
            self.is_animated = True

        self.current_frame = 0.0
        self.base_anim_speed = 0.35  # Base speed of frame cycling
        self.facing_angle = 0.0  # Track rotation so they face the right way when idle

    def move(self, keys, env_friction_mult: float = 1.0):
        """
        env_friction_mult: multiplier on friction from EnvironmentManager.
        Values < 1.0 (rain) make the surface more slippery — friction approaches
        1.0 and the player slides further before stopping.
        """
        if self.current_dash_cooldown > 0:
            self.current_dash_cooldown -= 1

        if keys[pygame.K_UP]:    self.vel_y -= self.accel
        if keys[pygame.K_DOWN]:  self.vel_y += self.accel
        if keys[pygame.K_LEFT]:  self.vel_x -= self.accel
        if keys[pygame.K_RIGHT]: self.vel_x += self.accel

        dashed = False
        if keys[pygame.K_SPACE] and self.current_dash_cooldown == 0:
            if self.vel_y < 0:
                self.vel_y -= self.dash_power
            elif self.vel_y > 0:
                self.vel_y += self.dash_power
            elif self.vel_x < 0:
                self.vel_x -= self.dash_power
            elif self.vel_x > 0:
                self.vel_x += self.dash_power
            else:
                self.vel_y -= self.dash_power
            self.current_dash_cooldown = self.dash_max_cooldown
            dashed = True

        if self.current_dash_cooldown < self.dash_max_cooldown - 10:
            self.vel_x = max(-self.max_speed, min(self.max_speed, self.vel_x))
            self.vel_y = max(-self.max_speed, min(self.max_speed, self.vel_y))

        # env_friction_mult < 1 → wet surface → friction moves toward 1.0
        # (less damping = more sliding). Clamp so it never exceeds 0.99.
        effective_friction = min(0.99,
                                 1.0 - (1.0 - self.friction) * env_friction_mult)
        self.vel_x *= effective_friction
        self.vel_y *= effective_friction

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
        self.facing_angle = 0.0  # Reset to face straight up

    def draw(self, screen):
        speed = math.hypot(self.vel_x, self.vel_y)

        if self.is_animated:
            # Update animation frame and rotation only if moving
            if speed > 0.5:
                # Frame changes faster if the player is moving faster
                self.current_frame += self.base_anim_speed * (speed / self.max_speed)
                if self.current_frame >= len(self.frames):
                    self.current_frame = 0.0

                # Calculate rotation angle.
                # atan2(-y, x) handles Pygame's inverted Y axis.
                # We subtract 90 because the original pngs are naturally facing UP.
                self.facing_angle = math.degrees(math.atan2(-self.vel_y, self.vel_x)) - 90
            else:
                self.current_frame = 0.0  # Return to idle frame when stopped

            # Fetch current frame and rotate it
            frame_img = self.frames[int(self.current_frame)]
            rotated_img = pygame.transform.rotate(frame_img, self.facing_angle)

            # Re-center the rotated image over the physical hitbox
            new_rect = rotated_img.get_rect(center=self.rect.center)
            screen.blit(rotated_img, new_rect.topleft)

        else:
            # --- Fallback Body (If PNGs are missing) ---
            pygame.draw.rect(screen, self.color, self.rect, border_radius=5)

            # --- Fallback Directional arrow ---
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
                wy = nx * wing
                base_x = cx - nx * 4
                base_y = cy - ny * 4
                arrow_pts = [
                    (tip_x, tip_y),
                    (base_x + wx, base_y + wy),
                    (base_x - wx, base_y - wy),
                ]
                arrow_color = tuple(max(0, c - 80) for c in self.color)
                pygame.draw.polygon(screen, arrow_color, arrow_pts)

        # --- Dash cooldown bar (Always drawn above the player) ---
        if self.current_dash_cooldown > 0:
            bar_w = self.rect.width
            fill = (self.dash_max_cooldown - self.current_dash_cooldown) / self.dash_max_cooldown
            pygame.draw.rect(screen, (255, 0, 0),
                             (self.rect.x, self.rect.y - 10, bar_w, 4))
            pygame.draw.rect(screen, (0, 255, 0),
                             (self.rect.x, self.rect.y - 10, int(bar_w * fill), 4))