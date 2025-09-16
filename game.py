import pygame
import json
import os
import math

import components.globals as cg
from components.functions_helper import get_scaling_params, scale_points, lines_params_prep
from components.car_class import Car

cg.MAP_FILE = os.path.join("map_generators", "map_data.json")

# Constants

BG_COLOR = (30, 30, 30)
INNER_COLOR = (200, 50, 50)  # (50, 50, 200)
OUTER_COLOR = (200, 50, 50)
TRACK_COLOR = (50, 200, 50)
FINISH_COLOR = (255, 255, 0)

ROW_OFFSET_FACTOR = 1.5
OFFSET_DISTANCE_FACTOR = 3
CAR_LENGTH_RATIO = 2
CAR_SPACING_FACTOR = 2.1
PERPENDICULAR_ANGLE_OFFSET = 90


def load_map(file_path):
    with open(file_path, "r") as f:
        data = json.load(f)
    return data


def calculate_starting_positions(finish_line, outer_line,
                                 inner_line, num_cars, offset_distance, row_offset, spacing):
    """
    Calculates the starting positions and angles for cars on the starting line.
    The function finds the closest points on the outer and inner track lines to the finish line,
    determines the orientation of the starting line, and places cars in rows and columns
    with the correct angle so that the front of the car always faces the track.

    :param finish_line: The finish line point (tuple)
    :param outer_line: List of points of the outer track line
    :param inner_line: List of points of the inner track line
    :param num_cars: Number of cars to place
    :param offset_distance: Distance from the finish line to the first row of cars
    :param row_offset: Distance between rows of cars
    :param spacing: Distance between cars in a row
    :return: List of tuples (x, y, angle) for each car
    """

    # Find the closest points on the outer and inner lines to the finish line
    outer_closest = min(outer_line, key=lambda p: math.dist(finish_line, p))
    inner_closest = min(inner_line, key=lambda p: math.dist(finish_line, p))
    x1, y1 = outer_closest
    x2, y2 = inner_closest

    # Vector of the finish line and its length
    dx = x2 - x1
    dy = y2 - y1
    length = math.hypot(dx, dy)
    if length == 0:
        raise ValueError("Finish line points are identical!")

    # Car angle: along the finish line (front facing the track)
    if abs(dx) > abs(dy):
        car_angle = math.degrees(math.atan2(dy, dx)) + PERPENDICULAR_ANGLE_OFFSET
    else:
        car_angle = math.degrees(math.atan2(dy, dx)) - PERPENDICULAR_ANGLE_OFFSET

    # Midpoint of the finish line
    midpoint_x = (x1 + x2) / 2
    midpoint_y = (y1 + y2) / 2

    # Perpendicular vector to the finish line (for row placement)
    perp_dx = -dy / length
    perp_dy = dx / length

    # Shift the starting line from the finish line
    shifted_x = midpoint_x + perp_dx * offset_distance
    shifted_y = midpoint_y + perp_dy * offset_distance

    positions = []
    for i in range(num_cars):
        row = i // 2
        col = i % 2
        # Car position along the finish line
        car_x = (shifted_x + (col - 0.5) * spacing * (dx / length)
                 - row * row_offset * perp_dx)
        car_y = (shifted_y + (col - 0.5) * spacing * (dy / length)
                 - row * row_offset * perp_dy)
        positions.append((car_x, car_y, car_angle))
    return positions


def draw_finish_line(screen, data, width, height, outer_line, inner_line):
    """
    Draw the finish line between the outer and inner lines.
    :param screen: Pygame surface to draw on.
    :param data: Map data containing the finish line point.
    :param width: Width of the screen.
    :param height: Height of the screen.
    :param outer_line: Scaled outer line points.
    :param inner_line: Scaled inner line points.
    """
    # Extract the center point of the finish line
    center_point = data["finish_line"]["point"]

    # Scale the center point
    min_x, min_y, scale = get_scaling_params([data["outer_points"], data["inner_points"]], width,
                                             height,
                                             scale_factor=0.9)

    _, _, rotated_finish, finish_rect = lines_params_prep(None, center_point, inner_line, min_x,
                                                          min_y, outer_line, scale)

    # Draw the finish line image on the screen
    screen.blit(rotated_finish, finish_rect.topleft)


def draw_checkpoints_line(screen, data, width, height, outer_line, inner_line, cars):
    """
    Draw the checkpoints line between the outer and inner lines.
    :param screen: Pygame surface to draw on.
    :param data: Map data containing the finish line point.
    :param width: Width of the screen.
    :param height: Height of the screen.
    :param outer_line: Scaled outer line points.
    :param inner_line: Scaled inner line points.
    """
    checkpoints_points = data["checkpoints"]
    min_x, min_y, scale = get_scaling_params([data["outer_points"], data["inner_points"]], width,
                                             height, scale_factor=0.9)

    for checkpoint in checkpoints_points:
        # Scale the checkpoint point
        checkpoint_scaled = scale_points([checkpoint], min_x, min_y, scale)[0]

        # Find the closest points on the outer and inner lines
        outer_closest = min(outer_line, key=lambda p: math.dist(checkpoint_scaled, p))
        inner_closest = min(inner_line, key=lambda p: math.dist(checkpoint_scaled, p))

        # Check if any car has passed the checkpoint
        passed = any(checkpoint in car.checkpoints for car in cars)
        color = (0, 255, 0) if passed else (255, 255, 0)

        pygame.draw.line(screen, color, outer_closest, inner_closest, 5)


def draw_track(screen, data):
    outer_raw = data["outer_points"]
    inner_raw = data["inner_points"]

    min_x, min_y, scale = get_scaling_params([outer_raw, inner_raw],
                                             cg.WIDTH, cg.HEIGHT, scale_factor=0.9)
    outer = scale_points(outer_raw, min_x, min_y, scale)
    inner = scale_points(inner_raw, min_x, min_y, scale)

    # Create a surface for the track
    track_surface = track_surface_create(inner, outer, cg.WIDTH, cg.HEIGHT)

    # Apply the track image to the surface
    track_surface.blit(cg.TRACK_IMAGE, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

    screen.blit(track_surface, (0, 0))

    inner_surface = pygame.Surface((cg.WIDTH, cg.HEIGHT), pygame.SRCALPHA)
    inner_surface.fill((0, 0, 0, 0))
    pygame.draw.polygon(inner_surface, (255, 255, 255), inner)
    inner_surface.blit(cg.BACKGROUND_IMAGE, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

    # Drawing on the screen
    screen.blit(inner_surface, (0, 0))

    pygame.draw.lines(screen, OUTER_COLOR, True, outer, 5)
    pygame.draw.lines(screen, INNER_COLOR, True, inner, 5)

    # Draw arrows with track direction
    draw_track_direction_arrows(screen, inner, outer)

    return outer, inner


def track_surface_create(inner, outer, width, height):
    track_surface = pygame.Surface((width, height), pygame.SRCALPHA)
    track_surface.fill((0, 0, 0, 0))
    pygame.draw.polygon(track_surface, (255, 255, 255), outer)
    pygame.draw.polygon(track_surface, (0, 0, 0), inner)
    return track_surface


def generate_track_mask(data, width, height):
    # Pobierz punkty toru
    outer_raw = data["outer_points"]
    inner_raw = data["inner_points"]

    # Oblicz skalowanie i przeskaluj punkty
    min_x, min_y, scale = get_scaling_params([outer_raw, inner_raw],
                                             width, height, scale_factor=0.9)
    outer = scale_points(outer_raw, min_x, min_y, scale)
    inner = scale_points(inner_raw, min_x, min_y, scale)

    # Stwórz powierzchnię toru
    track_surface = track_surface_create(inner, outer, width, height)

    # Wygeneruj maskę z powierzchni
    track_mask = pygame.mask.from_surface(track_surface)
    return track_mask


# DO NOT MERGE CLASSES BELOW
# Didactic purposes

class PlayerCar1(Car):
    def __init__(self, x, y, track_width, inner_line, outer_line, method=1):
        super().__init__(x, y, track_width, inner_line, outer_line)
        self.method = method  # 1 - arrows, 2 - WASD (not implemented yet)

    def choose_action(self, cars, state):
        # IMPORTANT
        # To turn on screenshots, set screenshots=True in car.states_generation(..., screenshots=True)!
        # You could also save screenshots to file! Just add debug=True to car.states_generation

        keys = pygame.key.get_pressed()
        action = None
        if keys[pygame.K_UP]:
            action = 0
        if keys[pygame.K_DOWN]:
            action = 1
        if keys[pygame.K_LEFT]:
            action = 2
        if keys[pygame.K_RIGHT]:
            action = 3
        if action is None:
            action = 10
        self.update(action, cars)


class PlayerCar2(Car):
    def __init__(self, x, y, track_width, inner_line, outer_line, method=1):
        super().__init__(x, y, track_width, inner_line, outer_line)
        self.method = method  # 1 - arrows, 2 - WASD (not implemented yet)

    def choose_action(self, cars, state):
        # IMPORTANT
        # To turn on screenshots, set screenshots=True in car.states_generation(..., screenshots=True)!
        # You could also save screenshots to file! Just add debug=True to car.states_generation

        keys = pygame.key.get_pressed()
        action = None
        if keys[pygame.K_UP]:
            action = 0
        if keys[pygame.K_DOWN]:
            action = 1
        if keys[pygame.K_LEFT]:
            action = 2
        if keys[pygame.K_RIGHT]:
            action = 3
        if action is None:
            action = 10
        self.update(action, cars)


class PlayerCar3(Car):
    def __init__(self, x, y, track_width, inner_line, outer_line, method=1):
        super().__init__(x, y, track_width, inner_line, outer_line)
        self.method = method  # 1 - arrows, 2 - WASD (not implemented yet)

    def choose_action(self, cars, state):
        # IMPORTANT
        # To turn on screenshots, set screenshots=True in car.states_generation(..., screenshots=True)!
        # You could also save screenshots to file! Just add debug=True to car.states_generation

        keys = pygame.key.get_pressed()
        action = None
        if keys[pygame.K_UP]:
            action = 0
        if keys[pygame.K_DOWN]:
            action = 1
        if keys[pygame.K_LEFT]:
            action = 2
        if keys[pygame.K_RIGHT]:
            action = 3
        if action is None:
            action = 10
        self.update(action, cars)


class PlayerCar4(Car):
    def __init__(self, x, y, track_width, inner_line, outer_line, method=1):
        super().__init__(x, y, track_width, inner_line, outer_line)
        self.method = method  # 1 - arrows, 2 - WASD (not implemented yet)

    def choose_action(self, cars, state):
        # IMPORTANT
        # To turn on screenshots, set screenshots=True in car.states_generation(..., screenshots=True)!
        # You could also save screenshots to file! Just add debug=True to car.states_generation

        keys = pygame.key.get_pressed()
        action = None
        if keys[pygame.K_UP]:
            action = 0
        if keys[pygame.K_DOWN]:
            action = 1
        if keys[pygame.K_LEFT]:
            action = 2
        if keys[pygame.K_RIGHT]:
            action = 3
        if action is None:
            action = 10
        self.update(action, cars)


class GameEngine:
    def __init__(self, visualize=True):
        self.visualize = visualize
        self.cars = []
        self.pygame_load()
        self.textures_load()
        self.track_load()
        self.cars_load()
        self.cars_number = len(self.cars)
        self.track_mask = generate_track_mask(self.data, cg.WIDTH, cg.HEIGHT)

    def pygame_load(self):
        pygame.init()
        self.screen = pygame.display.set_mode((cg.WIDTH, cg.HEIGHT))
        pygame.display.set_caption("Wyścigówka")

        self.clock = pygame.time.Clock()
        self.data = load_map(cg.MAP_FILE)

    def textures_load(self):
        cg.FINISH_TEXTURE = pygame.image.load(os.path.join("imgs", "finish.png")).convert_alpha()
        cg.TRACK_IMAGE = pygame.image.load(os.path.join("imgs", "road.jpg")).convert()
        cg.TRACK_IMAGE = pygame.transform.scale(cg.TRACK_IMAGE, (cg.WIDTH, cg.HEIGHT))
        # Load and scale the background image to fill the entire screen
        cg.BACKGROUND_IMAGE = pygame.image.load(os.path.join("imgs", "grass.jpg")).convert()
        cg.BACKGROUND_IMAGE = pygame.transform.scale(cg.BACKGROUND_IMAGE, (cg.WIDTH, cg.HEIGHT))

    def track_load(self):
        # Pobierz pozycję linii startu
        finish_line = self.data["finish_line"]["point"]
        min_x, min_y, scale = get_scaling_params(
            [self.data["outer_points"], self.data["inner_points"]],
            cg.WIDTH, cg.HEIGHT,
            scale_factor=0.9)
        self.finish_scaled = scale_points([finish_line], min_x, min_y, scale)[0]

        # Calculate track width
        self.outer = scale_points(self.data["outer_points"], min_x, min_y, scale)
        self.inner = scale_points(self.data["inner_points"], min_x, min_y, scale)
        outer_closest = min(self.outer, key=lambda p: math.dist(self.finish_scaled, p))
        inner_closest = min(self.inner, key=lambda p: math.dist(self.finish_scaled, p))
        self.track_width = math.dist(outer_closest, inner_closest)

    def cars_load(self):
        num_cars = 4
        car_width = self.track_width * cg.CAR_SIZE_RATIO
        car_length = car_width * CAR_LENGTH_RATIO
        offset_distance = car_length * OFFSET_DISTANCE_FACTOR  # Distance from the finish line
        row_offset = car_length * ROW_OFFSET_FACTOR
        spacing = car_width * CAR_SPACING_FACTOR  # Spacing between cars
        starting_positions = calculate_starting_positions(self.finish_scaled,
                                                          self.outer, self.inner, num_cars,
                                                          offset_distance,
                                                          row_offset,
                                                          spacing)

        # Place the cars at the starting line
        # self.cars = [PlayerCar(x, y, self.track_width, self.inner, self.outer, method=1) for
        #              x, y, angle in
        #              starting_positions]
        self.cars.append(PlayerCar1(starting_positions[0][0], starting_positions[0][1],
                                    self.track_width, self.inner, self.outer, method=1))
        self.cars.append(PlayerCar2(starting_positions[1][0], starting_positions[1][1],
                                    self.track_width, self.inner, self.outer, method=1))
        self.cars.append(PlayerCar3(starting_positions[2][0], starting_positions[2][1],
                                    self.track_width, self.inner, self.outer, method=1))
        self.cars.append(PlayerCar4(starting_positions[3][0], starting_positions[3][1],
                                    self.track_width, self.inner, self.outer, method=1))
        for car, (_, _, angle) in zip(self.cars, starting_positions):
            car.angle = angle
            car.fix_angle(self.data["finish_line"]["point"])

    def main_loop(self, qnetwork=None, counter=None):
        if counter is not None:
            counter += 1
        winners = 0
        running = True
        while running:
            self.screen.blit(cg.BACKGROUND_IMAGE, (0, 0))
            self.outer, self.inner = draw_track(self.screen, self.data)  # its switched?

            draw_finish_line(self.screen, self.data, cg.WIDTH, cg.HEIGHT, self.outer, self.inner)
            draw_checkpoints_line(self.screen, self.data, cg.WIDTH, cg.HEIGHT, self.outer,
                                  self.inner, self.cars)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

            for car in self.cars:  # Iterate over all cars
                state = car.states_generation(self.screen, self.data["checkpoints"], self.cars,
                                              screenshots=False, debug=False)
                car.choose_action(self.cars, state)
                car.check_checkpoints(self.data["checkpoints"], self.data, self.outer, self.inner,
                                      cg.WIDTH, cg.HEIGHT)
                car.check_finish_line(self.data["checkpoints"], self.data["finish_line"], self.data,
                                      self.outer, self.inner,
                                      cg.WIDTH, cg.HEIGHT)
                if not car.check_if_on_track(self.track_mask, self.inner, self.outer):
                    car.speed = 0
                if car.win_state():
                    winners += 1
                    self.cars.remove(car)
                    continue
                car.draw(self.screen)
                # Calculate rays and draw them
                rays, _ = car.get_rays_and_distances(self.track_mask, self.inner, self.cars)
                car.draw_rays(self.screen, rays)

            if self.visualize:
                pygame.display.flip()
                self.clock.tick(60)

            if winners == self.cars_number:
                running = False

        pygame.quit()
        return qnetwork, counter


def draw_track_direction_arrows(screen, inner, outer, arrow_color=(255, 0, 255), arrow_length=40,
                                arrow_width=6, step=10):
    """
    Draw arrows along the centerline of the track to indicate direction.
    :param screen: Pygame surface to draw on.
    :param inner: List of inner track points (scaled).
    :param outer: List of outer track points (scaled).
    :param arrow_color: Color of the arrows.
    :param arrow_length: Length of each arrow.
    :param arrow_width: Width of the arrow shaft.
    :param step: Distance between arrows (in points, not pixels).
    """
    num_points = min(len(inner), len(outer))
    for i in range(0, num_points, step):
        # Get corresponding points
        p_inner = inner[i % len(inner)]
        p_outer = outer[i % len(outer)]
        # Centerline point
        cx = (p_inner[0] + p_outer[0]) / 2
        cy = (p_inner[1] + p_outer[1]) / 2

        # Next centerline point for direction
        next_i = (i + 1) % num_points
        p_inner_next = inner[next_i % len(inner)]
        p_outer_next = outer[next_i % len(outer)]
        nx = (p_inner_next[0] + p_outer_next[0]) / 2
        ny = (p_inner_next[1] + p_outer_next[1]) / 2

        # Reverse direction vector to fix arrow direction
        dx = cx - nx
        dy = cy - ny
        length = math.hypot(dx, dy)
        if length == 0:
            continue
        dx /= length
        dy /= length

        # Arrow shaft
        end_x = cx + dx * arrow_length
        end_y = cy + dy * arrow_length
        pygame.draw.line(screen, arrow_color, (cx, cy), (end_x, end_y), arrow_width)

        # Arrow head
        head_size = arrow_length * 0.4
        angle = math.atan2(dy, dx)
        left_angle = angle + math.radians(150)
        right_angle = angle - math.radians(150)
        left_x = end_x + head_size * math.cos(left_angle)
        left_y = end_y + head_size * math.sin(left_angle)
        right_x = end_x + head_size * math.cos(right_angle)
        right_y = end_y + head_size * math.sin(right_angle)
        pygame.draw.polygon(screen, arrow_color,
                            [(end_x, end_y), (left_x, left_y), (right_x, right_y)])


if __name__ == "__main__":
    game = GameEngine()
    game.main_loop()
