# road.py
"""
N3 Dhaka-Mymensingh Road — IUT Board Bazar
===========================================
Top-down view. Player starts at BOTTOM footpath (IUT side) and crosses UP
to the far-side footpath (safe zone).

Modified to use user-provided static assets for buildings and road texture.

New geometry (from config.py):
  y=0   ..120  : far safe zone (70px highrise buildings [STATIC ASSET] + 50px footpath)
  y=120 ..260  : FAR LANE [STATIC ASSET ASPHALT]  →→→
  y=260 ..275  : MEDIAN [STATIC ASSET ASPHALT]
  y=260 ..400  : MIDDLE LANE [STATIC ASSET ASPHALT]  ←→
  y=400 ..540  : NEAR LANE [STATIC ASSET ASPHALT]  ←←←
  y=540 ..590  : near footpath (player start zone, 50px)
  y=590 ..700  : IUT compound + gate [STATIC ASSET] + trees (110px, compact)
"""

import pygame
import random
import os
from config import *

# ── Palette (Remaining for procedural elements) ─────────────────────────
ASPHALT       = (68,  66,  64)
MARKING_W     = (222, 218, 200)
MEDIAN_CONC   = (136, 128, 115)
MEDIAN_YEL    = (205, 162,  18)

# Footpath (both sides) — warm concrete
FOOTPATH_COL  = (185, 173, 152)
FOOTPATH_LINE = (160, 148, 128)

# Trees (Fallback compound only)
T_CANOPY  = [( 42,  98,  38), ( 55, 118,  48), ( 35,  82,  32)]
T_SHADOW  = ( 28,  68,  26)
T_TRUNK   = ( 88,  62,  38)
T_LIGHT   = ( 72, 138,  58)

# ── Highrise concrete building fallback palette ───────────────────────────
CONCRETE_WALLS = [
    (145, 148, 152), (132, 135, 140), (158, 160, 163),
    (120, 124, 130), (150, 152, 155), (138, 141, 145),
    (162, 164, 167), (128, 131, 136), (148, 150, 154),
    (135, 138, 142),
]
CONCRETE_DARK  = ( 88,  90,  94)
GLASS_COLS     = [
    ( 90, 120, 145), ( 75, 108, 135), (100, 130, 155),
    ( 62,  95, 125), ( 85, 115, 142),
]
GLASS_SHEEN    = (160, 195, 220)


class Road:
    def __init__(self):
        # ── Fallback Pre-bakes ──────────────────────────────────────────────
        self._asphalt_surf  = self._bake_asphalt()
        self._compound_surf = self._bake_compound()
        self._trees         = self._place_trees()
        self._buildings     = self._place_buildings()
        self._median_blocks = list(range(0, SCREEN_WIDTH, 36))

        # --- NEW: Load buildings image (STATIC ASSET) ---
        self.buildings_img = None
        for filename in ["buildings.png", "buildings.jpg"]:
            if os.path.exists(filename):
                try:
                    img = pygame.image.load(filename).convert_alpha()
                    # Scale to fit the ENTIRE top safe zone (120px), not just the 70px wall area!
                    self.buildings_img = pygame.transform.scale(img, (SCREEN_WIDTH, FOOTPATH_HEIGHT))
                    break
                except Exception as e:
                    print(f"Warning: Could not load {filename}: {e}")

        # --- NEW: Load road texture image (STATIC ASSET) ---
        self.road_img = None
        for filename in ["road.png", "road.jpg"]:
            if os.path.exists(filename):
                try:
                    img = pygame.image.load(filename).convert_alpha()
                    # Scale to fit the total road height (all 3 lanes and median)
                    # This replaces the need for separate baked surfaces per lane.
                    road_total_h = LANE_HEIGHT * 3 + 15
                    self.road_img = pygame.transform.scale(img, (SCREEN_WIDTH, road_total_h))
                    break
                except Exception as e:
                    print(f"Warning: Could not load {filename}: {e}")

        # --- NEW: Load gate image (STATIC ASSET) ---
        self.gate_img = None
        for filename in ["gate.png", "gate.jpg"]:
            if os.path.exists(filename):
                try:
                    img = pygame.image.load(filename).convert_alpha()
                    # Scale the image to perfectly fit the 110px compound area
                    self.gate_img = pygame.transform.scale(img, (SCREEN_WIDTH, SCREEN_HEIGHT - COMPOUND_Y))
                    break
                except Exception as e:
                    print(f"Warning: Could not load {filename}: {e}")

    # ════════════════════════════════════════════════════════════════════
    #  Baking (Fallbacks)
    # ════════════════════════════════════════════════════════════════════

    def _bake_asphalt(self):
        road_h = LANE_HEIGHT * 3 + 15
        s = pygame.Surface((SCREEN_WIDTH, road_h))
        s.fill(ASPHALT)
        rng = random.Random(42)
        for _ in range(420):
            rx = rng.randint(0, SCREEN_WIDTH - 12)
            ry = rng.randint(0, road_h - 5)
            d  = rng.randint(-14, 18)
            c  = tuple(max(0, min(255, v + d)) for v in ASPHALT)
            pygame.draw.rect(s, c, (rx, ry, rng.randint(4, 22), rng.randint(2, 6)))
        return s

    def _bake_compound(self):
        """Small fallback grass compound below the wall."""
        h = max(1, SCREEN_HEIGHT - COMPOUND_Y)
        s = pygame.Surface((SCREEN_WIDTH, h))
        s.fill((52, 108, 48))
        return s

    def _place_trees(self):
        """A few fallback trees inside the compound."""
        rng = random.Random(17)
        trees = []
        gate_left  = SCREEN_WIDTH // 2 - 90
        gate_right = SCREEN_WIDTH // 2 + 90
        tree_top = COMPOUND_Y + 18
        tree_bot = SCREEN_HEIGHT - 10
        if tree_bot <= tree_top: return trees
        for _ in range(6):
            tx = rng.randint(30, gate_left - 20)
            ty = rng.randint(tree_top, tree_bot)
            trees.append({"x": tx, "y": ty, "r": rng.randint(10, 18), "shade": rng.randint(0, len(T_CANOPY) - 1)})
        return trees

    def _place_buildings(self):
        """Highrise concrete fallback against y=0."""
        bldg_zone_h = FOOTPATH_HEIGHT - FAR_FOOTPATH_H   # 70px
        rng   = random.Random(55)
        bldgs = []
        x = 0
        while x < SCREEN_WIDTH:
            w = rng.randint(55, 115)
            bldgs.append({"x": x, "w": w, "h": bldg_zone_h, "wall": CONCRETE_WALLS[rng.randint(0, len(CONCRETE_WALLS)-1)]})
            x += w + rng.randint(2, 8)
        return bldgs

    # ════════════════════════════════════════════════════════════════════
    #  Update
    # ════════════════════════════════════════════════════════════════════
    def update(self):
        pass

    # ════════════════════════════════════════════════════════════════════
    #  Draw
    # ════════════════════════════════════════════════════════════════════
    def draw(self, screen):
        self._draw_buildings(screen)
        self._draw_far_footpath(screen)
        self._draw_road(screen)
        # Note: We keep drawing median blocks and markings ON TOP of the static texture
        self._draw_median(screen)
        self._draw_markings(screen)
        self._draw_near_footpath(screen)
        # Check image and blit, or fallback to procedural draw
        self._draw_compound(screen)
        self._draw_iut_gate(screen)
        # Only draw fallback trees if image is missing
        if not self.gate_img:
            self._draw_trees(screen)
        self._draw_labels(screen)

    # ── Highrise concrete buildings (top, safe zone) [STATIC ASSET] ──────
    def _draw_buildings(self, screen):
        bldg_zone_h = FOOTPATH_HEIGHT - FAR_FOOTPATH_H  # 70px

        # Sky / background between towers
        pygame.draw.rect(screen, (52, 54, 58), (0, 0, SCREEN_WIDTH, bldg_zone_h))

        # If image exists, use it!
        if self.buildings_img:
            screen.blit(self.buildings_img, (0, 0))
            return

        # --- FALLBACK: Procedural buildings (if image is missing) ---
        for b in self._buildings:
            pygame.draw.rect(screen, b["wall"], (b["x"], 0, b["w"] - 1, b["h"]))
            pygame.draw.rect(screen, CONCRETE_DARK, (b["x"], 0, b["w"] - 1, 5))

    # ── Far-side footpath (player destination) ────────────────────────────
    def _draw_far_footpath(self, screen):
        # Skip procedural footpath if the buildings image is handling it!
        if self.buildings_img:
            return

        fp_y = FOOTPATH_HEIGHT - FAR_FOOTPATH_H  # 70
        fp_h = FAR_FOOTPATH_H  # 50
        pygame.draw.rect(screen, FOOTPATH_COL, (0, fp_y, SCREEN_WIDTH, fp_h))
        for ty in range(fp_y + 10, fp_y + fp_h, 10):
            pygame.draw.line(screen, FOOTPATH_LINE, (0, ty), (SCREEN_WIDTH, ty), 1)
        for tx in range(0, SCREEN_WIDTH, 40):
            pygame.draw.line(screen, FOOTPATH_LINE,
                             (tx, fp_y), (tx, fp_y + fp_h), 1)
        pygame.draw.rect(screen, (110, 100, 85),
                         (0, fp_y + fp_h - 4, SCREEN_WIDTH, 4))


    # ── Road [STATIC ASSET] ──────────────────────────────────────────────
    def _draw_road(self, screen):
        # If image exists, use it!
        if self.road_img:
            screen.blit(self.road_img, (0, FAR_LANE_Y))
            return

        # --- FALLBACK: Pre-baked asphalt (if image is missing) ---
        screen.blit(self._asphalt_surf, (0, FAR_LANE_Y))

    # ── Median — drawn OVER road texture ──────────────────────────────────
    def _draw_median(self, screen):
        med_h = 15
        med_y = MIDDLE_LANE_Y + LANE_HEIGHT - med_h
        mr    = pygame.Rect(0, med_y, SCREEN_WIDTH, med_h)
        pygame.draw.rect(screen, MEDIAN_CONC, mr)
        for sx in range(0, SCREEN_WIDTH, 14 * 2):
            pygame.draw.rect(screen, MEDIAN_YEL, (sx, med_y, 14, med_h))
        for bx in self._median_blocks:
            pygame.draw.rect(screen, (78, 74, 68), (bx + 32, med_y, 4, med_h))

    # ── Lane markings — drawn OVER road texture ────────────────────────────
    def _draw_markings(self, screen):
        far_sub    = FAR_LANE_Y    + LANE_HEIGHT // 2
        middle_sub = MIDDLE_LANE_Y + LANE_HEIGHT // 2
        near_sub   = NEAR_LANE_Y   + LANE_HEIGHT // 2
        self._dashes(screen, far_sub,    MARKING_W)
        self._dashes(screen, middle_sub, MARKING_W)
        self._dashes(screen, near_sub,   MARKING_W)
        for ly in (FAR_LANE_Y, MIDDLE_LANE_Y, NEAR_LANE_Y):
            pygame.draw.line(screen, MARKING_W, (0, ly), (SCREEN_WIDTH, ly), 2)
        for ax in range(150, SCREEN_WIDTH, 250):
            self._arrow(screen, ax, near_sub,   "left",  MARKING_W)
            self._arrow(screen, ax, far_sub,    "right", MARKING_W)

    def _arrow(self, screen, x, y, d, col):
        if d == "left": pts = [(x+14, y-5), (x+14, y+5), (x, y)]
        else: pts = [(x-14, y-5), (x-14, y+5), (x, y)]
        pygame.draw.polygon(screen, col, pts)

    # ── Near-side footpath (player start zone) ────────────────────────────
    def _draw_near_footpath(self, screen):
        fp_y = NEAR_LANE_Y + LANE_HEIGHT   # 540
        fp_h = NEAR_FOOTPATH_H              # 50
        pygame.draw.rect(screen, FOOTPATH_COL, (0, fp_y, SCREEN_WIDTH, fp_h))
        pygame.draw.rect(screen, (110, 100, 85), (0, fp_y, SCREEN_WIDTH, 4))
        pygame.draw.rect(screen, (110, 100, 85), (0, fp_y + fp_h - 3, SCREEN_WIDTH, 3))

    # ── IUT compound [Fallback logic] ─────────────────────────────────────
    def _draw_compound(self, screen):
        # We blit the fallback compound surface ONLY if the gate image is missing.
        # If the gate image is present, it's assumed to include the ground.
        if not self.gate_img:
            screen.blit(self._compound_surf, (0, COMPOUND_Y))

    # ── IUT Gate [STATIC ASSET] ──────────────────────────────────────────
    def _draw_iut_gate(self, screen):
        # If the pixel art image loaded successfully, use it!
        if self.gate_img:
            # Align the image perfectly below the footpath
            screen.blit(self.gate_img, (0, COMPOUND_Y))
            return

        # --- FALLBACK: Procedural Gate Generation (if image is missing) ---
        pygame.draw.rect(screen, (158, 58, 42), (0, COMPOUND_Y, SCREEN_WIDTH, 16))

    # ── Labels — drawn OVER everything ─────────────────────────────────────
    def _draw_labels(self, screen):
        f_sm = pygame.font.SysFont("Arial", 11, bold=True)
        f_rd = pygame.font.SysFont("Arial", 10)

        # Road name in middle lane
        rn = f_rd.render("N3  ·  DHAKA-MYMENSINGH ROAD", True, (92, 90, 86))
        screen.blit(rn, (SCREEN_WIDTH // 2 - rn.get_width() // 2,
                         MIDDLE_LANE_Y + LANE_HEIGHT // 2 - 6))

        # Safe zone label in far footpath (Only if buildings image is missing)
        if not self.buildings_img:
            sz = f_sm.render("SAFE ZONE", True, (60, 148, 58))
            fp_y = FOOTPATH_HEIGHT - FAR_FOOTPATH_H
            screen.blit(sz, (SCREEN_WIDTH // 2 - sz.get_width() // 2,
                             fp_y + FAR_FOOTPATH_H // 2 - 6))

        # Start label on near footpath
        st = f_sm.render("START", True, (80, 148, 72))
        fp_near_y = NEAR_LANE_Y + LANE_HEIGHT
        screen.blit(st, (SCREEN_WIDTH // 2 - st.get_width() // 2,
                         fp_near_y + NEAR_FOOTPATH_H // 2 - 6))

    # ── Static dash helper ────────────────────────────────────────────────
    def _dashes(self, screen, y, color, dash=34, gap=46, thickness=2):
        x = 0
        while x < SCREEN_WIDTH:
            x2 = min(x + dash, SCREEN_WIDTH)
            pygame.draw.line(screen, color, (x, y), (x2, y), thickness)
            x += dash + gap