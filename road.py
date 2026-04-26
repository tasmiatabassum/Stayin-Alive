# road.py
"""
N3 Dhaka-Mymensingh Road — IUT Board Bazar
===========================================
Top-down view. Player starts at BOTTOM footpath (IUT side) and crosses UP
to the far-side footpath (safe zone).

New geometry (from config.py):
  y=0   ..120  : far safe zone (70px highrise buildings + 50px footpath)
  y=120 ..260  : FAR LANE  →→→
  y=260 ..275  : MEDIAN
  y=260 ..400  : MIDDLE LANE  ←→
  y=400 ..540  : NEAR LANE  ←←←
  y=540 ..590  : near footpath (player start zone, 50px)
  y=590 ..700  : IUT compound + gate + trees (110px, compact)
"""

import pygame
import random
from config import *

# ── Palette ───────────────────────────────────────────────────────────────
ASPHALT       = (68,  66,  64)
MARKING_W     = (222, 218, 200)
MEDIAN_CONC   = (136, 128, 115)
MEDIAN_YEL    = (205, 162,  18)

# IUT compound
IUT_GRASS     = ( 52, 108,  48)
BRICK_A       = (158,  58,  42)
BRICK_B       = (178,  78,  60)
BRICK_MORTAR  = ( 95,  38,  28)
ARCH_CREAM    = (232, 218, 195)
SIGN_GREEN    = ( 20,  95,  40)

# Footpath (both sides) — warm concrete
FOOTPATH_COL  = (185, 173, 152)
FOOTPATH_LINE = (160, 148, 128)

# Trees (IUT compound only)
T_CANOPY  = [( 42,  98,  38), ( 55, 118,  48), ( 35,  82,  32)]
T_SHADOW  = ( 28,  68,  26)
T_TRUNK   = ( 88,  62,  38)
T_LIGHT   = ( 72, 138,  58)

# ── Highrise concrete building palette ────────────────────────────────────
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
        self._asphalt_surf  = self._bake_asphalt()
        self._compound_surf = self._bake_compound()
        self._trees         = self._place_trees()
        self._buildings     = self._place_buildings()
        self._median_blocks = list(range(0, SCREEN_WIDTH, 36))

    # ════════════════════════════════════════════════════════════════════
    #  Baking
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
        for _ in range(55):
            tx = rng.randint(0, SCREEN_WIDTH)
            ty = rng.randint(0, road_h)
            pygame.draw.line(s, (55, 53, 51),
                             (tx, ty), (tx + rng.randint(20, 90), ty), 1)
        return s

    def _bake_compound(self):
        """Small IUT grass compound below the wall — no gate drawn here."""
        h = max(1, SCREEN_HEIGHT - COMPOUND_Y)
        s = pygame.Surface((SCREEN_WIDTH, h))
        s.fill(IUT_GRASS)
        rng = random.Random(9)
        for _ in range(120):
            gx = rng.randint(0, SCREEN_WIDTH - 10)
            gy = rng.randint(0, h - 6)
            d  = rng.randint(-10, 8)
            c  = tuple(max(0, min(255, v + d)) for v in IUT_GRASS)
            pygame.draw.rect(s, c, (gx, gy, rng.randint(6, 18), rng.randint(3, 8)))
        # Central path strip
        path_x = SCREEN_WIDTH // 2 - 24
        pygame.draw.rect(s, (165, 148, 122), (path_x, 0, 48, h))
        pygame.draw.line(s, (140, 125, 100), (path_x, 0), (path_x, h), 1)
        pygame.draw.line(s, (140, 125, 100), (path_x + 47, 0), (path_x + 47, h), 1)
        return s

    def _place_trees(self):
        """A few trees inside the compact compound, avoiding gate area."""
        rng = random.Random(17)
        trees = []
        gate_left  = SCREEN_WIDTH // 2 - 90
        gate_right = SCREEN_WIDTH // 2 + 90
        # Trees only deep in compound (below gate wall)
        tree_top = COMPOUND_Y + 18
        tree_bot = SCREEN_HEIGHT - 10

        if tree_bot <= tree_top:
            return trees

        for _ in range(6):
            tx = rng.randint(30, gate_left - 20)
            ty = rng.randint(tree_top, tree_bot)
            trees.append({"x": tx, "y": ty, "r": rng.randint(10, 18),
                          "shade": rng.randint(0, len(T_CANOPY) - 1)})
        for _ in range(6):
            tx = rng.randint(gate_right + 20, SCREEN_WIDTH - 30)
            ty = rng.randint(tree_top, tree_bot)
            trees.append({"x": tx, "y": ty, "r": rng.randint(10, 18),
                          "shade": rng.randint(0, len(T_CANOPY) - 1)})
        return trees

    def _place_buildings(self):
        """
        Highrise concrete towers flush against y=0.
        Buildings fill y=0..(FOOTPATH_HEIGHT - FAR_FOOTPATH_H).
        Each gets a facade of glass grid panels — top-down view shows
        the roof/top floor with window bands.
        """
        bldg_zone_h = FOOTPATH_HEIGHT - FAR_FOOTPATH_H   # 70px
        rng   = random.Random(55)
        bldgs = []
        x = 0
        while x < SCREEN_WIDTH:
            w = rng.randint(55, 115)
            bldgs.append({
                "x": x, "w": w, "h": bldg_zone_h,
                "wall":    CONCRETE_WALLS[rng.randint(0, len(CONCRETE_WALLS)-1)],
                "glass":   GLASS_COLS[rng.randint(0, len(GLASS_COLS)-1)],
                "floors":  rng.randint(8, 25),   # label only
                "win_cols": rng.randint(3, 7),
                "win_rows": rng.randint(2, 4),
            })
            x += w + rng.randint(2, 8)   # alley gap
        return bldgs

    # ════════════════════════════════════════════════════════════════════
    #  Update
    # ════════════════════════════════════════════════════════════════════
    def update(self):
        pass   # static scene

    # ════════════════════════════════════════════════════════════════════
    #  Draw
    # ════════════════════════════════════════════════════════════════════
    def draw(self, screen):
        self._draw_buildings(screen)
        self._draw_far_footpath(screen)
        self._draw_road(screen)
        self._draw_median(screen)
        self._draw_markings(screen)
        self._draw_near_footpath(screen)
        self._draw_compound(screen)
        self._draw_iut_gate(screen)
        self._draw_trees(screen)
        self._draw_labels(screen)

    # ── Highrise concrete buildings (top, safe zone) ──────────────────────
    def _draw_buildings(self, screen):
        bldg_zone_h = FOOTPATH_HEIGHT - FAR_FOOTPATH_H  # 70px

        # Sky / background between towers
        pygame.draw.rect(screen, (52, 54, 58), (0, 0, SCREEN_WIDTH, bldg_zone_h))

        for b in self._buildings:
            bx, bw, bh = b["x"], b["w"], b["h"]
            wall = b["wall"]
            glass = b["glass"]

            # ── Concrete facade (main body) ──────────────────────────────
            pygame.draw.rect(screen, wall, (bx, 0, bw - 1, bh))

            # Top edge: darker parapet / cornice
            pygame.draw.rect(screen, CONCRETE_DARK, (bx, 0, bw - 1, 5))

            # Concrete texture: subtle vertical ribs
            rib_step = max(8, bw // 6)
            for rx in range(bx + rib_step, bx + bw - 4, rib_step):
                pygame.draw.line(screen,
                                 tuple(max(0, v - 15) for v in wall),
                                 (rx, 5), (rx, bh - 1), 1)

            # ── Glass window band — horizontal rows ──────────────────────
            win_cols = b["win_cols"]
            win_rows = b["win_rows"]
            margin_x = 6
            margin_y = 8
            win_w = max(4, (bw - margin_x * 2 - (win_cols - 1) * 3) // win_cols)
            win_h = max(3, (bh - margin_y * 2 - (win_rows - 1) * 3) // win_rows)
            for row in range(win_rows):
                for col in range(win_cols):
                    wx = bx + margin_x + col * (win_w + 3)
                    wy = margin_y + row * (win_h + 3)
                    if wx + win_w < bx + bw - 3 and wy + win_h < bh - 2:
                        # Glass pane
                        pygame.draw.rect(screen, glass, (wx, wy, win_w, win_h))
                        # Sheen on top-left corner of each pane
                        pygame.draw.line(screen, GLASS_SHEEN,
                                         (wx, wy), (wx + win_w // 3, wy), 1)
                        pygame.draw.line(screen, GLASS_SHEEN,
                                         (wx, wy), (wx, wy + win_h // 2), 1)

            # ── Rooftop details ──────────────────────────────────────────
            rng2 = random.Random(b["x"] * 13)
            # Water tank
            if rng2.random() > 0.4:
                tx = bx + rng2.randint(4, max(5, bw // 2 - 8))
                pygame.draw.rect(screen, (105, 105, 108), (tx, 2, 8, 4))
            # AC units
            for _ in range(rng2.randint(0, 3)):
                ax = bx + rng2.randint(4, max(5, bw - 10))
                pygame.draw.rect(screen, (118, 120, 125), (ax, 3, 5, 3))

            # Floor count label (tiny)
            font_tiny = pygame.font.SysFont("Arial", 6)
            lbl = font_tiny.render(f"{b['floors']}F", True, (60, 62, 65))
            if lbl.get_width() < bw - 4:
                screen.blit(lbl, (bx + 2, bh - 8))

            # Alley shadow
            pygame.draw.rect(screen, (30, 30, 32), (bx + bw - 1, 0, 1, bh))

    # ── Far-side footpath (player destination) ────────────────────────────
    def _draw_far_footpath(self, screen):
        fp_y = FOOTPATH_HEIGHT - FAR_FOOTPATH_H   # 70
        fp_h = FAR_FOOTPATH_H                      # 50
        pygame.draw.rect(screen, FOOTPATH_COL, (0, fp_y, SCREEN_WIDTH, fp_h))
        # Paving tile lines
        for ty in range(fp_y + 10, fp_y + fp_h, 10):
            pygame.draw.line(screen, FOOTPATH_LINE, (0, ty), (SCREEN_WIDTH, ty), 1)
        # Vertical grout lines (every 40px)
        for tx in range(0, SCREEN_WIDTH, 40):
            pygame.draw.line(screen, FOOTPATH_LINE,
                             (tx, fp_y), (tx, fp_y + fp_h), 1)
        # Kerb at road edge (bottom of footpath)
        pygame.draw.rect(screen, (110, 100, 85),
                         (0, fp_y + fp_h - 4, SCREEN_WIDTH, 4))

    # ── Road ─────────────────────────────────────────────────────────────
    def _draw_road(self, screen):
        screen.blit(self._asphalt_surf, (0, FAR_LANE_Y))

    # ── Median ────────────────────────────────────────────────────────────
    def _draw_median(self, screen):
        med_h = 15
        med_y = MIDDLE_LANE_Y + LANE_HEIGHT - med_h
        mr    = pygame.Rect(0, med_y, SCREEN_WIDTH, med_h)
        pygame.draw.rect(screen, MEDIAN_CONC, mr)
        sw = 14
        for sx in range(0, SCREEN_WIDTH, sw * 2):
            pygame.draw.rect(screen, MEDIAN_YEL, (sx, med_y, sw, med_h))
        for bx in self._median_blocks:
            pygame.draw.rect(screen, (78, 74, 68), (bx + 32, med_y, 4, med_h))
        pygame.draw.line(screen, (75, 70, 62),
                         (0, med_y), (SCREEN_WIDTH, med_y), 2)
        pygame.draw.line(screen, (162, 155, 140),
                         (0, mr.bottom - 1), (SCREEN_WIDTH, mr.bottom - 1), 1)

    # ── Lane markings — STATIC ────────────────────────────────────────────
    def _draw_markings(self, screen):
        far_sub    = FAR_LANE_Y    + LANE_HEIGHT // 2
        middle_sub = MIDDLE_LANE_Y + LANE_HEIGHT // 2
        near_sub   = NEAR_LANE_Y   + LANE_HEIGHT // 2

        self._dashes(screen, far_sub,    MARKING_W)
        self._dashes(screen, middle_sub, MARKING_W)
        self._dashes(screen, near_sub,   MARKING_W)

        for ly in (FAR_LANE_Y, MIDDLE_LANE_Y, NEAR_LANE_Y):
            pygame.draw.line(screen, MARKING_W,
                             (0, ly), (SCREEN_WIDTH, ly), 2)

        for ax in range(150, SCREEN_WIDTH, 250):
            self._arrow(screen, ax, near_sub,   "left",  MARKING_W)
            self._arrow(screen, ax, far_sub,    "right", MARKING_W)

    def _arrow(self, screen, x, y, d, col):
        if d == "left":
            pts = [(x+14, y-5), (x+14, y+5), (x, y)]
            pygame.draw.line(screen, col, (x+14, y), (x+30, y), 3)
        else:
            pts = [(x-14, y-5), (x-14, y+5), (x, y)]
            pygame.draw.line(screen, col, (x-14, y), (x-30, y), 3)
        pygame.draw.polygon(screen, col, pts)

    # ── Near-side footpath (player start zone) ────────────────────────────
    def _draw_near_footpath(self, screen):
        fp_y = NEAR_LANE_Y + LANE_HEIGHT   # 540
        fp_h = NEAR_FOOTPATH_H              # 50
        pygame.draw.rect(screen, FOOTPATH_COL, (0, fp_y, SCREEN_WIDTH, fp_h))
        for ty in range(fp_y + 10, fp_y + fp_h, 10):
            pygame.draw.line(screen, FOOTPATH_LINE, (0, ty), (SCREEN_WIDTH, ty), 1)
        for tx in range(0, SCREEN_WIDTH, 40):
            pygame.draw.line(screen, FOOTPATH_LINE,
                             (tx, fp_y), (tx, fp_y + fp_h), 1)
        # Kerb at road edge (top)
        pygame.draw.rect(screen, (110, 100, 85), (0, fp_y, SCREEN_WIDTH, 4))
        # Kerb at compound edge (bottom)
        pygame.draw.rect(screen, (110, 100, 85),
                         (0, fp_y + fp_h - 3, SCREEN_WIDTH, 3))

    # ── IUT compound ──────────────────────────────────────────────────────
    def _draw_compound(self, screen):
        screen.blit(self._compound_surf, (0, COMPOUND_Y))

    # ── IUT Gate — full-size, sits at COMPOUND_Y wall ─────────────────────
    def _draw_iut_gate(self, screen):
        """
        Iconic IUT gate rendered top-down.
        - Full-width brick boundary wall at COMPOUND_Y (top of compound)
        - Central gate structure: wide, with twin towers, arch opening, green signs
        - Gate is fully ABOVE the player spawn zone (footpath)
        - Player walks through the arch opening at compound boundary
        """
        wall_y = COMPOUND_Y
        wall_h = 16

        # ── Full-width brick boundary wall ───────────────────────────────
        for bx in range(0, SCREEN_WIDTH, 28):
            col = BRICK_A if (bx // 28) % 2 == 0 else BRICK_B
            pygame.draw.rect(screen, col, (bx, wall_y, 27, wall_h))
        pygame.draw.line(screen, BRICK_MORTAR,
                         (0, wall_y), (SCREEN_WIDTH, wall_y), 2)
        pygame.draw.line(screen, BRICK_MORTAR,
                         (0, wall_y + wall_h // 2),
                         (SCREEN_WIDTH, wall_y + wall_h // 2), 1)
        pygame.draw.line(screen, (50, 22, 14),
                         (0, wall_y + wall_h - 1),
                         (SCREEN_WIDTH, wall_y + wall_h - 1), 2)

        # ── Central gate structure ────────────────────────────────────────
        cx      = SCREEN_WIDTH // 2
        gate_w  = 200
        gate_h  = 52          # full size gate that protrudes above the wall
        gate_x  = cx - gate_w // 2
        gate_y  = wall_y - (gate_h - wall_h)   # extends up into the footpath area

        # Gate body (brick)
        for bx in range(gate_x, gate_x + gate_w, 20):
            col = BRICK_A if ((bx - gate_x) // 20) % 2 == 0 else BRICK_B
            pygame.draw.rect(screen, col, (bx, gate_y, 19, gate_h))

        # Top and bottom edges of gate structure
        pygame.draw.rect(screen, BRICK_MORTAR, (gate_x, gate_y, gate_w, 2))
        pygame.draw.rect(screen, (50, 22, 14),
                         (gate_x, gate_y + gate_h - 2, gate_w, 2))

        # ── Arch opening (cream/white) ────────────────────────────────────
        arch_w  = 60
        arch_h  = gate_h - 8
        arch_x  = cx - arch_w // 2
        arch_y  = gate_y + 4
        pygame.draw.rect(screen, ARCH_CREAM,
                         (arch_x, arch_y, arch_w, arch_h), border_radius=6)

        # Arch columns flanking the opening
        for col_x in [arch_x - 12, arch_x + arch_w]:
            pygame.draw.rect(screen, (202, 192, 175),
                             (col_x, arch_y - 2, 12, arch_h + 4))
            pygame.draw.rect(screen, ARCH_CREAM,
                             (col_x + 2, arch_y, 8, arch_h), border_radius=2)

        # Shadow inside arch top
        pygame.draw.rect(screen, (165, 150, 128),
                         (arch_x + 4, arch_y, arch_w - 8, 6))

        # ── Green sign panels (left and right of arch) ────────────────────
        sign_h  = 14
        sign_y  = gate_y + (gate_h - sign_h) // 2
        lsign_x = gate_x + 4
        lsign_w = arch_x - gate_x - 16
        pygame.draw.rect(screen, SIGN_GREEN,
                         (lsign_x, sign_y, lsign_w, sign_h), border_radius=2)
        rsign_x = arch_x + arch_w + 24
        rsign_w = gate_x + gate_w - rsign_x - 4
        pygame.draw.rect(screen, SIGN_GREEN,
                         (rsign_x, sign_y, rsign_w, sign_h), border_radius=2)

        font_s = pygame.font.SysFont("Arial", 7, bold=True)
        lt = font_s.render("ISLAMIC UNIVERSITY", True, (220, 240, 210))
        rt = font_s.render("OF TECHNOLOGY", True, (220, 240, 210))
        screen.blit(lt, (lsign_x + 2, sign_y + 2))
        screen.blit(rt, (rsign_x + 2, sign_y + 2))

        # ── OIC logo circles on gate pillars ─────────────────────────────
        for ox in [gate_x + 18, gate_x + gate_w - 18]:
            pygame.draw.circle(screen, (215, 200, 178), (ox, gate_y + 16), 7)
            pygame.draw.circle(screen, SIGN_GREEN, (ox, gate_y + 16), 5)

        # ── IUT compound name above gate ──────────────────────────────────
        font_lbl = pygame.font.SysFont("Arial", 13, bold=True)
        lbl = font_lbl.render("ISLAMIC UNIVERSITY OF TECHNOLOGY",
                              True, (215, 235, 210))
        screen.blit(lbl, (cx - lbl.get_width() // 2, gate_y - 16))

    # ── Trees (compact compound) ──────────────────────────────────────────
    def _draw_trees(self, screen):
        for t in self._trees:
            x, y, r = t["x"], t["y"], t["r"]
            col = T_CANOPY[t["shade"]]
            pygame.draw.ellipse(screen, T_SHADOW,
                                (x - r + 4, y - r // 2 + 4,
                                 r * 2 - 2, int(r * 0.9)))
            pygame.draw.circle(screen, col, (x, y), r)
            pygame.draw.circle(screen, T_LIGHT,
                                (x - r // 3, y - r // 3), r // 2)
            pygame.draw.circle(screen, T_SHADOW,
                                (x + r // 4, y + r // 4), r // 3)
            pygame.draw.circle(screen, T_TRUNK, (x, y), max(2, r // 5))

    # ── Labels ────────────────────────────────────────────────────────────
    def _draw_labels(self, screen):
        f_sm = pygame.font.SysFont("Arial", 11, bold=True)
        f_rd = pygame.font.SysFont("Arial", 10)

        # Road name in middle lane
        rn = f_rd.render("N3  ·  DHAKA-MYMENSINGH ROAD", True, (92, 90, 86))
        screen.blit(rn, (SCREEN_WIDTH // 2 - rn.get_width() // 2,
                         MIDDLE_LANE_Y + LANE_HEIGHT // 2 - 6))

        # Safe zone label in far footpath
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