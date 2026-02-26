# pedestrian.py
import pygame
from config import *

class Pedestrian:
    def __init__(self, character_data):
        # Base setup
        self.rect = pygame.Rect(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 60, character_data["width"], character_data["height"])
        self.color = character_data["color"]
        self.name = character_data["name"]
        
        # Physics setup
        self.accel = character_data["accel"]
        self.friction = character_data["friction"]
        self.max_speed = character_data["max_speed"]
        
        # Velocity vectors
        self.vel_x = 0.0
        self.vel_y = 0.0
        
        # Dash mechanic
        self.dash_power = character_data["dash_power"]
        self.dash_max_cooldown = character_data["dash_cooldown"]
        self.current_dash_cooldown = 0
        
    def move(self, keys):
        # 1. Handle Cooldowns
        if self.current_dash_cooldown > 0:
            self.current_dash_cooldown -= 1

        # 2. Apply Acceleration (Input)
        if keys[pygame.K_UP]:
            self.vel_y -= self.accel
        if keys[pygame.K_DOWN]:
            self.vel_y += self.accel
        if keys[pygame.K_LEFT]:
            self.vel_x -= self.accel
        if keys[pygame.K_RIGHT]:
            self.vel_x += self.accel

        # 3. Dash Mechanic (Spacebar)
        if keys[pygame.K_SPACE] and self.current_dash_cooldown == 0:
            # Dash in the direction of current movement, or default to UP
            if self.vel_y < 0: self.vel_y -= self.dash_power
            elif self.vel_y > 0: self.vel_y += self.dash_power
            elif self.vel_x < 0: self.vel_x -= self.dash_power
            elif self.vel_x > 0: self.vel_x += self.dash_power
            else: self.vel_y -= self.dash_power # Default dash forward
            
            self.current_dash_cooldown = self.dash_max_cooldown

        # 4. Cap Speed (so they don't break the sound barrier, unless dashing)
        # We only cap speed if they aren't mid-dash
        if self.current_dash_cooldown < self.dash_max_cooldown - 10: 
            self.vel_x = max(-self.max_speed, min(self.max_speed, self.vel_x))
            self.vel_y = max(-self.max_speed, min(self.max_speed, self.vel_y))

        # 5. Apply Friction (Slows them down when keys are released)
        self.vel_x *= self.friction
        self.vel_y *= self.friction

        # 6. Update Position
        self.rect.x += int(self.vel_x)
        self.rect.y += int(self.vel_y)

        # 7. Screen Boundaries
        if self.rect.y > SCREEN_HEIGHT - 50:
            self.rect.y = SCREEN_HEIGHT - 50
            self.vel_y = 0
        if self.rect.x < 0:
            self.rect.x = 0
            self.vel_x = 0
        if self.rect.x > SCREEN_WIDTH - self.rect.width:
            self.rect.x = SCREEN_WIDTH - self.rect.width
            self.vel_x = 0
        
    def draw(self, screen):
        pygame.draw.rect(screen, self.color, self.rect)
        
        # Visual flair: Draw a cooldown bar for the dash above their head
        if self.current_dash_cooldown > 0:
            bar_width = self.rect.width
            fill_ratio = (self.dash_max_cooldown - self.current_dash_cooldown) / self.dash_max_cooldown
            pygame.draw.rect(screen, (255, 0, 0), (self.rect.x, self.rect.y - 10, bar_width, 4))
            pygame.draw.rect(screen, (0, 255, 0), (self.rect.x, self.rect.y - 10, bar_width * fill_ratio, 4))