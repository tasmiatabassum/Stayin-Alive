# environment.py
"""
Environmental Stochasticity — Weather & Pollution
===================================================
Manages two coupled environmental variables that evolve over time:

1. **Smog / Visibility**
   - Modelled as a Gaussian random walk clamped to [0, 1].
   - A semi-transparent grey overlay is drawn over the game world;
     opacity scales with smog level so distant vehicles fade out.
   - Vehicles beyond a computed "visibility distance" have their alpha
     reduced, creating a genuine depth-of-field / fog hazard.

2. **Rain**
   - Triggered stochastically when smog > RAIN_THRESHOLD (wet air).
   - Active rain applies a friction multiplier < 1 to the player
     (returned via `player_friction_mult`) and increases NaSch p_slow
     for vehicles (returned via `vehicle_p_slow_mult`).
   - Animated rain streaks rendered as short diagonal lines.

Both variables are exposed to `main.py` and `spawner.py` via simple
read-only properties so the rest of the codebase needs minimal changes.
"""

import random
import math
import pygame

# ── Tuning constants ────────────────────────────────────────────────────
SMOG_DRIFT_STD   = 0.006   # σ of per-frame Gaussian walk
SMOG_MEAN_PULL   = 0.003   # gentle mean-reversion toward 0.35 (Dhaka baseline)
SMOG_MEAN_TARGET = 0.35
SMOG_MIN, SMOG_MAX = 0.0, 1.0

RAIN_THRESHOLD   = 0.55    # smog level above which rain can start
RAIN_START_PROB  = 0.0008  # per-frame Bernoulli probability of rain onset
RAIN_STOP_PROB   = 0.0015  # per-frame Bernoulli probability of rain stopping

RAIN_NUM_DROPS   = 120
RAIN_SPEED_MIN   = 4
RAIN_SPEED_MAX   = 9
RAIN_LEN_MIN     = 6
RAIN_LEN_MAX     = 14

# Visual
SMOG_COLOR       = (200, 195, 185)   # warm grey-brown Dhaka smog tint
RAIN_COLOR       = (160, 190, 220)
RAIN_ALPHA_BASE  = 130


class EnvironmentManager:
    def __init__(self, screen_w: int, screen_h: int, seed: int = None):
        self.screen_w = screen_w
        self.screen_h = screen_h
        if seed is not None:
            random.seed(seed)

        self._smog      = SMOG_MEAN_TARGET   # start at Dhaka baseline
        self._raining   = False
        self._drops     = []                  # list of drop dicts
        self._frame     = 0

        # Pre-allocate transparent surfaces (reused every frame)
        self._smog_surf = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
        self._rain_surf = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)

        # Round-scaling: externally set by main.py
        self.current_round = 1

    # ── Public setters ───────────────────────────────────────────────────
    def set_round(self, r: int) -> None:
        """Call when a new round begins to nudge smog upward."""
        if r > self.current_round:
            # Only add the 0.04 bump if the round has actually increased!
            self._smog = min(SMOG_MAX, self._smog + 0.04)
            self.current_round = r
    # ── Public read-only properties ──────────────────────────────────────
    @property
    def smog(self) -> float:
        """Current smog level in [0, 1]."""
        return self._smog

    @property
    def raining(self) -> bool:
        return self._raining

    @property
    def player_friction_mult(self) -> float:
        """
        Multiplier applied to the player's friction coefficient when wet.
        Values < 1 make the player more slippery.
        Rain at full intensity reduces friction by ~30 %.
        """
        if not self._raining:
            return 1.0
        # Gradual onset: fraction of how long rain has been active
        return max(0.65, 1.0 - 0.35 * min(1.0, self._rain_intensity))

    @property
    def vehicle_p_slow_mult(self) -> float:
        """
        NaSch p_slow multiplier: rain makes drivers more erratic.
        Passed to spawner → Vehicle instances.
        """
        if not self._raining:
            return 1.0
        return 1.0 + 0.60 * min(1.0, self._rain_intensity)

    @property
    def visibility_alpha(self) -> int:
        """Alpha of the smog overlay (0=clear, 200=dense)."""
        return int(self._smog * 200)

    # ── Per-frame update ─────────────────────────────────────────────────
    def update(self) -> None:
        self._frame += 1
        self._update_smog()
        self._update_rain()

    def _update_smog(self) -> None:
        # Mean-reverting Gaussian random walk
        pull  = SMOG_MEAN_PULL * (SMOG_MEAN_TARGET - self._smog)
        drift = random.gauss(0, SMOG_DRIFT_STD)
        # Round bonus: higher rounds → higher smog equilibrium
        round_push = (self.current_round - 1) * 0.0003
        self._smog += pull + drift + round_push
        self._smog  = max(SMOG_MIN, min(SMOG_MAX, self._smog))

    def _update_rain(self) -> None:
        if not self._raining:
            # Rain can only start if smog exceeds threshold
            if (self._smog >= RAIN_THRESHOLD
                    and random.random() < RAIN_START_PROB):
                self._raining       = True
                self._rain_onset    = self._frame
                self._rain_intensity = 0.0
                self._drops = [self._new_drop() for _ in range(RAIN_NUM_DROPS)]
        else:
            # Ramp up intensity over ~120 frames
            self._rain_intensity = min(1.0,
                (self._frame - self._rain_onset) / 120.0)
            # Update drops
            for d in self._drops:
                d["y"] += d["speed"]
                d["x"] += d["speed"] * 0.3   # slight diagonal
                if d["y"] > self.screen_h + 20:
                    d.update(self._new_drop())
            # Chance to stop
            if random.random() < RAIN_STOP_PROB:
                self._raining = False
                self._drops   = []

    def _new_drop(self) -> dict:
        return {
            "x":      random.randint(0, self.screen_w),
            "y":      random.randint(-self.screen_h, 0),
            "speed":  random.randint(RAIN_SPEED_MIN, RAIN_SPEED_MAX),
            "length": random.randint(RAIN_LEN_MIN, RAIN_LEN_MAX),
        }

    # ── Draw ─────────────────────────────────────────────────────────────
    def draw(self, surface: pygame.Surface) -> None:
        """
        Draw environmental overlays on top of the game world.
        Call this AFTER road/vehicles/player have been drawn.
        """
        self._draw_smog(surface)
        if self._raining:
            self._draw_rain(surface)
        self._draw_hud_indicators(surface)

    def _draw_smog(self, surface: pygame.Surface) -> None:
        alpha = self.visibility_alpha
        if alpha < 5:
            return
        self._smog_surf.fill((0, 0, 0, 0))
        # Gradient: denser at the top (far vehicles harder to see)
        steps = 8
        for i in range(steps):
            band_h = self.screen_h // steps
            band_y = i * band_h
            # Alpha ramps from 0 at bottom (near player) to full at top
            band_alpha = int(alpha * (steps - i) / steps)
            r, g, b = SMOG_COLOR
            pygame.draw.rect(self._smog_surf, (r, g, b, band_alpha),
                             (0, band_y, self.screen_w, band_h + 1))
        surface.blit(self._smog_surf, (0, 0))

    def _draw_rain(self, surface: pygame.Surface) -> None:
        self._rain_surf.fill((0, 0, 0, 0))
        alpha = int(RAIN_ALPHA_BASE * min(1.0, self._rain_intensity))
        r, g, b = RAIN_COLOR
        for d in self._drops:
            x0, y0 = int(d["x"]), int(d["y"])
            length  = d["length"]
            dx      = int(length * 0.3)
            pygame.draw.line(self._rain_surf, (r, g, b, alpha),
                             (x0, y0), (x0 + dx, y0 + length), 1)
        surface.blit(self._rain_surf, (0, 0))

    def _draw_hud_indicators(self, surface: pygame.Surface) -> None:
        """Small status icons in the bottom-right corner."""
        font = pygame.font.SysFont("Courier New", 13, bold=True)
        x, y = self.screen_w - 160, self.screen_h - 52

        # Smog bar
        bar_w = 100
        smog_fill = int(bar_w * self._smog)
        smog_col = self._smog_bar_color()
        pygame.draw.rect(surface, (40, 40, 40), (x, y, bar_w, 10))
        if smog_fill > 0:
            pygame.draw.rect(surface, smog_col, (x, y, smog_fill, 10))
        pygame.draw.rect(surface, (80, 80, 80), (x, y, bar_w, 10), 1)
        lbl = font.render("SMOG", True, (160, 155, 145))
        surface.blit(lbl, (x - 42, y - 1))

        # Rain indicator
        if self._raining:
            rain_lbl = font.render("RAIN", True, RAIN_COLOR)
            surface.blit(rain_lbl, (x + bar_w + 6, y - 1))
            # Animate blinking ~
            if (pygame.time.get_ticks() // 400) % 2 == 0:
                pygame.draw.circle(surface, RAIN_COLOR,
                                   (x + bar_w + 42, y + 5), 3)

    def _smog_bar_color(self) -> tuple:
        """Green → yellow → red as smog increases."""
        s = self._smog
        if s < 0.4:
            return (60, 180, 60)
        elif s < 0.65:
            return (200, 180, 30)
        else:
            return (210, 60, 40)

    # ── Convenience: weather status string for POST_SESSION screen ───────
    def get_summary_line(self) -> str:
        avg_smog = round(self._smog, 2)
        rain_str = "YES" if self._raining else "NO"
        return f"Smog level: {avg_smog:.2f}   Rain active: {rain_str}"