#!/usr/bin/env python
# Simple Key Test Script
import pygame
import sys

# Initialize pygame
pygame.init()

# Create a simple window
screen = pygame.display.set_mode((800, 600))
pygame.display.set_caption("Key Test")

# Font for displaying text
font = pygame.font.SysFont('monospace', 24)

def draw_text(surface, text, color, x, y):
    text_surface = font.render(str(text), True, color)
    surface.blit(text_surface, (x, y))

# Main loop
running = True
last_key = "None"
keys_pressed = []

while running:
    # Process events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            
        elif event.type == pygame.KEYDOWN:
            key_name = pygame.key.name(event.key)
            last_key = key_name
            
            # Store the last 5 keys pressed
            keys_pressed.append(key_name)
            if len(keys_pressed) > 5:
                keys_pressed.pop(0)
            
            # Special exit case - Esc key
            if event.key == pygame.K_ESCAPE:
                running = False
                
            # Just print info for debugging
            print(f"Key pressed: {key_name} (keycode: {event.key})")
    
    # Clear the screen
    screen.fill((0, 0, 0))
    
    # Display the last key pressed
    draw_text(screen, f"Last key pressed: {last_key}", (255, 255, 255), 50, 50)
    
    # Display the last 5 keys
    draw_text(screen, "Recent keys:", (255, 255, 255), 50, 100)
    for i, key in enumerate(keys_pressed):
        draw_text(screen, key, (200, 200, 255), 50, 150 + i * 30)
    
    # Instructions
    draw_text(screen, "Press any key to test", (255, 200, 200), 50, 500)
    draw_text(screen, "Press Esc to exit", (255, 200, 200), 50, 530)
    
    # Update the display
    pygame.display.flip()

# Quit pygame
pygame.quit()
sys.exit()