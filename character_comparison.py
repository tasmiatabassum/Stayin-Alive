# character_comparison.py
"""
Character Win-Likelihood Comparison Panel
==========================================
Drop this module into your project and call it from your main game loop.

Usage
-----
    from character_comparison import CharacterComparison

    # Create once (pass the font you already use, or None to auto-create)
    comp = CharacterComparison()

    # After every attempt, record the result for each character:
    comp.record(name="BADRUL", success=True,  score=211, rounds=3)
    comp.record(name="RAHIM",  success=False, score=42,  rounds=1)

    # In your draw loop:
    comp.draw(screen)           # draws at default top-right corner
    comp.draw(screen, x=10, y=300)   # or any (x, y)
"""

import pygame
import math


# ── Palette (matches existing terminal HUD) ──────────────────────────────
_BG        = (10,  18,  10)       # near-black green tint
_BORDER    = (30,  80,  30)
_LABEL     = (60, 148,  58)       # muted green — headings
_DIM       = (40,  90,  40)       # very muted
_WHITE     = (210, 218, 200)
_GOLD      = (205, 162,  18)      # highlight / 1st place
_RED       = (210,  55,  40)
_CYAN      = ( 80, 210, 180)      # bar fill — winner
_BAR_BG    = ( 22,  40,  22)
_PANEL_W   = 230
_ROW_H     = 38
_HEADER_H  = 22
_FOOTER_H  = 18
_PAD       = 8


def _bayesian_rate(successes: int, attempts: int) -> float:
    """Laplace-smoothed success probability  (successes+1)/(attempts+2)."""
    return (successes + 1) / (attempts + 2)


def _win_likelihood(stats: dict) -> float:
    """
    Composite win-likelihood score in [0, 1].

    Weights
    -------
    60% Bayesian survival rate   — most important; immune to tiny sample bias
    25% Normalised average score — rewards high-scoring runs
    15% Normalised round depth   — rewards surviving more rounds on average
    """
    br    = _bayesian_rate(stats["successes"], stats["attempts"])
    # Clamp normalisation anchors; adjust MAX_SCORE / MAX_ROUND if needed
    MAX_SCORE = 500.0
    MAX_ROUND = 10.0
    avg_score = stats["total_score"] / max(stats["attempts"], 1)
    avg_round = stats["total_rounds"] / max(stats["attempts"], 1)
    ns = min(avg_score / MAX_SCORE, 1.0)
    nr = min(avg_round / MAX_ROUND, 1.0)
    return 0.60 * br + 0.25 * ns + 0.15 * nr


class CharacterComparison:
    """
    Renders a compact in-game panel ranking characters by win likelihood.

    Parameters
    ----------
    max_shown   : Maximum number of characters to display (default 5)
    alpha       : Panel background transparency 0-255 (default 210)
    """

    def __init__(self, max_shown: int = 5, alpha: int = 210):
        self._characters: dict[str, dict] = {}   # name → stats dict
        self._max_shown  = max_shown
        self._alpha      = alpha
        self._font_sm    = None
        self._font_md    = None
        self._font_xs    = None
        self._surf_cache = None   # cached panel surface (rebuilt on change)
        self._dirty      = True

    # ── Public API ────────────────────────────────────────────────────────

    def record(self, name: str, success: bool, score: int = 0, rounds: int = 1):
        """
        Log one completed attempt for a character.

        Call this at the end of every round / life.

        Parameters
        ----------
        name    : Character identifier (e.g. "BADRUL")
        success : True if the player reached the far footpath safely
        score   : Points earned this attempt
        rounds  : Number of rounds completed this attempt
        """
        if name not in self._characters:
            self._characters[name] = {
                "attempts":     0,
                "successes":    0,
                "total_score":  0,
                "total_rounds": 0,
                "best_score":   0,
            }
        s = self._characters[name]
        s["attempts"]     += 1
        s["successes"]    += int(success)
        s["total_score"]  += score
        s["total_rounds"] += rounds
        s["best_score"]    = max(s["best_score"], score)
        self._dirty = True

    def get_likelihood(self, name: str) -> float:
        """Return win likelihood for a character (0.0–1.0); 0.5 if unknown."""
        if name not in self._characters:
            return 0.5
        return _win_likelihood(self._characters[name])

    def ranking(self) -> list[tuple[str, float]]:
        """Return [(name, likelihood), ...] sorted best-first."""
        rows = [(n, _win_likelihood(s)) for n, s in self._characters.items()]
        rows.sort(key=lambda r: r[1], reverse=True)
        return rows

    # ── Drawing ───────────────────────────────────────────────────────────

    def draw(self, screen: pygame.Surface, x: int = None, y: int = 10):
        """
        Draw the comparison panel onto *screen*.

        Default position: top-right corner (10px from edge).
        """
        self._ensure_fonts()

        ranked = self.ranking()[: self._max_shown]
        if not ranked:
            return

        # ── Rebuild cached surface if data changed ──
        if self._dirty or self._surf_cache is None:
            self._surf_cache = self._build_surface(ranked)
            self._dirty = False

        sw = self._surf_cache.get_width()
        if x is None:
            x = screen.get_width() - sw - 10
        screen.blit(self._surf_cache, (x, y))

    # ── Internal ──────────────────────────────────────────────────────────

    def _ensure_fonts(self):
        if self._font_md is not None:
            return
        self._font_md = pygame.font.SysFont("Courier", 12, bold=True)
        self._font_sm = pygame.font.SysFont("Courier", 10, bold=True)
        self._font_xs = pygame.font.SysFont("Courier",  9)

    def _build_surface(self, ranked: list[tuple[str, float]]) -> pygame.Surface:
        n_rows  = len(ranked)
        panel_h = _HEADER_H + n_rows * _ROW_H + _FOOTER_H + _PAD * 2

        surf = pygame.Surface((_PANEL_W, panel_h), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 0))

        # Background
        bg = pygame.Surface((_PANEL_W, panel_h), pygame.SRCALPHA)
        bg.fill((*_BG, self._alpha))
        surf.blit(bg, (0, 0))
        pygame.draw.rect(surf, _BORDER, (0, 0, _PANEL_W, panel_h), 1)

        # Header
        hdr = self._font_sm.render("WIN LIKELIHOOD", True, _LABEL)
        surf.blit(hdr, (_PAD, _PAD))
        pygame.draw.line(surf, _BORDER,
                         (_PAD, _HEADER_H + _PAD - 2),
                         (_PANEL_W - _PAD, _HEADER_H + _PAD - 2), 1)

        top_likelihood = ranked[0][1] if ranked else 1.0

        for i, (name, likelihood) in enumerate(ranked):
            row_y = _PAD + _HEADER_H + i * _ROW_H

            is_leader = (i == 0)
            name_col  = _GOLD if is_leader else _WHITE
            bar_col   = _CYAN if is_leader else _LABEL

            # Rank badge
            rank_txt = self._font_sm.render(f"#{i+1}", True, _DIM if not is_leader else _GOLD)
            surf.blit(rank_txt, (_PAD, row_y + 4))

            # Name
            display = name[:10]   # truncate long names
            nm = self._font_md.render(display, True, name_col)
            surf.blit(nm, (_PAD + 24, row_y + 2))

            # Percentage label
            pct_str = f"{likelihood * 100:.1f}%"
            pct     = self._font_sm.render(pct_str, True, name_col)
            surf.blit(pct, (_PANEL_W - pct.get_width() - _PAD, row_y + 2))

            # Bar
            bar_x  = _PAD + 24
            bar_y  = row_y + _ROW_H - 11
            bar_w  = _PANEL_W - bar_x - _PAD - pct.get_width() - 4
            bar_h  = 5
            pygame.draw.rect(surf, _BAR_BG, (bar_x, bar_y, bar_w, bar_h), border_radius=2)
            fill_w = max(2, int(bar_w * likelihood))
            pygame.draw.rect(surf, bar_col, (bar_x, bar_y, fill_w, bar_h), border_radius=2)

            # Attempts annotation
            s = self._characters.get(name, {})
            ann = f"{s.get('successes', 0)}W/{s.get('attempts', 0)}A"
            at  = self._font_xs.render(ann, True, _DIM)
            surf.blit(at, (_PAD + 24, bar_y - 1))

            # Row separator
            if i < n_rows - 1:
                sep_y = row_y + _ROW_H - 1
                pygame.draw.line(surf, _BORDER, (_PAD, sep_y), (_PANEL_W - _PAD, sep_y), 1)

        # Footer
        footer_y = _PAD + _HEADER_H + n_rows * _ROW_H + 2
        pygame.draw.line(surf, _BORDER, (_PAD, footer_y), (_PANEL_W - _PAD, footer_y), 1)
        foot = self._font_xs.render("BAYES·SCORE·ROUNDS", True, _DIM)
        surf.blit(foot, (_PANEL_W // 2 - foot.get_width() // 2, footer_y + 4))

        return surf


# ── Convenience: live single-character badge ──────────────────────────────

class LiveLikelihoodBadge:
    """
    Tiny inline badge showing the current player's live win likelihood.
    Designed to sit inside your existing HUD (e.g. below the SURVIVAL line).

    Usage
    -----
        badge = LiveLikelihoodBadge()
        # feed it the same CharacterComparison object:
        badge.draw(screen, comp, current_name="BADRUL", x=10, y=190)
    """

    def __init__(self):
        self._font = None

    def draw(self, screen: pygame.Surface, comp: CharacterComparison,
             current_name: str, x: int = 10, y: int = 190):
        if self._font is None:
            self._font = pygame.font.SysFont("Courier", 11, bold=True)

        likelihood = comp.get_likelihood(current_name)
        ranked     = comp.ranking()
        rank       = next((i + 1 for i, (n, _) in enumerate(ranked) if n == current_name), "?")

        pct  = f"{likelihood * 100:.1f}%"
        col  = _GOLD if rank == 1 else (_CYAN if likelihood > 0.5 else _RED)
        line = f"WIN PROB : {pct}  (#{rank})"
        txt  = self._font.render(line, True, col)
        screen.blit(txt, (x, y))