import pygame
import sys
from config import *
from road import Road
from pedestrian import Pedestrian
from spawner import Spawner
from characters import CHARACTERS

# 1. Initialize
pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Stayin' Alive")
clock = pygame.time.Clock()

# 2. Setup World
road = Road()
spawner = Spawner()

# 3. Simple Character Select (Hardcoded for now - Change "Badrul" to "Mrittika" to test)
player = Pedestrian(CHARACTERS["Mrittika"])

# 4. Game Loop
running = True
while running:
    # A. Input
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    keys = pygame.key.get_pressed()
    player.move(keys)
    # CHECK WIN CONDITION
    if player.rect.y < FAR_LANE_Y:  # If player is above the Far Lane
        print("YOU SURVIVED! Reached the footpath.")
        # Reset player to start
        player.rect.y = SCREEN_HEIGHT - 60
        player.rect.x = SCREEN_WIDTH // 2

    # B. Updates
    spawner.update()

    # C. Collision Check (Simple)
    for v in spawner.vehicles:
        if player.rect.colliderect(v.rect):
            print(f"COLLISION! {player.name} hit by traffic!")
            # Reset player
            player.rect.y = SCREEN_HEIGHT - 60

    # D. Draw
    screen.fill(COLOR_BG)
    road.draw(screen)
    spawner.draw(screen)
    player.draw(screen)

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()
sys.exit()