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

# Create UI elements
toolbar_rect = pygame.Rect(0, 0, window_size[0], 50)  # Top toolbar
toolbar_panel = pygame_gui.elements.UIPanel(
    relative_rect=toolbar_rect,
    manager=manager
)

layers_rect = pygame.Rect(0, 50, 200, window_size[1] - 50)  # Left sidebar
layers_panel = pygame_gui.elements.UIPanel(
    relative_rect=layers_rect,
    manager=manager
)

# Add buttons to the toolbar
select_tool_button = pygame_gui.elements.UIButton(
    relative_rect=pygame.Rect(10, 10, 100, 30),
    text='Select Tool',
    manager=manager,
    container=toolbar_panel
)

draw_tool_button = pygame_gui.elements.UIButton(
    relative_rect=pygame.Rect(120, 10, 100, 30),
    text='Draw Tool',
    manager=manager,
    container=toolbar_panel
)

# Add a list to the layers panel
layers_list = pygame_gui.elements.UISelectionList(
    relative_rect=pygame.Rect(10, 10, 180, 400),
    item_list=['Layer 1', 'Layer 2', 'Layer 3'],
    manager=manager,
    container=layers_panel
)

# Add buttons for "Draw Tool" options
point_button = pygame_gui.elements.UIButton(
    relative_rect=pygame.Rect(240, 10, 100, 30),
    text='Point',
    manager=manager,
    container=toolbar_panel,
    visible=False  # Initially hidden
)

road_button = pygame_gui.elements.UIButton(
    relative_rect=pygame.Rect(350, 10, 100, 30),
    text='Road',
    manager=manager,
    container=toolbar_panel,
    visible=False  # Initially hidden
)

finish_line_button = pygame_gui.elements.UIButton(
    relative_rect=pygame.Rect(460, 10, 100, 30),
    text='Finish Line',
    manager=manager,
    container=toolbar_panel,
    visible=False  # Initially hidden
)

# Add buttons for saving and loading the map
save_map_button = pygame_gui.elements.UIButton(
    relative_rect=pygame.Rect(570, 10, 100, 30),
    text='Save Map',
    manager=manager,
    container=toolbar_panel
)

load_map_button = pygame_gui.elements.UIButton(
    relative_rect=pygame.Rect(680, 10, 100, 30),
    text='Load Map',
    manager=manager,
    container=toolbar_panel
)

finish_track_button = pygame_gui.elements.UIButton(
    relative_rect=pygame.Rect(790, 10, 100, 30),
    text='Finish Track',
    manager=manager,
    container=toolbar_panel
)


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


# Update the layers list to display Points, Roads, and Finish Line
def update_layers_list():
    """Update the layers list with current map data."""
    items = ["Points:"]
    for point in map_data.points:
        items.append(f"  - {point}")

    items.append("Roads:")
    for start, end in map_data.roads:
        items.append(f"  - {start} -> {end}")

    items.append("Finish Line:")
    if map_data.finish_line['point']:
        items.append(f"  - {map_data.finish_line['point']}")
    else:
        items.append("  - Not Set")

    layers_list.set_item_list(items)


# Main drawing area
drawing_area_rect = pygame.Rect(200, 50, window_size[0] - 200, window_size[1] - 50)

# Variables to track the selected tool
selected_tool = None
selected_detailed_tool = None


class Map:
    def __init__(self):
        self.points = []
        self.roads = []
        self.finish_line = {'point': None}
        self.selected_points = []

    def add_point(self, position):
        """Add a point to the map with a unique number."""
        if not any(p[1:] == position for p in self.points):  # Check if position already exists
            point_number = len(self.points) + 1
            self.points.append((point_number, *position))

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
        if (start_number, end_number) not in self.roads and (end_number, start_number) not in self.roads:
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

    # FILE

    def to_dict(self):
        """Convert the map data to a dictionary."""
        return {
            'points': self.points,
            'roads': self.roads,
            'finish_line': self.finish_line
        }

    def from_dict(self, data):
        """Load the map data from a dictionary."""
        self.points = data.get('points', [])
        self.roads = data.get('roads', [])
        self.finish_line = data.get('finish_line', {'point': None})

    def generate_track_width(self, width=20):
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
                finish_point = center_line.interpolate(center_line.project(Point(finish_point))).coords[0]
                self.finish_line['point'] = finish_point

        return inner, outer.tolist()

    def save_to_file(self, file_path):
        """Save the map data to a JSON file, including inner and outer points."""
        inner_points, outer_points = self.generate_track_width()
        data = {
            'points': self.points,
            'roads': self.roads,
            'finish_line': self.finish_line,
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
    def __init__(self):
        self.steps = []  # List of steps (functions)
        self.current_index = 0  # Current step index

        self.steps_initializer()
        self.window_initializer()

    def window_initializer(self):
        """Initialize TKinter step controller window."""
        root = tk.Tk()
        root.withdraw()

        next_button = tk.Button(root, text="Next Step", command=self.next_step)
        next_button.pack(side=tk.RIGHT, padx=10, pady=10)
        prev_button = tk.Button(root, text="Previous Step", command=self.previous_step)
        prev_button.pack(side=tk.LEFT, padx=10, pady=10)
        root.title("Step Controller")
        root.geometry("200x100")
        root.deiconify()

    def steps_initializer(self):
        """Initialize the steps for the controller."""
        self.add_step(lambda: print("Step 1: Create points"))
        self.add_step(lambda: print("Step 2: Connect points with roads"))
        self.add_step(lambda: print("Step 3: Smooth or extrapolate track"))
        self.add_step(lambda: print("Step 4: Set finish line"))
        self.add_step(lambda: print("Step 5: Save to file"))

    def add_step(self, step_function):
        """Add a step to the controller."""
        self.steps.append(step_function)

    def next_step(self):
        """Move to the next step if available."""
        if self.current_index < len(self.steps) - 1:
            self.current_index += 1

    def current_step(self):
        """Return the current step function."""
        if self.steps:
            return self.steps[self.current_index]
        return None

    def run_current_step(self, *args, **kwargs):
        """Run the current step function."""
        step_function = self.current_step()
        if step_function:
            step_function(*args, **kwargs)


def handle_button_click(event):
    """Handle button click events."""
    global selected_tool
    global selected_detailed_tool
    if event.ui_element == select_tool_button:
        selected_tool = 'Select Tool'
        # Hide "Draw Tool" options
        point_button.hide()
        road_button.hide()
        finish_line_button.hide()
    elif event.ui_element == draw_tool_button:
        selected_tool = 'Draw Tool'
        # Show "Draw Tool" options
        point_button.show()
        road_button.show()
        finish_line_button.show()
    elif event.ui_element == point_button:
        selected_detailed_tool = 'Point'
    elif event.ui_element == road_button:
        selected_detailed_tool = 'Road'
    elif event.ui_element == finish_line_button:
        selected_detailed_tool = 'Finish Line'
    elif event.ui_element == save_map_button:
        save_map()
    elif event.ui_element == load_map_button:
        load_map()
    elif event.ui_element == finish_track_button:
        try:
            map_data.smooth_or_extrapolate_track()
            for i in range(len(map_data.points)):
                start = map_data.points[i]
                end = map_data.points[(i + 1) % len(map_data.points)]  # Connect last point to the first
                map_data.add_road(start, end)
            update_layers_list()
            print("Track smoothed or extrapolated successfully.")
        except ValueError as e:
            print(f"Error: {e}")


# Add functions to handle saving and loading
def save_map():
    """Save the current map to a file."""
    map_data.save_to_file('map_data.json')
    print("Map saved to 'map_data.json'.")


def load_map():
    """Load the map from a file."""
    map_data.load_from_file('map_data.json')
    update_layers_list()
    print("Map loaded from 'map_data.json'.")


# Function to handle mouse clicks for the "Road" tool
def handle_mouse_click_road(event):
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
            distance = ((event.pos[0] - mid_point[0]) ** 2 + (event.pos[1] - mid_point[1]) ** 2) ** 0.5
            if distance < min_distance and distance <= max_distance:
                min_distance = distance
                closest_road = (start, end)

        # Remove the closest road if found
        if closest_road:
            start, end = closest_road
            map_data.remove_road(start, end)


def handle_mouse_click_finish_line(event):
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
                    cursor_vector[0] * road_vector[0] + cursor_vector[1] * road_vector[1]) / road_length_squared))
            closest_point = (start[1] + t * road_vector[0], start[2] + t * road_vector[1])

            # Calculate distance from cursor to the closest point
            distance = ((event.pos[0] - closest_point[0]) ** 2 + (event.pos[1] - closest_point[1]) ** 2) ** 0.5
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

# Replace the layers list initialization
layers_list = pygame_gui.elements.UISelectionList(
    relative_rect=pygame.Rect(10, 10, 180, 400),
    item_list=[],
    manager=manager,
    container=layers_panel
)

# Call update_layers_list whenever map data changes
map_data.add_point = lambda point: (Map.add_point(map_data, point), update_layers_list())
map_data.remove_point = lambda point: (Map.remove_point(map_data, point), update_layers_list())
map_data.add_road = lambda start, end: (
    Map.add_road(map_data, start, end), update_layers_list())
map_data.remove_road = lambda start, end: (Map.remove_road(map_data, start, end), update_layers_list())
map_data.set_finish_line = lambda start, end: (Map.set_finish_line(map_data, start, end), update_layers_list())


# Function to handle mouse clicks for adding/removing points
def handle_mouse_click(event):
    if selected_tool == 'Draw Tool' and selected_detailed_tool == 'Point':
        if event.button == 1:  # Right mouse button
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


# Main loop
clock = pygame.time.Clock()
is_running = True

while is_running:
    time_delta = clock.tick(60) / 1000.0
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            is_running = False

        manager.process_events(event)
        # Handle button clicks
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            handle_button_click(event)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            handle_mouse_click(event)

    # Draw the background
    window_surface.fill(WHITE)

    # Draw the central drawing area
    pygame.draw.rect(window_surface, GRAY, drawing_area_rect)
    draw_coordinate_grid(window_surface, drawing_area_rect)

    # Draw points
    for point in map_data.points:
        number, x, y = point
        color = (0, 0, 255) if point in map_data.selected_points else (255, 0, 0)
        pygame.draw.circle(window_surface, color, (x, y), 5)
        label = pygame.font.Font(None, 20).render(str(number), True, (0, 0, 0))
        window_surface.blit(label, (x + 5, y - 10))

    # Draw roads
    for start_number, end_number in map_data.roads:
        start = next(p for p in map_data.points if p[0] == start_number)
        end = next(p for p in map_data.points if p[0] == end_number)
        pygame.draw.line(window_surface, (0, 0, 0), (start[1], start[2]), (end[1], end[2]), 2)
        # Draw arrowhead for direction
        arrow_size = 10
        direction = (end[1] - start[1], end[2] - start[2])
        length = (direction[0] ** 2 + direction[1] ** 2) ** 0.5
        unit_dir = (direction[0] / length, direction[1] / length)
        arrow_point = (end[1] - unit_dir[0] * arrow_size, end[2] - unit_dir[1] * arrow_size)
        pygame.draw.line(window_surface, (0, 0, 0), arrow_point,
                         (arrow_point[0] - unit_dir[1] * 5, arrow_point[1] + unit_dir[0] * 5), 4)
        pygame.draw.line(window_surface, (0, 0, 0), arrow_point,
                         (arrow_point[0] + unit_dir[1] * 5, arrow_point[1] - unit_dir[0] * 5), 4)

    # Draw the finish line
    if map_data.finish_line['point']:
        finish_point = map_data.finish_line['point']
        pygame.draw.circle(window_surface, (0, 255, 0), (int(finish_point[0]), int(finish_point[1])),
                           6)  # Green point
        label = pygame.font.Font(None, 20).render("Finish", True, (0, 255, 0))
        window_surface.blit(label, (int(finish_point[0]) + 10, int(finish_point[1]) - 10))

    # Update the UI
    manager.update(time_delta)
    manager.draw_ui(window_surface)

    update_layers_list()

    pygame.display.update()

pygame.quit()
