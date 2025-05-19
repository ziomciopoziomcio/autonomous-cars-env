import pygame
import json
import math
import numpy as np
from scipy.interpolate import CubicSpline

# Constants
WIDTH, HEIGHT = 800, 600
FPS = 60
ROAD_WIDTH = 80
BORDER_WIDTH = 10

# Colors
ROAD_COLOR = (50, 50, 50)
BORDER_COLOR = (200, 0, 0)
FINISH_COLOR = (255, 0, 0)
CAR_COLOR = (255, 0, 0)


class Car:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.angle = 0
        self.vel = 0
        self.color = color
        self.width = 20
        self.height = 40
        self.acceleration = 0.2
        self.max_speed = 5
        self.brake_speed = 0.1
        self.rotation_speed = 5

    def draw(self, win):
        car_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        car_surface.fill(self.color)
        rotated_car = pygame.transform.rotate(car_surface, -self.angle)
        rect = rotated_car.get_rect(center=(self.x, self.y))
        win.blit(rotated_car, rect.topleft)

    def move(self, keys):
        if keys[pygame.K_w]:
            self.vel = min(self.vel + self.acceleration, self.max_speed)
        elif keys[pygame.K_s]:
            self.vel = max(self.vel - self.acceleration, -self.max_speed)
        else:
            if self.vel > 0:
                self.vel = max(self.vel - self.brake_speed, 0)
            elif self.vel < 0:
                self.vel = min(self.vel + self.brake_speed, 0)

        # Aktualizuj kąt tylko, gdy samochód się porusza
        if self.vel != 0:
            if keys[pygame.K_a]:
                self.angle += self.rotation_speed * (1 if self.vel > 0 else -1)
            if keys[pygame.K_d]:
                self.angle -= self.rotation_speed * (1 if self.vel > 0 else -1)

        # Przelicz pozycję na podstawie kąta i prędkości
        radians = math.radians(self.angle)
        self.x += math.cos(radians) * self.vel
        self.y += math.sin(radians) * self.vel

    def check_collision(self, road_mask):
        """Check if the car is on the road using masks."""
        # Generate a mask for the car
        car_surface = self.get_car_surface()
        car_mask = pygame.mask.from_surface(car_surface)

        # Calculate the offset between the car's position and the road mask
        car_offset = (int(self.x - road_mask.get_size()[0] / 2), int(self.y - road_mask.get_size()[1] / 2))

        # Check for overlap between the car mask and the road mask
        collision_point = road_mask.overlap(car_mask, car_offset)
        return collision_point is None  # Return True if the car is outside the road

    def get_car_surface(self):
        """Generate a rotated surface for the car."""
        car_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        car_surface.fill(self.color)
        return pygame.transform.rotate(car_surface, -self.angle)

    def handle_collision(self, road_mask):
        """Handle the effect of a collision."""
        # Save the current position
        prev_x, prev_y = self.x, self.y

        # Stop the car
        self.vel = 0

        # Move the car slightly back
        radians = math.radians(self.angle)
        self.x -= math.cos(radians) * 5
        self.y -= math.sin(radians) * 5

        # Check if the car is still outside the road
        if self.check_collision(road_mask):
            # If still outside, revert to the previous position
            self.x, self.y = prev_x, prev_y

def generate_road_mask(track_path, road_width, border_width, screen_size):
    """Generate a mask for the road borders."""
    road_surface = pygame.Surface(screen_size, pygame.SRCALPHA)
    road_surface.fill((0, 0, 0, 0))  # Transparent background

    for i in range(len(track_path)):
        start = track_path[i]
        end = track_path[(i + 1) % len(track_path)]
        dx, dy = end[0] - start[0], end[1] - start[1]
        length = math.sqrt(dx ** 2 + dy ** 2)
        perp = (-dy / length, dx / length)

        # Calculate road border points
        road_width_half = road_width / 2 + border_width / 2
        p1 = (start[0] + perp[0] * road_width_half, start[1] + perp[1] * road_width_half)
        p2 = (start[0] - perp[0] * road_width_half, start[1] - perp[1] * road_width_half)
        p3 = (end[0] - perp[0] * road_width_half, end[1] - perp[1] * road_width_half)
        p4 = (end[0] + perp[0] * road_width_half, end[1] + perp[1] * road_width_half)

        # Draw the road border
        pygame.draw.polygon(road_surface, (255, 255, 255), [p1, p2, p3, p4])

    return pygame.mask.from_surface(road_surface)

class Game:
    def __init__(self, width, height, track_file):
        pygame.init()
        self.win = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Racing Game")
        self.clock = pygame.time.Clock()
        self.running = True
        self.car = None
        self.track_path = []
        self.roads = []
        self.finish_line = None
        self.load_track(track_file)

    def load_track(self, file_path):
        with open(file_path, 'r') as file:
            data = json.load(file)
        self.track_path = [tuple(point[1:]) for point in data['points']]
        self.roads = data['roads']
        self.finish_line = tuple(data['finish_line']['point'])

    def draw_track(self):
        """Draw the track with interpolation applied only to connections."""
        road_width = ROAD_WIDTH / 2

        for road in self.roads:
            # Get the points for the connection
            start_idx, end_idx = road
            p1 = self.track_path[start_idx - 1]
            p2 = self.track_path[end_idx - 1]
            p0 = self.track_path[start_idx - 2] if start_idx > 1 else self.track_path[-1]
            p3 = self.track_path[(end_idx % len(self.track_path))]

            # Interpolate points for the connection
            interpolated_points = interpolate_connection(p0, p1, p2, p3)

            # Draw the road
            for i in range(len(interpolated_points) - 1):
                start = interpolated_points[i]
                end = interpolated_points[i + 1]

                # Calculate perpendicular vector for road width
                dx, dy = end[0] - start[0], end[1] - start[1]
                length = math.sqrt(dx ** 2 + dy ** 2)
                if length == 0:
                    continue
                perp = (-dy / length, dx / length)

                # Calculate road polygon points
                p1 = (start[0] + perp[0] * road_width, start[1] + perp[1] * road_width)
                p2 = (start[0] - perp[0] * road_width, start[1] - perp[1] * road_width)
                p3 = (end[0] - perp[0] * road_width, end[1] - perp[1] * road_width)
                p4 = (end[0] + perp[0] * road_width, end[1] + perp[1] * road_width)

                # Draw the road
                pygame.draw.polygon(self.win, ROAD_COLOR, [p1, p2, p3, p4])

        # Draw the finish line
        pygame.draw.circle(self.win, FINISH_COLOR, (int(self.finish_line[0]), int(self.finish_line[1])), 10)

    def run(self):
        self.car = Car(self.finish_line[0], self.finish_line[1], CAR_COLOR)
        road_mask = generate_road_mask(self.track_path, ROAD_WIDTH, BORDER_WIDTH, (WIDTH, HEIGHT))  # Generate road mask

        while self.running:
            self.clock.tick(FPS)
            keys = pygame.key.get_pressed()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

            self.win.fill((0, 0, 0))
            self.draw_track()

            # Check for collisions
            if self.car.check_collision(road_mask):  # Pass the road mask
                self.car.handle_collision(road_mask)  # Pass the road mask here

            self.car.move(keys)
            self.car.draw(self.win)
            pygame.display.update()

        pygame.quit()

def interpolate_connection(p0, p1, p2, p3, num_points=20):
    """Interpolate points for a single connection using Catmull-Rom spline."""
    return catmull_rom_spline(p0, p1, p2, p3, num_points)

def catmull_rom_spline(p0, p1, p2, p3, num_points=20):
    """Generate points using Catmull-Rom spline."""
    points = []
    for t in np.linspace(0, 1, num_points):
        t2 = t * t
        t3 = t2 * t

        # Catmull-Rom spline formula
        x = 0.5 * ((2 * p1[0]) +
                   (-p0[0] + p2[0]) * t +
                   (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 +
                   (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3)

        y = 0.5 * ((2 * p1[1]) +
                   (-p0[1] + p2[1]) * t +
                   (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 +
                   (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)

        points.append((x, y))
    return points

def interpolate_points(points, num_points=50):
    """Interpolate points using Catmull-Rom splines."""
    points = np.array(points)
    interpolated = []

    for i in range(len(points)):
        p0 = points[i - 1]
        p1 = points[i]
        p2 = points[(i + 1) % len(points)]
        p3 = points[(i + 2) % len(points)]

        # Generate spline points between p1 and p2
        spline_points = catmull_rom_spline(p0, p1, p2, p3, num_points)
        interpolated.extend(spline_points)

    return interpolated


if __name__ == "__main__":
    track_file = "../map_generators/map_data.json"
    game = Game(WIDTH, HEIGHT, track_file)
    game.run()
