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

# Main drawing area
drawing_area_rect = pygame.Rect(200, 50, window_size[0] - 200, window_size[1] - 50)


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


# Main loop
clock = pygame.time.Clock()
is_running = True

while is_running:
    time_delta = clock.tick(60) / 1000.0
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            is_running = False

        manager.process_events(event)

    # Draw the background
    window_surface.fill(WHITE)

    # Draw the central drawing area
    pygame.draw.rect(window_surface, GRAY, drawing_area_rect)
    draw_coordinate_grid(window_surface, drawing_area_rect)

    # Update the UI
    manager.update(time_delta)
    manager.draw_ui(window_surface)

    pygame.display.update()

pygame.quit()
