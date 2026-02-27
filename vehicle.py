# vehicle.py
import pygame
import random
from config import *

# --- Vehicle Type Definitions ---
VEHICLE_TYPES = {
    "car":        {"width": 70,  "height": 34, "weight": 5},
    "motorcycle": {"width": 38,  "height": 16, "weight": 3},
    "bus":        {"width": 130, "height": 46, "weight": 2},
    "truck":      {"width": 110, "height": 42, "weight": 2},
}

COLORS_LEFT = {
    "car":        [(220, 50, 50),  (200, 80, 40),  (160, 30, 30)],
    "motorcycle": [(230, 100, 20), (200, 60, 10)],
    "bus":        [(180, 40, 40),  (150, 20, 20)],
    "truck":      [(190, 60, 30),  (160, 40, 20)],
}
COLORS_RIGHT = {
    "car":        [(50, 100, 220), (40, 130, 200), (60, 80, 180)],
    "motorcycle": [(60, 180, 220), (40, 150, 200)],
    "bus":        [(30, 80, 180),  (20, 60, 155)],
    "truck":      [(40, 100, 170), (30, 75, 150)],
}

# ── NaSch parameters ────────────────────────────────────────────────────
# p_slow: probability of spontaneous deceleration each step.
# This is the "randomisation" term that produces phantom traffic jams.
# Values from literature: 0.1–0.3 (Nagel & Schreckenberg 1992).
NASCH_P_SLOW = {
    "car":        0.10,
    "motorcycle": 0.08,   # bikes react faster, fewer phantom jams
    "bus":        0.15,   # buses are erratic
    "truck":      0.18,   # trucks are the worst offenders
}
NASCH_ACCEL = 0.35        # px/frame² — acceleration per step


class Vehicle:
    def __init__(self, lane_y, direction_left=True, sub_lane=0,
                 vtype=None, speed_override=None):
        self.lane_y         = lane_y
        self.direction_left = direction_left
        self.sub_lane       = sub_lane

        self.vtype = vtype if vtype else "car"
        vdata = VEHICLE_TYPES[self.vtype]
        self.w = vdata["width"]
        self.h = vdata["height"]

        y_offset        = SUB_LANE_OFFSET_0 if self.sub_lane == 0 else SUB_LANE_OFFSET_1
        y_center_offset = (50 - self.h) // 2
        self.rect = pygame.Rect(0, lane_y + y_offset + y_center_offset, self.w, self.h)

        if speed_override is not None:
            raw_speed = speed_override
        else:
            raw_speed = random.randint(3, 6)

        if self.direction_left:
            self.rect.x    = SCREEN_WIDTH + 50
            self.base_speed = -abs(raw_speed)
            self.color      = random.choice(COLORS_LEFT[self.vtype])
        else:
            self.rect.x    = -self.w - 50
            self.base_speed = abs(raw_speed)
            self.color      = random.choice(COLORS_RIGHT[self.vtype])

        self.color_dark  = tuple(max(0,   c - 60) for c in self.color)
        self.color_light = tuple(min(255, c + 70) for c in self.color)
        self.shadow      = tuple(max(0,   c - 90) for c in self.color)

        self.current_speed   = self.base_speed
        self.switch_cooldown = 0

        # NaSch stochastic parameter for this vehicle instance
        self.p_slow = NASCH_P_SLOW.get(self.vtype, 0.10)

    # ── Update ──────────────────────────────────────────────────────────
    def update(self, all_vehicles, speed_multiplier: float = 1.0):
        self.switch_cooldown = max(0, self.switch_cooldown - 1)

        # Head-on evasion only needed in the chaotic middle lane
        if self.lane_y == MIDDLE_LANE_Y:
            self.check_head_on(all_vehicles)

        # Nagel-Schreckenberg 4-step rule replaces the old maintain_distance()
        self._nasch_step(all_vehicles, speed_multiplier)

    # ── Nagel-Schreckenberg Cellular Automaton ───────────────────────────
    def _nasch_step(self, all_vehicles, speed_multiplier: float) -> None:
        """
        Four-step NaSch update (Nagel & Schreckenberg 1992):

          1. Accelerate  : v ← min(v + a,  v_max)
          2. Brake       : v ← min(v,  gap / look_ahead)     [collision avoidance]
          3. Randomise   : v ← max(v - a,  0)  with prob p_slow  [phantom jams]
          4. Move        : x ← x + v

        All quantities in pixels/frame so no unit conversion is needed.
        The 'look_ahead' divisor converts pixel distance → speed headroom.
        """
        v_max  = abs(self.base_speed) * speed_multiplier
        accel  = NASCH_ACCEL

        spd = abs(self.current_speed)

        # ── Step 1 · Accelerate ─────────────────────────────────────────
        spd = min(spd + accel, v_max)

        # ── Step 2 · Brake ──────────────────────────────────────────────
        gap = self._gap_to_ahead(all_vehicles)
        if gap is not None:
            # Clamp speed so the vehicle won't close the gap in <8 frames.
            # Factor of 8 chosen empirically to prevent bumping at game speeds.
            safe_spd = max(0.0, (gap - self.w * 0.25) / 8.0)
            spd      = min(spd, safe_spd)

        # ── Step 3 · Stochastic deceleration (phantom traffic jams) ─────
        if random.random() < self.p_slow:
            spd = max(0.0, spd - accel)

        # ── Step 4 · Move ───────────────────────────────────────────────
        self.current_speed = -spd if self.direction_left else spd
        self.rect.x       += int(self.current_speed)

    def _gap_to_ahead(self, all_vehicles) -> float | None:
        """
        Returns the pixel gap to the nearest same-lane, same-direction
        vehicle that is directly ahead, or None if the road is clear.
        """
        min_gap = None
        for other in all_vehicles:
            if (other is not self
                    and other.lane_y        == self.lane_y
                    and other.sub_lane      == self.sub_lane
                    and other.direction_left == self.direction_left):

                if self.direction_left:
                    # Both move left.  'Ahead' means lower x than self.
                    d = self.rect.x - other.rect.right
                else:
                    # Both move right.  'Ahead' means higher x than self.
                    d = other.rect.x - self.rect.right

                if d > 0:
                    min_gap = d if min_gap is None else min(min_gap, d)
        return min_gap

    # ── Middle-lane AI (unchanged) ───────────────────────────────────────
    def check_head_on(self, all_vehicles):
        if self.switch_cooldown > 0:
            return
        for other in all_vehicles:
            if (other.lane_y == self.lane_y and
                    other.sub_lane == self.sub_lane and
                    other.direction_left != self.direction_left):
                distance = other.rect.x - self.rect.x
                danger   = ((-200 < distance < 0) if self.direction_left
                            else (0 < distance < 200))
                if danger:
                    self.attempt_lane_switch(all_vehicles)
                    break

    def attempt_lane_switch(self, all_vehicles):
        target_sub = 1 - self.sub_lane
        ty         = SUB_LANE_OFFSET_0 if target_sub == 0 else SUB_LANE_OFFSET_1
        tr         = self.rect.copy()
        tr.y       = self.lane_y + ty
        if all(not v.rect.colliderect(tr) for v in all_vehicles):
            self.sub_lane        = target_sub
            self.rect.y          = self.lane_y + ty
            self.switch_cooldown = 60

    # ── Draw (top-down) ──────────────────────────────────────────────────
    def draw(self, screen):
        {"car": self._draw_car, "motorcycle": self._draw_motorcycle,
         "bus": self._draw_bus, "truck": self._draw_truck}[self.vtype](screen)

    def _front_x(self, r):
        return r.right if not self.direction_left else r.x

    def _headlight_color(self):
        return (255, 255, 160) if not self.direction_left else (255, 70, 70)

    # ── CAR ──────────────────────────────────────────────────────────────
    def _draw_car(self, screen):
        r = self.rect
        pygame.draw.rect(screen, self.shadow, r.move(2, 2), border_radius=6)
        pygame.draw.rect(screen, self.color,  r,            border_radius=6)
        ws_w = 10
        ws_x = r.right - ws_w - 4 if not self.direction_left else r.x + 4
        pygame.draw.rect(screen, (180, 215, 255),
                         pygame.Rect(ws_x, r.y+4, ws_w, r.height-8), border_radius=3)
        pygame.draw.rect(screen, self.color_dark,
                         pygame.Rect(r.x+16, r.y+5, r.width-32, r.height-10), border_radius=4)
        rw_x = r.x+4 if not self.direction_left else r.right-12
        pygame.draw.rect(screen, (140, 180, 210),
                         pygame.Rect(rw_x, r.y+4, 8, r.height-8), border_radius=2)
        lc = self._headlight_color()
        fx = self._front_x(r)
        lx = fx-3 if not self.direction_left else fx+3
        pygame.draw.circle(screen, lc, (lx, r.y+6),       4)
        pygame.draw.circle(screen, lc, (lx, r.bottom-6),  4)
        bx = r.x+3 if not self.direction_left else r.right-3
        pygame.draw.circle(screen, (220, 30, 30), (bx, r.y+6),      3)
        pygame.draw.circle(screen, (220, 30, 30), (bx, r.bottom-6), 3)

    # ── MOTORCYCLE ───────────────────────────────────────────────────────
    def _draw_motorcycle(self, screen):
        r  = self.rect
        cx, cy = r.centerx, r.centery
        pygame.draw.ellipse(screen, self.shadow, r.move(2, 2))
        pygame.draw.rect(screen, self.color,
                         pygame.Rect(r.x, cy-5, r.width, 10), border_radius=5)
        pygame.draw.ellipse(screen, self.color_dark,
                            pygame.Rect(cx-9, cy-7, 18, 14))
        hx = r.right-8 if not self.direction_left else r.x+8
        pygame.draw.circle(screen, self.color_light, (hx, cy), 6)
        lc = self._headlight_color()
        fx = self._front_x(r)
        lx = fx-2 if not self.direction_left else fx+2
        pygame.draw.circle(screen, lc, (lx, cy), 3)

    # ── BUS ──────────────────────────────────────────────────────────────
    def _draw_bus(self, screen):
        r = self.rect
        pygame.draw.rect(screen, self.shadow, r.move(3, 3), border_radius=4)
        pygame.draw.rect(screen, self.color,  r,            border_radius=4)
        pygame.draw.rect(screen, self.color_dark,
                         pygame.Rect(r.x+10, r.y+4, r.width-20, r.height-8))
        win_h = 5
        num_w = (r.width - 24) // 14
        for i in range(num_w):
            wx = r.x + 12 + i * 14
            pygame.draw.rect(screen, (180, 215, 255), pygame.Rect(wx, r.y+1, 10, win_h))
            pygame.draw.rect(screen, (180, 215, 255), pygame.Rect(wx, r.bottom-1-win_h, 10, win_h))
        ws_w = 10
        ws_x = r.right-ws_w-2 if not self.direction_left else r.x+2
        pygame.draw.rect(screen, (180, 215, 255),
                         pygame.Rect(ws_x, r.y+3, ws_w, r.height-6))
        lc = self._headlight_color()
        fx = self._front_x(r)
        lx = fx-4 if not self.direction_left else fx+4
        pygame.draw.rect(screen, lc, pygame.Rect(lx-3, r.y+4,      6, 6))
        pygame.draw.rect(screen, lc, pygame.Rect(lx-3, r.bottom-10, 6, 6))

    # ── TRUCK ────────────────────────────────────────────────────────────
    def _draw_truck(self, screen):
        r       = self.rect
        cab_w   = int(r.width * 0.32)
        cargo_w = r.width - cab_w

        if not self.direction_left:
            cab_rect   = pygame.Rect(r.right-cab_w, r.y, cab_w,   r.height)
            cargo_rect = pygame.Rect(r.x,           r.y, cargo_w, r.height)
        else:
            cab_rect   = pygame.Rect(r.x,           r.y, cab_w,   r.height)
            cargo_rect = pygame.Rect(r.x+cab_w,     r.y, cargo_w, r.height)

        pygame.draw.rect(screen, self.shadow,     r.move(3, 3),  border_radius=4)
        pygame.draw.rect(screen, self.color_dark, cargo_rect,    border_radius=2)
        for py in range(cargo_rect.y+7, cargo_rect.bottom-5, 7):
            pygame.draw.line(screen, self.shadow,
                             (cargo_rect.x+3, py), (cargo_rect.right-3, py), 1)
        pygame.draw.rect(screen, self.color, cargo_rect, 2, border_radius=2)
        pygame.draw.rect(screen, self.color, cab_rect,   border_radius=5)
        ws_x = cab_rect.right-11 if not self.direction_left else cab_rect.x+2
        pygame.draw.rect(screen, (180, 215, 255),
                         pygame.Rect(ws_x, cab_rect.y+3, 9, cab_rect.height-6), border_radius=2)
        pygame.draw.rect(screen, self.color_dark,
                         pygame.Rect(cab_rect.x+4, cab_rect.y+4,
                                     cab_rect.width-8, cab_rect.height-8), border_radius=3)
        lc = self._headlight_color()
        fx = self._front_x(r)
        lx = fx-3 if not self.direction_left else fx+3
        pygame.draw.circle(screen, lc, (lx, cab_rect.y+6),       4)
        pygame.draw.circle(screen, lc, (lx, cab_rect.bottom-6),  4)