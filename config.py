# config.py
import pygame

# Dimensions
SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 700
FPS = 60

# Colors
COLOR_BG = (30, 30, 30)
COLOR_ROAD = (50, 50, 50)
COLOR_MARKING = (255, 255, 255)
COLOR_FOOTPATH = (200, 200, 200)

# Lane Structure
LANE_HEIGHT = 140       # Tall enough for 2 cars (50px each + gaps)
FOOTPATH_HEIGHT = 100

# Sub-Lane Offsets (Relative to the Lane Y)
# Row 0 (Top) and Row 1 (Bottom)
SUB_LANE_OFFSET_0 = 15
SUB_LANE_OFFSET_1 = 75

# Y Positions
FOOTPATH_Y = 0
FAR_LANE_Y = FOOTPATH_HEIGHT
MIDDLE_LANE_Y = FAR_LANE_Y + LANE_HEIGHT
NEAR_LANE_Y = MIDDLE_LANE_Y + LANE_HEIGHT