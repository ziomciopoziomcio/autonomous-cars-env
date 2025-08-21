import math
import pygame
import components.globals as cg


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


def lines_params_prep(car_rect, finish, inner_line, min_x, min_y, outer_line,
                      scale):
    finish_scaled = scale_points([finish], min_x, min_y, scale)[0]
    outer_closest = min(outer_line, key=lambda p: math.dist(finish_scaled, p))
    inner_closest = min(inner_line, key=lambda p: math.dist(finish_scaled, p))
    angle = math.degrees(
        math.atan2(inner_closest[1] - outer_closest[1], inner_closest[0] - outer_closest[0]))
    finish_width = int(math.dist(outer_closest, inner_closest))
    finish_height = 25
    scaled_finish = pygame.transform.scale(cg.FINISH_TEXTURE, (finish_width, finish_height))
    rotated_finish = pygame.transform.rotate(scaled_finish, -angle)
    finish_rect = rotated_finish.get_rect()
    finish_rect.center = ((outer_closest[0] + inner_closest[0]) // 2,
                          (outer_closest[1] + inner_closest[1]) // 2)
    finish_mask = pygame.mask.from_surface(rotated_finish)
    if car_rect is None:
        offset = (0, 0)
    else:
        offset = (finish_rect.left - car_rect.left, finish_rect.top - car_rect.top)
    return finish_mask, offset, rotated_finish, finish_rect
