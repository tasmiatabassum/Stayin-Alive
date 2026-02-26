# main.py
import pygame
import sys
from config import *
from road import Road
from pedestrian import Pedestrian
from spawner import Spawner
from characters import CHARACTERS

# 1. Initialize Pygame
pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Stayin' Alive (Boardbazar)")
clock = pygame.time.Clock()

# 2. Load Assets
try:
    start_bg = pygame.image.load("start.jpg")
    # Scale it to fit the window perfectly
    start_bg = pygame.transform.scale(start_bg, (SCREEN_WIDTH, SCREEN_HEIGHT))
except FileNotFoundError:
    print("Error: start.jpg not found. Please put the image in the project folder.")
    sys.exit()


try:
    # Load your new character selection image
    selection_bg = pygame.image.load("selection.jpg")
    selection_bg = pygame.transform.scale(selection_bg, (SCREEN_WIDTH, SCREEN_HEIGHT))
except FileNotFoundError:
    print("Error: selection.jpg not found. Please put the image in the project folder.")
    sys.exit()

# 3. Define Hitboxes (Invisible Clickable Areas)

# A. Start Screen Hitbox (Adjusted for typical center placement)
start_button_rect = pygame.Rect((SCREEN_WIDTH // 2) - 100, (SCREEN_HEIGHT // 2) + 50, 200, 80)

# B. Character Selection Hitboxes 
# Based on the image provided, the buttons are side-by-side in the lower half.
btn_w = 200
btn_h = 70
btn_y = (SCREEN_HEIGHT // 2) + 130  # Adjust this if the hitboxes don't line up vertically!

badrul_btn_rect = pygame.Rect((SCREEN_WIDTH // 2) - btn_w - 20, btn_y, btn_w, btn_h)
mrittika_btn_rect = pygame.Rect((SCREEN_WIDTH // 2) + 20, btn_y, btn_w, btn_h)

# 4. Define the "Start Button" Hitbox
button_width = 200
button_height = 80
button_x = (SCREEN_WIDTH // 2) - (button_width // 2)
button_y = (SCREEN_HEIGHT // 2) + 50  # Slightly below center
start_button_rect = pygame.Rect(button_x, button_y, button_width, button_height)

# 5. Setup Game World
road = Road()
spawner = Spawner() 
player = None 

# --- New Multi-Step Game States ---
# Flow: START -> SELECT -> RUNNING
GAME_STATE = "START"  

running = True
while running:
    # --- Input Handling ---
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        # Check for Mouse Clicks
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = event.pos
            
            # State 1: On the Start Screen
            if GAME_STATE == "START":
                if start_button_rect.collidepoint(mouse_pos):
                    print("Moving to Character Selection...")
                    GAME_STATE = "SELECT"
            
            # State 2: On the Selection Screen
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
            player.reset_position()
            spawner.vehicles.clear()

        # Check Collision
        for v in spawner.vehicles:
            if player.rect.colliderect(v.rect):
                print(f"COLLISION! {player.name} hit by traffic!")
                player.reset_position()
                spawner.vehicles.clear()

    # --- Drawing ---
    screen.fill(COLOR_BG)

    if GAME_STATE == "START":
        screen.blit(start_bg, (0, 0))
        # Debug: Uncomment this line to see the invisible start button hitbox
        # pygame.draw.rect(screen, (255, 0, 0), start_button_rect, 2)

    elif GAME_STATE == "SELECT":
        screen.blit(selection_bg, (0, 0))
        # Debug: Uncomment these lines to align the hitboxes perfectly with your image!
        # pygame.draw.rect(screen, (0, 255, 0), badrul_btn_rect, 2)
        # pygame.draw.rect(screen, (255, 0, 255), mrittika_btn_rect, 2)

    elif GAME_STATE == "RUNNING" and player is not None:
        road.draw(screen)
        spawner.draw(screen)
        player.draw(screen)

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()
sys.exit()