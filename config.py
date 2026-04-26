# config.py
import pygame

# ── Screen ────────────────────────────────────────────────────────────────
SCREEN_WIDTH  = 1000
SCREEN_HEIGHT = 700
FPS           = 60

# ── Colors ────────────────────────────────────────────────────────────────
COLOR_BG       = (30, 30, 30)
COLOR_ROAD     = (68, 66, 64)
COLOR_MARKING  = (222, 218, 200)
COLOR_FOOTPATH = (175, 165, 148)

# ── Lane geometry ─────────────────────────────────────────────────────────
#
#  y=0   ┌────────────────────────────────────────────────────┐
#        │  HIGHRISE BUILDINGS  (far / safe zone)
#        │  (70px building body)
#  y=70  ├────────────────────────────────────────────────────┤
#        │  FAR FOOTPATH  (50px paved, player destination)
#  y=120 ├────────────────────────────────────────────────────┤
#        │  FAR LANE   →→→  (LANE_HEIGHT = 140px)
#  y=260 ├────────────────────────────────────────────────────┤
#        │  CONCRETE MEDIAN  (15px)
#  y=275 ├────────────────────────────────────────────────────┤  (approx)
#        │  MIDDLE LANE  ←→  (LANE_HEIGHT = 140px)
#  y=400 ├────────────────────────────────────────────────────┤
#        │  NEAR LANE   ←←←  (LANE_HEIGHT = 140px)
#  y=540 ├────────────────────────────────────────────────────┤
#        │  NEAR FOOTPATH  (50px paved, player start)
#  y=590 ├────────────────────────────────────────────────────┤
#        │  IUT COMPOUND + GATE + TREES  (110px)
#  y=700 └────────────────────────────────────────────────────┘

LANE_HEIGHT      = 140
FOOTPATH_HEIGHT  = 120   # safe zone top height (buildings + far footpath)
FAR_FOOTPATH_H   = 50    # paved footpath width on far (safe) side
NEAR_FOOTPATH_H  = 50    # paved footpath width on IUT side

# Sub-lane offsets (within each 140px lane)
SUB_LANE_OFFSET_0 = 15
SUB_LANE_OFFSET_1 = 75

# Y positions
FOOTPATH_Y    = 0
FAR_LANE_Y    = FOOTPATH_HEIGHT        # 120
MIDDLE_LANE_Y = FAR_LANE_Y    + LANE_HEIGHT  # 260
NEAR_LANE_Y   = MIDDLE_LANE_Y + LANE_HEIGHT  # 400

# Compound starts after near footpath
COMPOUND_Y    = NEAR_LANE_Y + LANE_HEIGHT + NEAR_FOOTPATH_H  # 590