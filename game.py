import pygame
import json
import os
import math

MAP_FILE = os.path.join("map_generators", "map_data.json")
FINISH_TEXTURE = None
TRACK_IMAGE = None
BACKGROUND_IMAGE = None

# Constants
WIDTH, HEIGHT = 1200, 800
BG_COLOR = (30, 30, 30)
INNER_COLOR = (200, 50, 50)  # (50, 50, 200)
OUTER_COLOR = (200, 50, 50)
TRACK_COLOR = (50, 200, 50)
FINISH_COLOR = (255, 255, 0)
CAR_SIZE_RATIO = 0.25  # Ratio of car size to track width
ROW_OFFSET = -30  # Offset for the second row of cars

USED_CARS = 0
COLORS = ["red-car.png", "white-car.png", "green-car.png", "grey-car.png", "purple-car.png"]


class Car:
    def __init__(self, x, y, track_width):
        self.x = x
        self.y = y
        self.angle = 0
        self.speed = 0

        self.image = pygame.Surface((30, 20), pygame.SRCALPHA)
        self.image.fill((255, 0, 0))
        self.img = None

        self.mask = pygame.mask.from_surface(self.image)

        # PHYSICS
        self.max_speed = 10
        self.acceleration = 0.2
        self.friction = 0.05
        self.turn_slowdown = 0.1

        self.set_image(track_width)

    def update(self):
        turning = False
        # pygame keyboard handling
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
        # Car position update
        self.x += self.speed * math.cos(math.radians(self.angle))
        self.y -= self.speed * math.sin(math.radians(self.angle))

    def draw(self, screen):
        if self.img is not None:
            # Use the loaded image for rendering
            rotated_image = pygame.transform.rotate(self.image, self.angle)
            screen.blit(rotated_image, (self.x - rotated_image.get_width() // 2,
                                        self.y - rotated_image.get_height() // 2))
        else:
            # Fall back to rendering the car as a rectangle
            car_rect = pygame.Rect(self.x - 15, self.y - 10, 30, 20)
            rotated_car = pygame.transform.rotate(pygame.Surface(car_rect.size), -self.angle)
            rotated_car.fill((255, 0, 0))
            rotated_rect = rotated_car.get_rect(center=car_rect.center)
            screen.blit(rotated_car, rotated_rect.topleft)

    def get_mask(self):
        rotated_image = pygame.transform.rotate(self.image, -self.angle)
        return pygame.mask.from_surface(rotated_image), rotated_image.get_rect(
            center=(self.x, self.y))

    def get_distances_to_cars(self, cars):
        distances = []
        for other_car in cars:
            if other_car != self:
                dx = other_car.x - self.x
                dy = other_car.y - self.y
                distance = math.sqrt(dx ** 2 + dy ** 2)
                distances.append(distance)
        return distances

    def get_rays_and_distances(self, mask, inner_polygon):
        """
        Calculate the intersection points and distances for 8 rays extending
        from the center of the car to the track border.
        """
        if self.img is None:
            car_width = 30
            car_height = 20

            # Calculate center of the car
            center_x = self.x + car_width // 2
            center_y = self.y + car_height // 2
        else:
            # Calculate center of the car
            car_rect = self.image.get_rect(center=(self.x, self.y))
            center_x, center_y = car_rect.center

        angle_rad = -math.radians(self.angle)

        # Define ray angles relative to the car's orientation
        ray_angles = [0, 45, 90, 135, 180, 225, 270, 315]  # Angles in degrees
        rays = []
        distances = []

        # Border mask outline
        max_width, max_height = mask.get_size()
        max_length = 1000  # Maximum ray length

        for ray_angle in ray_angles:
            # Calculate the absolute angle of the ray
            total_angle = angle_rad + math.radians(ray_angle)
            dx = math.cos(total_angle)
            dy = math.sin(total_angle)

            # Extend the ray until it hits the border
            ray_length = 0
            while ray_length < max_length:
                test_x = int(center_x + ray_length * dx)
                test_y = int(center_y + ray_length * dy)

                # Check if the ray intersects the border
                if 0 <= test_x < max_width and 0 <= test_y < max_height:
                    if (mask.get_at((test_x, test_y)) != 1 or point_in_polygon(test_x, test_y,
                                                                               inner_polygon)):  # Collision detected
                        rays.append((center_x, center_y, test_x, test_y))
                        distances.append(ray_length)
                        break
                else:
                    # Ray goes out of bounds
                    break

                ray_length += 1

            else:
                # If no collision, the ray ends at its maximum length
                test_x = int(center_x + max_length * dx)
                test_y = int(center_y + max_length * dy)
                rays.append((center_x, center_y, test_x, test_y))
                distances.append(max_length)

        return rays, distances

    def draw_rays(self, surface, rays):
        """
        Draw rays on the surface.
        :param surface: Pygame surface to draw on.
        :param rays: List of rays [(start_x, start_y, end_x, end_y)].
        """
        for ray in rays:
            start_x, start_y, end_x, end_y = ray
            pygame.draw.line(surface, (255, 0, 0), (start_x, start_y), (end_x, end_y), 2)

        # directions = [
        #     "Front", "Front-right", "Right", "Back-right",
        #     "Back", "Back-left", "Left", "Front-left"
        # ]
        # for i, (direction, distance) in enumerate(zip(directions, distances)):
        #     distance_text = FONT.render(f"{direction}: {int(distance)} px", True, (255, 255, 255))
        #     win.blit(distance_text, (10, 10 + i * 30))

    def set_image(self, track_width):
        """
        Sets the car's image by scaling it based on the track width.

        :param track_width: The width of the track, used to scale the car's image.
        """
        global USED_CARS
        # Check if the limit of available colors is exceeded
        if USED_CARS >= len(COLORS):
            raise ValueError("Too many cars created, not enough colors available.")

        # Load the image
        self.img = pygame.image.load(os.path.join("imgs", COLORS[USED_CARS])).convert_alpha()

        # Increment USED_CARS only after the check passes
        USED_CARS += 1
        # Preserve original aspect ratio
        desired_car_width = track_width * CAR_SIZE_RATIO
        original_width, original_height = self.img.get_size()
        new_width = int(desired_car_width)
        new_height = int(original_height * (new_width / original_width))

        # Scale the image
        scaled_image = pygame.transform.scale(self.img, (new_width, new_height))

        # Rotate the image 90 degrees to the left (counterclockwise)
        self.image = pygame.transform.rotate(scaled_image, -90)
        self.mask = pygame.mask.from_surface(self.image)


def load_map(file_path):
    with open(file_path, "r") as f:
        data = json.load(f)
    return data


def calculate_starting_positions(finish_line, outer_line,
                                 inner_line, num_cars, offset_distance, spacing):
    """
    Calculates the starting positions for cars along a line parallel to the finish line.

    :param finish_line: The central point of the finish line.
    :param outer_line: Points of the outer track line.
    :param inner_line: Points of the inner track line.
    :param num_cars: Number of cars to position.
    :param offset_distance: Distance to shift the line from the finish line.
    :param spacing: Spacing between cars.
    :return: List of starting positions [(x, y, angle)].
    """
    # Find the closest points on the outer and inner track lines
    outer_closest = min(outer_line, key=lambda p: math.dist(finish_line, p))
    inner_closest = min(inner_line, key=lambda p: math.dist(finish_line, p))

    # Calculate the midpoint between the closest points
    midpoint_x = (outer_closest[0] + inner_closest[0]) / 2
    midpoint_y = (outer_closest[1] + inner_closest[1]) / 2

    # Calculate the angle of the finish line
    angle = math.atan2(inner_closest[1] - outer_closest[1], inner_closest[0] - outer_closest[0])

    # Determine the vector perpendicular to the finish line
    perpendicular_dx = -math.sin(angle)
    perpendicular_dy = math.cos(angle)

    # Shift the finish line by offset_distance to create a new line
    shifted_x = midpoint_x + perpendicular_dx * offset_distance
    shifted_y = midpoint_y + perpendicular_dy * offset_distance

    # Calculate the starting positions for each car along the shifted line
    positions = []
    for i in range(num_cars):
        row = i // 2  # Determine the row (0 or 1)
        col = i % 2  # Determine the column (0 or 1)
        car_x = (shifted_x + (col - 0.5) * spacing * math.cos(angle)
                 - row * ROW_OFFSET * perpendicular_dx)
        car_y = (shifted_y + (col - 0.5) * spacing * math.sin(angle)
                 - row * ROW_OFFSET * perpendicular_dy)
        positions.append((car_x, car_y, math.degrees(angle)))

    return positions


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
    scaled_finish = pygame.transform.scale(FINISH_TEXTURE, (finish_width, finish_height))

    # Rotate the finish line image
    rotated_finish = pygame.transform.rotate(scaled_finish, -angle)

    # Center the finish line image
    finish_rect = rotated_finish.get_rect()
    finish_rect.center = (
        (outer_closest[0] + inner_closest[0]) // 2, (outer_closest[1] + inner_closest[1]) // 2)

    # Draw the finish line image on the screen
    screen.blit(rotated_finish, finish_rect.topleft)


def draw_checkpoints_line(screen, data, width, height, outer_line, inner_line):
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

        # Calculate the rotation angle of the checkpoint line
        angle = math.degrees(
            math.atan2(inner_closest[1] - outer_closest[1], inner_closest[0] - outer_closest[0]))

        checkpoint_width = int(math.dist(outer_closest, inner_closest))
        checkpoint_height = 25

        # Scale the finish line image
        scaled_checkpoint = pygame.transform.scale(FINISH_TEXTURE, (
            checkpoint_width, checkpoint_height))  # TODO: use different image for checkpoints

        # Rotate the finish line image
        rotated_checkpoint = pygame.transform.rotate(scaled_checkpoint, -angle)

        # Center the finish line image
        checkpoint_rect = rotated_checkpoint.get_rect()
        checkpoint_rect.center = (
            (outer_closest[0] + inner_closest[0]) // 2, (outer_closest[1] + inner_closest[1]) // 2)

        # Draw the finish line image on the screen
        screen.blit(rotated_checkpoint, checkpoint_rect.topleft)


def draw_track(screen, data):
    outer_raw = data["outer_points"]
    inner_raw = data["inner_points"]

    min_x, min_y, scale = get_scaling_params([outer_raw, inner_raw],
                                             WIDTH, HEIGHT, scale_factor=0.9)
    outer = scale_points(outer_raw, min_x, min_y, scale)
    inner = scale_points(inner_raw, min_x, min_y, scale)

    # pygame.draw.polygon(screen, TRACK_COLOR, outer + inner[::-1])
    # pygame.draw.polygon(screen, TRACK_COLOR, outer)
    # pygame.draw.polygon(screen, BG_COLOR, inner)

    # Create a surface for the track
    track_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    track_surface.fill((0, 0, 0, 0))

    pygame.draw.polygon(track_surface, (255, 255, 255), outer)
    pygame.draw.polygon(track_surface, (0, 0, 0), inner)

    # Apply the track image to the surface
    track_surface.blit(TRACK_IMAGE, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

    screen.blit(track_surface, (0, 0))

    inner_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    inner_surface.fill((0, 0, 0, 0))
    pygame.draw.polygon(inner_surface, (255, 255, 255), inner)
    inner_surface.blit(BACKGROUND_IMAGE, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

    # Drawing on the screen
    screen.blit(inner_surface, (0, 0))

    pygame.draw.lines(screen, OUTER_COLOR, True, outer, 5)
    pygame.draw.lines(screen, INNER_COLOR, True, inner, 5)

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
    global FINISH_TEXTURE, TRACK_IMAGE, BACKGROUND_IMAGE

    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Wyścigówka")

    FINISH_TEXTURE = pygame.image.load(os.path.join("imgs", "finish.png")).convert_alpha()
    TRACK_IMAGE = pygame.image.load(os.path.join("imgs", "road.jpg")).convert()
    TRACK_IMAGE = pygame.transform.scale(TRACK_IMAGE, (WIDTH, HEIGHT))

    clock = pygame.time.Clock()
    data = load_map(MAP_FILE)

    # Load and scale the background image to fill the entire screen
    BACKGROUND_IMAGE = pygame.image.load(os.path.join("imgs", "grass.jpg")).convert()
    BACKGROUND_IMAGE = pygame.transform.scale(BACKGROUND_IMAGE, (WIDTH, HEIGHT))

    # Pobierz pozycję linii startu
    finish_line = data["finish_line"]["point"]
    min_x, min_y, scale = get_scaling_params([data["outer_points"], data["inner_points"]],
                                             WIDTH, HEIGHT,
                                             scale_factor=0.9)
    finish_scaled = scale_points([finish_line], min_x, min_y, scale)[0]

    # Calculate track width
    outer = scale_points(data["outer_points"], min_x, min_y, scale)
    inner = scale_points(data["inner_points"], min_x, min_y, scale)
    outer_closest = min(outer, key=lambda p: math.dist(finish_scaled, p))
    inner_closest = min(inner, key=lambda p: math.dist(finish_scaled, p))
    track_width = math.dist(outer_closest, inner_closest)

    num_cars = 4
    offset_distance = 30  # Distance from the finish line
    spacing = 15  # Spacing between cars
    starting_positions = calculate_starting_positions(finish_scaled,
                                                      outer, inner, num_cars, offset_distance,
                                                      spacing)

    # Place the cars at the starting line
    cars = [Car(x, y, track_width) for x, y, angle in starting_positions]
    for car, (_, _, angle) in zip(cars, starting_positions):
        car.angle = angle

    track_mask = generate_track_mask(data, WIDTH, HEIGHT)

    running = True
    while running:
        screen.blit(BACKGROUND_IMAGE, (0, 0))
        outer, inner = draw_track(screen, data)  # its switched?

        draw_finish_line(screen, data, WIDTH, HEIGHT, outer, inner)
        draw_checkpoints_line(screen, data, WIDTH, HEIGHT, outer, inner)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False


        for car in cars:  # Iterate over all cars
            car.update()
            if not check_if_on_track(car, track_mask , inner, outer):
                car.speed = 0
            car.draw(screen)
            # Calculate rays and draw them
            rays, distances = car.get_rays_and_distances(track_mask, inner)
            car.draw_rays(screen, rays)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
