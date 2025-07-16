import pygame
import json
import os
import math

MAP_FILE = os.path.join("..", "map_generators", "map_data.json")

# Stałe
WIDTH, HEIGHT = 1200, 800
BG_COLOR = (30, 30, 30)
INNER_COLOR = (50, 50, 200)
OUTER_COLOR = (200, 50, 50)
TRACK_COLOR = (50, 200, 50)
FINISH_COLOR = (255, 255, 0)

class Car:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.angle = 0
        self.speed = 0

        self.image = pygame.Surface((30, 20), pygame.SRCALPHA)
        self.image.fill((255, 0, 0))

        # PHYSICS
        self.max_speed = 10
        self.acceleration = 0.2
        self.friction = 0.05
        self.turn_slowdown = 0.1

    def update(self):
        turning = False
        # obsługa pygame klawiatury
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            self.angle += 5
            turning = True
        if keys[pygame.K_RIGHT]:
            self.angle -= 5
            turning = True
        if keys[pygame.K_UP]:
            self.speed += 1
        if keys[pygame.K_DOWN]:
            self.speed -= 1

        if not keys[pygame.K_UP] and not keys[pygame.K_DOWN]:
            if self.speed > 0:
                self.speed = max(self.speed - self.friction, 0)
            elif self.speed < 0:
                self.speed = min(self.speed + self.friction, 0)

        if turning:
            if self.speed > 0:
                self.speed = max(self.speed - self.turn_slowdown, 0)
            elif self.speed < 0:
                self.speed = min(self.speed + self.turn_slowdown, 0)
        # Aktualizacja pozycji samochodu
        self.x += self.speed * math.cos(math.radians(self.angle))
        self.y -= self.speed * math.sin(math.radians(self.angle))



    def draw(self, screen):
        car_rect = pygame.Rect(self.x - 15, self.y - 10, 30, 20)
        rotated_car = pygame.transform.rotate(pygame.Surface(car_rect.size), -self.angle)
        rotated_car.fill((255, 0, 0))
        rotated_rect = rotated_car.get_rect(center=car_rect.center)
        screen.blit(rotated_car, rotated_rect.topleft)

    def get_mask(self):
        rotated_image = pygame.transform.rotate(self.image, -self.angle)
        return pygame.mask.from_surface(rotated_image), rotated_image.get_rect(center=(self.x, self.y))


def load_map(file_path):
    with open(file_path, "r") as f:
        data = json.load(f)
    return data

def get_scaling_params(points_list, width, height, scale_factor=1.0):
    # Połącz wszystkie punkty z list
    all_points = [p for points in points_list for p in points]
    min_x = min(p[0] for p in all_points)
    max_x = max(p[0] for p in all_points)
    min_y = min(p[1] for p in all_points)
    max_y = max(p[1] for p in all_points)

    scale_x = width / (max_x - min_x)
    scale_y = height / (max_y - min_y)
    scale = min(scale_x, scale_y) * scale_factor
    return min_x, min_y, scale


def scale_points(points, min_x, min_y, scale):
    return [(int((x - min_x) * scale), int((y - min_y) * scale)) for x, y in points]


def draw_track(screen, data):
    outer_raw = data["outer_points"]
    inner_raw = data["inner_points"]

    min_x, min_y, scale = get_scaling_params([outer_raw, inner_raw], WIDTH, HEIGHT, scale_factor=0.9)
    outer = scale_points(outer_raw, min_x, min_y, scale)
    inner = scale_points(inner_raw, min_x, min_y, scale)
    finish = data["finish_line"]["point"]
    finish_scaled = scale_points([finish], min_x, min_y, scale)[0]

    # pygame.draw.polygon(screen, TRACK_COLOR, outer + inner[::-1])
    pygame.draw.polygon(screen, TRACK_COLOR, outer)
    pygame.draw.polygon(screen, BG_COLOR, inner)
    pygame.draw.lines(screen, OUTER_COLOR, True, outer, 5)
    pygame.draw.lines(screen, INNER_COLOR, True, inner, 5)
    pygame.draw.circle(screen, FINISH_COLOR, finish_scaled, 5)

    return outer, inner


# def check_collision(car, outer_points, inner_points):
#     # Sprawdź kolizję z linią zewnętrzną
#     for i in range(len(outer_points)):
#         next_i = (i + 1) % len(outer_points)
#         if line_collision(car.x, car.y, outer_points[i], outer_points[next_i]):
#             print("Kolizja z linią zewnętrzną!")
#             return
#
#     # Sprawdź kolizję z linią wewnętrzną
#     for i in range(len(inner_points)):
#         next_i = (i + 1) % len(inner_points)
#         if line_collision(car.x, car.y, inner_points[i], inner_points[next_i]):
#             print("Kolizja z linią wewnętrzną!")
#             return



def point_in_polygon(x, y, polygon):
    # Algorytm ray-casting
    num = len(polygon)
    j = num - 1
    inside = False

    for i in range(num):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if ((yi > y) != (yj > y)) and \
                (x < (xj - xi) * (y - yi) / (yj - yi + 1e-10) + xi):
            inside = not inside
        j = i

    return inside

def check_collision(car, outer_polygon, inner_polygon):
    cx, cy = int(car.x), int(car.y)
    if point_in_polygon(cx, cy, outer_polygon) and not point_in_polygon(cx, cy, inner_polygon):
        return False  # Jest na torze
    return True  # Kolizja

def generate_track_mask(data, width, height):
    # Pobierz punkty toru
    outer_raw = data["outer_points"]
    inner_raw = data["inner_points"]

    # Oblicz skalowanie i przeskaluj punkty
    min_x, min_y, scale = get_scaling_params([outer_raw, inner_raw], width, height, scale_factor=0.9)
    outer = scale_points(outer_raw, min_x, min_y, scale)
    inner = scale_points(inner_raw, min_x, min_y, scale)

    # Stwórz powierzchnię toru
    track_surface = pygame.Surface((width, height), pygame.SRCALPHA)
    track_surface.fill((0, 0, 0, 0))  # Przezroczyste tło

    # Narysuj tor jako biały obszar
    pygame.draw.polygon(track_surface, (255, 255, 255), outer)  # Zewnętrzny wielokąt
    pygame.draw.polygon(track_surface, (0, 0, 0), inner)  # Wewnętrzny wielokąt (dziura)

    # Wygeneruj maskę z powierzchni
    track_mask = pygame.mask.from_surface(track_surface)
    return track_mask

def check_if_on_track(car, track_mask, inner_polygon, outer_polygon):
    # Pobierz maskę samochodu
    car_mask = pygame.mask.from_surface(car.image)
    car_rect = car.image.get_rect(center=(car.x, car.y))

    # Oblicz offset między maską toru a maską samochodu
    offset = (car_rect.left - 0, car_rect.top - 0)  # Zakładamy, że maska toru zaczyna się od (0, 0)

    # Sprawdź, czy maski się pokrywają
    overlap = track_mask.overlap(car_mask, offset)
    if overlap is None:
        return False

    if point_in_polygon(car.x, car.y, inner_polygon):
        return False

    if not point_in_polygon(car.x, car.y, outer_polygon):
        return False  # Samochód jest poza torem

    return True

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Wyścigówka")

    clock = pygame.time.Clock()
    data = load_map(MAP_FILE)

    # Pobierz pozycję linii startu
    finish_line = data["finish_line"]["point"]
    min_x, min_y, scale = get_scaling_params([data["outer_points"], data["inner_points"]], WIDTH, HEIGHT,
                                             scale_factor=0.9)
    finish_scaled = scale_points([finish_line], min_x, min_y, scale)[0]

    # Ustaw samochód na linii startu
    car = Car(finish_scaled[0], finish_scaled[1])

    running = True
    while running:
        screen.fill(BG_COLOR)
        outer, inner = draw_track(screen, data) # its switched?

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        car.update()
        # if check_collision(car, outer, inner):
        #     print("💥 Kolizja!")
        #     car.speed = 0
        if check_if_on_track(car, generate_track_mask(data, WIDTH, HEIGHT), inner, outer):
            print("Na torze!")
        else:
            car.speed = 0

        car.draw(screen)
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

if __name__ == "__main__":
    main()
