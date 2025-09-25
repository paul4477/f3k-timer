import signal
import time
import pygame
import os

# --- Setup pygame ---
pygame.init()
pygame.mixer.init()
clock = pygame.time.Clock()

# Load an example sound (replace with your own file path)
sound_path = os.path.join(os.path.dirname(__file__), "../assets/sounds/en/0058.wav")
sound_path_seconds = os.path.join(os.path.dirname(__file__), "../assets/sounds/en/second1.wav")
if not os.path.exists(sound_path):
    raise FileNotFoundError(f"Sound file not found: {sound_path}")

sound = pygame.mixer.Sound(sound_path)
sound2 = pygame.mixer.Sound(sound_path_seconds)
channel = pygame.mixer.Channel(1)
#length_59 = sound.get_length()

# Define custom event types
PLAY_EVENT = pygame.USEREVENT + 1

def handle_play_signal(signum, frame):
    """Signal handler for SIGUSR1 that posts a Pygame PLAY event."""
    pygame.event.post(pygame.event.Event(PLAY_EVENT))

def handle_stop_signal(signum, frame):
    """Signal handler for SIGTERM that posts a QUIT event."""
    pygame.event.post(pygame.event.Event(pygame.QUIT))

# Register signal handlers
signal.signal(signal.SIGUSR1, handle_play_signal)
signal.signal(signal.SIGTERM, handle_stop_signal)

# --- Main loop ---
print("Service started. Waiting for signals...")
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            print("Received QUIT signal → shutting down gracefully.")
            running = False
        elif event.type == PLAY_EVENT:
            print("Received PLAY event from signal → playing sound!")
            #sound.play()
            channel.play(sound)
            print("Received PLAY event from signal → queueing sound!")
            channel.queue(sound2)

    clock.tick(4)

pygame.quit()
print("Service stopped.")


