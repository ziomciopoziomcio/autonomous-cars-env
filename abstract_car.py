import pygame
import time
import math
from utils import scale_image, blit_rotate_center

pygame.font.init()  # Initialize the font module
FONT = pygame.font.Font(None, 24)  # Use a default font with size 24

max_vel = 8
rotation_vel = 4

class AbstractCar:
    def __init__(self, name):
        self.img = None
        self.max_vel = max_vel
        self.vel = 0
        self.rotation_vel = rotation_vel
        self.angle = 0
        self.x = None
        self.y = None
        self.acceleration = 0.1
        self.mask = None
        self.name = name
        self.checkpoint_index = 0  # Start at the first checkpoint
        self.progress_distance = 0  # Distance along the track

    def get_center(self):
        """Get the center point of the car."""
        return self.x + self.img.get_width() // 2, self.y + self.img.get_height() // 2

    def get_distances_to_cars(self, other_cars):
        """
        Calculate the Euclidean distances to other cars.
        """
        distances = []
        for other_car in other_cars:
            if other_car is not self:
                center_x1, center_y1 = self.get_center()
                center_x2, center_y2 = other_car.get_center()
                distance = math.sqrt((center_x2 - center_x1) ** 2 + (center_y2 - center_y1) ** 2)
                distances.append(distance)
        return distances

    def set_image(self, img):
        self.img = img
        self.mask = pygame.mask.from_surface(self.img)  # Initialize the mask here

    def set_position(self, position):
        self.x, self.y = position

    def rotate(self, left=False, right=False):
        if left:
            self.angle += self.rotation_vel
        elif right:
            self.angle -= self.rotation_vel
        self.move()

    def draw(self, win, zoom, offset_x, offset_y):
        rotated_image = pygame.transform.rotate(self.img, self.angle)
        new_rect = rotated_image.get_rect(center=(self.x * zoom + offset_x, self.y * zoom + offset_y))
        win.blit(rotated_image, new_rect.topleft)

    def draw_rays(self, win, mask, zoom, offset_x, offset_y):
        # Get rays and distances
        rays, distances = self.get_rays_and_distances(mask)

        # for ray in rays:
        #     start_x, start_y, end_x, end_y = ray
        #     pygame.draw.line(win, (255, 0, 0), (start_x, start_y), (end_x, end_y), 2)
        for ray in rays:
            start_pos = (ray[0][0] * zoom + offset_x, ray[0][1] * zoom + offset_y)
            end_pos = (ray[1][0] * zoom + offset_x, ray[1][1] * zoom + offset_y)
            pygame.draw.line(win, (255, 0, 0), start_pos, end_pos, 1)

        # Display distances as text
        directions = [
            "Front", "Front-right", "Right", "Back-right",
            "Back", "Back-left", "Left", "Front-left"
        ]
        for i, (direction, distance) in enumerate(zip(directions, distances)):
            distance_text = FONT.render(f"{direction}: {int(distance)} px", True, (255, 255, 255))
            win.blit(distance_text, (10, 10 + i * 30))

        pygame.display.update()

    def move_forward(self):
        self.vel = min(self.vel + self.acceleration, self.max_vel)
        self.move()

    def move_backward(self):
        self.vel = max(self.vel - self.acceleration, -self.max_vel/2)
        self.move()

    def move(self):
        radians = math.radians(self.angle)
        vertical = math.cos(radians) * self.vel
        horizontal = math.sin(radians) * self.vel

        self.y -= vertical
        self.x -= horizontal

    def get_name(self):
        return self.name

    def collide(self, mask, x=0, y=0):
        car_mask = pygame.mask.from_surface(self.img)
        offset = (int(self.x - x), int(self.y - y))
        poi = mask.overlap(car_mask, offset)
        return poi

    def collide_car(self, other_car):
        """
        Check for collision with another car.
        The other car must be an instance of AbstractCar or a subclass.
        """
        offset = (int(self.x - other_car.x), int(self.y - other_car.y))
        return self.mask.overlap(other_car.mask, offset)

    def reset(self):
        self.angle = 0
        self.vel = 0
        self.checkpoint_index = 0  # Start at the first checkpoint
        self.progress_distance = 0  # Distance along the track

    def get_rays_and_distances(self, mask):
        """
        Calculate the intersection points and distances for 8 rays extending
        from the **center** of the car to the track border.
        """
        # Calculate center of the car
        center_x = self.x + self.img.get_width() // 2
        center_y = self.y + self.img.get_height() // 2

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
                    if mask.get_at((test_x, test_y)) == 1:  # Collision detected
                        rays.append(((center_x, center_y), (test_x, test_y)))
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
                rays.append(((center_x, center_y), (test_x, test_y)))
                distances.append(max_length)

        return rays, distances

    def reduce_speed(self):
        self.vel = max(self.vel - self.acceleration / 2, 0)
        self.move()

    def bounce(self):
        # self.vel = 0 # if your index number is odd uncomment this line
        self.vel = -self.vel #if your index is even uncomment this line
        self.move()

    def perform_action(self, action):
        """
        Perform an action based on the input.

        Actions:
        - "forward": Move the car forward.
        - "backward": Move the car backward.
        - "left": Turn the car left.
        - "right": Turn the car right.
        - "stop": Reduce the car's speed.
        """
        if action == "forward":
            self.move_forward()
        elif action == "backward":
            self.move_backward()
        elif action == "left":
            self.rotate(left=True)
        elif action == "right":
            self.rotate(right=True)
        elif action == "stop":
            self.reduce_speed()
        else:
            raise ValueError(f"Unknown action: {action}")

    def update_progress(self, checkpoints):
        """
        Update the car's progress based on the nearest checkpoint.
        """
        if self.checkpoint_index < len(checkpoints):
            checkpoint_x, checkpoint_y = checkpoints[self.checkpoint_index]
            distance = math.sqrt((self.x - checkpoint_x) ** 2 + (self.y - checkpoint_y) ** 2)

            # If the car is close enough to the checkpoint, move to the next one
            if distance < 40:  # Adjust the threshold as needed
                self.checkpoint_index += 1
                self.progress_distance += distance

    def get_progress(self):
        """Return the car's progress as a combination of checkpoints passed and distance."""
        return [self.checkpoint_index, self.progress_distance]
