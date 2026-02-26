# pedestrian.py
import pygame
from config import *

class Pedestrian:
    def __init__(self, character_data):
        self.rect = pygame.Rect(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 60, character_data["width"], character_data["height"])
        self.color = character_data["color"]
        self.name = character_data["name"]
        
        # Physics setup
        self.accel = character_data["accel"]
        self.friction = character_data["friction"]
        self.max_speed = character_data["max_speed"]
        
        # Exact position tracking (The Fix)
        self.true_x = float(self.rect.x)
        self.true_y = float(self.rect.y)
        
        self.vel_x = 0.0
        self.vel_y = 0.0
        
        self.dash_power = character_data["dash_power"]
        self.dash_max_cooldown = character_data["dash_cooldown"]
        self.current_dash_cooldown = 0
        
    def move(self, keys):
        if self.current_dash_cooldown > 0:
            self.current_dash_cooldown -= 1

        if keys[pygame.K_UP]: self.vel_y -= self.accel
        if keys[pygame.K_DOWN]: self.vel_y += self.accel
        if keys[pygame.K_LEFT]: self.vel_x -= self.accel
        if keys[pygame.K_RIGHT]: self.vel_x += self.accel

        if keys[pygame.K_SPACE] and self.current_dash_cooldown == 0:
            if self.vel_y < 0: self.vel_y -= self.dash_power
            elif self.vel_y > 0: self.vel_y += self.dash_power
            elif self.vel_x < 0: self.vel_x -= self.dash_power
            elif self.vel_x > 0: self.vel_x += self.dash_power
            else: self.vel_y -= self.dash_power
            self.current_dash_cooldown = self.dash_max_cooldown

        if self.current_dash_cooldown < self.dash_max_cooldown - 10: 
            self.vel_x = max(-self.max_speed, min(self.max_speed, self.vel_x))
            self.vel_y = max(-self.max_speed, min(self.max_speed, self.vel_y))

        self.vel_x *= self.friction
        self.vel_y *= self.friction

        # UPDATE EXACT FLOAT POSITION
        self.true_x += self.vel_x
        self.true_y += self.vel_y

        # SCREEN BOUNDARIES (Updates the float positions if hitting a wall)
        if self.true_y > SCREEN_HEIGHT - 50:
            self.true_y = SCREEN_HEIGHT - 50
            self.vel_y = 0
        if self.true_x < 0:
            self.true_x = 0
            self.vel_x = 0
        if self.true_x > SCREEN_WIDTH - self.rect.width:
            self.true_x = SCREEN_WIDTH - self.rect.width
            self.vel_x = 0

        # SYNC RECT TO FLOAT POSITION FOR DRAWING
        self.rect.x = int(self.true_x)
        self.rect.y = int(self.true_y)

    def reset_position(self):
        # A clean helper function to reset everything when hit or winning
        self.rect.y = SCREEN_HEIGHT - 60
        self.rect.x = SCREEN_WIDTH // 2
        self.true_x = float(self.rect.x)
        self.true_y = float(self.rect.y)
        self.vel_x = 0
        self.vel_y = 0
        
    def draw(self, screen):
        pygame.draw.rect(screen, self.color, self.rect)
        if self.current_dash_cooldown > 0:
            bar_width = self.rect.width
            fill_ratio = (self.dash_max_cooldown - self.current_dash_cooldown) / self.dash_max_cooldown
            pygame.draw.rect(screen, (255, 0, 0), (self.rect.x, self.rect.y - 10, bar_width, 4))
            pygame.draw.rect(screen, (0, 255, 0), (self.rect.x, self.rect.y - 10, bar_width * fill_ratio, 4))