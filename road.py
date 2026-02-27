# road.py
import pygame
from config import *


class Road:
    def __init__(self):
        self.footpath_rect = pygame.Rect(0, FOOTPATH_Y, SCREEN_WIDTH, FOOTPATH_HEIGHT)
        self.sidewalk_rect = pygame.Rect(0, SCREEN_HEIGHT - 50, SCREEN_WIDTH, 50)
        self.dash_offset = 0  # Animates the lane markings

    def update(self):
        # Scroll dashes each frame — different speeds per lane direction
        self.dash_offset = (self.dash_offset + 2) % 80  # 80 = dash + gap width

    def draw(self, screen):
        # --- Road background ---
        pygame.draw.rect(screen, COLOR_ROAD, (0, FAR_LANE_Y, SCREEN_WIDTH, LANE_HEIGHT * 3))

        # --- Safe Zone (top footpath) — green tint ---
        pygame.draw.rect(screen, (80, 160, 80), self.footpath_rect)
        # Subtle inner highlight
        pygame.draw.rect(screen, (100, 200, 100),
                         pygame.Rect(0, FOOTPATH_Y, SCREEN_WIDTH, 6))

        # --- Bottom Sidewalk (start zone) ---
        pygame.draw.rect(screen, (180, 160, 140), self.sidewalk_rect)
        # Top edge line
        pygame.draw.line(screen, (140, 120, 100),
                         (0, SCREEN_HEIGHT - 50), (SCREEN_WIDTH, SCREEN_HEIGHT - 50), 3)
        # Subtle brick pattern
        for bx in range(0, SCREEN_WIDTH, 60):
            pygame.draw.line(screen, (160, 140, 120),
                             (bx, SCREEN_HEIGHT - 50), (bx, SCREEN_HEIGHT), 1)
        pygame.draw.line(screen, (160, 140, 120),
                         (0, SCREEN_HEIGHT - 25), (SCREEN_WIDTH, SCREEN_HEIGHT - 25), 1)

        # --- Solid lane boundary lines ---
        pygame.draw.line(screen, COLOR_MARKING,
                         (0, MIDDLE_LANE_Y), (SCREEN_WIDTH, MIDDLE_LANE_Y), 3)
        pygame.draw.line(screen, COLOR_MARKING,
                         (0, NEAR_LANE_Y), (SCREEN_WIDTH, NEAR_LANE_Y), 3)

        # --- Animated dashed sub-lane dividers ---
        # Between sub-lanes inside FAR lane (moves RIGHT — cars go right here)
        self._draw_dashes(screen, FAR_LANE_Y + LANE_HEIGHT // 2,
                          offset=self.dash_offset, color=(180, 180, 180))

        # Between sub-lanes inside MIDDLE lane (mixed — neutral offset)
        self._draw_dashes(screen, MIDDLE_LANE_Y + LANE_HEIGHT // 2,
                          offset=self.dash_offset, color=(180, 180, 180))

        # Between sub-lanes inside NEAR lane (moves LEFT — reverse offset)
        self._draw_dashes(screen, NEAR_LANE_Y + LANE_HEIGHT // 2,
                          offset=-self.dash_offset, color=(180, 180, 180))

        # --- Labels ---
        font = pygame.font.SysFont("Arial", 22, bold=True)

        safe_label = font.render("SAFE ZONE", True, (30, 80, 30))
        screen.blit(safe_label,
                    (SCREEN_WIDTH // 2 - safe_label.get_width() // 2, FOOTPATH_Y + 38))

        start_label = font.render("START", True, (100, 80, 60))
        screen.blit(start_label,
                    (SCREEN_WIDTH // 2 - start_label.get_width() // 2, SCREEN_HEIGHT - 38))

    def _draw_dashes(self, screen, y, offset, color, dash_len=40, gap=40, thickness=2):
        x = -gap + (offset % (dash_len + gap))
        while x < SCREEN_WIDTH:
            x1 = max(x, 0)
            x2 = min(x + dash_len, SCREEN_WIDTH)
            if x2 > x1:
                pygame.draw.line(screen, color, (x1, y), (x2, y), thickness)
            x += dash_len + gap