import pygame
import json
import os

MAP_FILE = os.path.join("..", "map_generators", "map_data.json")

# Stałe
WIDTH, HEIGHT = 1200, 800
BG_COLOR = (30, 30, 30)
INNER_COLOR = (50, 50, 200)
OUTER_COLOR = (200, 50, 50)
TRACK_COLOR = (50, 200, 50)
FINISH_COLOR = (255, 255, 0)

def load_map(file_path):
    with open(file_path, "r") as f:
        data = json.load(f)
    return data

def draw_track(screen, data):
    inner = data["inner_points"]
    outer = data["outer_points"]
    finish = data["finish_line"]["point"]

    # Rysowanie linii zewnętrznej
    pygame.draw.lines(screen, OUTER_COLOR, True, [(int(x), int(y)) for x, y in outer], 5)

    # Rysowanie linii wewnętrznej
    pygame.draw.lines(screen, INNER_COLOR, True, [(int(x), int(y)) for x, y in inner], 5)

    # Wypełnienie obszaru między liniami
    pygame.draw.polygon(screen, TRACK_COLOR, [(int(x), int(y)) for x, y in outer])

    # Linia mety
    pygame.draw.circle(screen, FINISH_COLOR, (int(finish[0]), int(finish[1])), 5)

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Wyścigówka")

    clock = pygame.time.Clock()
    data = load_map(MAP_FILE)

    running = True
    while running:
        screen.fill(BG_COLOR)
        draw_track(screen, data)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

if __name__ == "__main__":
    main()
