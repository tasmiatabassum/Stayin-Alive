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
pygame.display.set_caption("Stayin' Alive (Boardbazar)")
clock = pygame.time.Clock()

# --- Font updated to Gothic 25 ---
font_lore = pygame.font.SysFont("Gothic", 25)

# 2. Load Assets
try:
    start_bg = pygame.image.load("start.jpg")
    start_bg = pygame.transform.scale(start_bg, (SCREEN_WIDTH, SCREEN_HEIGHT))
except FileNotFoundError:
    print("Error: start.jpg not found.")
    sys.exit()

try:
    selection_bg = pygame.image.load("selection.jpg")
    selection_bg = pygame.transform.scale(selection_bg, (SCREEN_WIDTH, SCREEN_HEIGHT))
except FileNotFoundError:
    print("Error: selection.jpg not found.")
    sys.exit()

# 3. Define Hitboxes

# A. Start Screen
start_button_rect = pygame.Rect((SCREEN_WIDTH // 2) - 100, (SCREEN_HEIGHT // 2) + 50, 200, 80)

# B. Character Selection
btn_w = 200
btn_h = 70
btn_y = (SCREEN_HEIGHT // 2) + 130
badrul_btn_rect   = pygame.Rect((SCREEN_WIDTH // 2) - btn_w - 20, btn_y, btn_w, btn_h)
mrittika_btn_rect = pygame.Rect((SCREEN_WIDTH // 2) + 20,         btn_y, btn_w, btn_h)

# C. NEW: Quit Button (Top Right Corner)
quit_btn_rect = pygame.Rect(SCREEN_WIDTH - 120, 20, 100, 40)

# 4. Setup Game World (single, clean initialization)
round_manager = RoundManager()
road    = Road()
spawner = Spawner(round_manager)
player  = None

# 5. Game State
# Flow: START -> SELECT -> RUNNING
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
        perks = "PERK: High Speed  |  FLAW: Slippery Shoes  |  DASH: Massive Leap"
    else:
        perks = "PERK: Tight Controls  |  FLAW: Slow Top Speed  |  DASH: Short Hop"
        
    lore_text = f"{char_data['bio']}\n{perks}"
    draw_text_wrapped(screen, lore_text, (0, 0, 0), lore_rect, font_lore)

# --- NEW: Draw Quit Button Function ---
def draw_quit_button(screen):
    # Draw a nice red rounded rectangle
    pygame.draw.rect(screen, (220, 50, 50), quit_btn_rect, border_radius=10)
    # Add the text
    quit_text = font_lore.render("QUIT", True, (255, 255, 255))
    text_rect = quit_text.get_rect(center=quit_btn_rect.center)
    screen.blit(quit_text, text_rect)

running = True
while running:

    # --- Input Handling ---
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        # --- NEW: Press ESC to quit from anywhere ---
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                print("ESC pressed. Quitting game...")
                running = False

        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = event.pos

            # --- NEW: Check if the visual Quit button was clicked ---
            if GAME_STATE in ["START", "SELECT"]:
                if quit_btn_rect.collidepoint(mouse_pos):
                    print("Quit button clicked. Exiting...")
                    running = False

            if GAME_STATE == "START":
                if start_button_rect.collidepoint(mouse_pos):
                    print("Moving to Character Selection...")
                    GAME_STATE = "SELECT"
            
            elif GAME_STATE == "SELECT":
                if badrul_btn_rect.collidepoint(mouse_pos):
                    print("Badrul Selected! Game Starting.")
                    player = Pedestrian(CHARACTERS["Badrul"])
                    GAME_STATE = "RUNNING"

                elif mrittika_btn_rect.collidepoint(mouse_pos):
                    print("Mrittika Selected! Game Starting.")
                    player = Pedestrian(CHARACTERS["Mrittika"])
                    GAME_STATE = "RUNNING"

    # --- Game Logic ---
    if GAME_STATE == "RUNNING" and player is not None:
        keys = pygame.key.get_pressed()
        player.move(keys)
        spawner.update()

        if player.rect.y < FAR_LANE_Y:
            print("YOU SURVIVED! Reached the footpath.")
            round_manager.record_win()
            player.reset_position()
            spawner.vehicles.clear()

        for v in spawner.vehicles:
            if player.rect.colliderect(v.rect):
                print(f"COLLISION! {player.name} hit by traffic!")
                round_manager.record_loss()
                player.reset_position()
                spawner.vehicles.clear()

    # --- Drawing ---
    screen.fill(COLOR_BG)

    if GAME_STATE == "START":
        screen.blit(start_bg, (0, 0))
        draw_quit_button(screen) # Draw the quit button on the start screen

    elif GAME_STATE == "SELECT":
        screen.blit(selection_bg, (0, 0))
        draw_quit_button(screen) # Draw the quit button on the select screen
        
        mouse_pos = pygame.mouse.get_pos()
        
        if badrul_btn_rect.collidepoint(mouse_pos):
            draw_lore_card(screen, "Badrul")
            
        elif mrittika_btn_rect.collidepoint(mouse_pos):
            draw_lore_card(screen, "Mrittika")

    elif GAME_STATE == "RUNNING" and player is not None:
        road.draw(screen)
        spawner.draw(screen)
        player.draw(screen)

        font = pygame.font.SysFont("Arial", 22, bold=True)
        hud = font.render(
            f"Round: {round_manager.current_round}  |  W: {round_manager.wins}  L: {round_manager.losses}",
            True, (255, 255, 255)
        )
        screen.blit(hud, (10, 10))

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()
sys.exit()