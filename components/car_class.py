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

        self.set_image(track_width)

        # checkpoints, finish line
        self.checkpoints = []
        self.win = False

        self.inner_polygon = inner_polygon
        self.outer_polygon = outer_polygon

    def update(self):
        if self.win is True:
            return
        old_x, old_y = self.x, self.y
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
        if check_collision(self, self.outer_polygon, self.inner_polygon) is True:
            # If the car collides with the track border, revert to old position
            self.x, self.y = old_x, old_y
            self.speed = 0

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

    def get_rays_and_distances(self, mask, inner_polygon, cars=None):
        """
        Calculate the intersection points and distances for 8 rays extending
        from the center of the car to the track border or screen edge and other cars.
        If another car is hit before the track, the ray ends at the car.
        :param mask: Track mask
        :param inner_polygon: Inner track polygon
        :param cars: List of all cars (including self)
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

        max_width, max_height = mask.get_size()
        max_length = 1000

        # Prepare masks and rects for other cars
        other_cars = []
        if cars is not None:
            for car in cars:
                if car is not self and not getattr(car, "win", False):
                    car_mask, car_rect = car.get_mask()
                    other_cars.append((car_mask, car_rect))

        for ray_angle in ray_angles:
            # Calculate the absolute angle of the ray
            total_angle = angle_rad + math.radians(ray_angle)
            dx = math.cos(total_angle)
            dy = math.sin(total_angle)

            # Extend the ray until it hits the border
            ray_length = 0
            last_valid_x = int(center_x)
            last_valid_y = int(center_y)
            hit = False
            car_hit_distance = None
            car_hit_point = None

            while ray_length < max_length:
                test_x = int(center_x + ray_length * dx)
                test_y = int(center_y + ray_length * dy)

                # Check car collision first
                if other_cars:
                    for car_mask, car_rect in other_cars:
                        # Offset for mask.overlap: (car_rect.left - test_x, car_rect.top - test_y)
                        offset = (test_x - car_rect.left, test_y - car_rect.top)
                        if 0 <= offset[0] < car_mask.get_size()[0] and 0 <= offset[1] < \
                                car_mask.get_size()[1]:
                            if car_mask.get_at(offset):
                                car_hit_distance = ray_length
                                car_hit_point = (test_x, test_y)
                                hit = True
                                break
                    if hit:
                        rays.append((center_x, center_y, car_hit_point[0], car_hit_point[1]))
                        distances.append(car_hit_distance)
                        break

                # Track border collision
                if 0 <= test_x < max_width and 0 <= test_y < max_height:
                    last_valid_x = test_x
                    last_valid_y = test_y
                    if (mask.get_at((test_x, test_y)) != 1 or point_in_polygon(test_x, test_y,
                                                                               inner_polygon)):
                        rays.append((center_x, center_y, test_x, test_y))
                        distances.append(ray_length)
                        hit = True
                        break
                else:
                    # Ray goes out of bounds, treat as hit at the edge
                    rays.append((center_x, center_y, last_valid_x, last_valid_y))
                    distances.append(math.hypot(last_valid_x - center_x, last_valid_y - center_y))
                    hit = True
                    break

                ray_length += 1
            if not hit:
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

    def check_checkpoints(self, checkpoints, data=None, outer_line=None, inner_line=None,
                          width=WIDTH, height=HEIGHT):
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
        if FINISH_TEXTURE is None or data is None:
            return False

        # Prepare scaling params
        min_x, min_y, scale = get_scaling_params([data["outer_points"], data["inner_points"]],
                                                 width, height, scale_factor=0.9)
        if outer_line is None:
            outer_line = scale_points(data["outer_points"], min_x, min_y, scale)
        if inner_line is None:
            inner_line = scale_points(data["inner_points"], min_x, min_y, scale)

        car_mask, car_rect = self.get_mask()

        for checkpoint in checkpoints:
            checkpoint_scaled = scale_points([checkpoint], min_x, min_y, scale)[0]
            outer_closest = min(outer_line, key=lambda p: math.dist(checkpoint_scaled, p))
            inner_closest = min(inner_line, key=lambda p: math.dist(checkpoint_scaled, p))
            angle = math.degrees(math.atan2(inner_closest[1] - outer_closest[1],
                                            inner_closest[0] - outer_closest[0]))
            checkpoint_width = int(math.dist(outer_closest, inner_closest))
            checkpoint_height = 25
            scaled_checkpoint = pygame.transform.scale(FINISH_TEXTURE,
                                                       (checkpoint_width, checkpoint_height))
            rotated_checkpoint = pygame.transform.rotate(scaled_checkpoint, -angle)
            checkpoint_rect = rotated_checkpoint.get_rect()
            checkpoint_rect.center = ((outer_closest[0] + inner_closest[0]) // 2,
                                      (outer_closest[1] + inner_closest[1]) // 2)
            checkpoint_mask = pygame.mask.from_surface(rotated_checkpoint)
            offset = (checkpoint_rect.left - car_rect.left, checkpoint_rect.top - car_rect.top)
            if car_mask.overlap(checkpoint_mask, offset):
                if checkpoint not in self.checkpoints:
                    self.checkpoints.append(checkpoint)
                    # print(f"Checkpoint reached: {checkpoint}")
                    return True
        return False

    def check_finish_line(self, checkpoints, finish_line, data=None, outer_line=None,
                          inner_line=None, width=WIDTH, height=HEIGHT):
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
        if FINISH_TEXTURE is None or data is None:
            return False

        if self.win is True:
            return False

        if len(checkpoints) > len(self.checkpoints):
            return False

        # Prepare scaling params
        min_x, min_y, scale = get_scaling_params([data["outer_points"], data["inner_points"]],
                                                 width, height, scale_factor=0.9)
        if outer_line is None:
            outer_line = scale_points(data["outer_points"], min_x, min_y, scale)
        if inner_line is None:
            inner_line = scale_points(data["inner_points"], min_x, min_y, scale)

        car_mask, car_rect = self.get_mask()

        finish = finish_line["point"]
        finish_scaled = scale_points([finish], min_x, min_y, scale)[0]
        outer_closest = min(outer_line, key=lambda p: math.dist(finish_scaled, p))
        inner_closest = min(inner_line, key=lambda p: math.dist(finish_scaled, p))
        angle = math.degrees(
            math.atan2(inner_closest[1] - outer_closest[1], inner_closest[0] - outer_closest[0]))
        finish_width = int(math.dist(outer_closest, inner_closest))
        finish_height = 25
        scaled_finish = pygame.transform.scale(FINISH_TEXTURE, (finish_width, finish_height))
        rotated_finish = pygame.transform.rotate(scaled_finish, -angle)
        finish_rect = rotated_finish.get_rect()
        finish_rect.center = ((outer_closest[0] + inner_closest[0]) // 2,
                              (outer_closest[1] + inner_closest[1]) // 2)
        finish_mask = pygame.mask.from_surface(rotated_finish)
        offset = (finish_rect.left - car_rect.left, finish_rect.top - car_rect.top)
        if car_mask.overlap(finish_mask, offset):
            # print(f"Finish line crossed: {finish}")
            self.win = True
            return True
        return False
