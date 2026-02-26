# main.py
import pygame
import sys
from config import *
from road import Road
from pedestrian import Pedestrian
from spawner import Spawner
from characters import CHARACTERS
from round_manager import RoundManager

# 1. Initialize Pygame
pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Stayin' Alive (in boardbazar)")
clock = pygame.time.Clock()

# --- Simulation Fonts ---
font_lore = pygame.font.SysFont("Gothic", 25)
font_title = pygame.font.SysFont("Courier New", 40, bold=True)
font_stats = pygame.font.SysFont("Courier New", 24)
font_telemetry = pygame.font.SysFont("Courier New", 16, bold=True) # HUD Font

# 2. Load Assets
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

# 3. Define Hitboxes
start_button_rect = pygame.Rect((SCREEN_WIDTH // 2) - 100, (SCREEN_HEIGHT // 2) + 50, 200, 80)

btn_w = 200
btn_h = 70
btn_y = (SCREEN_HEIGHT // 2) + 130
badrul_btn_rect   = pygame.Rect((SCREEN_WIDTH // 2) - btn_w - 20, btn_y, btn_w, btn_h)
mrittika_btn_rect = pygame.Rect((SCREEN_WIDTH // 2) + 20,         btn_y, btn_w, btn_h)

quit_btn_rect = pygame.Rect(SCREEN_WIDTH - 120, 20, 100, 40)

# 4. Setup Game World
round_manager = RoundManager()
road    = Road()
spawner = Spawner(round_manager)
player  = None

# --- NEW: Session Tracking Variables ---
session_frames = 0
total_dashes_used = 0

# 5. Game State
# Flow: START -> SELECT -> RUNNING -> POST_SESSION
GAME_STATE = "START"

# --- UI Helper Functions ---
def draw_text_wrapped(surface, text, color, rect, font):
    lines = []
    for block in text.split('\n'):
        words = block.split(' ')
        current_line = ""
        for word in words:
            test_line = current_line + word + " "
            if font.size(test_line)[0] < rect.width - 40: 
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word + " "
        lines.append(current_line)

    total_height = len(lines) * font.get_linesize()
    start_y = rect.y + (rect.height - total_height) // 2

    for i, line in enumerate(lines):
        text_surf = font.render(line.strip(), True, color)
        text_rect = text_surf.get_rect(center=(rect.centerx, start_y + i * font.get_linesize() + text_surf.get_height() // 2))
        surface.blit(text_surf, text_rect)

def draw_lore_card(screen, char_key):
    char_data = CHARACTERS[char_key]
    box_width = 850      
    box_height = 130     
    box_x = (SCREEN_WIDTH // 2) - (box_width // 2)
    box_y = SCREEN_HEIGHT - box_height - 15 
    lore_rect = pygame.Rect(box_x, box_y, box_width, box_height)
    
    COLOR_LORE_BOX = (20, 145, 195) 
    pygame.draw.rect(screen, COLOR_LORE_BOX, lore_rect, border_radius=20)
    
    if char_key == "Badrul":
        perks = "PERK: High Speed  |  FLAW: Low Friction  |  DASH: Kinetic Leap"
    else:
        perks = "PERK: High Precision  |  FLAW: Speed Capped  |  DASH: Micro-Hop"
        
    lore_text = f"{char_data['bio']}\n{perks}"
    draw_text_wrapped(screen, lore_text, (0, 0, 0), lore_rect, font_lore)

def draw_quit_button(screen):
    pygame.draw.rect(screen, (220, 50, 50), quit_btn_rect, border_radius=10)
    quit_text = font_lore.render("QUIT", True, (255, 255, 255))
    text_rect = quit_text.get_rect(center=quit_btn_rect.center)
    screen.blit(quit_text, text_rect)

def draw_radar_grid(surface):
    # Draws a subtle dark green matrix grid for the background
    for x in range(0, SCREEN_WIDTH, 40):
        pygame.draw.line(surface, (15, 35, 25), (x, 0), (x, SCREEN_HEIGHT))
    for y in range(0, SCREEN_HEIGHT, 40):
        pygame.draw.line(surface, (15, 35, 25), (0, y), (SCREEN_WIDTH, y))

running = True
while running:

    # --- Input Handling ---
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if GAME_STATE == "RUNNING":
                    print("Simulation paused. Compiling session data...")
                    GAME_STATE = "POST_SESSION"
                else:
                    running = False

        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = event.pos

            if GAME_STATE == "POST_SESSION":
                running = False

            if GAME_STATE in ["START", "SELECT"]:
                if quit_btn_rect.collidepoint(mouse_pos):
                    running = False

            if GAME_STATE == "START":
                if start_button_rect.collidepoint(mouse_pos):
                    GAME_STATE = "SELECT"
            
            elif GAME_STATE == "SELECT":
                if badrul_btn_rect.collidepoint(mouse_pos):
                    player = Pedestrian(CHARACTERS["Badrul"])
                    session_frames = 0
                    total_dashes_used = 0
                    GAME_STATE = "RUNNING"
                elif mrittika_btn_rect.collidepoint(mouse_pos):
                    player = Pedestrian(CHARACTERS["Mrittika"])
                    session_frames = 0
                    total_dashes_used = 0
                    GAME_STATE = "RUNNING"

    # --- Game Logic ---
    if GAME_STATE == "RUNNING" and player is not None:
        # Increment time
        session_frames += 1

        keys = pygame.key.get_pressed()
        
        # Track Dash Usage (only count if space is pressed and cooldown is ready)
        if keys[pygame.K_SPACE] and player.current_dash_cooldown == 0:
            total_dashes_used += 1

        player.move(keys)
        spawner.update()

        if player.rect.y < FAR_LANE_Y:
            print("TARGET ZONE BREACHED.")
            round_manager.record_win()
            player.reset_position()
            spawner.vehicles.clear()

        for v in spawner.vehicles:
            if player.rect.colliderect(v.rect):
                print(f"COLLISION DETECTED. Subject {player.name} terminated.")
                round_manager.record_loss()
                player.reset_position()
                spawner.vehicles.clear()

    # --- Drawing ---
    screen.fill(COLOR_BG)

    if GAME_STATE == "START":
        screen.blit(start_bg, (0, 0))
        draw_quit_button(screen)

    elif GAME_STATE == "SELECT":
        screen.blit(selection_bg, (0, 0))
        draw_quit_button(screen)
        
        mouse_pos = pygame.mouse.get_pos()
        if badrul_btn_rect.collidepoint(mouse_pos):
            draw_lore_card(screen, "Badrul")
        elif mrittika_btn_rect.collidepoint(mouse_pos):
            draw_lore_card(screen, "Mrittika")

    elif GAME_STATE == "RUNNING" and player is not None:
        road.draw(screen)
        spawner.draw(screen)
        player.draw(screen)

        # # --- LIVE TELEMETRY HUD ---
        # hud_width = 430  # Increased from 300 to fit the long text
        # hud_height = 140 # Increased from 110 for better padding
        
        # # Draw a semi-transparent dark box
        # hud_bg = pygame.Surface((hud_width, hud_height), pygame.SRCALPHA)
        # hud_bg.fill((10, 10, 15, 200))
        # screen.blit(hud_bg, (10, 5))
        # pygame.draw.rect(screen, (0, 255, 127), (10, 10, hud_width, hud_height), 2, border_radius=3) 
        
        # # Convert frames to mm:ss
        # total_seconds = session_frames // FPS
        # mins = total_seconds // 60
        # secs = total_seconds % 60
        
        # telemetry_data = [
        #     f"SUBJECT: {player.name.upper()}",
        #     f"VELOCITY: X:{player.vel_x:.1f} Y:{player.vel_y:.1f}",
        #     f"DASHES DEPLOYED: {total_dashes_used}",
        #     f"CYCLE: {round_manager.current_round} | SUCCESS: {round_manager.wins} | FAIL: {round_manager.losses}",
        #     f"T-PLUS: {mins:02d}:{secs:02d}"
        # ]
        
        # for i, text in enumerate(telemetry_data):
        #     hud_surf = font_telemetry.render(text, True, (0, 255, 127)) 
        #     # Increased line spacing from 18 to 22 so they don't overlap
        #     screen.blit(hud_surf, (20, 20 + (i * 22)))

    # --- POST-SESSION ANALYTICS SCREEN ---
    elif GAME_STATE == "POST_SESSION":
        # Draw Dark Background + Radar Grid
        screen.fill((10, 15, 15))
        draw_radar_grid(screen)
        
        # Title
        title_surf = font_title.render("SIMULATION DATA LOG", True, (0, 255, 127))
        screen.blit(title_surf, (SCREEN_WIDTH // 2 - title_surf.get_width() // 2, 60))
        
        # Calculate Math
        total_attempts = round_manager.wins + round_manager.losses
        survival_rate = (round_manager.wins / total_attempts * 100) if total_attempts > 0 else 0.0
        
        total_sec = session_frames // FPS
        m = total_sec // 60
        s = total_sec % 60
        
        # Define the text lines
        stats_lines = [
            f"> Subject Profile.......... {player.name.upper()}",
            f"> Total Time Elapsed....... {m:02d}:{s:02d}",
            f"> Kinetic Dashes Used...... {total_dashes_used}",
            f"> Total Rounds Played...... {total_attempts}",
            f"> Wins..................... {round_manager.wins}",
            f"> Losses................... {round_manager.losses}",
            f"> Projected Survival Rate.. {survival_rate:.1f}%"
        ]
        
        # Draw the stats in a terminal style
        start_y = 160
        for i, line in enumerate(stats_lines):
            color = (200, 220, 200) # Terminal off-white
            
            # Highlight Survival Rate
            if "Survival Rate" in line:
                if survival_rate >= 50.0:
                    color = (0, 255, 127) # Green if good
                else:
                    color = (255, 50, 50) # Red if bad
                    
            stat_surf = font_stats.render(line, True, color)
            # Left align like a computer terminal, instead of center
            screen.blit(stat_surf, (SCREEN_WIDTH // 2 - 250, start_y + (i * 45)))
            
        # Draw exit instruction
        exit_surf = font_telemetry.render("PRESS [ESC] OR CLICK ANYWHERE TO TERMINATE", True, (0, 255, 127))
        # Flash the text based on time for an old CRT monitor effect
        if (pygame.time.get_ticks() // 500) % 2 == 0: 
            screen.blit(exit_surf, (SCREEN_WIDTH // 2 - exit_surf.get_width() // 2, SCREEN_HEIGHT - 60))

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()
sys.exit()