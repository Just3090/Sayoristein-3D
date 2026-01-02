# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True
# cython: initializedcheck=False

"""
Module: stein_core
==================

Description:
    High-performance, native Raycasting and Voxel rendering engine designed for RenPy.
    This module handles computationally intensive tasks (DDA algorithm, collision detection)
    outside the Python interpreter to ensure stable 60+ FPS on mobile and desktop platforms.

Architecture: "Standalone Shared Library" Pattern
-------------------------------------------------
    Unlike traditional Python Extensions (.pyd/.so linked against libpython), this module is 
    compiled as a standalone C shared library. It does not initialize a Python module structure 
    (PyModuleDef) nor interacts with the Python C-API during execution.

    Integration is achieved via Python's 'ctypes' foreign function interface (FFI), treating 
    this module strictly as a dynamic binary library (DLL/Shared Object).

Design Rationale:
    1. Android/RAPT Compatibility:
       RenPy on Android uses a highly customized Python environment. Standard Cython modules 
       often trigger SIGSEGV errors (in 'sem_wait' / 'PyThread_acquire_lock') due to Global 
       Interpreter Lock (GIL) state mismatches during module initialization.
       By bypassing 'PyInit' and the Python C-API entirely, we eliminate ABI conflicts.

    2. Cross-Platform ABI:
       This architecture allows the same rendering logic to be compiled with MSVC (Windows) 
       and CMake/NDK (Android) without version-specific dependencies (e.g., python3.10 vs 3.12),
       as the interface relies solely on C primitives.

Implementation Guidelines:
--------------------------
    * Type Safety: Public functions ('cdef public') must exclusively use standard C types 
      ('int', 'ouble', 'void'). Usage of Python objects ('PyObject*', 'list', 'tuple') or 
      Cython MemoryViews in the public interface is strictly prohibited to prevent GIL acquisition.

    * Memory Addressing: All memory pointers passed from Python must be typed as 'size_t'
      (defined in 'libc.stddef'). Do not use 'long' or 'int' for pointers, as this causes 
      heap corruption on LLP64 architectures (specifically Windows x64).

    * Data Output: Functions should return 'void' or primitive scalars. Complex data 
      structures must be populated via pointer arguments (pass-by-reference buffers) pre-allocated 
      by the host Python application.

Build Instructions:
-------------------
    1. Source Generation:
       $ python -m cython -3 stein_core.pyx -o stein_core.c

    2. Compilation (Windows - MSVC):
       Requires 'stein_core.def' for explicit symbol export.
       $ cl /LD /O2 /Tc stein_core.c /I "PATH_TO_INCLUDE" /link /LIBPATH:"PATH_TO_LIBS" /DEF:stein_core.def

    3. Compilation (Android - CMake):
       Target as a standard shared library. Do not link against 'libpython'. 
       Use flag: `-Wl,` (if necessary).
    
    You can see an example in game/core/notes.txt
"""

from libc.math cimport floor, abs, sqrt
from libc.stddef cimport size_t


cdef public void cast_ray_c(
    double start_x, double start_y, double start_z, 
    double dir_x, double dir_y, double dir_z, 
    size_t flat_map_addr, 
    int map_w, int map_h, int map_layers, int min_layer,
    double max_dist,
    size_t out_addr
):
    cdef int* flat_map = <int*>flat_map_addr
    cdef int* output = <int*>out_addr
    
    output[0] = 0
    
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

    cdef double dist = 0.0
    cdef int side = 0
    cdef int idx = 0
    cdef int layer_offset = 0
    cdef int hit = 0
    
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

    if hit:
        output[0] = 1
        output[1] = map_x
        output[2] = map_y
        output[3] = map_z
        output[4] = side
        output[5] = step_x
        output[6] = step_y
        output[7] = step_z


cdef inline bint is_wall(int x, int y, int z, int w, int h, int layers, int min_layer, int* flat_map):
    if x < 0 or x >= w or y < 0 or y >= h: return 1
    cdef int layer_offset = z - min_layer
    if layer_offset < 0 or layer_offset >= layers: return 0 
    cdef int idx = (layer_offset * w * h) + (x * h) + y
    return flat_map[idx] > 0

cdef public void resolve_movement_c(
    double x, double y, double z,
    double dx, double dy, 
    double radius,
    size_t flat_map_addr, 
    int w, int h, int layers, int min_layer,
    size_t out_addr
):
    cdef int* flat_map = <int*>flat_map_addr
    cdef double* output = <double*>out_addr
    
    cdef double new_x = x + dx
    cdef double new_y = y + dy
    cdef int iz = <int>floor(z + 0.5)
    
    if dx != 0:
        if is_wall(<int>floor(new_x + (radius if dx > 0 else -radius)), <int>floor(y + radius), iz, w, h, layers, min_layer, flat_map) or \
           is_wall(<int>floor(new_x + (radius if dx > 0 else -radius)), <int>floor(y - radius), iz, w, h, layers, min_layer, flat_map):
            if dx > 0: new_x = floor(new_x + radius) - radius - 0.001
            else:      new_x = floor(new_x - radius) + 1.0 + radius + 0.001

    if dy != 0:
        if is_wall(<int>floor(new_x + radius), <int>floor(new_y + (radius if dy > 0 else -radius)), iz, w, h, layers, min_layer, flat_map) or \
           is_wall(<int>floor(new_x - radius), <int>floor(new_y + (radius if dy > 0 else -radius)), iz, w, h, layers, min_layer, flat_map):
            if dy > 0: new_y = floor(new_y + radius) - radius - 0.001
            else:      new_y = floor(new_y - radius) + 1.0 + radius + 0.001

    output[0] = new_x
    output[1] = new_y