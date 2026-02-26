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

# 4. Setup Game World (single, clean initialization)
round_manager = RoundManager()
road    = Road()
spawner = Spawner(round_manager)
player  = None

# 5. Game State
# Flow: START -> SELECT -> RUNNING
GAME_STATE = "START"

running = True
while running:

    # --- Input Handling ---
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = event.pos

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

        # Check Win Condition
        if player.rect.y < FAR_LANE_Y:
            print("YOU SURVIVED! Reached the footpath.")
            round_manager.record_win()
            player.reset_position()
            spawner.vehicles.clear()

        # Check Collision
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
        # pygame.draw.rect(screen, (255, 0, 0), start_button_rect, 2)  # Debug

    elif GAME_STATE == "SELECT":
        screen.blit(selection_bg, (0, 0))
        # pygame.draw.rect(screen, (0, 255, 0), badrul_btn_rect, 2)    # Debug
        # pygame.draw.rect(screen, (255, 0, 255), mrittika_btn_rect, 2) # Debug

    elif GAME_STATE == "RUNNING" and player is not None:
        road.draw(screen)
        spawner.draw(screen)
        player.draw(screen)

        # HUD: Round info top-left
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