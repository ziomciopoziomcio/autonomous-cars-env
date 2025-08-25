import pygame
import os
import math
import json

import components.globals as cg
from components.functions_helper import point_in_polygon, scale_points, get_scaling_params, \
    lines_params_prep


class Car:
    def __init__(self, x, y, track_width, inner_polygon, outer_polygon):
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

        self.set_image(track_width=track_width)

        # checkpoints, finish line
        self.checkpoints = []
        self.win = False

        self.inner_polygon = inner_polygon
        self.outer_polygon = outer_polygon

        self.rays_to_cars = []
        self.rays_to_border = []
        self.distances_to_cars = []
        self.distances_to_border = []
        self.rays = []
        self.distances = []

        self.white_car = pygame.image.load(os.path.join("imgs", "white-car.png")).convert_alpha()
        self.purple_car = pygame.image.load(os.path.join("imgs", "purple-car.png")).convert_alpha()

        self._state_screenshot_map_data = None  # Cache for map data used in state_screenshot

    def fix_angle(self, finish_point):
        """
        Adjust the car's angle so it looks directly along the finish line segment
        (from closest point on outer_polygon to closest point on inner_polygon).
        :param finish_point: tuple (x, y) - finish line center point
        """
        # Find closest points on outer and inner polygons to the finish_point
        outer_closest = min(self.outer_polygon, key=lambda p: math.dist(finish_point, p))
        inner_closest = min(self.inner_polygon, key=lambda p: math.dist(finish_point, p))

        # The finish line is the segment from outer_closest to inner_closest
        dx = inner_closest[0] - outer_closest[0]
        dy = inner_closest[1] - outer_closest[1]
        angle_rad = math.atan2(-dy, dx)
        self.angle = math.degrees(angle_rad) + 90

    def _handle_action(self, action):
        turning = False
        if action == 2:  # Turn left
            self.angle += 5
            turning = True
        if action == 3:  # Turn right
            self.angle -= 5
            turning = True
        if action == 0:  # UP key
            self.speed += 1
        if action == 1:  # DOWN key
            self.speed -= 1
        return turning

    def _handle_no_action(self):
        if self.speed > 0:
            self.speed = max(self.speed - self.friction, 0)
        elif self.speed < 0:
            self.speed = min(self.speed + self.friction, 0)

    def _handle_turning(self):
        if self.speed > 0:
            self.speed = max(self.speed - self.turn_slowdown, 0)
        elif self.speed < 0:
            self.speed = min(self.speed + self.turn_slowdown, 0)

    def _handle_collision(self, old_x, old_y, cars):
        if self.check_collision(self.outer_polygon, self.inner_polygon, cars):
            self.x, self.y = old_x, old_y
            self.speed = 0

    def update(self, action, cars):
        if self.win is True:
            return
        old_x, old_y = self.x, self.y
        turning = self._handle_action(action)
        if action == 10:  # No action
            self._handle_no_action()
        if turning:
            self._handle_turning()
        # Car position update
        self.x += self.speed * math.cos(math.radians(self.angle))
        self.y -= self.speed * math.sin(math.radians(self.angle))
        self._handle_collision(old_x, old_y, cars)

    def draw(self, screen):
        if self.win is True:
            return
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

    def _check_car_collision(self, test_x, test_y, other_cars):
        for car_mask, car_rect in other_cars:
            offset = (test_x - car_rect.left, test_y - car_rect.top)
            if 0 <= offset[0] < car_mask.get_size()[0] and 0 <= offset[1] < car_mask.get_size()[1]:
                if car_mask.get_at(offset):
                    return (test_x, test_y)
        return None

    def _check_border_collision(self, test_x, test_y, mask, inner_polygon):
        if (mask.get_at((test_x, test_y)) != 1 or point_in_polygon(test_x, test_y, inner_polygon)):
            return (test_x, test_y)
        return None

    def _cast_single_ray(self, center, direction, max_length, bounds, mask, inner_polygon,
                         other_cars):
        center_x, center_y = center
        dx, dy = direction
        max_width, max_height = bounds
        ray_length = 0
        car_hit = None
        car_hit_distance = None
        border_hit = None
        border_hit_distance = None
        while ray_length < max_length:
            test_x = int(center_x + ray_length * dx)
            test_y = int(center_y + ray_length * dy)
            if not (0 <= test_x < max_width and 0 <= test_y < max_height):
                border_hit = (test_x, test_y)
                border_hit_distance = math.hypot(test_x - center_x, test_y - center_y)
                break
            if car_hit is None and other_cars:
                car_collision = self._check_car_collision(test_x, test_y, other_cars)
                if car_collision:
                    car_hit = car_collision
                    car_hit_distance = ray_length
            if border_hit is None:
                border_collision = self._check_border_collision(test_x, test_y, mask, inner_polygon)
                if border_collision:
                    border_hit = border_collision
                    border_hit_distance = ray_length
                    break
            if car_hit is not None and border_hit is not None:
                break
            ray_length += 1
        if border_hit is None:
            test_x = int(center_x + max_length * dx)
            test_y = int(center_y + max_length * dy)
            border_hit = (test_x, test_y)
            border_hit_distance = max_length
        return car_hit, car_hit_distance, border_hit, border_hit_distance

    def _get_ray_params(self, center_x, center_y, dx, dy, max_length, max_width, max_height, mask,
                        inner_polygon, other_cars):
        center = (center_x, center_y)
        direction = (dx, dy)
        bounds = (max_width, max_height)
        return center, direction, max_length, bounds, mask, inner_polygon, other_cars

    def _prepare_other_cars(self, cars):
        other_cars = []
        if cars is not None:
            for car in cars:
                if car is not self and not getattr(car, "win", False):
                    car_mask, car_rect = car.get_mask()
                    other_cars.append((car_mask, car_rect))
        return other_cars

    def _process_single_ray(self, center_x, center_y, dx, dy, max_length, max_width, max_height,
                            mask, inner_polygon, other_cars):
        params = self._get_ray_params(center_x, center_y, dx, dy, max_length, max_width, max_height,
                                      mask, inner_polygon, other_cars)
        car_hit, car_hit_distance, border_hit, border_hit_distance = self._cast_single_ray(*params)
        ray_result = {}
        if car_hit is not None and (car_hit_distance <= border_hit_distance):
            ray_result['ray'] = (center_x, center_y, car_hit[0], car_hit[1])
            ray_result['distance'] = car_hit_distance
        else:
            ray_result['ray'] = (center_x, center_y, border_hit[0], border_hit[1])
            ray_result['distance'] = border_hit_distance
        ray_result['ray_to_car'] = (center_x, center_y, car_hit[0],
                                    car_hit[1]) if car_hit is not None else None
        ray_result['distance_to_car'] = car_hit_distance if car_hit is not None else None
        ray_result['ray_to_border'] = (center_x, center_y, border_hit[0], border_hit[1])
        ray_result['distance_to_border'] = border_hit_distance
        return ray_result

    def get_rays_and_distances(self, mask, inner_polygon, cars=None):
        if self.img is None:
            car_width = 30
            car_height = 20
            center_x = self.x + car_width // 2
            center_y = self.y + car_height // 2
        else:
            car_rect = self.image.get_rect(center=(self.x, self.y))
            center_x, center_y = car_rect.center
        angle_rad = -math.radians(self.angle)
        ray_angles = [0, 45, 90, 135, 180, 225, 270, 315]
        self.rays = []
        self.distances = []
        self.rays_to_cars = []
        self.distances_to_cars = []
        self.rays_to_border = []
        self.distances_to_border = []
        max_width, max_height = mask.get_size()
        max_length = 1000
        other_cars = self._prepare_other_cars(cars)
        for ray_angle in ray_angles:
            total_angle = angle_rad + math.radians(ray_angle)
            dx = math.cos(total_angle)
            dy = math.sin(total_angle)
            ray_result = self._process_single_ray(center_x, center_y, dx, dy, max_length, max_width,
                                                  max_height, mask, inner_polygon, other_cars)
            self.rays.append(ray_result['ray'])
            self.distances.append(ray_result['distance'])
            self.rays_to_cars.append(ray_result['ray_to_car'])
            self.distances_to_cars.append(ray_result['distance_to_car'])
            self.rays_to_border.append(ray_result['ray_to_border'])
            self.distances_to_border.append(ray_result['distance_to_border'])
        return self.rays, self.distances

    def draw_rays(self, surface, rays):
        """
        Draw rays on the surface.
        :param surface: Pygame surface to draw on.
        :param rays: List of rays [(start_x, start_y, end_x, end_y)].
        """
        if self.win:
            return
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
        # Check if the limit of available colors is exceeded
        if cg.USED_CARS >= len(cg.COLORS):
            raise ValueError("Too many cars created, not enough colors available.")

        # Load the image
        self.img = pygame.image.load(os.path.join("imgs", cg.COLORS[cg.USED_CARS])).convert_alpha()

        # Increment cg.USED_CARS only after the check passes
        cg.USED_CARS += 1
        # Preserve original aspect ratio
        self.image_setter(track_width=track_width)

    def image_setter(self, track_width=None, desired_car_width=None):
        if desired_car_width is None:
            # Calculate desired car width based on the track width
            desired_car_width = track_width * cg.CAR_SIZE_RATIO
        original_width, original_height = self.img.get_size()
        new_width = int(desired_car_width)
        new_height = int(original_height * (new_width / original_width))
        # Scale the image
        scaled_image = pygame.transform.scale(self.img, (new_width, new_height))
        # Rotate the image 90 degrees to the left (counterclockwise)
        self.image = pygame.transform.rotate(scaled_image, -90)
        self.mask = pygame.mask.from_surface(self.image)
        return desired_car_width

    def check_checkpoints(self, checkpoints, data=None, outer_line=None, inner_line=None,
                          width=cg.WIDTH, height=cg.HEIGHT):
        """
        Check if the car has passed any checkpoints using mask collision.
        :param checkpoints: List of checkpoint positions [(x, y), ...].
        :param data: Map data (must contain 'outer_points', 'inner_points')
        :param outer_line: Scaled outer line points (optional)
        :param inner_line: Scaled inner line points (optional)
        :param width: Screen width
        :param height: Screen height
        :return: True if the car has passed a checkpoint, False otherwise.
        """
        if cg.FINISH_TEXTURE is None or data is None:
            return False

        # Prepare scaling params
        car_mask, car_rect, inner_line, min_x, min_y, outer_line, scale = self.scaling_params_prep(
            data, height, inner_line, outer_line, width)
        for checkpoint in checkpoints:
            checkpoint_mask, offset, _, _ = lines_params_prep(car_rect, checkpoint, inner_line,
                                                              min_x,
                                                              min_y, outer_line, scale)
            if car_mask.overlap(checkpoint_mask, offset):
                if checkpoint not in self.checkpoints:
                    self.checkpoints.append(checkpoint)
                    # print(f"Checkpoint reached: {checkpoint}")
                    return True
        return False

    def check_finish_line(self, checkpoints, finish_line, data=None, outer_line=None,
                          inner_line=None, width=cg.WIDTH, height=cg.HEIGHT):
        """
        Check if the car has crossed the finish line using mask collision.
        :param finish_line: List of finish line positions [(x, y), ...].
        :param data: Map data (must contain 'outer_points', 'inner_points')
        :param outer_line: Scaled outer line points (optional)
        :param inner_line: Scaled inner line points (optional)
        :param width: Screen width
        :param height: Screen height
        :return: True if the car has crossed the finish line, False otherwise.
        """
        if cg.FINISH_TEXTURE is None or data is None:
            return False

        if self.win is True:
            return False

        if len(checkpoints) > len(self.checkpoints):
            return False

        # Prepare scaling params
        car_mask, car_rect, inner_line, min_x, min_y, outer_line, scale = self.scaling_params_prep(
            data, height, inner_line, outer_line, width)

        finish = finish_line["point"]
        finish_mask, offset, _, _ = lines_params_prep(car_rect, finish, inner_line, min_x,
                                                      min_y, outer_line, scale)
        if car_mask.overlap(finish_mask, offset):
            # print(f"Finish line crossed: {finish}")
            self.win = True
            return True
        return False

    def scaling_params_prep(self, data, height, inner_line, outer_line, width):
        min_x, min_y, scale = get_scaling_params([data["outer_points"], data["inner_points"]],
                                                 width, height, scale_factor=0.9)
        if outer_line is None:
            outer_line = scale_points(data["outer_points"], min_x, min_y, scale)
        if inner_line is None:
            inner_line = scale_points(data["inner_points"], min_x, min_y, scale)
        car_mask, car_rect = self.get_mask()
        return car_mask, car_rect, inner_line, min_x, min_y, outer_line, scale

    def check_if_on_track(self, track_mask, inner_polygon, outer_polygon):
        # Get the car's mask
        car_mask = pygame.mask.from_surface(self.image)
        car_rect = self.image.get_rect(center=(self.x, self.y))

        # Calculate offset between the track mask and the car mask
        offset = (car_rect.left - 0,
                  car_rect.top - 0)  # Assume the track mask starts at (0, 0)

        # Check if the masks overlap
        overlap = track_mask.overlap(car_mask, offset)
        if overlap is None:
            return False

        if point_in_polygon(self.x, self.y, inner_polygon):
            return False

        if not point_in_polygon(self.x, self.y, outer_polygon):
            return False  # The car is outside the track

        return True

    def check_collision(self, outer_polygon, inner_polygon, cars):
        # Check collision with other cars (full masks)
        self_mask, self_rect = self.get_mask()
        for other_car in cars:
            if other_car != self:
                if other_car.win is True:
                    continue
                other_mask, other_rect = other_car.get_mask()
                offset = (other_rect.left - self_rect.left, other_rect.top - self_rect.top)
                if self_mask.overlap(other_mask, offset):
                    return True
        # Collision with the track
        cx, cy = int(self.x), int(self.y)
        if point_in_polygon(cx, cy, outer_polygon) and not point_in_polygon(cx, cy, inner_polygon):
            return False  # The car is on the track
        return True  # Collision

    def states_generation(self, screen, checkpoints, cars, screenshots=False):
        """
         Parameters:
            state (list): A 3-element list representing the car's current state:
                - state[0]: A list of 8 float values representing distances to the track border
                            in 8 directions (every 45 degrees, starting from forward).
                - state[1]: A list of 8 float values representing distances to the nearest car
                           in the same 8 directions.
                - state[2]: A 2-element list representing progress information:
                            - state[2][0]: The index of the closest checkpoint.
                            - state[2][1]: The car's progress, e.g., distance to the next checkpoint
                                           or normalized progress value.
                - state[3]: A 2-element list representing car angles:
                            - state[3][0]: The car's current angle (compass).
                            - state[3][1]: The angle to the next checkpoint.
                - state[4]: Image of the screen.
        :return: list of states
        """
        state = []
        # Distances to the track border
        distances_to_border = self.state_from_distances_to_border()
        state.append(distances_to_border)

        # Distances to other cars
        distances_to_cars = self.state_from_distances_to_cars()
        state.append(distances_to_cars)

        # Progress information
        progress_info = self.progress_info(checkpoints)
        state.append(progress_info)

        # Temporary None for future use
        state.append(None)

        # Screenshot of the screen
        screenshot = self.state_screenshot(cars, screen, screenshots)
        state.append(screenshot)

        return state

    def state_from_angles(self, checkpoints):
        """
        Returns a tuple:
            (car's current angle, angle to the next checkpoint)
        """
        state_compass = self.angle

        # Find next checkpoint index (first not in self.checkpoints)
        next_index = None
        for i, cp in enumerate(checkpoints):
            if cp not in self.checkpoints:
                next_index = i
                break
        if next_index is None:
            # All checkpoints passed, wrap to first
            return (state_compass, None)

        next_checkpoint = checkpoints[next_index]
        dx = next_checkpoint[0] - self.x
        dy = next_checkpoint[1] - self.y
        angle_to_next = math.degrees(math.atan2(-dy, dx))
        # Normalize angle difference to [-180, 180]
        angle_diff = (angle_to_next - self.angle + 180) % 360 - 180

        return (state_compass, angle_diff)

    def state_from_distances_to_border(self):
        return self.distances_to_border

    def state_from_distances_to_cars(self):
        return self.distances_to_cars

    def progress_info(self, checkpoints):
        """
        Returns progress information for the car.
        :param checkpoints: List of checkpoints.
        :return: A tuple containing the index of the closest checkpoint and the car's progress.
        """
        if not checkpoints:
            return (-1. - 1)  # No checkpoints available

        # Find the closest checkpoint
        closest_checkpoint = min(checkpoints, key=lambda cp: math.dist((self.x, self.y), cp))
        closest_index = checkpoints.index(closest_checkpoint)

        # Calculate progress (distance to the next checkpoint or normalized value)
        if closest_index < len(checkpoints) - 1:
            next_checkpoint = checkpoints[closest_index + 1]
            progress = math.dist((self.x, self.y), next_checkpoint)
        else:
            progress = 0
        return (closest_index, progress)

    def track_width_calculation(self, car, screen):
        map_data = None
        if hasattr(car, "outer_polygon") and hasattr(car, "inner_polygon"):
            # Determine track width at the car's position
            # Use the car's center to find the closest points on both lines
            if hasattr(self,
                       "_state_screenshot_map_data") and self._state_screenshot_map_data is not None:
                map_data = self._state_screenshot_map_data
            else:
                with open(cg.MAP_FILE, "r") as f:
                    map_data = json.load(f)
                    self._state_screenshot_map_data = map_data
            min_x, min_y, scale = get_scaling_params(
                [map_data["outer_points"], map_data["inner_points"]],
                screen.get_width(), screen.get_height(), scale_factor=0.9)
            outer = scale_points(map_data["outer_points"], min_x, min_y, scale)
            inner = scale_points(map_data["inner_points"], min_x, min_y, scale)
            car_pos = (car.x, car.y)
            outer_closest = min(outer, key=lambda p: math.dist(car_pos, p))
            inner_closest = min(inner, key=lambda p: math.dist(car_pos, p))
            track_width = math.dist(outer_closest, inner_closest)
        else:
            # Fallback
            track_width = 40
        return track_width

    def _swap_car_images_for_screenshot(self, cars, screen):
        """Swap car images for screenshot: player to white, others to purple. Returns original (img, image, mask) for each car and desired_car_width for self."""
        original_states = [(car.img, car.image, car.mask) for car in cars]
        desired_car_width = None
        for car in cars:
            if car is self:
                # Assign a fresh, scaled copy of the white car image
                car.img = self.white_car.copy()
                track_width = self.track_width_calculation(car, screen)
                desired_car_width = track_width * cg.CAR_SIZE_RATIO
                original_width, original_height = car.img.get_size()
                new_width = int(desired_car_width)
                new_height = int(original_height * (new_width / original_width))
                scaled_image = pygame.transform.scale(car.img, (new_width, new_height))
                car.image = pygame.transform.rotate(scaled_image, -90)
                car.mask = pygame.mask.from_surface(car.image)
            else:
                # Assign a fresh, scaled copy of the purple car image
                car.img = self.purple_car.copy()
                track_width = self.track_width_calculation(car, screen)
                desired_car_width_other = track_width * cg.CAR_SIZE_RATIO
                original_width, original_height = car.img.get_size()
                new_width = int(desired_car_width_other)
                new_height = int(original_height * (new_width / original_width))
                scaled_image = pygame.transform.scale(car.img, (new_width, new_height))
                car.image = pygame.transform.rotate(scaled_image, -90)
                car.mask = pygame.mask.from_surface(car.image)
        return original_states, desired_car_width

    def _restore_car_images_after_screenshot(self, cars, original_states, desired_car_width):
        """Restore original car images, image, and mask after screenshot."""
        for car, (orig_img, orig_image, orig_mask) in zip(cars, original_states):
            car.img = orig_img
            car.image = orig_image
            car.mask = orig_mask

    def _get_or_load_map_data(self):
        """Load map data if not already loaded."""
        if not hasattr(self, "_state_screenshot_map_data"):
            with open(cg.MAP_FILE, "r") as f:
                self._state_screenshot_map_data = json.load(f)
        return self._state_screenshot_map_data

    def _draw_screenshot_surface(self, screen, cars):
        """Draw background, track, and cars on a new surface."""
        screenshot_surface = pygame.Surface(screen.get_size())
        screenshot_surface.blit(cg.BACKGROUND_IMAGE, (0, 0))
        from game import draw_track
        map_data = self._get_or_load_map_data()
        draw_track(screenshot_surface, map_data)
        for car in cars:
            car.draw(screenshot_surface)
        return screenshot_surface

    def state_screenshot(self, cars, screen, screenshots_state):
        if not screenshots_state:
            return None
        # Swap images and scale for screenshot
        original_imgs, desired_car_width = self._swap_car_images_for_screenshot(cars, screen)
        # Draw everything on screenshot surface
        screenshot_surface = self._draw_screenshot_surface(screen, cars)
        # Get screenshot array
        screenshot = pygame.surfarray.array3d(screenshot_surface)
        # Restore original images and scaling
        self._restore_car_images_after_screenshot(cars, original_imgs, desired_car_width)
        # Save screenshot to file
        pygame.image.save(screenshot_surface, "state_screenshot.png")
        return screenshot
