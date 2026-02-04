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
pygame.display.set_caption("Project: Stayin' Alive (Boardbazar)")
clock = pygame.time.Clock()

# 2. Load Assets
try:
    start_bg = pygame.image.load("start.jpg")
    # Scale it to fit the window perfectly
    start_bg = pygame.transform.scale(start_bg, (SCREEN_WIDTH, SCREEN_HEIGHT))
except FileNotFoundError:
    print("Error: start.jpg not found. Please put the image in the project folder.")
    sys.exit()

# 3. Define the "Start Button" Hitbox
# Based on your image, the button is roughly in the center-bottom.
# Let's define an invisible rectangle over that area to detect clicks.
# (Adjust these numbers if the button area feels off)
button_width = 200
button_height = 80
button_x = (SCREEN_WIDTH // 2) - (button_width // 2)
button_y = (SCREEN_HEIGHT // 2) + 50  # Slightly below center
start_button_rect = pygame.Rect(button_x, button_y, button_width, button_height)

# 4. Setup Game World (But don't run it yet)
road = Road()
spawner = Spawner()
player = Pedestrian(CHARACTERS["Badrul"])

# Game States
GAME_STATE = "WAITING"  # Options: WAITING, RUNNING, GAME_OVER

running = True
while running:
    # --- Input Handling ---
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        # Check for Mouse Clicks
        if event.type == pygame.MOUSEBUTTONDOWN:
            if GAME_STATE == "WAITING":
                # Get mouse position
                mouse_pos = event.pos
                # Check if they clicked the invisible button rectangle
                if start_button_rect.collidepoint(mouse_pos):
                    print("Start Button Clicked!")
                    GAME_STATE = "RUNNING"

    # --- Game Logic ---
    if GAME_STATE == "RUNNING":
        keys = pygame.key.get_pressed()
        player.move(keys)
        spawner.update()

        # Check Win Condition
        if player.rect.y < FAR_LANE_Y:
            print("YOU SURVIVED! Reached the footpath.")
            player.rect.y = SCREEN_HEIGHT - 60
            player.rect.x = SCREEN_WIDTH // 2

        # Check Collision
        for v in spawner.vehicles:
            if player.rect.colliderect(v.rect):
                print(f"COLLISION! {player.name} hit by traffic!")
                player.rect.y = SCREEN_HEIGHT - 60

    # --- Drawing ---
    screen.fill(COLOR_BG)

    if GAME_STATE == "WAITING":
        # Draw the Start Screen Image
        screen.blit(start_bg, (0, 0))

        # Debug: Uncomment this line to see where the invisible button is
        # pygame.draw.rect(screen, (255, 0, 0), start_button_rect, 2)

    elif GAME_STATE == "RUNNING":
        road.draw(screen)
        spawner.draw(screen)
        player.draw(screen)

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()
sys.exit()