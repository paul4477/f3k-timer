import signal
import time
import pygame
import os

# --- Setup pygame ---
pygame.init()
pygame.mixer.init()

# Load an example sound (replace with your own file path)
sound_path = os.path.join(os.path.dirname(__file__), "../assets/sounds/en/0059.wav")
if not os.path.exists(sound_path):
    raise FileNotFoundError(f"Sound file not found: {sound_path}")

sound = pygame.mixer.Sound(sound_path)
sound.play()
time.sleep(5)

pygame.quit()
