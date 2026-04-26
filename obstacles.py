# obstacles.py
"""
Dhaka-Specific Obstacles
=========================
Three obstacle classes that live on the footpaths and median:

1. **Pothole** — static hazard on the near footpath.
   On collision the player is stunned (velocity zeroed, stun timer set).
   Rendered as a rough dark ellipse with cracked-asphalt texture.

2. **StreetVendor** — static cart/stall placed at the near footpath edges.
   Acts as an impassable box the player must navigate around.
   Does NOT stun; purely a navigation obstacle.

3. **NPCPedestrian** — AI pedestrian that crosses the road on a random
   gap-acceptance schedule drawn from a Log-Normal distribution
   (matching the logger model in logger.py).
   - If hit by a vehicle it flashes red and resets (warning to player).
   - Player can "tail" behind them, but the NPC may stop mid-lane if
     its sampled gap turns out to be unsafe.

All three are managed by **ObstacleManager** which is the only public
interface used by main.py.
"""

import pygame
import random
import math
from config import (SCREEN_WIDTH, SCREEN_HEIGHT, COMPOUND_Y,
                    NEAR_LANE_Y, LANE_HEIGHT, FAR_LANE_Y,
                    NEAR_FOOTPATH_H, FOOTPATH_HEIGHT, FAR_FOOTPATH_H,
                    MIDDLE_LANE_Y)

# ── Palette ──────────────────────────────────────────────────────────────
POTHOLE_DARK = (35, 30, 28)
POTHOLE_RIM = (85, 78, 70)
CRACK_COL = (50, 44, 40)
VENDOR_BODY = (180, 135, 60)
VENDOR_AWNING = (200, 55, 35)
VENDOR_GOODS = (220, 190, 80)
NPC_COLORS = [(240, 160, 80), (100, 180, 240), (200, 240, 100),
              (240, 120, 160), (160, 100, 240)]

# ── Footpath y-range for near side ──────────────────────────────────────
NEAR_FP_TOP = NEAR_LANE_Y + LANE_HEIGHT  # 540
NEAR_FP_BOT = COMPOUND_Y - 4  # ~586

# Stun duration in frames (60 frames = 1 second at 60 fps)
STUN_DURATION = 60


# ════════════════════════════════════════════════════════════════════════
class Pothole:
    """A static pothole on the near footpath."""

    def __init__(self, x: int, y: int, rx: int = 18, ry: int = 11):
        self.x, self.y = x, y
        self.rx, self.ry = rx, ry
        self.rect = pygame.Rect(x - rx, y - ry, rx * 2, ry * 2)
        # Precompute crack offsets (deterministic per position)
        rng = random.Random(x * 37 + y)
        self._cracks = [
            (rng.randint(-rx + 2, rx - 2), rng.randint(-ry + 2, ry - 2),
             rng.randint(-rx, rx), rng.randint(-ry, ry))
            for _ in range(4)
        ]

    def draw(self, surface: pygame.Surface) -> None:
        pygame.draw.ellipse(surface, POTHOLE_DARK,
                            (self.x - self.rx, self.y - self.ry,
                             self.rx * 2, self.ry * 2))
        pygame.draw.ellipse(surface, POTHOLE_RIM,
                            (self.x - self.rx, self.y - self.ry,
                             self.rx * 2, self.ry * 2), 2)
        for x0, y0, x1, y1 in self._cracks:
            pygame.draw.line(surface, CRACK_COL,
                             (self.x + x0, self.y + y0),
                             (self.x + x1, self.y + y1), 1)

    def check_collision(self, player_rect: pygame.Rect) -> bool:
        return self.rect.colliderect(player_rect)


# ════════════════════════════════════════════════════════════════════════
class StreetVendor:
    """A static cart/stall — solid navigation obstacle on the footpath."""

    def __init__(self, x: int, y: int):
        self.rect = pygame.Rect(x, y, 38, 24)
        # Deterministic colours per position
        rng = random.Random(x * 13)
        self._awning = (rng.randint(150, 220),
                        rng.randint(40, 80),
                        rng.randint(20, 60))
        self._goods = (rng.randint(180, 240),
                       rng.randint(160, 210),
                       rng.randint(40, 100))

    def draw(self, surface: pygame.Surface) -> None:
        r = self.rect
        # Cart body
        pygame.draw.rect(surface, VENDOR_BODY, r, border_radius=3)
        # Awning stripe
        awn_r = pygame.Rect(r.x, r.y, r.width, 8)
        pygame.draw.rect(surface, self._awning, awn_r, border_radius=3)
        # Goods dots
        for gx in range(r.x + 5, r.right - 4, 8):
            pygame.draw.circle(surface, self._goods, (gx, r.centery + 4), 3)
        # Wheel hints
        for wx in [r.x + 5, r.right - 5]:
            pygame.draw.circle(surface, (50, 40, 30), (wx, r.bottom + 2), 3)
        pygame.draw.rect(surface, (100, 80, 50), r, 1, border_radius=3)

    def check_collision(self, player_rect: pygame.Rect) -> bool:
        return self.rect.colliderect(player_rect)


# ════════════════════════════════════════════════════════════════════════
class NPCPedestrian:
    """
    AI pedestrian that attempts road crossings on a log-normal gap schedule.
    Serves as a visual warning system for the human player.
    """
    # Log-normal parameters from literature (Petzoldt 2014 baseline)
    LN_MU = 1.2
    LN_SIGMA = 0.50
    FPS = 60

    def __init__(self, x: int, color_idx: int = 0):
        self._color = NPC_COLORS[color_idx % len(NPC_COLORS)]
        self._w = 20
        self._h = 20
        spawn_y = NEAR_FP_BOT - self._h
        self.rect = pygame.Rect(x, spawn_y, self._w, self._h)
        self._true_y = float(self.rect.y)
        self._speed = 1.8 + random.uniform(-0.3, 0.4)  # px/frame
        self._crossing = False
        self._wait_frames = self._sample_wait()
        self._flash_timer = 0  # red flash on vehicle collision
        self._stun_timer = 0  # brief pause mid-crossing after NPC gets hit

    # ── Log-normal gap wait ──────────────────────────────────────────────
    def _sample_wait(self) -> int:
        """Convert a log-normal gap (seconds) to frames of waiting."""
        gap_s = random.lognormvariate(self.LN_MU, self.LN_SIGMA)
        gap_s = max(1.0, min(gap_s, 12.0))
        return int(gap_s * self.FPS)

    # ── Update ───────────────────────────────────────────────────────────
    def update(self, vehicles: list) -> None:
        if self._stun_timer > 0:
            self._stun_timer -= 1
            return

        if self._flash_timer > 0:
            self._flash_timer -= 1

        if not self._crossing:
            self._wait_frames -= 1
            if self._wait_frames <= 0:
                self._crossing = True
        else:
            self._true_y -= self._speed
            self.rect.y = int(self._true_y)

            # Check if a vehicle is nearby — NPC may hesitate
            if self._is_threatened(vehicles):
                self._flash_timer = 25
                self._stun_timer = 40  # pause ~0.7s
                return

            # Reached safe zone — reset
            if self.rect.y < FOOTPATH_HEIGHT:
                self._reset()

    def _is_threatened(self, vehicles: list) -> bool:
        """True if a vehicle overlaps or is very close horizontally."""
        margin = 50
        for v in vehicles:
            expanded = v.rect.inflate(margin * 2, 10)
            if expanded.colliderect(self.rect):
                return True
        return False

    def _reset(self) -> None:
        self._true_y = float(NEAR_FP_BOT - self._h)
        self.rect.y = int(self._true_y)
        self._crossing = False
        self._wait_frames = self._sample_wait()

    # ── Vehicle collision (called from ObstacleManager) ──────────────────
    def notify_vehicle_hit(self) -> None:
        """Flash red and stun briefly — visible warning for the player."""
        self._flash_timer = 40
        self._stun_timer = 80
        self._reset()

    # ── Draw ─────────────────────────────────────────────────────────────
    def draw(self, surface: pygame.Surface) -> None:
        col = (240, 60, 60) if self._flash_timer > 0 else self._color
        pygame.draw.rect(surface, col, self.rect, border_radius=4)
        # Direction arrow (if crossing)
        if self._crossing:
            cx, cy = self.rect.centerx, self.rect.centery
            pts = [(cx, cy - 8), (cx - 5, cy + 4), (cx + 5, cy + 4)]
            arrow_col = tuple(max(0, c - 70) for c in col)
            pygame.draw.polygon(surface, arrow_col, pts)


# ════════════════════════════════════════════════════════════════════════
class ObstacleManager:
    """
    Single entry point for main.py.
    Generates obstacles at round start and exposes update/draw/check APIs.
    """

    def __init__(self):
        self.potholes: list[Pothole] = []
        self.vendors: list[StreetVendor] = []
        self.npcs: list[NPCPedestrian] = []
        self._stun_timer = 0  # counts DOWN to 0 — player is stunned while > 0
        self._stun_source_idx = -1  # index of the pothole that caused the stun;
        # ignored for re-collision until player exits it

    # ── Accessors ─────────────────────────────────────────────────────────
    @property
    def player_is_stunned(self) -> bool:
        return self._stun_timer > 0

    @property
    def stun_timer(self) -> int:
        return self._stun_timer

    # ── Round initialisation ──────────────────────────────────────────────
    def reset_for_round(self, round_num: int, seed: int = None) -> None:
        """
        Rebuild obstacles for the new round.
        More obstacles appear as rounds increase.
        """
        rng = random.Random(seed or round_num * 71)
        self._stun_timer = 0
        self._stun_source_idx = -1

        # ── Potholes — placed inside the three road lanes ─────────────────
        LANE_MARGIN = 20
        lane_y_ranges = [
            (FAR_LANE_Y + LANE_MARGIN, FAR_LANE_Y + LANE_HEIGHT - LANE_MARGIN),
            (MIDDLE_LANE_Y + LANE_MARGIN, MIDDLE_LANE_Y + LANE_HEIGHT - LANE_MARGIN),
            (NEAR_LANE_Y + LANE_MARGIN, NEAR_LANE_Y + LANE_HEIGHT - LANE_MARGIN),
        ]
        n_potholes = min(2 + round_num, 7)
        self.potholes = []
        used_xs = []
        for i in range(n_potholes):
            lane_top, lane_bot = lane_y_ranges[i % len(lane_y_ranges)]
            for _ in range(30):
                px = rng.randint(60, SCREEN_WIDTH - 60)
                if all(abs(px - ux) > 90 for ux in used_xs):
                    used_xs.append(px)
                    break
            py = rng.randint(lane_top, lane_bot)
            rx = rng.randint(14, 22)
            ry = rng.randint(8, 13)
            self.potholes.append(Pothole(px, py, rx, ry))

        # ── Street vendors (1–3 per side) ────────────────────────────────
        n_vendors = min(1 + round_num // 2, 4)
        self.vendors = []
        for i in range(n_vendors):
            side_x = (rng.randint(10, 80) if i % 2 == 0
                      else rng.randint(SCREEN_WIDTH - 90, SCREEN_WIDTH - 20))
            vy = rng.randint(NEAR_FP_TOP + 4, NEAR_FP_BOT - 28)
            self.vendors.append(StreetVendor(side_x, vy))

        # ── NPC pedestrians (1–3) ─────────────────────────────────────────
        n_npcs = min(1 + round_num // 3, 3)
        self.npcs = []
        for i in range(n_npcs):
            nx = rng.randint(100, SCREEN_WIDTH - 100)
            self.npcs.append(NPCPedestrian(nx, color_idx=i))

    # ── Per-frame update ──────────────────────────────────────────────────
    def update(self, player_rect: pygame.Rect, vehicles: list) -> None:
        """Call every frame while GAME_STATE == "RUNNING"."""

        # Handle the stun countdown
        if self._stun_timer > 0:
            self._stun_timer -= 1

        # Check if we are still standing on the pothole that stunned us
        if self._stun_source_idx != -1:
            source_pothole = self.potholes[self._stun_source_idx]
            # If we are no longer colliding with the source, clear it
            if not source_pothole.check_collision(player_rect):
                self._stun_source_idx = -1

        # NPC updates
        for npc in self.npcs:
            npc.update(vehicles)
            for v in vehicles:
                if npc.rect.colliderect(v.rect):
                    npc.notify_vehicle_hit()
                    break

        # Pothole–player collision
        # Only look for NEW collisions if the timer is 0
        if self._stun_timer == 0:
            for idx, ph in enumerate(self.potholes):
                # If we are still standing on the old source, don't re-stun
                if idx == self._stun_source_idx:
                    continue
                if ph.check_collision(player_rect):
                    self._stun_timer = STUN_DURATION
                    self._stun_source_idx = idx
                    break

    # ── Draw ──────────────────────────────────────────────────────────────
    def draw(self, surface: pygame.Surface) -> None:
        for ph in self.potholes:
            ph.draw(surface)
        for vd in self.vendors:
            vd.draw(surface)
        for npc in self.npcs:
            npc.draw(surface)

    # ── Vendor solid-block collision (push-back helper) ──────────────────
    def resolve_vendor_collision(self, player) -> None:
        """
        Called from main.py after player.move().
        Pushes the player out of any vendor stall bounding box.
        """
        for vd in self.vendors:
            if player.rect.colliderect(vd.rect):
                # Simple axis-aligned push-back
                overlap_x = min(player.rect.right - vd.rect.left,
                                vd.rect.right - player.rect.left)
                overlap_y = min(player.rect.bottom - vd.rect.top,
                                vd.rect.bottom - player.rect.top)
                if overlap_x < overlap_y:
                    if player.rect.centerx < vd.rect.centerx:
                        player.rect.x -= overlap_x
                    else:
                        player.rect.x += overlap_x
                    player.vel_x = 0
                    player.true_x = float(player.rect.x)
                else:
                    if player.rect.centery < vd.rect.centery:
                        player.rect.y -= overlap_y
                    else:
                        player.rect.y += overlap_y
                    player.vel_y = 0
                    player.true_y = float(player.rect.y)