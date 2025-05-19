import pygame
import json
import math

# Constants
WIDTH, HEIGHT = 800, 600
FPS = 60
ROAD_WIDTH = 50
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

        if keys[pygame.K_a]:
            self.angle += self.rotation_speed
        if keys[pygame.K_d]:
            self.angle -= self.rotation_speed

        radians = math.radians(self.angle)
        self.x += math.cos(radians) * self.vel
        self.y += math.sin(radians) * self.vel

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
        """Draw the track as roads with smooth curves."""
        for road in self.roads:
            start = self.track_path[road[0] - 1]
            end = self.track_path[road[1] - 1]

            # Calculate perpendicular vector for road width
            dx, dy = end[0] - start[0], end[1] - start[1]
            length = math.sqrt(dx ** 2 + dy ** 2)
            perp = (-dy / length, dx / length)  # Perpendicular unit vector

            # Calculate road polygon points
            road_width = ROAD_WIDTH / 2
            p1 = (start[0] + perp[0] * road_width, start[1] + perp[1] * road_width)
            p2 = (start[0] - perp[0] * road_width, start[1] - perp[1] * road_width)
            p3 = (end[0] - perp[0] * road_width, end[1] - perp[1] * road_width)
            p4 = (end[0] + perp[0] * road_width, end[1] + perp[1] * road_width)

            # Draw the road
            pygame.draw.polygon(self.win, ROAD_COLOR, [p1, p2, p3, p4])

            # Draw borders
            border_width = BORDER_WIDTH / 2
            outer_p1 = (
            start[0] + perp[0] * (road_width + border_width), start[1] + perp[1] * (road_width + border_width))
            outer_p2 = (
            start[0] - perp[0] * (road_width + border_width), start[1] - perp[1] * (road_width + border_width))
            outer_p3 = (end[0] - perp[0] * (road_width + border_width), end[1] - perp[1] * (road_width + border_width))
            outer_p4 = (end[0] + perp[0] * (road_width + border_width), end[1] + perp[1] * (road_width + border_width))

            pygame.draw.polygon(self.win, BORDER_COLOR, [outer_p1, outer_p2, outer_p3, outer_p4], width=1)

        # Draw the finish line
        pygame.draw.circle(self.win, FINISH_COLOR, (int(self.finish_line[0]), int(self.finish_line[1])), 10)

    def run(self):
        self.car = Car(self.finish_line[0], self.finish_line[1], CAR_COLOR)
        while self.running:
            self.clock.tick(FPS)
            keys = pygame.key.get_pressed()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

            self.win.fill((0, 0, 0))
            self.draw_track()
            self.car.move(keys)
            self.car.draw(self.win)
            pygame.display.update()

        pygame.quit()

if __name__ == "__main__":
    track_file = "../map_generators/map_data.json"
    game = Game(WIDTH, HEIGHT, track_file)
    game.run()