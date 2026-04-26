# vehicle.py
import pygame
import random
from config import SCREEN_WIDTH


class Vehicle:
    def __init__(self, vtype, x, y, direction_left, speed, p_slow, image_dict, size, color=(200, 50, 50)):
        self.vtype = vtype
        self.rect = pygame.Rect(x, y, size[0], size[1])

        # Identifying tags used by logger.py and obstacles.py
        self.lane_y = y
        self.direction_left = direction_left

        # Physics / NaSch Variables
        self.current_speed = speed
        self.max_speed = speed
        self.p_slow = p_slow

        # Sprite Rendering
        self.image_dict = image_dict  # Contains pre-flipped {"left": img, "right": img}
        self.fallback_color = color

    def update(self, gap_ahead, env_p_slow_mult):
        # 1. Acceleration: Naturally speed up to max speed
        self.current_speed = min(self.current_speed + 0.2, self.max_speed)

        # 2. Braking (NaSch Model): Slow down to avoid hitting the car ahead
        if gap_ahead is not None:
            # We subtract 5px to leave a tiny visual bumper gap
            self.current_speed = min(self.current_speed, max(0, gap_ahead - 5))

        # 3. Randomization: Unpredictable Dhaka traffic braking (scales with Rain!)
        if random.random() < (self.p_slow * env_p_slow_mult):
            self.current_speed = max(0.0, self.current_speed - 1.0)

        # 4. Movement Execution
        if self.direction_left:
            self.rect.x -= self.current_speed
        else:
            self.rect.x += self.current_speed

    def draw(self, surface):
        if self.image_dict:
            # Fetch the correct pre-flipped image based on the lane direction
            img = self.image_dict["left"] if self.direction_left else self.image_dict["right"]
            surface.blit(img, self.rect)
        else:
            # Fallback block if an image is missing
            pygame.draw.rect(surface, self.fallback_color, self.rect, border_radius=4)