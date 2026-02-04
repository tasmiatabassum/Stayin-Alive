import pygame
from config import *


class Pedestrian:
    def __init__(self, character_data):
        self.rect = pygame.Rect(SCREEN_WIDTH//2, SCREEN_HEIGHT -60, character_data["width"], character_data["height"])
        self.color = character_data["color"]
        self.speed = character_data["speed"]
        self.name = character_data["name"]

    def move(self, keys):
        if keys[pygame.K_LEFT]:
            self.rect.x -= self.speed
        if keys[pygame.K_RIGHT]:
            self.rect.x += self.speed
        if keys[pygame.K_UP]:
            self.rect.y -= self.speed
        if keys[pygame.K_DOWN]:
            self.rect.y += self.speed


        if self.rect.y> SCREEN_HEIGHT-50:
            self.rect.y = SCREEN_HEIGHT-50

    def draw(self, screen):
        pygame.draw.rect(screen, self.color, self.rect)