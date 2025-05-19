import pygame
import pygame_gui

# Initialize pygame and pygame_gui
pygame.init()
pygame.display.set_caption('Map Editor')
window_size = (800, 600)
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
    if map_data.finish_line['start'] and map_data.finish_line['end']:
        items.append(f"  - {map_data.finish_line['start']} -> {map_data.finish_line['end']}")
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
        self.numbers_of_roads = 0
        self.roads = [{'start': None, 'end': None} for _ in range(self.numbers_of_roads)]
        self.finish_line = {
            'start': None,
            'end': None
        }
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
        """Add a road between two points using their numbers."""
        start_number = start[0]
        end_number = end[0]
        if (start_number, end_number) not in self.roads and (end_number, start_number) not in self.roads:
            self.roads.append((start_number, end_number))

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
map_data.add_road = lambda start, end: (Map.add_road(map_data, start, end), update_layers_list())
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
    if selected_tool == 'Draw Tool' and selected_detailed_tool == 'Road':
        handle_mouse_click_road(event)


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

    # Update the UI
    manager.update(time_delta)
    manager.draw_ui(window_surface)

    update_layers_list()

    pygame.display.update()

pygame.quit()
