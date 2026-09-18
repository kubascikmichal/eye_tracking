import pygame
import random
import pylsl
from pylsl import StreamInfo, StreamOutlet
import numpy as np

def main():
    # --- Config ---
    N = 8
    DOT_TIME = 1600
    BG = (0, 0, 0)
    DOT = (255, 255, 255)
    RADIUS = 20

    WIDTH, HEIGHT = 1920, 1080
    PAD = 200

    # --- Setup ---
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Simple Dot Sequence")
    clock = pygame.time.Clock()

    random.seed(10)

    def rand_pos():
        x = random.randint(PAD, WIDTH - PAD)
        y = random.randint(PAD, HEIGHT - PAD)
        return (x, y)

    dots = [rand_pos() for _ in range(N)]

    # LSL connection to BrainAccessBoard
    info = StreamInfo(
        name="Visual_test",
        type="Dots",
        channel_count=2,
        nominal_srate=0.625,
        channel_format="float32",
    )
    channels = info.desc().append_child("channels")
    for label in ["Coordinate_X", "Coordinate_Y"]:
        ch = channels.append_child("channel")
        ch.append_child_value("label", label)
    outlet = StreamOutlet(info)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        if not running:
            break

        for i in range(N):
            screen.fill(BG)
            pygame.draw.circle(screen, DOT, dots[i], RADIUS)

            stamp = pylsl.local_clock()
            sample = np.array(dots[i])
            print(sample)
            print(stamp)
            # sending data over lsl
            outlet.push_sample(sample, stamp)

            pygame.display.flip()

            # Wait for DOT_TIME, but allow quit
            t0 = pygame.time.get_ticks()
            while pygame.time.get_ticks() - t0 < DOT_TIME:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                        break
                if not running:
                    break
                clock.tick(60)

    pygame.quit()

if __name__ == "__main__":
    main()
