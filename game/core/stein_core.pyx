# cython: language_level=3
# stein_core.pyx

from libc.math cimport floor, abs, sqrt

ctypedef int[:] MapBuffer

cpdef tuple cast_ray_fast(
    double start_x, double start_y, double start_z, 
    double dir_x, double dir_y, double dir_z, 
    MapBuffer flat_map, 
    int map_w, int map_h, int map_layers, int min_layer,
    double max_dist=100.0
):
    cdef int map_x = <int>floor(start_x)
    cdef int map_y = <int>floor(start_y)
    cdef int map_z = <int>floor(start_z)
    cdef double delta_dist_x = abs(1.0 / dir_x) if dir_x != 0 else 1e30
    cdef double delta_dist_y = abs(1.0 / dir_y) if dir_y != 0 else 1e30
    cdef double delta_dist_z = abs(1.0 / dir_z) if dir_z != 0 else 1e30
    cdef int step_x = 1 if dir_x > 0 else -1
    cdef int step_y = 1 if dir_y > 0 else -1
    cdef int step_z = 1 if dir_z > 0 else -1
    cdef double side_dist_x, side_dist_y, side_dist_z
    
    if dir_x > 0: side_dist_x = (map_x + 1.0 - start_x) * delta_dist_x
    else:         side_dist_x = (start_x - map_x) * delta_dist_x
    if dir_y > 0: side_dist_y = (map_y + 1.0 - start_y) * delta_dist_y
    else:         side_dist_y = (start_y - map_y) * delta_dist_y
    if dir_z > 0: side_dist_z = (map_z + 1.0 - start_z) * delta_dist_z
    else:         side_dist_z = (start_z - map_z) * delta_dist_z

    cdef bint hit = 0
    cdef int side = 0
    cdef double dist = 0.0
    cdef int idx = 0
    cdef int layer_offset = 0
    
    with nogil:
        while dist < max_dist:
            if side_dist_x < side_dist_y:
                if side_dist_x < side_dist_z:
                    dist = side_dist_x
                    side_dist_x += delta_dist_x
                    map_x += step_x
                    side = 0
                else:
                    dist = side_dist_z
                    side_dist_z += delta_dist_z
                    map_z += step_z
                    side = 2
            else:
                if side_dist_y < side_dist_z:
                    dist = side_dist_y
                    side_dist_y += delta_dist_y
                    map_y += step_y
                    side = 1
                else:
                    dist = side_dist_z
                    side_dist_z += delta_dist_z
                    map_z += step_z
                    side = 2
            
            if map_z == -1: 
                hit = 1
                break
            if map_x < 0 or map_x >= map_w or map_y < 0 or map_y >= map_h:
                continue
            layer_offset = map_z - min_layer
            if layer_offset >= 0 and layer_offset < map_layers:
                idx = (layer_offset * map_w * map_h) + (map_x * map_h) + map_y
                if flat_map[idx] > 0:
                    hit = 1
                    break
    if hit: return (True, map_x, map_y, map_z, side, step_x, step_y, step_z)
    return (False, 0, 0, 0, 0, 0, 0, 0)


cdef inline bint is_wall(int x, int y, int z, int w, int h, int layers, int min_layer, MapBuffer flat_map):
    if x < 0 or x >= w or y < 0 or y >= h: return 1
    cdef int layer_offset = z - min_layer
    if layer_offset < 0 or layer_offset >= layers: return 0 
    cdef int idx = (layer_offset * w * h) + (x * h) + y
    return flat_map[idx] > 0

cpdef tuple resolve_movement(
    double x, double y, double z,
    double dx, double dy, 
    double radius,
    MapBuffer flat_map, 
    int w, int h, int layers, int min_layer
):
    cdef double new_x = x + dx
    cdef double new_y = y + dy
    
    cdef int iz = <int>floor(z + 0.5)
    
    # X
    if dx != 0:
        if is_wall(<int>floor(new_x + (radius if dx > 0 else -radius)), <int>floor(y + radius), iz, w, h, layers, min_layer, flat_map) or \
           is_wall(<int>floor(new_x + (radius if dx > 0 else -radius)), <int>floor(y - radius), iz, w, h, layers, min_layer, flat_map):
            if dx > 0:
                new_x = floor(new_x + radius) - radius - 0.001
            else:
                new_x = floor(new_x - radius) + 1.0 + radius + 0.001

    # Y
    if dy != 0:
        if is_wall(<int>floor(new_x + radius), <int>floor(new_y + (radius if dy > 0 else -radius)), iz, w, h, layers, min_layer, flat_map) or \
           is_wall(<int>floor(new_x - radius), <int>floor(new_y + (radius if dy > 0 else -radius)), iz, w, h, layers, min_layer, flat_map):
            if dy > 0:
                new_y = floor(new_y + radius) - radius - 0.001
            else:
                new_y = floor(new_y - radius) + 1.0 + radius + 0.001

    return (new_x, new_y)