# main.py
import pygame
import sys
import random
import math
from config import *
from road import Road
from pedestrian import Pedestrian
from spawner import Spawner
from characters import CHARACTERS
from round_manager import RoundManager
from logger import GapAcceptanceLogger
from environment import EnvironmentManager
from obstacles import ObstacleManager
from character_comparison import CharacterComparison, LiveLikelihoodBadge

pygame.init()

# ── Display scaling system ────────────────────────────────────────────────
_LOGICAL_W = SCREEN_WIDTH   # 1000
_LOGICAL_H = SCREEN_HEIGHT  # 700

_WIN_PRESETS = [
    ("XS",  700,  490),
    ("SM",  800,  560),
    ("MD", 1000,  700),
    ("LG", 1200,  840),
    ("XL", 1400,  980),
]
_preset_idx    = 2
_is_fullscreen = False

_info = pygame.display.Info()
_DESK_W, _DESK_H = _info.current_w, _info.current_h


def _apply_window():
    global screen
    if _is_fullscreen:
        screen = pygame.display.set_mode((_DESK_W, _DESK_H), pygame.FULLSCREEN)
    else:
        _, ww, wh = _WIN_PRESETS[_preset_idx]
        screen = pygame.display.set_mode((ww, wh), pygame.RESIZABLE)


_apply_window()
pygame.display.set_caption("Stayin' Alive (in boardbazar)")
clock = pygame.time.Clock()


def _remap_mouse(raw_pos):
    sw, sh = screen.get_size()
    return (int(raw_pos[0] * _LOGICAL_W / sw),
            int(raw_pos[1] * _LOGICAL_H / sh))


def toggle_fullscreen():
    global _is_fullscreen
    _is_fullscreen = not _is_fullscreen
    _apply_window()


def cycle_window_size(direction=1):
    global _preset_idx, _is_fullscreen
    _is_fullscreen = False
    _preset_idx = max(0, min(len(_WIN_PRESETS) - 1, _preset_idx + direction))
    _apply_window()


def handle_resize(new_w, new_h):
    global screen
    if not _is_fullscreen:
        screen = pygame.display.set_mode((new_w, new_h), pygame.RESIZABLE)


# --- Fonts ---
font_lore     = pygame.font.SysFont("Gothic", 25)
font_title    = pygame.font.SysFont("Courier New", 40, bold=True)
font_stats    = pygame.font.SysFont("Courier New", 24)
font_telemetry= pygame.font.SysFont("Courier New", 16, bold=True)
font_hud      = pygame.font.SysFont("Courier New", 18, bold=True)
font_popup    = pygame.font.SysFont("Arial", 32, bold=True)
font_shake    = pygame.font.SysFont("Arial", 52, bold=True)
font_game_over= pygame.font.SysFont("Impact", 90)
font_sub      = pygame.font.SysFont("Arial", 18, bold=True)
font_stat_go  = pygame.font.SysFont("Arial", 22)
font_btn      = pygame.font.SysFont("Arial", 20, bold=True)

# --- Colors ---
C_ORANGE   = (230,  60,  20)
C_LIME     = (185, 233,   1)
C_WHITE    = (255, 255, 255)
C_OFFWHITE = (220, 220, 220)
C_GOLD     = (255, 215,   0)
C_DIM      = (120, 120, 120)
C_BLACK    = (  0,   0,   0)

# --- Assets ---
try:
    start_bg = pygame.image.load("2.png")
    start_bg = pygame.transform.scale(start_bg, (SCREEN_WIDTH, SCREEN_HEIGHT))
except FileNotFoundError:
    print("FATAL ERROR: start.jpg missing.")
    sys.exit()

try:
    selection_bg = pygame.image.load("selection.jpg")
    selection_bg = pygame.transform.scale(selection_bg, (SCREEN_WIDTH, SCREEN_HEIGHT))
except FileNotFoundError:
    print("FATAL ERROR: selection.jpg missing.")
    sys.exit()

# --- Hitboxes ---
start_button_rect  = pygame.Rect((SCREEN_WIDTH//2)-100, (SCREEN_HEIGHT//2), 200, 80)
btn_w, btn_h       = 200, 70
btn_y              = (SCREEN_HEIGHT // 2) + 130
badrul_btn_rect    = pygame.Rect((SCREEN_WIDTH // 2) - btn_w - 20, btn_y, btn_w, btn_h)
mrittika_btn_rect  = pygame.Rect((SCREEN_WIDTH // 2) + 20,          btn_y, btn_w, btn_h)
quit_btn_rect      = pygame.Rect(SCREEN_WIDTH - 120, 20, 100, 40)


GO_W, GO_H = 220, 58
go_retry_rect = pygame.Rect((SCREEN_WIDTH // 2) - GO_W - 20, SCREEN_HEIGHT - 80, GO_W, GO_H)
go_select_rect = pygame.Rect((SCREEN_WIDTH // 2) + 20, SCREEN_HEIGHT - 80, GO_W, GO_H)

PB_W, PB_H         = 260, 52
pause_resume_rect  = pygame.Rect((SCREEN_WIDTH//2)-PB_W//2, 250, PB_W, PB_H)
pause_session_rect = pygame.Rect((SCREEN_WIDTH//2)-PB_W//2, 315, PB_W, PB_H)
pause_home_rect    = pygame.Rect((SCREEN_WIDTH//2)-PB_W//2, 380, PB_W, PB_H)
pause_quit_rect    = pygame.Rect((SCREEN_WIDTH//2)-PB_W//2, 445, PB_W, PB_H)

_SZ_BTN            = 34
pause_sz_label_rect= pygame.Rect((SCREEN_WIDTH//2)-60,             516, 120,    _SZ_BTN)
pause_sz_down_rect = pygame.Rect((SCREEN_WIDTH//2)-60-_SZ_BTN-6,  516, _SZ_BTN,_SZ_BTN)
pause_sz_up_rect   = pygame.Rect((SCREEN_WIDTH//2)+60+6,           516, _SZ_BTN,_SZ_BTN)
pause_fs_rect      = pygame.Rect((SCREEN_WIDTH//2)-PB_W//2,        560, PB_W,   _SZ_BTN)

# --- Game world ---
round_manager    = None
road             = Road()
spawner          = None
player           = None
gap_logger       = None
env_manager      = None
obstacle_manager = ObstacleManager()
session_frames   = 0
total_dashes_used= 0
lives            = 3
max_lives        = 3
invincible_timer = 0
INVINCIBLE_DUR   = 90
new_hs_timer     = 0

# ── Character comparison (persists across all sessions) ──────────────────
comp       = CharacterComparison()
live_badge = LiveLikelihoodBadge()

# ── Popups ───────────────────────────────────────────────────────────────
popups = []


def spawn_popup(text, x, y, color):
    popups.append({"text": text, "x": float(x), "y": float(y),
                   "alpha": 255, "color": color, "timer": 80})


def update_and_draw_popups(surface):
    for p in popups[:]:
        p["timer"] -= 1
        p["y"]     -= 0.9
        p["alpha"]  = int(255 * (p["timer"] / 80))
        s = font_popup.render(p["text"], True, p["color"])
        s.set_alpha(p["alpha"])
        surface.blit(s, (int(p["x"] - s.get_width()//2), int(p["y"])))
        if p["timer"] <= 0:
            popups.remove(p)


# ── Shake ─────────────────────────────────────────────────────────────────
shake_timer = 0


def trigger_shake():
    global shake_timer
    shake_timer = 45


def get_shake_offset():
    if shake_timer <= 0: return 0, 0
    i = int(8 * (shake_timer / 45))
    return random.randint(-i, i), random.randint(-i, i)


def draw_shake_message(surface):
    if shake_timer <= 0: return
    alpha = int(200 * (shake_timer / 45))
    ov = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    ov.fill((200, 0, 0, min(alpha, 75)))
    surface.blit(ov, (0, 0))
    if shake_timer % 6 < 4:
        msg = font_shake.render("pls STAY ALIVE", True, (255, 55, 55))
        msg.set_alpha(alpha)
        surface.blit(msg, (SCREEN_WIDTH//2 - msg.get_width()//2,
                           SCREEN_HEIGHT//2 - msg.get_height()//2))


def draw_stun_overlay(surface, stun_timer: int, max_stun: int = 65):
    if stun_timer <= 0: return
    alpha = int(180 * (stun_timer / max_stun))
    ov = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    ov.fill((180, 140, 0, min(alpha, 60)))
    surface.blit(ov, (0, 0))
    if stun_timer % 8 < 5:
        msg = font_shake.render("STUNNED! (POTHOLE)", True, (255, 200, 0))
        msg.set_alpha(alpha)
        surface.blit(msg, (SCREEN_WIDTH//2 - msg.get_width()//2,
                           SCREEN_HEIGHT//2 - msg.get_height()//2))


# ── HUD ───────────────────────────────────────────────────────────────────
def _lerp_col(c1, c2, t):
    return tuple(int(c1[i] + (c2[i]-c1[i])*t) for i in range(3))


def draw_hud(surface):
    hw, hx, hy = 340, 10, 10
    # 148px for 5 stat lines + win-prob line (22px) + 34px NHPP strip
    hh = 148 + 22 + 34
    bg = pygame.Surface((hw, hh), pygame.SRCALPHA)
    bg.fill((8, 12, 10, 215))
    surface.blit(bg, (hx, hy))
    pygame.draw.rect(surface, (0, 210, 100), (hx, hy, hw, hh), 2, border_radius=4)

    ts      = session_frames // FPS
    m, s    = ts // 60, ts % 60
    tr      = round_manager.wins + round_manager.losses
    pct     = (round_manager.wins / tr * 100) if tr > 0 else 0.0
    sc      = C_GOLD if round_manager.new_highscore else (255, 255, 200)

    for i, (txt, col) in enumerate([
        (f"SUBJECT : {player.name.upper()}",                       (0, 220, 120)),
        (f"SCORE   : {round_manager.score}   BEST: {round_manager.high_score}", sc),
        (f"ROUND   : {round_manager.current_round}   T+ {m:02d}:{s:02d}", (180, 220, 180)),
        (f"SUCCESS : {round_manager.wins}   FAIL: {round_manager.losses}", (180, 220, 180)),
        (f"SURVIVAL: {pct:.1f}%", (0, 255, 120) if pct >= 50 else (255, 80, 80)),
    ]):
        surface.blit(font_hud.render(txt, True, col), (hx+10, hy+8+i*26))

    # ── Win-likelihood line ──────────────────────────────────────────────
    lk      = comp.get_likelihood(player.name)
    ranked  = comp.ranking()
    rank    = next((i+1 for i,(n,_) in enumerate(ranked) if n == player.name), "?")
    lk_pct  = f"{lk*100:.1f}%"
    lk_col  = (C_GOLD if rank == 1
               else ((0, 210, 180) if lk > 0.50 else (255, 80, 80)))
    lk_txt  = font_hud.render(f"WIN PROB: {lk_pct}  #{rank}", True, lk_col)
    surface.blit(lk_txt, (hx+10, hy+8+5*26))   # line 5 (0-indexed)

    # Lives
    for i in range(max_lives):
        cx = hx + hw - 14 - i * 22
        c  = (220, 50, 50) if i < lives else (50, 50, 50)
        pygame.draw.circle(surface, c, (cx, hy+12), 8)
        pygame.draw.circle(surface, (255,100,100) if i < lives else (80,80,80),
                           (cx, hy+12), 5)

    # ── NHPP λ(t) rush-hour strip ─────────────────────────────────────────
    strip_y = hy + 148 + 22 + 4   # pushed down by the extra win-prob line
    strip_x = hx + 8
    strip_w = hw - 16
    strip_h = 24
    bar_bg  = pygame.Surface((strip_w, strip_h), pygame.SRCALPHA)
    bar_bg.fill((5, 20, 12, 200))
    surface.blit(bar_bg, (strip_x, strip_y))
    pygame.draw.rect(surface, (0, 140, 70), (strip_x, strip_y, strip_w, strip_h), 1)

    n_pts = strip_w - 2

    def _mult(tau):
        m_ = 0.85 * math.exp(-((tau-0.20)**2) / (2*0.06**2))
        e_ = 1.00 * math.exp(-((tau-0.72)**2) / (2*0.05**2))
        return 0.40 + m_ + e_

    min_m, max_m = 0.38, 1.42
    prev_pt = None
    for px in range(n_pts):
        tau  = px / max(1, n_pts-1)
        mult = _mult(tau)
        norm = (mult-min_m) / (max_m-min_m)
        py   = strip_y + strip_h - 2 - int(norm*(strip_h-4))
        t_col= _lerp_col((30,200,80), (255,60,30), norm)
        if prev_pt:
            pygame.draw.line(surface, t_col, prev_pt, (strip_x+1+px, py), 1)
        prev_pt = (strip_x+1+px, py)

    tau_now  = min(1.0, round_manager.session_frame /
                   max(1, round_manager.session_duration))
    cur_x    = strip_x + 1 + int(tau_now*(n_pts-1))
    cur_mult = _mult(tau_now)
    cur_norm = (cur_mult-min_m) / (max_m-min_m)
    cur_y    = strip_y + strip_h - 2 - int(cur_norm*(strip_h-4))
    pygame.draw.circle(surface, (255,255,100), (cur_x, cur_y), 3)
    pygame.draw.line(surface, (255,255,100,120),
                     (cur_x, strip_y), (cur_x, strip_y+strip_h-1), 1)

    phase_lbl, intensity = round_manager.get_rush_phase()
    lbl_col  = _lerp_col((40,220,100), (255,60,30), intensity)
    lbl_surf = font_telemetry.render(f"λ(t)  {phase_lbl}  ×{cur_mult:.2f}", True, lbl_col)
    lbl_x    = min(strip_x+strip_w-lbl_surf.get_width()-2,
                   max(strip_x+2, cur_x-lbl_surf.get_width()//2))
    surface.blit(lbl_surf, (lbl_x, strip_y+strip_h//2-lbl_surf.get_height()//2))


def draw_new_hs_flash(surface):
    global new_hs_timer
    if new_hs_timer <= 0: return
    new_hs_timer -= 1
    s = font_popup.render("★ NEW HIGH SCORE! ★", True, C_GOLD)
    s.set_alpha(min(255, new_hs_timer*6))
    surface.blit(s, (SCREEN_WIDTH//2 - s.get_width()//2, 140))


# ── GAME OVER ─────────────────────────────────────────────────────────────
def _pill(surface, rect, bg, label):
    pygame.draw.rect(surface, bg, rect, border_radius=rect.height//2)
    t = font_btn.render(label, True, C_BLACK)
    surface.blit(t, (rect.centerx-t.get_width()//2, rect.centery-t.get_height()//2))


def draw_game_over(surface):
    surface.fill(C_BLACK)
    cx = SCREEN_WIDTH // 2

    go = font_game_over.render("GAME OVER", True, C_ORANGE)
    surface.blit(go, (cx-go.get_width()//2, 50))

    sub = font_sub.render(f"IN BOARDBAZAR  ·  {player.name.upper()}", True, C_WHITE)
    surface.blit(sub, (cx-sub.get_width()//2, 158))

    sy = 200
    if round_manager.new_highscore:
        hs = font_sub.render("★ NEW HIGH SCORE ★", True, C_GOLD)
        surface.blit(hs, (cx-hs.get_width()//2, sy))
        sy += 30; sc_col = C_GOLD
    else:
        best = font_sub.render(f"BEST  {round_manager.high_score}", True, C_DIM)
        surface.blit(best, (cx-best.get_width()//2, sy))
        sy += 26; sc_col = C_WHITE

    sc_big = font_game_over.render(str(round_manager.score), True, sc_col)
    sc_big = pygame.transform.scale(sc_big, (sc_big.get_width()*2//3, sc_big.get_height()*2//3))
    surface.blit(sc_big, (cx-sc_big.get_width()//2, sy))
    sy += sc_big.get_height() + 16

    pygame.draw.line(surface, (45,45,45), (cx-200,sy), (cx+200,sy), 1)
    sy += 16

    # Stats
    total = round_manager.wins + round_manager.losses
    pct = (round_manager.wins / total * 100) if total > 0 else 0
    ts = session_frames // FPS
    m, s = ts // 60, ts % 60

    for label, value in [
        ("Rounds Survived", str(round_manager.wins)),
        ("Times Hit", str(round_manager.losses)),
        ("Dashes Used", str(total_dashes_used)),
        ("Survival Rate", f"{pct:.1f}%"),
        ("Time Played", f"{m:02d}:{s:02d}"),
    ]:
        surface.blit(font_stat_go.render(label, True, C_DIM), (cx - 200, sy))
        surface.blit(font_stat_go.render(value, True, C_OFFWHITE), (cx + 80, sy))
        sy += 28  # <-- Reduced slightly from 32 to save space

    sy += 15  # Add a small buffer gap before your new section

    # --- YOUR CHARACTER COMPARISON SECTION ---
    comp_title = font_sub.render("CHARACTER COMPARISON", True, C_DIM)
    surface.blit(comp_title, (cx - comp_title.get_width() // 2, sy))
    sy += 25  # <-- CRITICAL: Push down after title!

    # Make sure to format your actual variables in here
    line1 = font_stat_go.render("#1 BADRUL       62.2% WIN LIKELIHOOD", True, C_GOLD)
    surface.blit(line1, (cx - line1.get_width() // 2, sy))
    sy += 25  # <-- CRITICAL: Push down after Badrul!

    line2 = font_stat_go.render("#2 MRITTIKA     37.8% WIN LIKELIHOOD", True, (150, 150, 150))
    surface.blit(line2, (cx - line2.get_width() // 2, sy))
    sy += 25  # <-- CRITICAL: Push down after Mrittika!

    # Pill buttons
    _pill(surface, go_retry_rect, C_LIME, "PLAY AGAIN")
    _pill(surface, go_select_rect, (200, 200, 200), "CHANGE CHARACTER")

# ── PAUSE MENU ────────────────────────────────────────────────────────────
def draw_pause(surface):
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0,0,0,175))
    surface.blit(overlay, (0,0))

    cx    = SCREEN_WIDTH // 2
    title = font_game_over.render("PAUSED", True, C_ORANGE)
    surface.blit(title, (cx-title.get_width()//2, 155))

    _pill(surface, pause_resume_rect,  C_LIME,          "RESUME")
    _pill(surface, pause_session_rect, (100,160,220),   "SESSION DATA")
    _pill(surface, pause_home_rect,    (200,200,200),   "HOME")
    _pill(surface, pause_quit_rect,    (180,40,40),     "QUIT GAME")

    font_sz = pygame.font.SysFont("Courier New", 14, bold=True)
    label   = (_WIN_PRESETS[_preset_idx][0] if not _is_fullscreen else "FS")
    _pill(surface, pause_sz_down_rect,  (60,60,60),  "<")
    _pill(surface, pause_sz_label_rect, (40,40,40),  label)
    _pill(surface, pause_sz_up_rect,    (60,60,60),  ">")
    fs_col = (C_GOLD if _is_fullscreen else (55,55,55))
    _pill(surface, pause_fs_rect, fs_col, "F11  FULLSCREEN (NO BARS)")
    hint = font_sz.render("WINDOW SIZE", True, (100,100,100))
    surface.blit(hint, (cx-hint.get_width()//2, 505))


# ── POST SESSION SCREEN ───────────────────────────────────────────────────
_ps_fonts = {}

def _ps_font(name, size, bold=False):
    key = (name, size, bold)
    if key not in _ps_fonts:
        _ps_fonts[key] = pygame.font.SysFont(name, size, bold=bold)
    return _ps_fonts[key]


def _ps_card(surface, x, y, w, h, fill=(14,20,14), border=(22,58,22)):
    pygame.draw.rect(surface, fill,   (x, y, w, h), border_radius=6)
    pygame.draw.rect(surface, border, (x, y, w, h), 1, border_radius=6)


def _ps_card_hdr(surface, x, y, w, label):
    f = _ps_font("Courier New", 10, bold=True)
    t = f.render(label, True, (45, 115, 45))
    surface.blit(t, (x + 10, y + 7))
    pygame.draw.line(surface, (20, 52, 20), (x+1, y+22), (x+w-1, y+22), 1)


def draw_post_session(surface):
    # ── Background ────────────────────────────────────────────────────────
    surface.fill((8, 13, 8))
    for gy in range(0, SCREEN_HEIGHT, 38):
        pygame.draw.line(surface, (12, 19, 12), (0, gy), (SCREEN_WIDTH, gy))
    for gx in range(0, SCREEN_WIDTH, 38):
        pygame.draw.line(surface, (12, 19, 12), (gx, 0), (gx, SCREEN_HEIGHT))

    CW   = 445      # card width
    LX   = 28       # left column x
    RX   = SCREEN_WIDTH - 28 - CW   # right column x
    BRIGHT = (0, 245, 120)
    HDRC   = (45, 115, 45)
    VALC   = (170, 235, 170)
    C_G    = (255, 210, 0)

    # ── Title ─────────────────────────────────────────────────────────────
    title = _ps_font("Courier New", 28, bold=True).render(
        "SIMULATION  DATA  LOG", True, BRIGHT)
    surface.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 18))
    pygame.draw.line(surface, (0, 90, 45),
                     (LX, 58), (SCREEN_WIDTH - LX, 58), 1)

    if not (player and round_manager):
        return

    ta   = round_manager.wins + round_manager.losses
    sr   = (round_manager.wins / ta * 100) if ta > 0 else 0.0
    t_   = session_frames // FPS
    mm, ss = t_//60, t_%60

    f_hdr  = lambda s: _ps_font("Courier New", s, bold=True)
    f_body = lambda s: _ps_font("Courier New", s)

    # ══════════ LEFT COLUMN ═══════════════════════════════════════════════

    # 1. Subject card
    _ps_card(surface, LX, 68, CW, 52)
    _ps_card_hdr(surface, LX, 68, CW, "SUBJECT PROFILE")
    nm = f_hdr(15).render(player.name.upper(), True, BRIGHT)
    surface.blit(nm, (LX+14, 90))
    # Initials badge
    pygame.draw.circle(surface, (0,72,36), (LX+CW-30, 94), 15)
    init = f_hdr(14).render(player.name[0].upper(), True, BRIGHT)
    surface.blit(init, (LX+CW-30-init.get_width()//2, 94-init.get_height()//2))

    # 2. Score card
    sc_col = C_G if round_manager.new_highscore else (220,220,220)
    _ps_card(surface, LX, 130, CW, 86)
    _ps_card_hdr(surface, LX, 130, CW, "SESSION SCORE")
    if round_manager.new_highscore:
        hs_t = f_hdr(10).render("★  NEW HIGH SCORE  ★", True, C_G)
        surface.blit(hs_t, (LX+CW//2-hs_t.get_width()//2, 152))
    sc_big = pygame.font.SysFont("Impact", 48).render(
        str(round_manager.score), True, sc_col)
    surface.blit(sc_big, (LX+14, 156))
    best_t = f_body(10).render(f"BEST  {round_manager.high_score}", True, (65,65,65))
    surface.blit(best_t, (LX+CW-best_t.get_width()-12, 200))

    # 3. Session metrics — 2×2 grid
    _ps_card(surface, LX, 226, CW, 136)
    _ps_card_hdr(surface, LX, 226, CW, "SESSION METRICS")
    metrics = [
        ("TIME",   f"{mm:02d}:{ss:02d}", VALC),
        ("DASHES", str(total_dashes_used),   VALC),
        ("WINS",   str(round_manager.wins),  (75, 215, 115)),
        ("LOSSES", str(round_manager.losses),(215, 75,  75)),
    ]
    cell_w = CW // 2
    for i, (lbl, val, vc) in enumerate(metrics):
        cx_ = LX + (i%2)*cell_w + cell_w//2
        ry_ = 252 + (i//2)*52
        pygame.draw.rect(surface, (18,28,18),
                         (LX+(i%2)*cell_w+6, ry_-3, cell_w-12, 44), border_radius=4)
        pygame.draw.line(surface, (22,55,22),
                         (LX+(i%2)*cell_w+6, ry_-3),
                         (LX+(i%2)*cell_w+cell_w-6, ry_-3), 1)
        lb_ = f_body(10).render(lbl, True, HDRC)
        vl_ = f_hdr(16).render(val, True, vc)
        surface.blit(lb_, (cx_-lb_.get_width()//2, ry_+2))
        surface.blit(vl_, (cx_-vl_.get_width()//2, ry_+16))

    # 4. Survival rate card
    sr_col = (75,215,115) if sr >= 50 else (215,75,75)
    _ps_card(surface, LX, 372, CW, 76)
    _ps_card_hdr(surface, LX, 372, CW, "PROJECTED SURVIVAL RATE")
    sr_t = f_hdr(18).render(f"{sr:.1f}%", True, sr_col)
    surface.blit(sr_t, (LX+14, 394))
    BX, BW = LX+14, CW-28
    pygame.draw.rect(surface, (22,22,22), (BX, 422, BW, 12), border_radius=6)
    fw = max(5, int(BW * sr / 100))
    pygame.draw.rect(surface, sr_col, (BX, 422, fw, 12), border_radius=6)
    pygame.draw.rect(surface, tuple(min(255,c+60) for c in sr_col),
                     (BX, 422, fw, 4), border_radius=6)
    pygame.draw.line(surface, (45,45,45),        # 50% midline
                     (BX+BW//2, 419), (BX+BW//2, 437), 1)
    mid_t = f_body(9).render("50%", True, (45,45,45))
    surface.blit(mid_t, (BX+BW//2-mid_t.get_width()//2, 438))

    # ══════════ RIGHT COLUMN ══════════════════════════════════════════════

    # 5. Win likelihood card
    ranked = comp.ranking()
    n_show = min(3, len(ranked)) if ranked else 0
    WL_H   = 26 + n_show*40 + 14 if n_show else 52
    _ps_card(surface, RX, 68, CW, WL_H)
    _ps_card_hdr(surface, RX, 68, CW, "WIN LIKELIHOOD")
    if ranked:
        bx2, bw2 = RX+14, CW-28
        by2 = 96
        for i,(name, lk) in enumerate(ranked[:n_show]):
            is_top = (i == 0)
            nc   = (230, 60, 20) if is_top else (100,100,100)
            nm_s = f_hdr(12).render(f"#{i+1}  {name.upper()}", True, nc)
            pt_s = f_hdr(12).render(f"{lk*100:.1f}%", True, nc)
            surface.blit(nm_s, (bx2, by2))
            surface.blit(pt_s, (bx2+bw2-pt_s.get_width(), by2))
            by2 += 16
            pygame.draw.rect(surface, (26,26,26), (bx2, by2, bw2, 10), border_radius=5)
            fw2 = max(6, int(bw2 * lk))
            bc2 = (230,60,20) if is_top else (55,55,55)
            pygame.draw.rect(surface, bc2, (bx2, by2, fw2, 10), border_radius=5)
            if is_top:
                pygame.draw.rect(surface, (255,110,50), (bx2, by2, fw2, 3), border_radius=5)
            by2 += 24

    # 6. Gap acceptance card
    GY = 68 + WL_H + 10
    gap_lines = gap_logger.get_hud_lines() if gap_logger else ["No gap logger."]
    GAP_H = 26 + len(gap_lines)*22 + 12
    _ps_card(surface, RX, GY, CW, GAP_H)
    _ps_card_hdr(surface, RX, GY, CW, "GAP ACCEPTANCE MODEL  (LOG-NORMAL)")
    gy2 = GY + 30
    for ln in gap_lines:
        lt = f_body(11).render(ln, True, (135, 195, 135))
        surface.blit(lt, (RX+14, gy2))
        gy2 += 22

    # 7. Environment card
    EY = GY + GAP_H + 10
    env_line = env_manager.get_summary_line() if env_manager else ""
    _ps_card(surface, RX, EY, CW, 52)
    _ps_card_hdr(surface, RX, EY, CW, "ENVIRONMENT")
    ev = f_body(11).render(env_line, True, (135, 195, 155))
    surface.blit(ev, (RX+14, EY+28))

    # ── Footer (flashing) ─────────────────────────────────────────────────
    if (pygame.time.get_ticks()//550) % 2 == 0:
        ft = f_body(12).render(
            "PRESS  [ESC]  OR  CLICK  ANYWHERE  TO  EXIT", True, (0, 170, 85))
        surface.blit(ft, (SCREEN_WIDTH//2-ft.get_width()//2, SCREEN_HEIGHT-28))


# ── Misc helpers ──────────────────────────────────────────────────────────
def draw_text_wrapped(surface, text, color, rect, font):
    lines = []
    for block in text.split('\n'):
        words, cur = block.split(' '), ""
        for w in words:
            test = cur + w + " "
            lines.append(cur) if font.size(test)[0] >= rect.width-40 else None
            cur = w+" " if font.size(test)[0] >= rect.width-40 else test
        lines.append(cur)
    th = len(lines)*font.get_linesize()
    sy = rect.y + (rect.height-th)//2
    for i, line in enumerate(lines):
        s = font.render(line.strip(), True, color)
        surface.blit(s, s.get_rect(center=(rect.centerx,
                                           sy+i*font.get_linesize()+s.get_height()//2)))


def draw_lore_card(surface, char_key):
    cd   = CHARACTERS[char_key]
    bw, bh = 850, 130
    lr   = pygame.Rect((SCREEN_WIDTH-bw)//2, SCREEN_HEIGHT-bh-15, bw, bh)
    pygame.draw.rect(surface, (20,145,195), lr, border_radius=20)
    perks = ("PERK: High Speed  |  FLAW: Low Friction  |  DASH: Kinetic Leap"
             if char_key=="Badrul" else
             "PERK: High Precision  |  FLAW: Speed Capped  |  DASH: Micro-Hop")
    draw_text_wrapped(surface, f"{cd['bio']}\n{perks}", (0,0,0), lr, font_lore)


def draw_quit_button(surface):
    pygame.draw.rect(surface, (220,50,50), quit_btn_rect, border_radius=10)
    t = font_lore.render("QUIT", True, C_WHITE)
    surface.blit(t, t.get_rect(center=quit_btn_rect.center))


def draw_radar_grid(surface):
    for x in range(0, SCREEN_WIDTH, 40):
        pygame.draw.line(surface, (15,35,25), (x,0), (x,SCREEN_HEIGHT))
    for y in range(0, SCREEN_HEIGHT, 40):
        pygame.draw.line(surface, (15,35,25), (0,y), (SCREEN_WIDTH,y))


def start_game(char_key):
    global player, round_manager, spawner, gap_logger, env_manager
    global session_frames, total_dashes_used, lives, max_lives
    global invincible_timer, new_hs_timer
    player            = Pedestrian(CHARACTERS[char_key])
    round_manager     = RoundManager(char_key)
    env_manager       = EnvironmentManager(SCREEN_WIDTH, SCREEN_HEIGHT)
    spawner           = Spawner(round_manager, env_manager)
    gap_logger        = GapAcceptanceLogger(char_key, fps=FPS)
    lives             = CHARACTERS[char_key]["lives"]
    max_lives         = lives
    session_frames    = 0
    total_dashes_used = 0
    invincible_timer  = 0
    new_hs_timer      = 0
    popups.clear()
    obstacle_manager.reset_for_round(1)


GAME_STATE = "START"

# ── Main loop ─────────────────────────────────────────────────────────────
running = True
while running:

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.VIDEORESIZE:
            handle_resize(event.w, event.h)
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_F11:
                toggle_fullscreen()
            if event.key == pygame.K_ESCAPE:
                if GAME_STATE == "RUNNING":
                    GAME_STATE = "PAUSED"
                elif GAME_STATE == "PAUSED":
                    GAME_STATE = "RUNNING"
                else:
                    running = False
        if event.type == pygame.MOUSEBUTTONDOWN:
            mp = _remap_mouse(event.pos)
            if GAME_STATE == "POST_SESSION": running = False
            if GAME_STATE in ["START","SELECT"]:
                if quit_btn_rect.collidepoint(mp): running = False
            if GAME_STATE == "PAUSED":
                if pause_resume_rect.collidepoint(mp):
                    GAME_STATE = "RUNNING"
                elif pause_session_rect.collidepoint(mp):
                    GAME_STATE = "POST_SESSION"
                elif pause_home_rect.collidepoint(mp):
                    GAME_STATE = "START"
                elif pause_quit_rect.collidepoint(mp):
                    running = False
                elif pause_sz_down_rect.collidepoint(mp):
                    cycle_window_size(-1)
                elif pause_sz_up_rect.collidepoint(mp):
                    cycle_window_size(+1)
                elif pause_fs_rect.collidepoint(mp):
                    toggle_fullscreen()
            if GAME_STATE == "START":
                if start_button_rect.collidepoint(mp): GAME_STATE = "SELECT"
            elif GAME_STATE == "SELECT":
                if badrul_btn_rect.collidepoint(mp):
                    start_game("Badrul");   GAME_STATE = "RUNNING"
                elif mrittika_btn_rect.collidepoint(mp):
                    start_game("Mrittika"); GAME_STATE = "RUNNING"
            elif GAME_STATE == "GAME_OVER":
                if go_retry_rect.collidepoint(mp):
                    start_game(player.name); GAME_STATE = "RUNNING"
                elif go_select_rect.collidepoint(mp):
                    GAME_STATE = "SELECT"

    if GAME_STATE == "RUNNING" and player:
        session_frames += 1
        if shake_timer    > 0: shake_timer    -= 1
        if invincible_timer>0: invincible_timer-= 1
        if new_hs_timer   > 0: new_hs_timer   -= 1

        round_manager.tick_session()

        if env_manager:
            env_manager.set_round(round_manager.current_round)
            env_manager.update()

        keys = pygame.key.get_pressed()
        if keys[pygame.K_SPACE] and player.current_dash_cooldown == 0:
            total_dashes_used += 1

        if obstacle_manager.player_is_stunned:
            player.vel_x *= 0.7
            player.vel_y *= 0.7
            player.rect.x = int(player.true_x)
            player.rect.y = int(player.true_y)
        else:
            friction_mult = (env_manager.player_friction_mult if env_manager else 1.0)
            player.move(keys, env_friction_mult=friction_mult)

        obstacle_manager.update(player.rect, spawner.vehicles)
        obstacle_manager.resolve_vendor_collision(player)

        if gap_logger:
            gap_logger.check_and_log(player, spawner.vehicles,
                                     session_frames, round_manager.current_round)
        spawner.update()

        # ── Win ───────────────────────────────────────────────────────────
        if player.rect.y < FAR_LANE_Y:
            round_manager.record_win()
            comp.record(player.name, True,
                        score=round_manager.score,
                        rounds=round_manager.current_round)
            pts = 10 + round_manager.current_round * 2
            spawn_popup(f"+{pts} pts",  player.rect.centerx, player.rect.centery-55, C_GOLD)
            spawn_popup("+1 SUCCESS",   player.rect.centerx, player.rect.centery-20, (0,255,120))
            if round_manager.new_highscore: new_hs_timer = 40
            player.reset_position()
            spawner.vehicles.clear()
            obstacle_manager.reset_for_round(round_manager.current_round)

        # ── Hit detection ─────────────────────────────────────────────────
        if invincible_timer == 0:
            for v in spawner.vehicles:
                if player.rect.colliderect(v.rect):
                    lives -= 1
                    round_manager.record_loss()
                    comp.record(player.name, False,
                                score=round_manager.score,
                                rounds=round_manager.current_round)
                    trigger_shake()
                    invincible_timer = INVINCIBLE_DUR
                    if lives <= 0:
                        if gap_logger: gap_logger.save()
                        GAME_STATE = "GAME_OVER"
                    else:
                        spawn_popup(
                            f"OUCH!  {lives} {'life' if lives==1 else 'lives'} left",
                            player.rect.centerx, player.rect.centery-20, (255,120,50))
                        player.reset_position()
                        spawner.vehicles.clear()
                    break

    # ── Draw ──────────────────────────────────────────────────────────────
    ox, oy = get_shake_offset() if GAME_STATE == "RUNNING" else (0,0)
    canvas  = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    canvas.fill(COLOR_BG)

    if GAME_STATE == "START":
        canvas.blit(start_bg, (0,0))
        draw_quit_button(canvas)

    elif GAME_STATE == "SELECT":
        canvas.blit(selection_bg, (0,0))
        draw_quit_button(canvas)
        mp = _remap_mouse(pygame.mouse.get_pos())
        if badrul_btn_rect.collidepoint(mp):
            draw_lore_card(canvas, "Badrul")
        elif mrittika_btn_rect.collidepoint(mp):
            draw_lore_card(canvas, "Mrittika")

    elif GAME_STATE == "RUNNING" and player:
        road.update()
        road.draw(canvas)
        obstacle_manager.draw(canvas)
        spawner.draw(canvas)
        if invincible_timer == 0 or (invincible_timer//6)%2 == 0:
            player.draw(canvas)

        if env_manager:
            env_manager.draw(canvas)

        draw_hud(canvas)
        update_and_draw_popups(canvas)
        draw_shake_message(canvas)
        draw_new_hs_flash(canvas)
        draw_stun_overlay(canvas, obstacle_manager.stun_timer)

        # ── Character comparison panel (top-right) ────────────────────────
        comp.draw(canvas)

        hint = font_telemetry.render("[ESC] Pause   [F11] Fullscreen", True, (80,120,80))
        canvas.blit(hint, (SCREEN_WIDTH-hint.get_width()-12, 12))

    elif GAME_STATE == "PAUSED":
        road.draw(canvas)
        if spawner: spawner.draw(canvas)
        if player:  player.draw(canvas)
        draw_pause(canvas)

    elif GAME_STATE == "GAME_OVER":
        draw_game_over(canvas)

    elif GAME_STATE == "POST_SESSION":
        draw_post_session(canvas)

    # Scale to window
    shake_surf = pygame.Surface((_LOGICAL_W, _LOGICAL_H))
    shake_surf.fill(COLOR_BG)
    shake_surf.blit(canvas, (ox,oy))
    scaled = pygame.transform.smoothscale(shake_surf, screen.get_size())
    screen.blit(scaled, (0,0))
    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()
sys.exit()