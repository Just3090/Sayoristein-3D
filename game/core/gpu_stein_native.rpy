# TODO:
######## Android

# if a xbox gamepad is connected in android, the Axis are mapped like Xbox PC, but
# the other buttons are normally Android gamepad, not like PC.

# Other Android gamepad are mapped like:

### Joysticks

# LeftUp=A4 0 to minus 1
# LeftDown=A4 0 to 1
# LeftLeft=A0 0 to minus 1
# LeftRight=A0 0 to 1

# RightUp=A3 0 to minus 1
# RightDown=A3 0 to 1
# RightLeft=A2 0 to minus 1
# RightRight=A2 0 to 1

### Buttons

# L3=B7
# R3=B8
# Select=B4
# Start=B6
# A=B0
# B=B1
# X=B2
# Y=B3
# L1=B9
# L2=B15
# R1=B10
# R2=B16

### D-Pad
# Up=B11
# Down=B12
# Left=B13
# Right=B14

init -50 python:
    import ctypes
    import sys
    import os

    class RayResult(ctypes.Structure):
        _fields_ = [
            ("hit", ctypes.c_int),
            ("map_x", ctypes.c_int), ("map_y", ctypes.c_int), ("map_z", ctypes.c_int),
            ("side", ctypes.c_int),
            ("step_x", ctypes.c_int), ("step_y", ctypes.c_int), ("step_z", ctypes.c_int)
        ]

    class EnemyData(ctypes.Structure):
        _fields_ = [
            ("x", ctypes.c_double),
            ("y", ctypes.c_double),
            ("z", ctypes.c_double),
            ("dir_x", ctypes.c_double),
            ("dir_y", ctypes.c_double),
            ("hp", ctypes.c_double),
            ("state", ctypes.c_int),
            ("texture_idx", ctypes.c_int),
            ("timer", ctypes.c_double),
            ("move_speed", ctypes.c_double),
            ("enemy_type", ctypes.c_int)
        ]

    class PlayerData(ctypes.Structure):
        _fields_ = [
            ("x", ctypes.c_double),
            ("y", ctypes.c_double),
            ("z", ctypes.c_double),
            ("vel_z", ctypes.c_double),
            ("rot", ctypes.c_double),
            ("is_grounded", ctypes.c_int),
            ("is_crouching", ctypes.c_int)
        ]

    class MoveResult(ctypes.Structure):
        _fields_ = [("x", ctypes.c_double), ("y", ctypes.c_double)]

    class ProjectileData(ctypes.Structure):
        _fields_ = [
            ("x", ctypes.c_double), ("y", ctypes.c_double), ("z", ctypes.c_double),
            ("dir_x", ctypes.c_double), ("dir_y", ctypes.c_double), ("dir_z", ctypes.c_double),
            ("speed", ctypes.c_double),
            ("active", ctypes.c_int),      # 1/0
            ("texture_idx", ctypes.c_int),
            ("pitch", ctypes.c_double),
            ("damage", ctypes.c_int),
            ("from_player", ctypes.c_int)  # 1/0
        ]

    class SteinWrapper:
        ray_out_array = (ctypes.c_int * 8)()
        ray_out_ptr = ctypes.addressof(ray_out_array)
        
        move_out_array = (ctypes.c_double * 2)()
        move_out_ptr = ctypes.addressof(move_out_array)

        @staticmethod
        def update_projectiles_native(proj_addr, count, dt, map_addr, w, h, layers, min_layer):
            stein_lib.update_projectiles_c(
                proj_addr, count, dt, 
                map_addr, w, h, layers, min_layer
            )

        @staticmethod
        def prepare_scene_sprites(px, py, proj_ptr, max_projs, enemy_ptr, num_enemies, static_ptr, num_statics, out_ptr, max_sprites):
            return stein_lib.prepare_scene_sprites_c(
                px, py,
                proj_ptr, max_projs,
                enemy_ptr, num_enemies,
                static_ptr, num_statics,
                out_ptr, max_sprites
            )

        @staticmethod
        def check_line_of_sight(sx, sy, z, tx, ty, map_addr, w, h, layers, min_layer):
            result = stein_lib.check_line_of_sight_c(
                sx, sy, z, tx, ty,
                map_addr, w, h, layers, min_layer
            )
            return result == 1

        @staticmethod
        def get_map_height(x, y, check_z, map_addr, w, h, layers, min_layer):
            return stein_lib.get_map_height_c(
                x, y, check_z, 
                map_addr, w, h, layers, min_layer
            )

        @staticmethod
        def cast_ray_fast(*args):
            stein_lib.cast_ray_c(*args, SteinWrapper.ray_out_ptr)
            if SteinWrapper.ray_out_array[0]:
                return (True, *SteinWrapper.ray_out_array[1:])
            return (False, 0, 0, 0, 0, 0, 0, 0)

        @staticmethod
        def resolve_movement(*args):
            stein_lib.resolve_movement_c(*args, SteinWrapper.move_out_ptr)
            return (SteinWrapper.move_out_array[0], SteinWrapper.move_out_array[1])

        @staticmethod
        def update_player_complete(player_addr, dt, speed, strafe, turn, move_speed, rot_speed, map_addr, w, h, layers, min_layer):
            stein_lib.update_player_complete_c(
                player_addr, dt, 
                speed, strafe, turn, 
                move_speed, rot_speed,
                map_addr, w, h, layers, min_layer
            )

    stein_lib = None
    library_path = None
    USING_CYTHON = False
    STEIN_NATIVE_AVAILABLE = False
    STEIN_NATIVE_ERROR = None

    try:
        if renpy.android:
            library_path = "libstein_core.so"
        
        elif renpy.windows:
            library_path = os.path.join(config.gamedir, "core", "stein_core.dll")
            if not os.path.exists(library_path):
                library_path = os.path.join(config.gamedir, "stein_core.dll")

        elif renpy.linux:
            library_path = os.path.join(config.gamedir, "core", "stein_core.so")

        if library_path:
            stein_lib = ctypes.CDLL(library_path)
            
            stein_lib.cast_ray_c.argtypes = [
                ctypes.c_double, ctypes.c_double, ctypes.c_double,
                ctypes.c_double, ctypes.c_double, ctypes.c_double,
                ctypes.c_void_p,
                ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                ctypes.c_double,
                ctypes.c_void_p
            ]
            stein_lib.cast_ray_c.restype = None

            stein_lib.resolve_movement_c.argtypes = [
                ctypes.c_double, ctypes.c_double, ctypes.c_double,
                ctypes.c_double, ctypes.c_double, ctypes.c_double,
                ctypes.c_void_p,
                ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                ctypes.c_void_p
            ]
            stein_lib.resolve_movement_c.restype = None

            stein_lib.check_line_of_sight_c.argtypes = [
                ctypes.c_double, ctypes.c_double, ctypes.c_double, # Start X, Y, Z
                ctypes.c_double, ctypes.c_double,                  # Target X, Y
                ctypes.c_void_p,                                   # Map Pointer
                ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int # Map Data
            ]
            stein_lib.check_line_of_sight_c.restype = ctypes.c_int

            stein_lib.get_map_height_c.argtypes = [
                ctypes.c_double, ctypes.c_double, ctypes.c_double, # x, y, check_z
                ctypes.c_void_p,                                   # map_ptr
                ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int # w, h, layers, min
            ]
            stein_lib.get_map_height_c.restype = ctypes.c_double

            stein_lib.update_projectiles_c.argtypes = [
                ctypes.c_void_p, ctypes.c_int, ctypes.c_double, # array, count, dt
                ctypes.c_void_p,                                # map_ptr
                ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int
            ]
            stein_lib.update_projectiles_c.restype = None

            stein_lib.prepare_scene_sprites_c.argtypes = [
                ctypes.c_double, ctypes.c_double,
                ctypes.c_void_p, ctypes.c_int,
                ctypes.c_void_p, ctypes.c_int,
                ctypes.c_void_p, ctypes.c_int,
                ctypes.c_void_p, ctypes.c_int
            ]
            stein_lib.prepare_scene_sprites_c.restype = ctypes.c_int

            stein_lib.update_enemies_c.argtypes = [
                ctypes.c_void_p,    # enemies_addr (pointer to array)
                ctypes.c_int,       # count
                ctypes.c_double, ctypes.c_double, ctypes.c_double, # player x, y, z
                ctypes.c_double,    # dt
                ctypes.c_void_p,    # flat_map_addr
                ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int # map dimensions
            ]
            stein_lib.update_enemies_c.restype = None

            stein_lib.check_hitscan_c.argtypes = [
                ctypes.c_double, ctypes.c_double, ctypes.c_double, # ray origin
                ctypes.c_double, ctypes.c_double, ctypes.c_double, # ray dir
                ctypes.c_void_p,    # enemies_addr
                ctypes.c_int,       # count
                ctypes.c_double,    # max_dist
                ctypes.c_double     # damage
            ]
            stein_lib.check_hitscan_c.restype = ctypes.c_int # Returns index of hit enemy (-1 if none)

            stein_lib.update_player_physics_c.argtypes = [
                ctypes.c_void_p,    # player_addr (pointer to PlayerData struct)
                ctypes.c_double,    # dt
                ctypes.c_void_p,    # flat_map_addr
                ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int # map dimensions
            ]
            stein_lib.update_player_physics_c.restype = None

            stein_lib.update_player_complete_c.argtypes = [
                ctypes.c_void_p,    # player_addr
                ctypes.c_double,    # dt
                ctypes.c_double, ctypes.c_double, ctypes.c_double, # inputs: speed, strafe, turn
                ctypes.c_double, ctypes.c_double, # stats: move_speed, rot_speed
                ctypes.c_void_p,    # map_addr
                ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int
            ]
            stein_lib.update_player_complete_c.restype = None

            SteinWrapper.stein_lib = stein_lib

            sys.modules["stein_core"] = SteinWrapper
            print(f"Sayoristein: Native motor loaded in {library_path}")
            USING_CYTHON = True
            STEIN_NATIVE_AVAILABLE = True

    except Exception as e:
        STEIN_NATIVE_ERROR = str(e)
        print(f"Sayoristein Error Loading Library: {e}")

    stein_native_available = STEIN_NATIVE_AVAILABLE
    stein_native_error = STEIN_NATIVE_ERROR

