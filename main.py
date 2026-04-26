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
# Local fonts used only on the Game Over screen
_go_f_label = None
_go_f_val   = None
_go_f_small = None
_go_f_bar   = None

def _init_go_fonts():
    global _go_f_label, _go_f_val, _go_f_small, _go_f_bar
    if _go_f_label is None:
        _go_f_label = pygame.font.SysFont("Arial", 16)
        _go_f_val   = pygame.font.SysFont("Arial", 16, bold=True)
        _go_f_small = pygame.font.SysFont("Courier New", 11, bold=True)
        _go_f_bar   = pygame.font.SysFont("Courier New", 13, bold=True)


def _pill(surface, rect, bg, label):
    pygame.draw.rect(surface, bg, rect, border_radius=rect.height//2)
    t = font_btn.render(label, True, C_BLACK)
    surface.blit(t, (rect.centerx-t.get_width()//2, rect.centery-t.get_height()//2))


def _card(surface, x, y, w, h, fill, border, radius=7):
    pygame.draw.rect(surface, fill,   (x, y, w, h), border_radius=radius)
    pygame.draw.rect(surface, border, (x, y, w, h), 1, border_radius=radius)


def draw_game_over(surface):
    _init_go_fonts()

    # ── Background: near-black with faint horizontal scanlines ─────────────
    surface.fill((10, 8, 8))
    for scan_y in range(0, SCREEN_HEIGHT, 4):
        pygame.draw.line(surface, (18, 14, 14), (0, scan_y), (SCREEN_WIDTH, scan_y))

    cx   = SCREEN_WIDTH // 2
    CARD_W = 460
    cx_l   = cx - CARD_W // 2   # left edge of all cards

    # ── Title ────────────────────────────────────────────────────────────────
    # Shadow
    sh = font_game_over.render("GAME OVER", True, (70, 22, 5))
    surface.blit(sh, (cx - sh.get_width()//2 + 3, 28))
    go = font_game_over.render("GAME OVER", True, C_ORANGE)
    surface.blit(go, (cx - go.get_width()//2, 25))
    # Orange underline
    pygame.draw.rect(surface, C_ORANGE, (cx - 180, 125, 360, 3), border_radius=2)

    # Subject
    sub = font_sub.render(f"IN BOARDBAZAR  ·  {player.name.upper()}", True, (155, 155, 155))
    surface.blit(sub, (cx - sub.get_width()//2, 135))

    # ── Score card ───────────────────────────────────────────────────────────
    SC_Y, SC_H = 162, 74
    _card(surface, cx_l, SC_Y, CARD_W, SC_H,
          fill=(20, 14, 12), border=(70, 28, 10))

    if round_manager.new_highscore:
        hs_t = font_sub.render("★  NEW HIGH SCORE  ★", True, C_GOLD)
        surface.blit(hs_t, (cx - hs_t.get_width()//2, SC_Y + 5))
        sc_col  = C_GOLD
        score_y = SC_Y + 26
    else:
        sc_col  = C_WHITE
        score_y = SC_Y + 8
        best_t  = _go_f_small.render(f"BEST  {round_manager.high_score}", True, (85, 85, 85))
        surface.blit(best_t, (cx_l + CARD_W - best_t.get_width() - 12, SC_Y + 54))

    sc_surf = font_game_over.render(str(round_manager.score), True, sc_col)
    sc_surf = pygame.transform.scale(
        sc_surf, (sc_surf.get_width() * 52 // 100, sc_surf.get_height() * 52 // 100))
    surface.blit(sc_surf, (cx - sc_surf.get_width()//2, score_y))

    # ── Stats card ───────────────────────────────────────────────────────────
    total = round_manager.wins + round_manager.losses
    pct   = (round_manager.wins / total * 100) if total > 0 else 0
    ts    = session_frames // FPS
    m, s  = ts // 60, ts % 60

    stats = [
        ("Rounds Survived", str(round_manager.wins),      (80, 220, 120)),
        ("Times Hit",       str(round_manager.losses),     (220, 80,  80)),
        ("Dashes Used",     str(total_dashes_used),        C_OFFWHITE),
        ("Survival Rate",   f"{pct:.1f}%",
         (80, 220, 120) if pct >= 50 else (220, 80, 80)),
        ("Time Played",     f"{m:02d}:{s:02d}",            C_OFFWHITE),
    ]

    ST_Y = SC_Y + SC_H + 10
    ROW_H = 24
    ST_H  = len(stats) * ROW_H + 18
    _card(surface, cx_l, ST_Y, CARD_W, ST_H, fill=(16, 16, 16), border=(42, 42, 42))

    ry = ST_Y + 10
    for i, (lbl, val, vcol) in enumerate(stats):
        # Alternating row tint
        if i % 2 == 0:
            pygame.draw.rect(surface, (22, 22, 22),
                             (cx_l + 2, ry - 2, CARD_W - 4, ROW_H - 1), border_radius=3)
        lbl_s = _go_f_label.render(lbl, True, (115, 115, 115))
        val_s = _go_f_val.render(val, True, vcol)
        surface.blit(lbl_s, (cx_l + 14, ry + 2))
        surface.blit(val_s, (cx_l + CARD_W - val_s.get_width() - 14, ry + 2))
        ry += ROW_H

    # ── Character comparison card ─────────────────────────────────────────────
    ranked = comp.ranking()
    if ranked:
        CM_Y  = ST_Y + ST_H + 10
        n_show = min(2, len(ranked))
        CM_H  = n_show * 42 + 34
        _card(surface, cx_l, CM_Y, CARD_W, CM_H, fill=(12, 18, 12), border=(38, 75, 38))

        # Header
        hdr = _go_f_small.render("CHARACTER  WIN LIKELIHOOD", True, (55, 130, 55))
        surface.blit(hdr, (cx - hdr.get_width()//2, CM_Y + 8))

        BAR_X = cx_l + 14
        BAR_W = CARD_W - 28
        bar_y = CM_Y + 28

        for i, (name, lk) in enumerate(ranked[:n_show]):
            is_leader = (i == 0)
            name_col  = C_ORANGE if is_leader else (130, 130, 130)
            bar_fill  = C_ORANGE if is_leader else (65, 65, 65)

            # Name + percentage on the same line
            rank_t = _go_f_bar.render(f"#{i+1}  {name.upper()}", True, name_col)
            pct_t  = _go_f_bar.render(f"{lk*100:.1f}%", True, name_col)
            surface.blit(rank_t, (BAR_X, bar_y))
            surface.blit(pct_t,  (BAR_X + BAR_W - pct_t.get_width(), bar_y))

            # Bar
            bar_y += 18
            pygame.draw.rect(surface, (30, 30, 30),
                             (BAR_X, bar_y, BAR_W, 10), border_radius=5)
            fill_w = max(8, int(BAR_W * lk))
            pygame.draw.rect(surface, bar_fill,
                             (BAR_X, bar_y, fill_w, 10), border_radius=5)
            # Thin highlight on top of bar
            if is_leader:
                pygame.draw.rect(surface, (255, 120, 60),
                                 (BAR_X, bar_y, fill_w, 3), border_radius=5)
            bar_y += 24

    # ── Buttons ──────────────────────────────────────────────────────────────
    _pill(surface, go_retry_rect,  C_LIME,        "PLAY AGAIN")
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
        canvas.fill((10,15,15))
        draw_radar_grid(canvas)
        ts = font_title.render("SIMULATION DATA LOG", True, (0,255,127))
        canvas.blit(ts, (SCREEN_WIDTH//2-ts.get_width()//2, 60))
        if player and round_manager:
            ta  = round_manager.wins + round_manager.losses
            sr  = (round_manager.wins/ta*100) if ta > 0 else 0.0
            t   = session_frames // FPS
            m,s = t//60, t%60
            for i, (line, tag) in enumerate([
                (f"> Subject Profile.......... {player.name.upper()}", None),
                (f"> Final Score.............. {round_manager.score}", "score"),
                (f"> High Score............... {round_manager.high_score}", "hs"),
                (f"> Total Time Elapsed....... {m:02d}:{s:02d}", None),
                (f"> Kinetic Dashes Used...... {total_dashes_used}", None),
                (f"> Wins..................... {round_manager.wins}", None),
                (f"> Losses................... {round_manager.losses}", None),
                (f"> Projected Survival Rate.. {sr:.1f}%", sr),
            ]):
                col = (C_GOLD if tag in ("score","hs") and
                                 (tag=="score" or round_manager.new_highscore)
                       else (0,255,127) if isinstance(tag,float) and tag >= 50
                       else (255,50,50) if isinstance(tag,float)
                       else (150,150,150) if tag=="hs"
                       else (200,220,200))
                canvas.blit(font_stats.render(line, True, col),
                            (SCREEN_WIDTH//2-260, 155+i*42))

        # Gap acceptance
        if gap_logger:
            gap_lines = gap_logger.get_hud_lines()
            gy = 155 + 8*42 + 12
            pygame.draw.line(canvas, (0,100,50),
                             (SCREEN_WIDTH//2-260,gy),(SCREEN_WIDTH//2+260,gy),1)
            gy += 10
            canvas.blit(font_hud.render("> Gap Acceptance Model", True, (0,200,100)),
                        (SCREEN_WIDTH//2-260, gy))
            gy += 28
            for ln in gap_lines:
                canvas.blit(font_telemetry.render(ln, True, (160,210,160)),
                            (SCREEN_WIDTH//2-260, gy))
                gy += 22

        # Environment
        if env_manager:
            gy_env  = 155 + 8*42 + 12 + 28 + 4*22 + 14
            env_line= env_manager.get_summary_line()
            pygame.draw.line(canvas, (0,80,50),
                             (SCREEN_WIDTH//2-260,gy_env),(SCREEN_WIDTH//2+260,gy_env),1)
            gy_env += 8
            canvas.blit(font_hud.render("> Environment", True, (0,180,90)),
                        (SCREEN_WIDTH//2-260, gy_env))
            gy_env += 26
            canvas.blit(font_telemetry.render(env_line, True, (140,200,155)),
                        (SCREEN_WIDTH//2-260, gy_env))

        # Win-likelihood comparison in POST_SESSION
        ranked = comp.ranking()
        if ranked:
            gy_cmp = gy_env + 48 if env_manager else 155 + 8*42 + 60
            pygame.draw.line(canvas, (0,80,50),
                             (SCREEN_WIDTH//2-260,gy_cmp),(SCREEN_WIDTH//2+260,gy_cmp),1)
            gy_cmp += 8
            canvas.blit(font_hud.render("> Win Likelihood", True, (0,180,90)),
                        (SCREEN_WIDTH//2-260, gy_cmp))
            gy_cmp += 26
            for i, (name, lk) in enumerate(ranked):
                col = C_GOLD if i==0 else (160,210,160)
                ln  = f"#{i+1}  {name.upper():<12}  {lk*100:.1f}%"
                canvas.blit(font_telemetry.render(ln, True, col),
                            (SCREEN_WIDTH//2-260, gy_cmp))
                gy_cmp += 22

        es = font_telemetry.render("PRESS [ESC] OR CLICK ANYWHERE TO TERMINATE",
                                   True, (0,255,127))
        if (pygame.time.get_ticks()//500)%2 == 0:
            canvas.blit(es, (SCREEN_WIDTH//2-es.get_width()//2, SCREEN_HEIGHT-60))

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