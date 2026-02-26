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

# --- NEW: Font updated to Inter Bold 36 ---
# Note: If "Inter" isn't installed on your PC, Pygame will use a default sans-serif font.
font_lore = pygame.font.SysFont("Gothic", 25)

# 2. Load Assets
try:
    start_bg = pygame.image.load("start.jpg")
    start_bg = pygame.transform.scale(start_bg, (SCREEN_WIDTH, SCREEN_HEIGHT))
except FileNotFoundError:
    print("Error: start.jpg not found. Please put the image in the project folder.")
    sys.exit()

try:
    selection_bg = pygame.image.load("selection.jpg")
    selection_bg = pygame.transform.scale(selection_bg, (SCREEN_WIDTH, SCREEN_HEIGHT))
except FileNotFoundError:
    print("Error: selection.jpg not found. Please put the image in the project folder.")
    sys.exit()

# 3. Define Hitboxes (Invisible Clickable Areas)
start_button_rect = pygame.Rect((SCREEN_WIDTH // 2) - 100, (SCREEN_HEIGHT // 2) + 50, 200, 80)

btn_w = 200
btn_h = 70
btn_y = (SCREEN_HEIGHT // 2) + 160  

badrul_btn_rect = pygame.Rect((SCREEN_WIDTH // 2) - btn_w - 20, btn_y, btn_w, btn_h)
mrittika_btn_rect = pygame.Rect((SCREEN_WIDTH // 2) + 20, btn_y, btn_w, btn_h)

# 4. Setup Game World
road = Road()
spawner = Spawner() 
player = None 

GAME_STATE = "START" 

#  Text Wrapping Helper Function ---
def draw_text_wrapped(surface, text, color, rect, font):
    lines = []
    
    # First, split the text by manual line breaks (\n)
    for block in text.split('\n'):
        words = block.split(' ')
        current_line = ""
        
        # Then, wrap the words so they don't hit the box edges
        for word in words:
            test_line = current_line + word + " "
            if font.size(test_line)[0] < rect.width - 40: # 40px padding
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word + " "
        lines.append(current_line)

    # Center all the generated lines vertically in the box
    total_height = len(lines) * font.get_linesize()
    start_y = rect.y + (rect.height - total_height) // 2

    # Draw each line centered horizontally
    for i, line in enumerate(lines):
        text_surf = font.render(line.strip(), True, color)
        text_rect = text_surf.get_rect(center=(rect.centerx, start_y + i * font.get_linesize() + text_surf.get_height() // 2))
        surface.blit(text_surf, text_rect)

# --- REDESIGNED: Lore Box Function ---
def draw_lore_card(screen, char_key):
    char_data = CHARACTERS[char_key]
    
    # 1. Define the Box 
    box_width = 850      # Made wider to fit the long perk text
    box_height = 130     # Made taller to fit 2-3 lines of text
    box_x = (SCREEN_WIDTH // 2) - (box_width // 2)
    box_y = SCREEN_HEIGHT - box_height - 15 
    
    lore_rect = pygame.Rect(box_x, box_y, box_width, box_height)
    
    # 2. Draw the Box background
    COLOR_LORE_BOX = (20, 145, 195) 
    pygame.draw.rect(screen, COLOR_LORE_BOX, lore_rect, border_radius=20)
    
    # 3. Bring back the full Perks
    if char_key == "Badrul":
        perks = "PERK: High Speed  |  FLAW: Slippery Shoes  |  DASH: Massive Leap"
    else:
        perks = "PERK: Tight Controls  |  FLAW: Slow Top Speed  |  DASH: Short Hop"
        
    # Combine the Bio and Perks with a line break (\n)
    lore_text = f"{char_data['bio']}\n{perks}"
    
    # 4. Draw the wrapped text in Black
    draw_text_wrapped(screen, lore_text, (0, 0, 0), lore_rect, font_lore)

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

        if player.rect.y < FAR_LANE_Y:
            print("YOU SURVIVED! Reached the footpath.")
            player.reset_position()
            spawner.vehicles.clear()

        for v in spawner.vehicles:
            if player.rect.colliderect(v.rect):
                print(f"COLLISION! {player.name} hit by traffic!")
                player.reset_position()
                spawner.vehicles.clear()

    # --- Drawing ---
    screen.fill(COLOR_BG)

    if GAME_STATE == "START":
        screen.blit(start_bg, (0, 0))

    elif GAME_STATE == "SELECT":
        screen.blit(selection_bg, (0, 0))
        mouse_pos = pygame.mouse.get_pos()
        
        # Hover logic to display the new lore box
        if badrul_btn_rect.collidepoint(mouse_pos):
            draw_lore_card(screen, "Badrul")
            
        elif mrittika_btn_rect.collidepoint(mouse_pos):
            draw_lore_card(screen, "Mrittika")

    elif GAME_STATE == "RUNNING" and player is not None:
        road.draw(screen)
        spawner.draw(screen)
        player.draw(screen)

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()
sys.exit()