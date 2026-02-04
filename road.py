# road.py
import pygame
from config import *


class Road:
    def __init__(self):
        # The safe zone at the top
        self.footpath_rect = pygame.Rect(0, FOOTPATH_Y, SCREEN_WIDTH, FOOTPATH_HEIGHT)

    def draw(self, screen):
        # Draw the main road background
        pygame.draw.rect(screen, COLOR_ROAD, (0, FAR_LANE_Y, SCREEN_WIDTH, LANE_HEIGHT * 3))

        # Draw the Target Footpath (Top)
        pygame.draw.rect(screen, COLOR_FOOTPATH, self.footpath_rect)

        # Draw Lane Dividers
        # 1. Between Far and Middle
        pygame.draw.line(screen, COLOR_MARKING, (0, MIDDLE_LANE_Y), (SCREEN_WIDTH, MIDDLE_LANE_Y), 4)
        # 2. Between Middle and Near
        pygame.draw.line(screen, COLOR_MARKING, (0, NEAR_LANE_Y), (SCREEN_WIDTH, NEAR_LANE_Y), 4)

        # Optional: Add "FINISH" text on the footpath
        if pygame.font.get_init():
            font = pygame.font.SysFont("Arial", 30, bold=True)
            label = font.render("SAFE ZONE (FINISH)", True, (50, 50, 50))
            screen.blit(label, (SCREEN_WIDTH // 2 - 100, FOOTPATH_Y + 30))