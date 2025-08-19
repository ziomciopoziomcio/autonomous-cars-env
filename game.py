import pygame
import json
import os
import math

import components.globals as cg
from components.functions_helper import *
from components.car_class import Car

cg.MAP_FILE = os.path.join("map_generators", "map_data.json")

# Constants

BG_COLOR = (30, 30, 30)
INNER_COLOR = (200, 50, 50)  # (50, 50, 200)
OUTER_COLOR = (200, 50, 50)
TRACK_COLOR = (50, 200, 50)
FINISH_COLOR = (255, 255, 0)

ROW_OFFSET_FACTOR = 1.1
OFFSET_DISTANCE_FACTOR = 2
CAR_LENGTH_RATIO = 2
CAR_SPACING_FACTOR = 1.5
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
    center_scaled = scale_points([center_point], min_x, min_y, scale)[0]

    # Find the closest points on the outer and inner lines
    outer_closest = min(outer_line, key=lambda p: math.dist(center_scaled, p))
    inner_closest = min(inner_line, key=lambda p: math.dist(center_scaled, p))

    # Calculate the rotation angle of the finish line
    angle = math.degrees(
        math.atan2(inner_closest[1] - outer_closest[1], inner_closest[0] - outer_closest[0]))

    finish_width = int(math.dist(outer_closest, inner_closest))
    finish_height = 25

    # Scale the finish line image
    scaled_finish = pygame.transform.scale(cg.FINISH_TEXTURE, (finish_width, finish_height))

    # Rotate the finish line image
    rotated_finish = pygame.transform.rotate(scaled_finish, -angle)

    # Center the finish line image
    finish_rect = rotated_finish.get_rect()
    finish_rect.center = (
        (outer_closest[0] + inner_closest[0]) // 2, (outer_closest[1] + inner_closest[1]) // 2)

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
    track_surface = pygame.Surface((cg.WIDTH, cg.HEIGHT), pygame.SRCALPHA)
    track_surface.fill((0, 0, 0, 0))

    pygame.draw.polygon(track_surface, (255, 255, 255), outer)
    pygame.draw.polygon(track_surface, (0, 0, 0), inner)

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

    return outer, inner


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
    track_surface = pygame.Surface((width, height), pygame.SRCALPHA)
    track_surface.fill((0, 0, 0, 0))  # Przezroczyste tło

    # Narysuj tor jako biały obszar
    pygame.draw.polygon(track_surface, (255, 255, 255), outer)  # Zewnętrzny wielokąt
    pygame.draw.polygon(track_surface, (0, 0, 0), inner)  # Wewnętrzny wielokąt (dziura)

    # Wygeneruj maskę z powierzchni
    track_mask = pygame.mask.from_surface(track_surface)
    return track_mask

class PlayerCar(Car):
    def __init__(self, x, y, track_width, inner_line, outer_line, method=1):
        super().__init__(x, y, track_width, inner_line, outer_line)
        self.method = method  # 1 - arrows, 2 - WASD (not implemented yet)

    def choose_action(self):
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
        self.update(action)




def main():
    pygame.init()
    screen = pygame.display.set_mode((cg.WIDTH, cg.HEIGHT))
    pygame.display.set_caption("Wyścigówka")

    cg.FINISH_TEXTURE = pygame.image.load(os.path.join("imgs", "finish.png")).convert_alpha()
    cg.TRACK_IMAGE = pygame.image.load(os.path.join("imgs", "road.jpg")).convert()
    cg.TRACK_IMAGE = pygame.transform.scale(cg.TRACK_IMAGE, (cg.WIDTH, cg.HEIGHT))

    clock = pygame.time.Clock()
    data = load_map(cg.MAP_FILE)

    # Load and scale the background image to fill the entire screen
    cg.BACKGROUND_IMAGE = pygame.image.load(os.path.join("imgs", "grass.jpg")).convert()
    cg.BACKGROUND_IMAGE = pygame.transform.scale(cg.BACKGROUND_IMAGE, (cg.WIDTH, cg.HEIGHT))

    # Pobierz pozycję linii startu
    finish_line = data["finish_line"]["point"]
    min_x, min_y, scale = get_scaling_params([data["outer_points"], data["inner_points"]],
                                             cg.WIDTH, cg.HEIGHT,
                                             scale_factor=0.9)
    finish_scaled = scale_points([finish_line], min_x, min_y, scale)[0]

    # Calculate track width
    outer = scale_points(data["outer_points"], min_x, min_y, scale)
    inner = scale_points(data["inner_points"], min_x, min_y, scale)
    outer_closest = min(outer, key=lambda p: math.dist(finish_scaled, p))
    inner_closest = min(inner, key=lambda p: math.dist(finish_scaled, p))
    track_width = math.dist(outer_closest, inner_closest)

    num_cars = 4
    car_width = track_width * cg.CAR_SIZE_RATIO
    car_length = car_width * CAR_LENGTH_RATIO
    offset_distance = car_length * OFFSET_DISTANCE_FACTOR  # Distance from the finish line
    row_offset = car_length * ROW_OFFSET_FACTOR
    spacing = car_width * CAR_SPACING_FACTOR  # Spacing between cars
    starting_positions = calculate_starting_positions(finish_scaled,
                                                      outer, inner, num_cars, offset_distance,
                                                      row_offset,
                                                      spacing)

    # Place the cars at the starting line
    cars = [PlayerCar(x, y, track_width, inner, outer, method=1) for x, y, angle in starting_positions]
    for car, (_, _, angle) in zip(cars, starting_positions):
        car.angle = angle

    track_mask = generate_track_mask(data, cg.WIDTH, cg.HEIGHT)

    running = True
    while running:
        screen.blit(cg.BACKGROUND_IMAGE, (0, 0))
        outer, inner = draw_track(screen, data)  # its switched?

        draw_finish_line(screen, data, cg.WIDTH, cg.HEIGHT, outer, inner)
        draw_checkpoints_line(screen, data, cg.WIDTH, cg.HEIGHT, outer, inner, cars)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        for car in cars:  # Iterate over all cars
            car.choose_action()
            car.check_checkpoints(data["checkpoints"], data, outer, inner, cg.WIDTH, cg.HEIGHT)
            car.check_finish_line(data["checkpoints"], data["finish_line"], data, outer, inner,
                                  cg.WIDTH, cg.HEIGHT)
            if not car.check_if_on_track(track_mask, inner, outer):
                car.speed = 0
            car.draw(screen)
            # Calculate rays and draw them
            rays, distances = car.get_rays_and_distances(track_mask, inner, cars)
            car.draw_rays(screen, rays)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
