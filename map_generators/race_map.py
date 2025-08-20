import tkinter as tk
import threading
import pygame
import pygame_gui
import json
import numpy as np
from scipy.interpolate import CubicSpline
from shapely.geometry.linestring import LineString
from shapely.geometry.point import Point

# Initialize pygame and pygame_gui
pygame.init()
pygame.display.set_caption('Map Editor')
window_size = (1024, 768)
window_surface = pygame.display.set_mode(window_size)
manager = pygame_gui.UIManager(window_size)

# Colors
WHITE = (255, 255, 255)
GRAY = (200, 200, 200)

# Constants for checkpoints

CHECKPOINT_COLLISION_OFFSET = 5
CHECKPOINT_COLLISION_SIZE = 10


def interpolate_points(start, end, num_points=5):
    """Generate intermediate points between start and end."""
    points = []
    for i in range(1, num_points + 1):
        t = i / (num_points + 1)
        x = start[0] + t * (end[0] - start[0])
        y = start[1] + t * (end[1] - start[1])
        points.append((x, y))
    return points


def extrapolate_points(start, end, distance=50):
    """Extend the line beyond the end point."""
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = (dx ** 2 + dy ** 2) ** 0.5

    if length == 0:
        raise ValueError("Start and end points are the same, cannot extrapolate.")

    # Normalize the direction vector
    unit_dx = dx / length
    unit_dy = dy / length

    # Calculate the new end point
    new_end = (end[0] + unit_dx * distance, end[1] + unit_dy * distance)
    return new_end


# Main drawing area
drawing_area_rect = pygame.Rect(0, 0, window_size[0], window_size[1])

# Variables to track the selected tool
selected_tool = None
selected_detailed_tool = None


class Map:
    def __init__(self):
        self.points = []
        self.roads = []
        self.finish_line = {'point': None}
        self.checkpoints = []
        self.selected_points = []
        self.point_index = 1

    def add_point(self, position):
        """Add a point to the map with a unique number."""
        if not any(p[1:] == position for p in self.points):  # Check if position already exists
            point_number = self.point_index
            self.points.append((point_number, *position))
            self.point_index += 1

    def remove_point(self, position):
        """Remove a point by its position and all associated roads."""
        point_to_remove = next((p for p in self.points if p[1:] == position), None)
        if point_to_remove:
            self.points.remove(point_to_remove)
            # Remove all roads connected to this point
            self.roads = [road for road in self.roads if
                          road[0] != point_to_remove[0] and road[1] != point_to_remove[0]]

    def toggle_point_selection(self, position):
        """Toggle the selection of a point."""
        for point in self.points:
            if point[1:] == position:
                if point in self.selected_points:
                    self.selected_points.remove(point)
                else:
                    self.selected_points.append(point)
                break

    def add_road(self, start, end):
        """Add a road between two points."""
        start_number = start[0]
        end_number = end[0]
        if (start_number, end_number) not in self.roads and (
                end_number, start_number) not in self.roads:
            self.roads.append((start_number, end_number))

    def is_track_closed(self):
        """
        Check if the track is logically closed based on the roads.
        """
        if not self.roads:
            return False

        # Build adjacency list for the graph
        graph = {}
        for road in self.roads:
            start, end = road
            if start not in graph:
                graph[start] = []
            if end not in graph:
                graph[end] = []
            graph[start].append(end)
            graph[end].append(start)

        # Perform DFS to check connectivity and closure
        visited = set()
        stack = [self.roads[0][0]]  # Start from the first point in the first road

        while stack:
            current = stack.pop()
            if current not in visited:
                visited.add(current)
                stack.extend(neighbor for neighbor in graph[current] if neighbor not in visited)

        # Check if all points are visited and if we returned to the starting point
        all_points = {point[0] for point in self.points}
        return visited == all_points and len(visited) > 2

    def smooth_or_extrapolate_track(self, num_samples=100):
        """
        Smooth or extrapolate the track using cubic spline interpolation.

        :param num_samples: Number of samples to generate for the smooth track.
        """
        if len(self.points) < 3:
            raise ValueError("At least 3 points are required to smooth the track.")

        # Ensure the track is logically closed
        if not self.is_track_closed():
            raise ValueError("The track must be logically closed (all roads form a loop).")

        # Ensure the first point is repeated at the end for interpolation
        if self.points[0] != self.points[-1]:
            self.points.append(self.points[0])

        # Extract x and y coordinates
        x = [p[1] for p in self.points]
        y = [p[2] for p in self.points]

        # Create a parameter t for the points
        t = np.linspace(0, 1, len(self.points))

        # Fit cubic splines for x and y
        spline_x = CubicSpline(t, x, bc_type='periodic')
        spline_y = CubicSpline(t, y, bc_type='periodic')

        # Generate new points
        t_new = np.linspace(0, 1, num_samples)
        x_smooth = spline_x(t_new)
        y_smooth = spline_y(t_new)

        # Replace the original points with the smoothed points
        self.points = list(zip(range(1, len(x_smooth) + 1), x_smooth, y_smooth))

    def remove_road(self, start, end):
        """Remove a road between two points using their numbers."""
        start_number = start[0]
        end_number = end[0]
        if (start_number, end_number) in self.roads:
            self.roads.remove((start_number, end_number))
        elif (end_number, start_number) in self.roads:
            self.roads.remove((end_number, start_number))

    def set_finish_line(self, start, end):
        """Set the finish line for the map."""
        if start not in self.points:
            raise ValueError("Start point not found in points.")
        if end not in self.points:
            raise ValueError("End point not found in points.")
        self.finish_line['start'] = start
        self.finish_line['end'] = end

    def add_checkpoint(self, position):
        """Add a checkpoint at the specified position."""
        if position not in self.checkpoints:
            self.checkpoints.append(position)

    def remove_checkpoint(self, position):
        """Remove a checkpoint at the specified position."""
        if position in self.checkpoints:
            self.checkpoints.remove(position)

    # FILE

    def to_dict(self):
        """Convert the map data to a dictionary."""
        return {
            'points': self.points,
            'roads': self.roads,
            'finish_line': self.finish_line,
            'checkpoints': self.checkpoints
        }

    def from_dict(self, data):
        """Load the map data from a dictionary."""
        self.points = data.get('points', [])
        self.roads = data.get('roads', [])
        self.finish_line = data.get('finish_line', {'point': None})
        self.checkpoints = data.get('checkpoints', [])

    def generate_track_width(self, width=50):
        """
          Generate smooth inner and outer track boundaries based on the centerline points.

          This function uses the current list of points (assumed to be smoothed/interpolated)
          to create a centerline, then generates the inner and outer boundaries by buffering
          the centerline using the specified width. The result is maximally smooth track edges.

          :param width: The half-width of the track (distance from centerline to edge).
          :return: Tuple (inner_points, outer_points) as lists of (x, y) coordinates.
        """
        # Extract centerline coordinates from points
        coords = [(p[1], p[2]) for p in self.points]
        if coords[0] != coords[-1]:
            coords.append(coords[0])
        center_line = LineString(coords)

        # Generate the outer boundary with high resolution for smoothness
        outer_poly = center_line.buffer(width, cap_style=2, join_style=2, resolution=256)
        outer = np.array(outer_poly.exterior.coords)
        if np.allclose(outer[0], outer[-1]):
            outer = outer[:-1]

        # Generate the inner boundary
        inner_poly = center_line.buffer(-width, cap_style=2, join_style=2, resolution=256)
        if inner_poly.is_empty:
            # If the inner buffer fails, return the centerline as a fallback
            inner = np.array(center_line.coords)
            if np.allclose(inner[0], inner[-1]):
                inner = inner[:-1]
            inner = inner.tolist()
        else:
            inner = np.array(inner_poly.exterior.coords)
            if np.allclose(inner[0], inner[-1]):
                inner = inner[:-1]
            inner = inner.tolist()

        # Ensure the finish line is included in the track
        if self.finish_line['point']:
            finish_point = self.finish_line['point']
            if not center_line.contains(Point(finish_point)):
                # Snap the finish line to the nearest point on the centerline
                finish_point = \
                    center_line.interpolate(center_line.project(Point(finish_point))).coords[0]
                self.finish_line['point'] = finish_point

        # Snap all checkpoints to the nearest point on the centerline
        snapped_checkpoints = []
        for checkpoint in self.checkpoints:
            if not center_line.contains(Point(checkpoint)):
                snapped_point = \
                    center_line.interpolate(center_line.project(Point(checkpoint))).coords[0]
                snapped_checkpoints.append(snapped_point)
            else:
                snapped_checkpoints.append(checkpoint)
        self.checkpoints = snapped_checkpoints

        return inner, outer.tolist()

    def save_to_file(self, file_path):
        """Save the map data to a JSON file, including inner and outer points."""
        inner_points, outer_points = self.generate_track_width()
        data = {
            'points': self.points,
            'roads': self.roads,
            'finish_line': self.finish_line,
            'checkpoints': self.checkpoints,
            'inner_points': inner_points,
            'outer_points': outer_points
        }
        with open(file_path, 'w') as file:
            json.dump(data, file, indent=4)

    def load_from_file(self, file_path):
        """Load the map data from a JSON file."""
        with open(file_path, 'r') as file:
            data = json.load(file)
            self.from_dict(data)


class StepController:
    """
    Class to control the steps of the map generation process using Tkinter.
    """

    def __init__(self):
        self.steps = []  # List of steps (functions)
        self.step_names = []
        self.current_index = 0  # Current step index

        self.root = None

        self.steps_initializer()
        self.start_tkinter_thread()

        self.wait_window = None  # Initialize wait window
        self.step_listbox = None

    def start_tkinter_thread(self):
        """Start the Tkinter window in a separate thread."""
        tkinter_thread = threading.Thread(target=self.window_initializer, daemon=True)
        tkinter_thread.start()

    def window_initializer(self):
        """Initialize TKinter step controller window."""
        self.root = tk.Tk()

        # Two buttons for next step and previous step
        next_button = tk.Button(self.root, text="Next Step", command=self.next_step)
        next_button.pack(side=tk.RIGHT, padx=10, pady=10)

        # Listbox for displaying steps
        self.step_listbox = tk.Listbox(self.root, height=len(self.steps), selectmode=tk.SINGLE)
        for step_name in self.step_names:
            self.step_listbox.insert(tk.END, step_name)
        self.step_listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.root.title("Step Controller")
        self.root.geometry("300x200")
        self.root.deiconify()  # Ensure the window is visible
        self.update_step_highlight()
        self.root.mainloop()  # Start the Tkinter main loop

    def steps_initializer(self):
        """Initialize the steps for the controller."""
        self.add_step("Step 1: Create points",
                      lambda: print("Step 1: Create points"))
        self.add_step("Step 2: Connect points with roads",
                      lambda: print("Step 2: Connect points with roads"))
        self.add_step("Step 3: Smooth or extrapolate track",
                      lambda: print("Step 3: Smooth or extrapolate track"))
        self.add_step("Step 4: Set finish line",
                      lambda: print("Step 4: Set finish line"))
        self.add_step("Step 5: Add checkpoints",
                      lambda: print("Step 5: Add checkpoints"))
        self.add_step("Step 6: Save to file",
                      lambda: print("Step 6: Save to file"))

    def add_step(self, step_name, step_function):
        """Add a step to the controller."""
        self.steps.append(step_function)
        self.step_names.append(step_name)

    def next_step(self):
        """Move to the next step if available."""
        if self.current_index < len(self.steps) - 1:
            self.current_index += 1
            self.start_wait_window()
            self.update_step_highlight()

    def update_step_highlight(self):
        """Highlight the current step in the Listbox."""
        if self.step_listbox:
            self.step_listbox.selection_clear(0, tk.END)
            self.step_listbox.selection_set(self.current_index)
            self.step_listbox.activate(self.current_index)

    def current_step(self):
        """Return the current step index."""
        if self.steps:
            return self.current_index
        return None

    def run_current_step(self, *args, **kwargs):
        """Run the current step function."""
        step_function = self.current_step()
        if step_function:
            step_function(*args, **kwargs)

    def start_wait_window(self):
        """Start a waiting window."""
        self.wait_window = tk.Toplevel(self.root)
        self.wait_window.title("Please wait")
        label = tk.Label(self.wait_window, text="Processing, please wait...")
        label.pack(padx=20, pady=20)
        self.wait_window.geometry("300x100")
        self.wait_window.deiconify()

    def stop_wait_window(self):
        """Stop the waiting window."""
        if self.wait_window is not None:
            self.wait_window.destroy()
            del self.wait_window
            self.wait_window = None


# Add functions to handle saving and loading
def save_map():
    """Save the current map to a file."""
    map_data.save_to_file('map_data.json')
    print("Map saved to 'map_data.json'.")


def handle_mouse_click_road(event):
    if event.type == pygame.MOUSEBUTTONDOWN:  # Ensure the event is a mouse button down event
        if event.button == 1:  # Left mouse button
            # Check if a point was clicked
            for point in map_data.points:
                if pygame.Rect(point[1] - 5, point[2] - 5, 10, 10).collidepoint(event.pos):
                    map_data.toggle_point_selection((point[1], point[2]))
                    break
            # If two points are selected, create a road
            if len(map_data.selected_points) == 2:
                start, end = map_data.selected_points
                map_data.add_road(start, end)
                map_data.selected_points.clear()
        elif event.button == 3:  # Right mouse button
            closest_road = None
            min_distance = float('inf')
            max_distance = 15  # Maximum distance to consider for road removal

            # Find the closest road to the cursor
            for road in map_data.roads:
                start_number, end_number = road
                start = next(p for p in map_data.points if p[0] == start_number)
                end = next(p for p in map_data.points if p[0] == end_number)
                mid_point = ((start[1] + end[1]) // 2, (start[2] + end[2]) // 2)

                # Calculate distance from cursor to the midpoint of the road
                distance = ((event.pos[0] - mid_point[0]) ** 2 + (
                        event.pos[1] - mid_point[1]) ** 2) ** 0.5
                if distance < min_distance and distance <= max_distance:
                    closest_road = (start, end)
                    min_distance = distance

            # Remove the closest road if found
            if closest_road:
                start, end = closest_road
                map_data.remove_road(start, end)


def handle_mouse_click_finish_line(event):
    if event.type == pygame.MOUSEBUTTONDOWN:
        if event.button == 1:  # Left mouse button
            # Find the closest road to the cursor
            closest_road = None
            closest_point_on_road = None
            min_distance = float('inf')
            max_distance = 15  # Maximum distance to consider for finish line placement

            for road in map_data.roads:
                start_number, end_number = road
                start = next(p for p in map_data.points if p[0] == start_number)
                end = next(p for p in map_data.points if p[0] == end_number)

                # Calculate the closest point on the road to the cursor
                road_vector = (end[1] - start[1], end[2] - start[2])
                road_length_squared = road_vector[0] ** 2 + road_vector[1] ** 2
                if road_length_squared == 0:
                    continue  # Skip degenerate roads

                cursor_vector = (event.pos[0] - start[1], event.pos[1] - start[2])
                t = max(0, min(1, (
                        cursor_vector[0] * road_vector[0] + cursor_vector[1] * road_vector[
                    1]) / road_length_squared))
                closest_point = (start[1] + t * road_vector[0], start[2] + t * road_vector[1])

                # Calculate distance from cursor to the closest point
                distance = ((event.pos[0] - closest_point[0]) ** 2 + (
                        event.pos[1] - closest_point[1]) ** 2) ** 0.5
                if distance < min_distance and distance <= max_distance:
                    min_distance = distance
                    closest_road = road
                    closest_point_on_road = closest_point

            # Set the finish line if a road is found
            if closest_road and closest_point_on_road:
                map_data.finish_line['point'] = closest_point_on_road

        elif event.button == 3:  # Right mouse button
            # Remove the finish line
            map_data.finish_line['point'] = None


def handle_mouse_click_checkpoint(event):
    if event.type == pygame.MOUSEBUTTONDOWN:
        if event.button == 1:  # Left mouse button
            # Add a checkpoint at the clicked position
            map_data.add_checkpoint(event.pos)
        elif event.button == 3:  # Right mouse button
            # Remove a checkpoint at the clicked position
            for checkpoint in map_data.checkpoints:
                if pygame.Rect(
                        checkpoint[0] - CHECKPOINT_COLLISION_OFFSET,
                        checkpoint[1] - CHECKPOINT_COLLISION_OFFSET,
                        CHECKPOINT_COLLISION_SIZE,
                        CHECKPOINT_COLLISION_SIZE
                ).collidepoint(event.pos):
                    map_data.remove_checkpoint(checkpoint)
                    break


def draw_coordinate_grid(surface, rect, grid_size=50, color=(0, 0, 0)):
    """Draw a coordinate grid in the specified rectangle."""
    # Draw vertical lines
    for x in range(rect.left, rect.right, grid_size):
        pygame.draw.line(surface, color, (x, rect.top), (x, rect.bottom))
        # Draw x-axis labels
        label = pygame.font.Font(None, 20).render(str(x - rect.left), True, color)
        surface.blit(label, (x + 2, rect.top + 2))

    # Draw horizontal lines
    for y in range(rect.top, rect.bottom, grid_size):
        pygame.draw.line(surface, color, (rect.left, y), (rect.right, y))
        # Draw y-axis labels
        label = pygame.font.Font(None, 20).render(str(y - rect.top), True, color)
        surface.blit(label, (rect.left + 2, y + 2))


# Create an instance of the Map class
map_data = Map()


# Function to handle mouse clicks for adding/removing points
def handle_mouse_click(event):
    if selected_tool == 'Draw Tool' and selected_detailed_tool == 'Point':
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left mouse button
                # Add point only if within the drawing area
                if drawing_area_rect.collidepoint(event.pos):
                    map_data.add_point(event.pos)
            elif event.button == 3:  # Left mouse button
                # Remove point
                for point in map_data.points:
                    if pygame.Rect(point[1] - 5, point[2] - 5, 10, 10).collidepoint(event.pos):
                        map_data.remove_point((point[1], point[2]))
                        break
    elif selected_tool == 'Draw Tool' and selected_detailed_tool == 'Road':
        handle_mouse_click_road(event)
    elif selected_tool == 'Draw Tool' and selected_detailed_tool == 'Finish Line':
        handle_mouse_click_finish_line(event)


def step_by_step_generator():
    global selected_tool, selected_detailed_tool
    step = 1  # Current step in the process
    clock = pygame.time.Clock()

    step_controller = StepController()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return  # Exit the generator

            manager.process_events(event)

            if step == 1:  # Step 1: Create points
                selected_tool = 'Draw Tool'
                selected_detailed_tool = 'Point'
                step_controller.stop_wait_window()
                handle_mouse_click(event)

            elif step == 2:  # Step 2: Connect points with roads
                step_controller.stop_wait_window()
                handle_mouse_click_road(event)

            elif step == 3:  # Step 3: Finish track

                try:
                    map_data.smooth_or_extrapolate_track()
                    for i in range(len(map_data.points)):
                        start = map_data.points[i]
                        end = map_data.points[(i + 1) % len(map_data.points)]
                        map_data.add_road(start, end)

                    step = 4  # Proceed to the next step
                except ValueError as e:
                    print(f"Error: {e}")

                finally:
                    step_controller.stop_wait_window()
                    step_controller.next_step()

            elif step == 4:  # Step 4: Set finish line
                selected_tool = 'Draw Tool'
                selected_detailed_tool = 'Finish Line'
                step_controller.stop_wait_window()
                handle_mouse_click(event)

            elif step == 5:  # Step 5: Add checkpoints
                selected_tool = 'Draw Tool'
                selected_detailed_tool = 'Checkpoint'
                step_controller.stop_wait_window()
                handle_mouse_click_checkpoint(event)

            elif step == 6:  # Step 6: Save to file
                save_map()
                step_controller.stop_wait_window()
                print("Map saved successfully.")
                return  # Exit the generator

        # Draw the UI and map
        window_surface.fill(WHITE)
        pygame.draw.rect(window_surface, GRAY, drawing_area_rect)
        draw_coordinate_grid(window_surface, drawing_area_rect)

        for point in map_data.points:
            number, x, y = point
            color = (0, 0, 255) if point in map_data.selected_points else (255, 0, 0)
            pygame.draw.circle(window_surface, color, (x, y), 5)
            label = pygame.font.Font(None, 20).render(str(number), True, (0, 0, 0))
            window_surface.blit(label, (x + 5, y - 10))

        for start_number, end_number in map_data.roads:
            start = next(p for p in map_data.points if p[0] == start_number)
            end = next(p for p in map_data.points if p[0] == end_number)
            pygame.draw.line(window_surface, (0, 0, 0), (start[1], start[2]), (end[1], end[2]), 2)

        # Draw checkpoints
        for checkpoint in map_data.checkpoints:
            pygame.draw.circle(window_surface, (255, 255, 0), checkpoint, 6)
            label = pygame.font.Font(None, 20).render("Checkpoint", True, (255, 255, 0))
            window_surface.blit(label, (checkpoint[0] + 10, checkpoint[1] - 10))

        if map_data.finish_line['point']:
            finish_point = map_data.finish_line['point']
            pygame.draw.circle(window_surface, (0, 255, 0),
                               (int(finish_point[0]), int(finish_point[1])), 6)
            label = pygame.font.Font(None, 20).render("Finish", True, (0, 255, 0))
            window_surface.blit(label, (int(finish_point[0]) + 10, int(finish_point[1]) - 10))

        manager.update(clock.tick(60) / 1000.0)
        manager.draw_ui(window_surface)
        pygame.display.update()

        step = step_controller.current_step() + 1  # IMPORTANT! index starts from 0


# Call the step-by-step generator
step_by_step_generator()
