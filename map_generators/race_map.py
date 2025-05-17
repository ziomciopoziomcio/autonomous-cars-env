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

    def add_point(self, point):
        """Add a point to the map."""
        if point not in self.points:
            self.points.append(point)

    def remove_point(self, point):
        """Remove a point from the map."""
        if point in self.points:
            self.points.remove(point)

    def toggle_point_selection(self, point):
        """Toggle the selection of a point."""
        if point in self.selected_points:
            self.selected_points.remove(point)
        else:
            self.selected_points.append(point)

    def add_road(self, start, end):
        """Add a road between two points."""
        if (start, end) not in self.roads and (end, start) not in self.roads:
            self.roads.append((start, end))

    def remove_road(self, start, end):
        """Remove a road between two points."""
        if (start, end) in self.roads:
            self.roads.remove((start, end))
        elif (end, start) in self.roads:
            self.roads.remove((end, start))
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
            if pygame.Rect(point[0] - 5, point[1] - 5, 10, 10).collidepoint(event.pos):
                map_data.toggle_point_selection(point)
                break
        # If two points are selected, create a road
        if len(map_data.selected_points) == 2:
            start, end = map_data.selected_points
            map_data.add_road(start, end)
            map_data.selected_points.clear()
    elif event.button == 3:  # Right mouse button
        # Check if a road was clicked
        for road in map_data.roads:
            start, end = road
            mid_point = ((start[0] + end[0]) // 2, (start[1] + end[1]) // 2)
            if pygame.Rect(mid_point[0] - 5, mid_point[1] - 5, 10, 10).collidepoint(event.pos):
                map_data.remove_road(start, end)
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
        if event.button == 3:  # Left mouse button
            # add point
            for point in map_data.points:
                if pygame.Rect(point[0] - 5, point[1] - 5, 10, 10).collidepoint(event.pos):
                    map_data.remove_point(point)
                    break
        elif event.button == 1:  # Right mouse button
            # remove point
            map_data.add_point(event.pos)
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
        color = (0, 0, 255) if point in map_data.selected_points else (255, 0, 0)
        pygame.draw.circle(window_surface, color, point, 5)
        if point in map_data.selected_points:
            index = map_data.selected_points.index(point) + 1
            label = pygame.font.Font(None, 20).render(str(index), True, (0, 0, 0))
            window_surface.blit(label, (point[0] + 5, point[1] - 10))

    # Draw roads
    for start, end in map_data.roads:
        pygame.draw.line(window_surface, (0, 0, 0), start, end, 2)
        # Draw arrowhead for direction
        arrow_size = 10
        direction = (end[0] - start[0], end[1] - start[1])
        length = (direction[0] ** 2 + direction[1] ** 2) ** 0.5
        unit_dir = (direction[0] / length, direction[1] / length)
        arrow_point = (end[0] - unit_dir[0] * arrow_size, end[1] - unit_dir[1] * arrow_size)
        pygame.draw.line(window_surface, (0, 0, 0), arrow_point,
                         (arrow_point[0] - unit_dir[1] * 5, arrow_point[1] + unit_dir[0] * 5), 2)
        pygame.draw.line(window_surface, (0, 0, 0), arrow_point,
                         (arrow_point[0] + unit_dir[1] * 5, arrow_point[1] - unit_dir[0] * 5), 2)

    # Update the UI
    manager.update(time_delta)
    manager.draw_ui(window_surface)

    pygame.display.update()

pygame.quit()
