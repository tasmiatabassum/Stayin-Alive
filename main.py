# main.py
import pygame
import sys
import random
from config import *
from road import Road
from pedestrian import Pedestrian
from spawner import Spawner
from characters import CHARACTERS
from round_manager import RoundManager

pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Stayin' Alive (in boardbazar)")
clock = pygame.time.Clock()

# --- Fonts ---
font_lore      = pygame.font.SysFont("Gothic", 25)
font_title     = pygame.font.SysFont("Courier New", 40, bold=True)
font_stats     = pygame.font.SysFont("Courier New", 24)
font_telemetry = pygame.font.SysFont("Courier New", 16, bold=True)
font_hud       = pygame.font.SysFont("Courier New", 18, bold=True)
font_popup     = pygame.font.SysFont("Arial", 32, bold=True)
font_shake     = pygame.font.SysFont("Arial", 52, bold=True)
font_game_over = pygame.font.SysFont("Impact", 90)
font_sub       = pygame.font.SysFont("Arial", 18, bold=True)
font_stat_go   = pygame.font.SysFont("Arial", 22)
font_btn       = pygame.font.SysFont("Arial", 20, bold=True)

# --- Colors matching start screen ---
C_ORANGE   = (230, 60,  20)
C_LIME     = (185, 233,  1)
C_WHITE    = (255, 255, 255)
C_OFFWHITE = (220, 220, 220)
C_GOLD     = (255, 215,  0)
C_DIM      = (120, 120, 120)
C_BLACK    = (0,   0,   0)

# 2. Assets
try:
    start_bg = pygame.image.load("start.jpg")
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

# 3. Hitboxes
start_button_rect = pygame.Rect((SCREEN_WIDTH//2)-100, (SCREEN_HEIGHT//2)+50, 200, 80)
btn_w, btn_h = 200, 70
btn_y = (SCREEN_HEIGHT//2)+130
badrul_btn_rect   = pygame.Rect((SCREEN_WIDTH//2)-btn_w-20, btn_y, btn_w, btn_h)
mrittika_btn_rect = pygame.Rect((SCREEN_WIDTH//2)+20,       btn_y, btn_w, btn_h)
quit_btn_rect     = pygame.Rect(SCREEN_WIDTH-120, 20, 100, 40)

GO_W, GO_H = 220, 58
go_retry_rect  = pygame.Rect((SCREEN_WIDTH//2)-GO_W-20, SCREEN_HEIGHT-130, GO_W, GO_H)
go_select_rect = pygame.Rect((SCREEN_WIDTH//2)+20,      SCREEN_HEIGHT-130, GO_W, GO_H)

# Pause menu buttons
PB_W, PB_H = 260, 58
pause_resume_rect  = pygame.Rect((SCREEN_WIDTH//2)-PB_W//2, 280, PB_W, PB_H)
pause_session_rect = pygame.Rect((SCREEN_WIDTH//2)-PB_W//2, 355, PB_W, PB_H)
pause_home_rect    = pygame.Rect((SCREEN_WIDTH//2)-PB_W//2, 430, PB_W, PB_H)
pause_quit_rect    = pygame.Rect((SCREEN_WIDTH//2)-PB_W//2, 505, PB_W, PB_H)

# 4. Game world
round_manager     = None
road              = Road()
spawner           = None
player            = None
session_frames    = 0
total_dashes_used = 0
lives             = 3
max_lives         = 3
invincible_timer  = 0
INVINCIBLE_DUR    = 90
new_hs_timer      = 0

# ── Popups ──────────────────────────────────────────────────────────────
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

# ── Shake ────────────────────────────────────────────────────────────────
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

# ── HUD ──────────────────────────────────────────────────────────────────
def draw_hud(surface):
    hw, hh, hx, hy = 340, 148, 10, 10
    bg = pygame.Surface((hw, hh), pygame.SRCALPHA)
    bg.fill((8, 12, 10, 215))
    surface.blit(bg, (hx, hy))
    pygame.draw.rect(surface, (0, 210, 100), (hx, hy, hw, hh), 2, border_radius=4)

    ts = session_frames // FPS
    m, s = ts // 60, ts % 60
    tr = round_manager.wins + round_manager.losses
    pct = (round_manager.wins / tr * 100) if tr > 0 else 0.0
    sc = C_GOLD if round_manager.new_highscore else (255, 255, 200)

    for i, (txt, col) in enumerate([
        (f"SUBJECT : {player.name.upper()}",                         (0, 220, 120)),
        (f"SCORE   : {round_manager.score}   BEST: {round_manager.high_score}", sc),
        (f"ROUND   : {round_manager.current_round}   T+ {m:02d}:{s:02d}", (180, 220, 180)),
        (f"SUCCESS : {round_manager.wins}   FAIL: {round_manager.losses}", (180, 220, 180)),
        (f"SURVIVAL: {pct:.1f}%", (0, 255, 120) if pct >= 50 else (255, 80, 80)),
    ]):
        surface.blit(font_hud.render(txt, True, col), (hx+10, hy+8+i*26))

    for i in range(max_lives):
        cx = hx + hw - 14 - i * 22
        c = (220, 50, 50) if i < lives else (50, 50, 50)
        pygame.draw.circle(surface, c, (cx, hy+12), 8)
        pygame.draw.circle(surface, (255, 100, 100) if i < lives else (80, 80, 80),
                           (cx, hy+12), 5)

def draw_new_hs_flash(surface):
    global new_hs_timer
    if new_hs_timer <= 0: return
    new_hs_timer -= 1
    s = font_popup.render("NEW HIGH SCORE!", True, C_GOLD)
    s.set_alpha(min(255, new_hs_timer * 6))
    surface.blit(s, (SCREEN_WIDTH//2 - s.get_width()//2, 140))

# ── GAME OVER — start screen themed ─────────────────────────────────────
def _pill(surface, rect, bg, label):
    pygame.draw.rect(surface, bg, rect, border_radius=rect.height//2)
    t = font_btn.render(label, True, C_BLACK)
    surface.blit(t, (rect.centerx - t.get_width()//2,
                     rect.centery - t.get_height()//2))

def draw_game_over(surface):
    surface.fill(C_BLACK)
    cx = SCREEN_WIDTH // 2

    # Giant orange "GAME OVER"
    go = font_game_over.render("GAME OVER", True, C_ORANGE)
    surface.blit(go, (cx - go.get_width()//2, 50))

    # Subtitle
    sub = font_sub.render(f"IN BOARDBAZAR  ·  {player.name.upper()}", True, C_WHITE)
    surface.blit(sub, (cx - sub.get_width()//2, 158))

    # Score area
    sy = 200
    if round_manager.new_highscore:
        hs = font_sub.render("★ NEW HIGH SCORE ★", True, C_GOLD)
        surface.blit(hs, (cx - hs.get_width()//2, sy))
        sy += 30
        sc_col = C_GOLD
    else:
        best = font_sub.render(f"BEST  {round_manager.high_score}", True, C_DIM)
        surface.blit(best, (cx - best.get_width()//2, sy))
        sy += 26
        sc_col = C_WHITE

    # Big score number
    sc_big = font_game_over.render(str(round_manager.score), True, sc_col)
    sc_big = pygame.transform.scale(
        sc_big, (sc_big.get_width()*2//3, sc_big.get_height()*2//3))
    surface.blit(sc_big, (cx - sc_big.get_width()//2, sy))
    sy += sc_big.get_height() + 16

    # Divider
    pygame.draw.line(surface, (45, 45, 45), (cx-200, sy), (cx+200, sy), 1)
    sy += 16

    # Stats — left label, right value
    total = round_manager.wins + round_manager.losses
    pct   = (round_manager.wins / total * 100) if total > 0 else 0
    ts    = session_frames // FPS
    m, s  = ts // 60, ts % 60

    for label, value in [
        ("Rounds Survived", str(round_manager.wins)),
        ("Times Hit",        str(round_manager.losses)),
        ("Dashes Used",      str(total_dashes_used)),
        ("Survival Rate",    f"{pct:.1f}%"),
        ("Time Played",      f"{m:02d}:{s:02d}"),
    ]:
        surface.blit(font_stat_go.render(label, True, C_DIM),      (cx-200, sy))
        surface.blit(font_stat_go.render(value, True, C_OFFWHITE), (cx+80,  sy))
        sy += 32

    # Pill buttons
    _pill(surface, go_retry_rect,  C_LIME,         "PLAY AGAIN")
    _pill(surface, go_select_rect, (200, 200, 200), "CHANGE CHARACTER")

# ── PAUSE MENU — same black/orange aesthetic ─────────────────────────────
def draw_pause(surface):
    # Dim the game underneath
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 175))
    surface.blit(overlay, (0, 0))

    cx = SCREEN_WIDTH // 2

    # "PAUSED" title in orange
    title = font_game_over.render("PAUSED", True, C_ORANGE)
    surface.blit(title, (cx - title.get_width()//2, 170))

    # Subtitle
    # sub = font_sub.render("IN BOARDBAZAR", True, C_DIM)
    # surface.blit(sub, (cx - sub.get_width()//2, 248))

    # Four pill buttons
    _pill(surface, pause_resume_rect,  C_LIME,         "RESUME")
    _pill(surface, pause_session_rect, (100, 160, 220), "SESSION DATA")
    _pill(surface, pause_home_rect,    (200, 200, 200), "HOME")
    _pill(surface, pause_quit_rect,    (180, 40,  40),  "QUIT GAME")

# ── Misc helpers ─────────────────────────────────────────────────────────
def draw_text_wrapped(surface, text, color, rect, font):
    lines = []
    for block in text.split('\n'):
        words, cur = block.split(' '), ""
        for w in words:
            test = cur + w + " "
            lines.append(cur) if font.size(test)[0] >= rect.width-40 else None
            cur = w+" " if font.size(test)[0] >= rect.width-40 else test
        lines.append(cur)
    th = len(lines) * font.get_linesize()
    sy = rect.y + (rect.height - th) // 2
    for i, line in enumerate(lines):
        s = font.render(line.strip(), True, color)
        surface.blit(s, s.get_rect(center=(rect.centerx,
                                            sy + i*font.get_linesize() + s.get_height()//2)))

def draw_lore_card(surface, char_key):
    cd = CHARACTERS[char_key]
    bw, bh = 850, 130
    lr = pygame.Rect((SCREEN_WIDTH-bw)//2, SCREEN_HEIGHT-bh-15, bw, bh)
    pygame.draw.rect(surface, (20, 145, 195), lr, border_radius=20)
    perks = ("PERK: High Speed  |  FLAW: Low Friction  |  DASH: Kinetic Leap"
             if char_key == "Badrul" else
             "PERK: High Precision  |  FLAW: Speed Capped  |  DASH: Micro-Hop")
    draw_text_wrapped(surface, f"{cd['bio']}\n{perks}", (0,0,0), lr, font_lore)

def draw_quit_button(surface):
    pygame.draw.rect(surface, (220, 50, 50), quit_btn_rect, border_radius=10)
    t = font_lore.render("QUIT", True, C_WHITE)
    surface.blit(t, t.get_rect(center=quit_btn_rect.center))

def draw_radar_grid(surface):
    for x in range(0, SCREEN_WIDTH, 40):
        pygame.draw.line(surface, (15, 35, 25), (x,0), (x, SCREEN_HEIGHT))
    for y in range(0, SCREEN_HEIGHT, 40):
        pygame.draw.line(surface, (15, 35, 25), (0,y), (SCREEN_WIDTH, y))

def start_game(char_key):
    global player, round_manager, spawner
    global session_frames, total_dashes_used, lives, max_lives
    global invincible_timer, new_hs_timer
    player            = Pedestrian(CHARACTERS[char_key])
    round_manager     = RoundManager(char_key)
    spawner           = Spawner(round_manager)
    lives             = CHARACTERS[char_key]["lives"]
    max_lives         = lives
    session_frames    = 0
    total_dashes_used = 0
    invincible_timer  = 0
    new_hs_timer      = 0
    popups.clear()

GAME_STATE = "START"

# ── Main loop ─────────────────────────────────────────────────────────────
running = True
while running:

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if GAME_STATE == "RUNNING":
                    GAME_STATE = "PAUSED"
                elif GAME_STATE == "PAUSED":
                    GAME_STATE = "RUNNING"
                else:
                    running = False
        if event.type == pygame.MOUSEBUTTONDOWN:
            mp = event.pos
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
        session_frames   += 1
        if shake_timer      > 0: shake_timer      -= 1
        if invincible_timer > 0: invincible_timer -= 1
        if new_hs_timer     > 0: new_hs_timer     -= 1

        keys = pygame.key.get_pressed()
        if keys[pygame.K_SPACE] and player.current_dash_cooldown == 0:
            total_dashes_used += 1
        player.move(keys)
        spawner.update()

        if player.rect.y < FAR_LANE_Y:
            round_manager.record_win()
            pts = 10 + round_manager.current_round * 2
            spawn_popup(f"+{pts} pts", player.rect.centerx, player.rect.centery-55, C_GOLD)
            spawn_popup("+1 SUCCESS",  player.rect.centerx, player.rect.centery-20, (0,255,120))
            if round_manager.new_highscore: new_hs_timer = 40
            player.reset_position()
            spawner.vehicles.clear()

        if invincible_timer == 0:
            for v in spawner.vehicles:
                if player.rect.colliderect(v.rect):
                    lives -= 1
                    round_manager.record_loss()
                    trigger_shake()
                    invincible_timer = INVINCIBLE_DUR
                    if lives <= 0:
                        GAME_STATE = "GAME_OVER"
                    else:
                        spawn_popup(f"OUCH!  {lives} {'life' if lives==1 else 'lives'} left",
                                    player.rect.centerx, player.rect.centery-20, (255,120,50))
                        player.reset_position()
                        spawner.vehicles.clear()
                    break

    # ── Draw ───────────────────────────────────────────────────────────────
    ox, oy = get_shake_offset() if GAME_STATE == "RUNNING" else (0, 0)
    canvas = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    canvas.fill(COLOR_BG)

    if GAME_STATE == "START":
        canvas.blit(start_bg, (0,0))
        draw_quit_button(canvas)

    elif GAME_STATE == "SELECT":
        canvas.blit(selection_bg, (0,0))
        draw_quit_button(canvas)
        mp = pygame.mouse.get_pos()
        if   badrul_btn_rect.collidepoint(mp):   draw_lore_card(canvas, "Badrul")
        elif mrittika_btn_rect.collidepoint(mp): draw_lore_card(canvas, "Mrittika")

    elif GAME_STATE == "RUNNING" and player:
        road.update()
        road.draw(canvas)
        spawner.draw(canvas)
        if invincible_timer == 0 or (invincible_timer // 6) % 2 == 0:
            player.draw(canvas)
        draw_hud(canvas)
        update_and_draw_popups(canvas)
        draw_shake_message(canvas)
        draw_new_hs_flash(canvas)
        hint = font_telemetry.render("[ESC] Pause", True, (80,120,80))
        canvas.blit(hint, (SCREEN_WIDTH - hint.get_width() - 12, 12))

    elif GAME_STATE == "PAUSED":
        # Draw frozen game world underneath
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
        canvas.blit(ts, (SCREEN_WIDTH//2 - ts.get_width()//2, 60))
        if player and round_manager:
            ta = round_manager.wins + round_manager.losses
            sr = (round_manager.wins / ta * 100) if ta > 0 else 0.0
            t  = session_frames // FPS
            m, s = t//60, t%60
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
                       (tag == "score" or round_manager.new_highscore)
                       else (0,255,127) if isinstance(tag,float) and tag>=50
                       else (255,50,50) if isinstance(tag,float)
                       else (150,150,150) if tag=="hs"
                       else (200,220,200))
                canvas.blit(font_stats.render(line, True, col),
                            (SCREEN_WIDTH//2-260, 155+i*42))
        es = font_telemetry.render("PRESS [ESC] OR CLICK ANYWHERE TO TERMINATE",
                                    True, (0,255,127))
        if (pygame.time.get_ticks()//500) % 2 == 0:
            canvas.blit(es, (SCREEN_WIDTH//2 - es.get_width()//2, SCREEN_HEIGHT-60))

    screen.blit(canvas, (ox, oy))
    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()
sys.exit()