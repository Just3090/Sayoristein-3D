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
            ("from_player", ctypes.c_int), # 1/0
            ("hit_target", ctypes.c_int)   # -1=None, -2=Player, >=0 EnemyIndex
        ]

    class SteinWrapper:
        ray_out_array = (ctypes.c_int * 8)()
        ray_out_ptr = ctypes.addressof(ray_out_array)
        
        move_out_array = (ctypes.c_double * 2)()
        move_out_ptr = ctypes.addressof(move_out_array)

        raycast_mesh_out_array = (ctypes.c_double * 5)()
        raycast_mesh_out_ptr = ctypes.addressof(raycast_mesh_out_array)

        @staticmethod
        def update_projectiles_native(proj_addr, count, enemy_ptr, num_enemies, player_ptr, dt, map_addr, w, h, layers, min_layer):
            stein_lib.update_projectiles_c(
                proj_addr, count, 
                enemy_ptr, num_enemies,
                player_ptr,
                dt, 
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

        @staticmethod
        def raycast_triangles(ro_x, ro_y, ro_z, rd_x, rd_y, rd_z, v_addr, i_addr, num_tris):
            stein_lib.raycast_triangles_c(
                ro_x, ro_y, ro_z,
                rd_x, rd_y, rd_z,
                v_addr, i_addr, num_tris,
                SteinWrapper.raycast_mesh_out_ptr
            )
            if SteinWrapper.raycast_mesh_out_array[0] > 0.5:
                return (True, SteinWrapper.raycast_mesh_out_array[1], SteinWrapper.raycast_mesh_out_array[2], SteinWrapper.raycast_mesh_out_array[3], SteinWrapper.raycast_mesh_out_array[4])
            return (False, 0.0, 0.0, 0.0, 0.0)

    stein_lib = None
    library_path = None
    USING_CYTHON = False

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
                ctypes.c_void_p, ctypes.c_int,                  # array, count
                ctypes.c_void_p, ctypes.c_int,                  # enemies, num
                ctypes.c_void_p,                                # player
                ctypes.c_double,                                # dt
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

            stein_lib.raycast_triangles_c.argtypes = [
                ctypes.c_double, ctypes.c_double, ctypes.c_double,
                ctypes.c_double, ctypes.c_double, ctypes.c_double,
                ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int,
                ctypes.c_void_p
            ]
            stein_lib.raycast_triangles_c.restype = None

            SteinWrapper.stein_lib = stein_lib

            sys.modules["stein_core"] = SteinWrapper
            print(f"Sayoristein: Native motor loaded in {library_path}")
            USING_CYTHON = True

    except Exception as e:
        print(f"Sayoristein Error Loading Library: {e}")

init -10 python:
    import sys
    import os
    import ctypes
    import array

    core_path = os.path.join(config.gamedir, "core")
    if core_path not in sys.path:
        sys.path.append(core_path)

    try:
        import stein_core
    except ImportError:
        if not USING_CYTHON:
            raise ImportError("ERROR: stein_core lib is not loaded.")


    def flatten_world_map(world_map, width, height, min_layer, max_layer):
        num_layers = max_layer - min_layer + 1
        total_size = width * height * num_layers
        
        flat = array.array('i', [0] * total_size)
        solid_count = 0
        
        # Use Duck Typing for RenPy Revertable types
        if hasattr(world_map, 'items'):
            # print(f"DEBUG: WorldMap Keys: {list(world_map.keys())}")
            for z, grid in world_map.items():
                try:
                    layer_idx = int(z) - min_layer
                except:
                    # print(f"DEBUG: Skipped non-int layer {z}")
                    continue 
                
                if layer_idx < 0 or layer_idx >= num_layers: 
                    # print(f"DEBUG: Layer {z} out of bounds {layer_idx}/{num_layers}")
                    continue
                
                base_idx = layer_idx * width * height
                # print(f"DEBUG: Processing Layer {z}. Rows: {len(grid)}")
                for x in range(min(len(grid), width)):
                    row = grid[x]
                    # if layer_idx == 0 and x == 0:
                    #    print(f"DEBUG MAP ROW sample: {row}")
                    
                    for y in range(min(len(row), height)):
                        if row[y] > 0:
                            flat[base_idx + (x * height) + y] = row[y]
                            solid_count += 1
                            
        elif isinstance(world_map, list):
            layer_idx = 0 - min_layer
            if 0 <= layer_idx < num_layers:
                base_idx = layer_idx * width * height
                for x in range(min(len(world_map), width)):
                    row = world_map[x]
                    for y in range(min(len(row), height)):
                        if row[y] > 0:
                            flat[base_idx + (x * height) + y] = row[y]
                            solid_count += 1

        return flat

    SLOT_MELEE   = 0
    SLOT_HANDGUN = 1
    SLOT_LONG    = 2
    SLOT_SPECIAL = 3

    renpy.register_shader("stein.raycaster", variables="""
        uniform float u_volumetric_clouds;
        uniform float u_rain_intensity;
        uniform float u_snow_intensity;
        uniform float u_wetness;
        uniform float u_time_of_day;
        uniform float u_time;
        uniform vec2 u_resolution;
        uniform vec2 u_player_pos;
        uniform vec2 u_player_dir;
        uniform vec2 u_player_plane;
        uniform float u_pitch;
        uniform float u_z_offset;
        uniform float u_vertical_scale;
        uniform sampler2D u_sky_texture;
        uniform sampler2D u_map_texture;
        uniform sampler2D u_selection_texture;
        uniform vec2 u_map_size;
        uniform float u_map_layer_base_y;
        uniform float u_map_layer_count;
        uniform vec2 u_map_layer_norm_size; // (w_norm, h_norm) of a single layer cell
        uniform float u_map_grid_cols; // Number of columns in the grid
        uniform vec2 u_map_tex_pixel_size;
        uniform vec2 u_map_uv_scale;
        uniform sampler2D u_wall_atlas; 
        uniform sampler2D u_floor_texture;
        uniform float u_num_textures;
        uniform sampler2D u_sprite_atlas; 
        uniform float u_num_sprite_textures;
        uniform vec4 u_sprites[64]; // x, y, texture_id, pitch_offset
        uniform int u_num_active_sprites;
        uniform vec4 u_objects[128]; // xyz=pos, w=model_id
        uniform vec4 u_obj_origins[128]; // Original world position packed as vec4
        uniform vec4 u_obj_rots[128]; // xyz=euler angles (radians), w=unused
        uniform vec4 u_obj_scales[128]; // xyz=scale, w=unused
        uniform float u_num_objects;
        uniform sampler2D u_model_atlas;
        uniform float u_num_models;
        uniform float u_flash_intensity;
        uniform vec4 u_light_positions[16];
        uniform float u_num_active_lights;
        uniform float u_flashlight_active;
        uniform vec2 u_flashlight_bob;
        uniform float u_soft_shadows;
        uniform float u_enable_shadows;
        uniform float u_max_dist;
        uniform float u_simple_floor;
        uniform float u_obj_scale;
        uniform vec3 u_highlight_pos;
        uniform vec3 u_pivot_pos;
        uniform vec3 u_group_offsets[16];
        uniform float u_group_rots[16];
        uniform vec3 u_group_pivots[16];
        uniform vec3 u_ambient_color;
        uniform vec3 u_ambient_near_color;
        varying vec2 v_tex_coord;
        attribute vec2 a_tex_coord;
    """, vertex_200="""
        v_tex_coord = a_tex_coord;
    """, fragment_functions="""
        float hash(vec2 p) {
            p = fract(p * vec2(123.34, 456.21));
            p += dot(p, p + 45.32);
            return fract(p.x * p.y);
        }

        mat3 eulerToMat3(vec3 euler) {
            float cx = cos(euler.x); float sx = sin(euler.x);
            float cy = cos(euler.y); float sy = sin(euler.y);
            float cz = cos(euler.z); float sz = sin(euler.z);
            
            // GLSL is Column-Major: mat3(col0, col1, col2)
            mat3 mx = mat3(1, 0, 0,  0, cx, sx,  0, -sx, cx);
            mat3 my = mat3(cy, 0, -sy,  0, 1, 0,  sy, 0, cy);
            mat3 mz = mat3(cz, sz, 0,  -sz, cz, 0,  0, 0, 1);
            
            return mz * my * mx;
        }

        float noise(vec2 p) {
            vec2 i = floor(p);
            vec2 f = fract(p);
            f = f * f * (3.0 - 2.0 * f);
            float a = hash(i);
            float b = hash(i + vec2(1.0, 0.0));
            float c = hash(i + vec2(0.0, 1.0));
            float d = hash(i + vec2(1.0, 1.0));
            return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
        }

        float fbm(vec2 p) {
            float v = 0.0;
            float a = 0.5;
            for (int i = 0; i < 5; i++) {
                v += a * noise(p);
                p *= 2.0;
                a *= 0.5;
            }
            return v;
        }

        float ripple_layer(vec2 uv, float t) {
            vec2 p = uv * 5.0;
            vec2 g = floor(p);
            vec2 f = fract(p) - 0.5;
            
            vec2 rand_offset = (vec2(hash(g), hash(g + 11.5)) - 0.5) * 0.8;
            f -= rand_offset;
            
            float h = hash(g + vec2(3.0, 7.0));
            float t_local = fract(t * 1.2 + h * 10.0);
            
            float d = length(f);
            float r = 0.5 * t_local;
            
            float circle = smoothstep(0.05, 0.0, abs(d - r));
            float fade = 1.0 - t_local;
            
            return circle * fade;
        }

        float rain_layer(vec2 uv, float t) {
            vec2 st = uv;
            st.x *= 20.0; 
            st.y *= 0.5;  
            
            vec2 g = floor(st);
            
            float col_offset = hash(vec2(g.x, 0.0)); 
            float y_move = st.y + t + col_offset * 10.0;
            
            float cell_y = floor(y_move);
            float cell_fract = fract(y_move);
            
            float h = hash(vec2(g.x, cell_y));
            
            if (h < 0.85) return 0.0;
            
            float drop = 1.0 - cell_fract; 
            float beam = smoothstep(0.4, 0.5, fract(st.x)) * smoothstep(0.6, 0.5, fract(st.x));
            
            return drop * beam;
        }

        float intersectAABB(vec3 rayOrigin, vec3 rayDir, vec3 boxMin, vec3 boxMax, out float tFar) {
            vec3 tMin = (boxMin - rayOrigin) / rayDir;
            vec3 tMax = (boxMax - rayOrigin) / rayDir;
            vec3 t1 = min(tMin, tMax);
            vec3 t2 = max(tMin, tMax);
            float tNear = max(max(t1.x, t1.y), t1.z);
            tFar = min(min(t2.x, t2.y), t2.z);
            return tNear;
        }

        float intersectPyramid(vec3 ro, vec3 rd, out vec3 outNormal) {
            float tMin = 10000.0;
            bool hit = false;
            
            vec3 N[4]; float D[4];
            N[0] = vec3(1.0, 0.0, 1.0); D[0] = -1.0;
            N[1] = vec3(-1.0, 0.0, 1.0); D[1] = 0.0;
            N[2] = vec3(0.0, 1.0, 1.0); D[2] = -1.0;
            N[3] = vec3(0.0, -1.0, 1.0); D[3] = 0.0;
            
            for(int i=0; i<4; i++) {
                float denom = dot(rd, N[i]);
                if (denom < -0.0001) {
                    float t = -(dot(ro, N[i]) + D[i]) / denom;
                    if (t > 0.0) {
                        vec3 p = ro + rd * t;
                        if (p.z >= 0.0 && p.z <= 0.5) {
                            float h = 0.5 - p.z;
                            if (p.x >= 0.5 - h - 0.01 && p.x <= 0.5 + h + 0.01 &&
                                p.y >= 0.5 - h - 0.01 && p.y <= 0.5 + h + 0.01) {
                                if (t < tMin) {
                                    tMin = t;
                                    outNormal = normalize(N[i]);
                                    hit = true;
                                }
                            }
                        }
                    }
                }
            }
            if (hit) return tMin;
            return -1.0;
        }
    """, fragment_300="""
        const int MAX_STEPS = 400; 
        
        vec2 stein_uv = v_tex_coord;

        // RAY GENERATION (3D)
        // Player Position (Camera Origin). Z=1.6 is eye level + offsets
        vec3 rayPos = vec3(u_player_pos.x, u_player_pos.y, 1.6 + u_z_offset);
        
        // Pitch Angle
        float pitchAngle = atan(u_pitch);
        float cp = cos(pitchAngle);
        float sp = sin(pitchAngle);
        vec3 rightAxis = normalize(vec3(u_player_plane, 0.0));

        // Ray Direction
        float cameraX = 2.0 * stein_uv.x - 1.0; 
        float screenY = (0.5 - stein_uv.y) * 2.0; 
        
        vec3 baseDir = vec3(u_player_dir, 0.0) + vec3(u_player_plane, 0.0) * cameraX + vec3(0.0, 0.0, 1.0) * (screenY / u_vertical_scale);
        
        vec3 rayDir = baseDir * cp + cross(rightAxis, baseDir) * sp + rightAxis * dot(rightAxis, baseDir) * (1.0 - cp);
        rayDir = normalize(rayDir);

        vec3 flashBase = vec3(u_player_dir, 0.0) + vec3(u_player_plane, 0.0) * u_flashlight_bob.x + vec3(0.0, 0.0, 1.0) * u_flashlight_bob.y;
        vec3 flashDir = flashBase * cp + cross(rightAxis, flashBase) * sp + rightAxis * dot(rightAxis, flashBase) * (1.0 - cp);
        flashDir = normalize(flashDir);
        
        // DDA SETUP
        ivec3 mapPos = ivec3(floor(rayPos));
        vec3 deltaDist = abs(1.0 / rayDir);
        ivec3 stepDir;
        vec3 sideDist;
        
        if (rayDir.x < 0.0) { stepDir.x = -1; sideDist.x = (rayPos.x - float(mapPos.x)) * deltaDist.x; }
        else                { stepDir.x = 1;  sideDist.x = (float(mapPos.x) + 1.0 - rayPos.x) * deltaDist.x; }
        
        if (rayDir.y < 0.0) { stepDir.y = -1; sideDist.y = (rayPos.y - float(mapPos.y)) * deltaDist.y; }
        else                { stepDir.y = 1;  sideDist.y = (float(mapPos.y) + 1.0 - rayPos.y) * deltaDist.y; }
        
        if (rayDir.z < 0.0) { stepDir.z = -1; sideDist.z = (rayPos.z - float(mapPos.z)) * deltaDist.z; }
        else                { stepDir.z = 1;  sideDist.z = (float(mapPos.z) + 1.0 - rayPos.z) * deltaDist.z; }

        // DDA LOOP (3D)
        int hit = 0;
        int side = 0; // 0=X, 1=Y, 2=Z
        int wallID = 0;
        float rayDist = 0.0;
        vec3 hitNormal = vec3(0.0);

        // Pre-calculate constants to avoid repeated casting/math in the tight loop
        int i_map_w = int(u_map_size.x);
        int i_map_h = int(u_map_size.y);
        int i_layer_base = int(u_map_layer_base_y);
        int i_layer_count = int(u_map_layer_count);

        for (int i = 0; i < MAX_STEPS; i++) {
            if (sideDist.x < sideDist.y) {
                if (sideDist.x < sideDist.z) {
                    rayDist = sideDist.x;
                    sideDist.x += deltaDist.x;
                    mapPos.x += stepDir.x;
                    side = 0;
                } else {
                    rayDist = sideDist.z;
                    sideDist.z += deltaDist.z;
                    mapPos.z += stepDir.z;
                    side = 2;
                }
            } else {
                if (sideDist.y < sideDist.z) {
                    rayDist = sideDist.y;
                    sideDist.y += deltaDist.y;
                    mapPos.y += stepDir.y;
                    side = 1;
                } else {
                    rayDist = sideDist.z;
                    sideDist.z += deltaDist.z;
                    mapPos.z += stepDir.z;
                    side = 2;
                }
            }
            
            if (rayDist > u_max_dist) { hit = 2; break; } // Too far
            
            // OSimplified Bounds & Layer Check
            if (mapPos.x >= 0 && mapPos.x < i_map_w && mapPos.y >= 0 && mapPos.y < i_map_h) {
                int layer_idx = mapPos.z - i_layer_base;
                
                if (layer_idx >= 0 && layer_idx < i_layer_count) {
                    // Grid Packing Logic
                    float f_idx = float(layer_idx);
                    float col = mod(f_idx, u_map_grid_cols);
                    float row = floor(f_idx / u_map_grid_cols);
                    
                    vec2 layerOffset = vec2(col * u_map_layer_norm_size.x, row * u_map_layer_norm_size.y);
                    vec2 cellUV = (vec2(float(mapPos.x), float(mapPos.y)) + 0.5) * u_map_tex_pixel_size;
                    
                    vec2 mapUV = layerOffset + cellUV;
                    
                    vec4 mapPixel = texture2D(u_map_texture, mapUV);
                    if (mapPixel.r > 0.5) {
                        wallID = int(mapPixel.g * 255.0 + 0.5);
                        hit = 1;
                        break;
                    }
                }
            }
        }
        
        // Object rendering
        float objDist = rayDist;
        if (hit == 0 || hit == 2) objDist = u_max_dist; // If no wall hit, max distance
        
        int objHit = 0;
        int objModelHitID = -1;
        int hitObjIndex = -1;
        vec3 objHitNormal = vec3(0.0);
        vec3 hitObjPos = vec3(0.0); 
        int objVoxelID = 0;
        
        for (int i=0; i<128; i++) {
            if (float(i) >= u_num_objects) break;
            
            vec3 objPos = u_objects[i].xyz;
            float modelID = u_objects[i].w;
            if (modelID < 0.0) continue;
            
            // Transform Logic (Rotation + Scale)
            vec3 euler = u_obj_rots[i].xyz;
            vec3 objScale = u_obj_scales[i].xyz;
            
            vec3 lRayPos = rayPos;
            vec3 lRayDir = rayDir;
            mat3 rotMat = mat3(1.0);
            bool rotated = dot(euler, euler) > 0.0001;
            
            if (rotated || length(objScale - vec3(1.0)) > 0.0001) {
                // To transform object by M, we transform ray by inverse(M).
                // M = Translation * Rotation * Scale
                // Inverse(M) = Scale^-1 * Rotation^T * Translation^-1
                
                vec3 center = objPos + objScale * 0.5;
                rotMat = eulerToMat3(euler);
                
                // Translate to center
                lRayPos = rayPos - center;
                // Rotate (Inverse)
                lRayPos = transpose(rotMat) * lRayPos;
                lRayDir = transpose(rotMat) * rayDir;
                // Scale (Inverse)
                lRayPos = lRayPos / objScale;
                lRayDir = lRayDir / objScale;
                // Translate back to local box space
                lRayPos = lRayPos + vec3(0.5); // Local box is now -0.5 to 0.5, move to 0..1
                
            }
            float tFarBox;
            // Intersection with virtual unit box (0..1) since we transformed the ray
            float tNearBox = intersectAABB(lRayPos, lRayDir, vec3(0.0), vec3(1.0), tFarBox);
            
            if (tNearBox < tFarBox && tFarBox > 0.0 && tNearBox < objDist) {
                // Add tiny epsilon to enter the box safely
                float tStart = max(0.0, tNearBox + 0.0001); 
                
                vec3 enterPos = lRayPos + lRayDir * tStart;
                
                // Inside the unit box, we always map to 16x16x16 voxels
                vec3 localPos = enterPos * 16.0;
                vec3 localDir = lRayDir;
                float invScale = 16.0; // Correction factor for DDA t-value
                
                // Local DDA
                ivec3 lMapPos = ivec3(floor(localPos));
                vec3 lDeltaDist = abs(1.0 / localDir);
                ivec3 lStepDir;
                vec3 lSideDist;
                
                if (localDir.x < 0.0) { lStepDir.x = -1; lSideDist.x = (localPos.x - float(lMapPos.x)) * lDeltaDist.x; }
                else                  { lStepDir.x = 1;  lSideDist.x = (float(lMapPos.x) + 1.0 - localPos.x) * lDeltaDist.x; }
                if (localDir.y < 0.0) { lStepDir.y = -1; lSideDist.y = (localPos.y - float(lMapPos.y)) * lDeltaDist.y; }
                else                  { lStepDir.y = 1;  lSideDist.y = (float(lMapPos.y) + 1.0 - localPos.y) * lDeltaDist.y; }
                if (localDir.z < 0.0) { lStepDir.z = -1; lSideDist.z = (localPos.z - float(lMapPos.z)) * lDeltaDist.z; }
                else                  { lStepDir.z = 1;  lSideDist.z = (float(lMapPos.z) + 1.0 - lMapPos.z) * lDeltaDist.z; }
                
                int lHit = 0;
                int lSide = 0;
                
                for(int j=0; j<80; j++) {
                    if (lSideDist.x < lSideDist.y) {
                        if (lSideDist.x < lSideDist.z) {
                            lSideDist.x += lDeltaDist.x; lMapPos.x += lStepDir.x; lSide=0;
                        } else {
                            lSideDist.z += lDeltaDist.z; lMapPos.z += lStepDir.z; lSide=2;
                        }
                    } else {
                        if (lSideDist.y < lSideDist.z) {
                            lSideDist.y += lDeltaDist.y; lMapPos.y += lStepDir.y; lSide=1;
                        }
                        else {
                            lSideDist.z += lDeltaDist.z; lMapPos.z += lStepDir.z; lSide=2;
                        }
                    }
                    
                    if (lMapPos.x < 0 || lMapPos.x > 15 || lMapPos.y < 0 || lMapPos.y > 15 || lMapPos.z < 0 || lMapPos.z > 15) break;
                    
                    float tu = (float(lMapPos.z) * 16.0 + float(lMapPos.x) + 0.5) / 256.0;
                    float tv = (modelID * 16.0 + float(lMapPos.y) + 0.5) / (16.0 * max(1.0, u_num_models));
                    
                    vec4 val = texture2D(u_model_atlas, vec2(tu, tv), -16.0);
                    
                    if (val.a > 0.5) { 
                        int voxID = int((val.g / val.a) * 255.0 + 0.5);
                        if (voxID > 0) {
                            lHit = 1;
                            objVoxelID = voxID;
                            break; 
                        }
                    }
                }
                
                if (lHit == 1) {
                        float distInBox = 0.0;
                        if (lSide == 0) distInBox = (lSideDist.x - lDeltaDist.x) / invScale;
                        else if (lSide == 1) distInBox = (lSideDist.y - lDeltaDist.y) / invScale;
                        else distInBox = (lSideDist.z - lDeltaDist.z) / invScale;
                        
                        float totalDist = tStart + distInBox;
                        
                        if (totalDist < objDist) {
                            objDist = totalDist;
                            objHit = 1;
                            objModelHitID = int(modelID);
                            hitObjIndex = i;
                            hitObjPos = objPos;
                            
                            if (lSide == 0) objHitNormal = vec3(-float(lStepDir.x), 0.0, 0.0);
                            else if (lSide == 1) objHitNormal = vec3(0.0, -float(lStepDir.y), 0.0);
                            else objHitNormal = vec3(0.0, 0.0, -float(lStepDir.z));
                            
                            if (rotated) objHitNormal = rotMat * objHitNormal;
                        }
                }
            } 
        }
        
        if (objHit == 1) {
            rayDist = objDist;
            hit = 3; 
            hitNormal = objHitNormal;
            wallID = objVoxelID; // Temporary reuse of wallID
        }

        vec3 color;
        
        if (hit == 1 || hit == 3) {
            vec3 hitPos = rayPos + rayDir * rayDist;
            
            vec2 texUV;
            
            if (hit == 3) {
                vec3 hitLocal = (hitPos - hitObjPos) * (16.0 / u_obj_scale);
                vec3 inVoxel = hitLocal - floor(hitLocal); // 0..1 inside voxel
                
                if (abs(hitNormal.x) > 0.5) { 
                    float wallX = inVoxel.y;
                    if (hitNormal.x > 0.0) wallX = inVoxel.y; 
                    else wallX = 1.0 - inVoxel.y;
                    texUV = vec2(wallX, 1.0 - inVoxel.z);
                }
                else if (abs(hitNormal.y) > 0.5) { 
                    float wallX = inVoxel.x;
                    if (hitNormal.y > 0.0) wallX = 1.0 - inVoxel.x;
                    else wallX = inVoxel.x;
                    texUV = vec2(wallX, 1.0 - inVoxel.z);
                }
                else { 
                    texUV = vec2(inVoxel.x, inVoxel.y);
                }
            } else {
                if (side == 0) { // X-Side
                    float wallX = hitPos.y; 
                    if (rayDir.x > 0.0) wallX = 1.0 - wallX;
                    texUV = vec2(fract(wallX), fract(1.0 - hitPos.z));
                } 
                else if (side == 1) { // Y-Side
                    float wallX = hitPos.x;
                    if (rayDir.y < 0.0) wallX = 1.0 - wallX;
                    texUV = vec2(fract(wallX), fract(1.0 - hitPos.z));
                }
                else { // Side 2 (Wall Top/Bottom)
                    texUV = vec2(fract(hitPos.x), fract(hitPos.y));
                }
            }
            
            float texRes = 64.0;
            texUV = (floor(texUV * texRes) + 0.5) / texRes;
            
            float singleTexWidth = 1.0 / u_num_textures;
            float texOffset = float(wallID - 1) * singleTexWidth;
            
            float clampedU = texUV.x * (1.0 - 0.002) + 0.001;
            float finalU = texOffset + (clampedU * singleTexWidth);
            float finalV = texUV.y;
            
            if (finalV < 0.0 || finalV > 1.0) {
                color = vec3(0.0);
            } else {
                color = texture2D(u_wall_atlas, vec2(finalU, finalV), 0.0).rgb;
            }
            
            vec3 finalColor = color;
            
            float fogDist = length(hitPos.xy - u_player_pos);
            
            vec3 ambientLight = u_ambient_color; 
            
            // float personalLight = max(0.0, 1.0 - (fogDist / 4.0)); 
            // ambientLight += u_ambient_near_color * personalLight;
            
            vec3 totalLight = ambientLight;

            if (u_flashlight_active > 0.5) {
                vec3 flashPos = rayPos;

                vec3 lightVec = normalize(hitPos - flashPos);
                
                float dotProd = dot(lightVec, flashDir); 
                float dist3D = distance(hitPos, flashPos);

                if (dotProd > 0.82) { 
                    float spotEffect = smoothstep(0.82, 0.92, dotProd);
                    
                    float att = 1.0 / (1.5 + dist3D * 0.03 + dist3D * dist3D * 0.002);
                    vec3 flashLightColor = vec3(0.95, 0.95, 1.0);
                    
                    totalLight += flashLightColor * att * 2.2 * spotEffect;
                }
            }

            if (u_flash_intensity > 0.01) {
                float distToPlayer = distance(hitPos.xy, u_player_pos);
                float flashAtt = 1.0 / (0.5 + (distToPlayer * distToPlayer) * 0.1);
                vec3 flashColor = vec3(1.0, 0.8, 0.4);
                totalLight += flashColor * u_flash_intensity * flashAtt * 2.0;
            }

            for (int i = 0; i < 16; i++) {
                if (float(i) >= u_num_active_lights) break;
                
                vec4 lightData = u_light_positions[i]; 
                vec2 lightPos = lightData.xy;
                float radius = lightData.z;
                float intensity = lightData.w;
                
                float distToLight = distance(hitPos.xy, lightPos);
                
                if (distToLight < radius) {
                    float visibility = 1.0;
                    
                    if (u_enable_shadows > 0.5) {
                        visibility = 0.0;
                        int samples = 1;
                        float spread = 0.0;
                        
                        if (u_soft_shadows > 0.5) {
                            samples = 9;
                            spread = 0.55;
                        }
                        
                        vec2 dirToLight = normalize(lightPos - hitPos.xy);
                        vec2 perp = vec2(-dirToLight.y, dirToLight.x) * spread;
                        
                        for (int k = 0; k < 9; k++) {
                            if (k >= samples) break;
                            
                            float offScale = 0.0;
                            if (k == 1) offScale = 1.0;
                            if (k == 2) offScale = -1.0;
                            if (k == 3) offScale = 0.5;
                            if (k == 4) offScale = -0.5;
                            if (k == 5) offScale = 0.75;
                            if (k == 6) offScale = -0.75;
                            if (k == 7) offScale = 0.25;
                            if (k == 8) offScale = -0.25;
                            
                            vec2 offset = perp * offScale;
                            
                            vec2 targetPos = lightPos + offset;
                            vec2 lightRayDir = normalize(targetPos - hitPos.xy);
                            float lightRayDist = distance(targetPos, hitPos.xy);
                            
                            float stepSize = 0.2;
                            int steps = int(lightRayDist / stepSize);
                            vec2 checkPos = hitPos.xy + lightRayDir * 0.1;
                            bool hitWall = false;
                            
                            for(int s=0; s<64; s++) { 
                                if (s >= steps) break;
                                checkPos += lightRayDir * stepSize;
                                
                                if (abs(floor(checkPos.x) - float(mapPos.x)) < 0.1 && abs(floor(checkPos.y) - float(mapPos.y)) < 0.1) continue;

                                vec2 mapUV = (floor(checkPos) + 0.5) / u_map_size;
                                mapUV *= u_map_uv_scale;
                                vec4 shadowMapPixel = texture2D(u_map_texture, mapUV);
                                if (shadowMapPixel.r > 0.5) {
                                    hitWall = true;
                                    break;
                                }
                            }
                            
                            if (!hitWall) visibility += 1.0;
                        }
                        
                        visibility /= float(samples);
                    }

                    if (visibility > 0.0) {
                        float att = 1.0 - (distToLight / radius);
                        att = att * att; 
                        
                        vec3 lampColor = vec3(0.2, 1.0, 0.2); 
                        totalLight += lampColor * intensity * att * visibility;
                    }
                }
            }

            float faceShadow = 1.0;
            if (hit == 3) {
                if (abs(hitNormal.y) > 0.5) faceShadow = 0.7;
            } else {
                if (side == 1) faceShadow = 0.7; 
                if (side == 2) faceShadow = 1.0; 
            }
            
            color = finalColor * totalLight * faceShadow;

            bool is_selected = false;
            
            if (hit == 1) {
                // Map Voxel Highlight
                if (distance(vec3(mapPos), u_highlight_pos) < 0.1) is_selected = true;
                
                // Multi-selection map check
                int layer_idx_sel = mapPos.z - int(u_map_layer_base_y);
                
                float f_idx = float(layer_idx_sel);
                float col = mod(f_idx, u_map_grid_cols);
                float row = floor(f_idx / u_map_grid_cols);
                
                vec2 layerOffset = vec2(col * u_map_layer_norm_size.x, row * u_map_layer_norm_size.y);
                vec2 cellUV_sel = (vec2(float(mapPos.x), float(mapPos.y)) + 0.5) * u_map_tex_pixel_size;
                
                vec2 mapUV_sel = layerOffset + cellUV_sel;
                
                vec4 selData = texture2D(u_selection_texture, mapUV_sel);
                
                if (selData.r > 0.5) is_selected = true;
                if (selData.g > 0.5) color = mix(color, vec3(0.0, 1.0, 0.5), 0.5); // Bones
                if (distance(vec3(mapPos), u_pivot_pos) < 0.1) color = mix(color, vec3(0.0, 1.0, 1.0), 0.6); // Pivot
            }
            else if (hit == 3 && hitObjIndex >= 0) {
                // color = vec3(0.0, 1.0, 0.0); 
                
                vec3 hitLocal = (hitPos - hitObjPos) * (16.0 / u_obj_scale);
                ivec3 finalMapPos = ivec3(floor(hitLocal));
                vec3 globalPos = u_obj_origins[hitObjIndex].xyz + vec3(finalMapPos);
                
                if (distance(globalPos, u_highlight_pos) < 0.1) is_selected = true;
                
                int gx = int(globalPos.x); int gy = int(globalPos.y); int gz = int(globalPos.z);
                
                if (gx >= 0 && gx < int(u_map_size.x) && gy >= 0 && gy < int(u_map_size.y)) {
                    vec2 cellUV_sel = (vec2(float(gx), float(gy)) + 0.5) * u_map_tex_pixel_size;
                    int layer_idx_sel = gz - int(u_map_layer_base_y);
                    
                    if (layer_idx_sel >= 0 && layer_idx_sel < int(u_map_layer_count)) {
                        float f_idx = float(layer_idx_sel);
                        float col = mod(f_idx, u_map_grid_cols);
                        float row = floor(f_idx / u_map_grid_cols);
                        
                        vec2 layerOffset = vec2(col * u_map_layer_norm_size.x, row * u_map_layer_norm_size.y);
                        vec2 cellUV_sel = (vec2(float(gx), float(gy)) + 0.5) * u_map_tex_pixel_size;
                        vec2 mapUV_sel = layerOffset + cellUV_sel;
                        
                        vec4 selData = texture2D(u_selection_texture, mapUV_sel);
                        
                        if (selData.r > 0.5) is_selected = true;
                        if (selData.g > 0.5) color = mix(color, vec3(0.0, 1.0, 0.5), 0.5);
                        if (distance(globalPos, u_pivot_pos) < 0.1) color = mix(color, vec3(0.0, 1.0, 1.0), 0.6);
                    }
                }
            }

            if (is_selected) {
                color = mix(color, vec3(1.0, 0.5, 0.0), 0.4);
            }

        } else {
            if (u_volumetric_clouds > 0.5) {
                vec3 skyColorTop;
                vec3 skyColorBottom;
                vec3 cloudColor;
                
                // Day Cycle Colors
                vec3 nightTop = vec3(0.0, 0.0, 0.1);
                vec3 nightBot = vec3(0.05, 0.05, 0.2);
                vec3 nightCloud = vec3(0.1, 0.1, 0.15);

                vec3 dayTop = vec3(0.0, 0.4, 0.8);
                vec3 dayBot = vec3(0.6, 0.8, 1.0);
                vec3 dayCloud = vec3(1.0, 1.0, 1.0);

                vec3 sunsetTop = vec3(0.2, 0.1, 0.4);
                vec3 sunsetBot = vec3(1.0, 0.4, 0.2);
                vec3 sunsetCloud = vec3(1.0, 0.6, 0.5);

                float t = mod(u_time_of_day, 24.0); // Ensure 0-24 range

                
                if (t < 5.0) {
                    skyColorTop = nightTop; skyColorBottom = nightBot; cloudColor = nightCloud;
                } else if (t < 8.0) {
                    float p = (t - 5.0) / 3.0;
                    skyColorTop = mix(nightTop, dayTop, p);
                    skyColorBottom = mix(nightBot, dayBot, p);
                    cloudColor = mix(nightCloud, dayCloud, p);
                } else if (t < 16.0) {
                    skyColorTop = dayTop; skyColorBottom = dayBot; cloudColor = dayCloud;
                } else if (t < 19.0) {
                    float p = (t - 16.0) / 3.0;
                    skyColorTop = mix(dayTop, sunsetTop, p);
                    skyColorBottom = mix(dayBot, sunsetBot, p);
                    cloudColor = mix(dayCloud, sunsetCloud, p);
                } else if (t < 21.0) {
                    float p = (t - 19.0) / 2.0;
                    skyColorTop = mix(sunsetTop, nightTop, p);
                    skyColorBottom = mix(sunsetBot, nightBot, p);
                    cloudColor = mix(sunsetCloud, nightCloud, p);
                } else {
                    skyColorTop = nightTop; skyColorBottom = nightBot; cloudColor = nightCloud;
                }

                float skyGradient = smoothstep(-0.5, 0.5, rayDir.z);
                vec3 skyBase = mix(skyColorBottom, skyColorTop, skyGradient);
                
                color = skyBase;

                if (rayDir.z > 0.01) {
                    vec2 cloudUV = rayDir.xy / rayDir.z;
                    cloudUV += u_time * 0.05;
                    
                    float n = fbm(cloudUV * 0.5);
                    float c = smoothstep(0.4, 0.8, n);
                    c *= smoothstep(0.0, 0.2, rayDir.z);
                    
                    float brightness = 1.0;
                    if (t < 6.0 || t > 20.0) brightness = 0.3;
                    else if (t < 8.0) brightness = mix(0.3, 1.0, (t - 6.0) / 2.0);
                    else if (t > 18.0) brightness = mix(1.0, 0.3, (t - 18.0) / 2.0);
                    
                    color = mix(color, cloudColor * brightness, c);
                }
                
                float starVisibility = 0.0;
                if (t < 6.0) starVisibility = 1.0;
                else if (t < 7.0) starVisibility = 1.0 - (t - 6.0);
                else if (t > 20.0) starVisibility = (t - 20.0) / 1.0;
                if (t > 21.0) starVisibility = 1.0;

                if (starVisibility > 0.01 && rayDir.z > 0.01) {
                    vec2 starUV = rayDir.xy / (1.0 + rayDir.z);
                    
                    float scale = 300.0; 
                    vec2 gridUV = starUV * scale;
                    vec2 gridID = floor(gridUV);
                    vec2 gridLocal = fract(gridUV) - 0.5;
                    
                    float h = hash(gridID);
                    
                    if (h > 0.97) {
                        // Stable random position in cell
                        float r1 = hash(gridID + vec2(12.34, 56.78));
                        float r2 = hash(gridID + vec2(90.12, 34.56));
                        vec2 pos = (vec2(r1, r2) - 0.5) * 0.7;
                        
                        float dist = length(gridLocal - pos);
                        
                        float brightness = smoothstep(0.4, 0.1, dist);
                        
                        float twinkle = 0.7 + 0.3 * sin(u_time * 2.0 + h * 50.0);
                        
                        // Horizon fade
                        float fade = smoothstep(0.01, 0.1, rayDir.z);
                        
                        color += vec3(brightness * twinkle * fade * starVisibility);
                    }
                }
            } else {
                // Skybox
                vec2 skyUV = stein_uv;
                // Apply pitch to skyUV.y
                skyUV.y -= u_pitch; 
                skyUV.y = clamp(skyUV.y, 0.0, 1.0);
                color = texture2D(u_sky_texture, skyUV).rgb;
            }
        }

        // SPRITE RENDERING (Adapted for 3D)
        // We approximate 2D billboard logic using the 3D ray distance
        
        // Calculate Camera Forward Vector (Rotated)
        vec3 forwardUnrot = vec3(u_player_dir, 0.0);
        vec3 forwardRot = forwardUnrot * cp + cross(rightAxis, forwardUnrot) * sp + rightAxis * dot(rightAxis, forwardUnrot) * (1.0 - cp);
        
        float perpWallDist = dot(rayDir * rayDist, forwardRot);
        
        // If we didnt hit a wall (Sky/Void), the depth is infinite
        if (hit != 1) perpWallDist = 10000.0;
        
        float currentDepth = perpWallDist;
        
        // Precalculate pitch shift in pixels for sprites
        // float pitchPixeLCTRL = u_pitch * u_vertical_scale * (u_resolution.y / 2.0);

        float invDet = 1.0 / (u_player_plane.x * u_player_dir.y - u_player_dir.x * u_player_plane.y);

        for (int i = 0; i < 64; i++) {
            if (i >= u_num_active_sprites) break;
            
            vec4 spriteData = u_sprites[i];
            vec2 spritePos = spriteData.xy;
            float texID = spriteData.z;
            float spritePitch = spriteData.w; 

            if (texID > 200.0) continue;

            float spX = spritePos.x - u_player_pos.x;
            float spY = spritePos.y - u_player_pos.y;

            float transformX = invDet * (u_player_dir.y * spX - u_player_dir.x * spY);
            float transformY = invDet * (-u_player_plane.y * spX + u_player_plane.x * spY); 
            
            // Apply Pitch Rotation to Sprite Position
            float camHeight = 1.6 + u_z_offset;
            float spriteZ = -camHeight;
            
            float rotY = transformY * cp + spriteZ * sp;
            float rotZ = -transformY * sp + spriteZ * cp;

            if (rotY <= 0.1) continue;
            // Robust depth check
            if (rotY >= currentDepth) continue; 

            float spriteScreenX = (u_resolution.x / 2.0) * (1.0 + transformX / rotY);
            
            // Scale sprites
            // scaleY = World Height in blocks
            // scaleX = World Width in blocks
            
            float scaleY = 1.0;
            float scaleX = 1.0;
            
            if (texID < 0.5) { scaleY = 0.9; scaleX = 0.7; }
            else if (texID < 3.5) { scaleY = 2.0; scaleX = 1.0; }
            else if (texID < 5.5) { scaleY = 1.0; scaleX = 0.5; }
            else if (texID < 8.5) { scaleY = 0.4; scaleX = 0.4; }
            else if (texID < 10.5) { scaleY = 1.2; scaleX = 0.6; }
            else { scaleY = 0.5; scaleX = 0.5; }

            float spriteHeight = abs(u_resolution.y / rotY) * u_vertical_scale * scaleY; 
            float spriteWidth = abs(u_resolution.y / rotY) * u_vertical_scale * scaleX; 

            // Sprite Anchoring Logic (Floor Alignment)
            // Calculate Screen Y of the floor (rotZ)
            float screenY_floor = (rotZ / rotY) * u_vertical_scale;
            float pixelY_floor = (0.5 - screenY_floor / 2.0) * u_resolution.y;
            
            float spritePixeLCTRL = spritePitch * u_vertical_scale * (u_resolution.y / 2.0);
            
            float drawEndY = pixelY_floor - spritePixeLCTRL;
            float drawStartY = drawEndY - spriteHeight;
            
            float drawStartX = spriteScreenX - spriteWidth / 2.0;
            float drawEndX = spriteScreenX + spriteWidth / 2.0;

            float currentPixelX = stein_uv.x * u_resolution.x; 
            float currentPixelY = stein_uv.y * u_resolution.y;

            if (currentPixelX >= drawStartX && currentPixelX <= drawEndX) {
                float texX = (currentPixelX - drawStartX) / spriteWidth;
                
                float texY = (currentPixelY - drawStartY) / spriteHeight;
                // texY = 1.0 - texY;

                if (texY >= 0.0 && texY <= 1.0) {
                    float singleTexW = 1.0 / u_num_sprite_textures;
                    float atlasX = (texID * singleTexW) + (texX * singleTexW);
                    
                    vec4 spriteCol = texture2D(u_sprite_atlas, vec2(atlasX, texY));
                    
                    if (spriteCol.a > 0.5) {
                        
                        float sprDist = length(vec2(spX, spY)); 
                        
                        vec3 sprLight = u_ambient_color;
                        // float sprPersonal = max(0.0, 1.0 - (sprDist / 4.0));
                        // sprLight += u_ambient_near_color * sprPersonal;

                        if (u_flashlight_active > 0.5) {
                            float dotProd = dot(rayDir, flashDir);
                            
                            float dist3D = transformY;
                            
                            if (dotProd > 0.82) {
                                float spotEffect = smoothstep(0.82, 0.92, dotProd);
                                float att = 1.0 / (1.5 + dist3D * 0.03 + dist3D * dist3D * 0.002);
                                vec3 flashLightColor = vec3(0.95, 0.95, 1.0);
                                
                                sprLight += flashLightColor * att * 2.2 * spotEffect;
                            }
                        }

                        if (u_flash_intensity > 0.01) {
                            float flashAtt = 1.0 / (0.5 + (sprDist * sprDist) * 0.1);
                            vec3 flashColor = vec3(1.0, 0.8, 0.4);
                            sprLight += flashColor * u_flash_intensity * flashAtt * 2.0;
                        }

                        for (int j = 0; j < 16; j++) {
                            if (float(j) >= u_num_active_lights) break;
                            
                            vec4 lData = u_light_positions[j];
                            float lDist = distance(spritePos, lData.xy);
                            
                            if (lDist < lData.z) {
                                float visibility = 1.0;
                                
                                if (u_enable_shadows > 0.5) {
                                    visibility = 0.0;
                                    int samples = 1;
                                    float spread = 0.0;
                                    
                                    if (u_soft_shadows > 0.5) {
                                        samples = 9;
                                        spread = 0.55;
                                    }
                                    
                                    vec2 dirToLight = normalize(lData.xy - spritePos);
                                    vec2 perp = vec2(-dirToLight.y, dirToLight.x) * spread;
                                    
                                    for (int k = 0; k < 9; k++) {
                                        if (k >= samples) break;
                                        
                                        float offScale = 0.0;
                                        if (k == 1) offScale = 1.0;
                                        if (k == 2) offScale = -1.0;
                                        if (k == 3) offScale = 0.5;
                                        if (k == 4) offScale = -0.5;
                                        if (k == 5) offScale = 0.75;
                                        if (k == 6) offScale = -0.75;
                                        if (k == 7) offScale = 0.25;
                                        if (k == 8) offScale = -0.25;
                                        
                                        vec2 offset = perp * offScale;
                                        
                                        vec2 targetPos = lData.xy + offset;
                                        vec2 sprLightRayDir = normalize(targetPos - spritePos);
                                        float sprLightRayDist = distance(targetPos, spritePos);
                                        
                                        float stepSize = 0.2;
                                        int steps = int(sprLightRayDist / stepSize);
                                        vec2 checkPos = spritePos + sprLightRayDir * 0.1;
                                        bool hitWall = false;
                                        
                                        for(int s=0; s<64; s++) {
                                            if (s >= steps) break;
                                            checkPos += sprLightRayDir * stepSize;
                                            
                                            vec2 mapUV = (floor(checkPos) + 0.5) / u_map_size;
                                            mapUV *= u_map_uv_scale;
                                            vec4 smp = texture2D(u_map_texture, mapUV);
                                            if (smp.r > 0.5) {
                                                hitWall = true;
                                                break;
                                            }
                                        }
                                        
                                        if (!hitWall) visibility += 1.0;
                                    }
                                    
                                    visibility /= float(samples);
                                }

                                if (visibility > 0.0) {
                                    float att = 1.0 - (lDist / lData.z);
                                    att = att * att;
                                    vec3 lampColor = vec3(0.4, 0.9, 0.4);
                                    sprLight += lampColor * lData.w * att * visibility;
                                }
                            }
                        }

                        color = spriteCol.rgb * sprLight;
                        currentDepth = transformY; 
                    }
                }
            }
        }

        if (u_rain_intensity > 0.0) {
            float rainVal = 0.0;
            for (int i=1; i<=4; i++) {
                float dist = float(i) * 2.5; 
                if (dist > currentDepth) break;
                
                vec3 p = rayPos + rayDir * dist;
                
                vec2 uv1 = vec2(p.y, p.z) * vec2(1.0, 2.0); // YZ Plane
                vec2 uv2 = vec2(p.x, p.z) * vec2(1.0, 2.0); // XZ Plane
                
                float t = u_time * 15.0;
                float n1 = rain_layer(uv1, t);
                float n2 = rain_layer(uv2, t);
                
                float blend = abs(rayDir.x);
                float n = mix(n2, n1, blend);
                
                // Distance Fade
                float fade = 1.0 - (dist / 12.0);
                if (fade < 0.0) fade = 0.0;
                
                rainVal += n * fade;
            }
            color = mix(color, vec3(0.7, 0.8, 0.9), rainVal * u_rain_intensity * 0.4);
        }

        if (u_snow_intensity > 0.0) {
            float snowVal = 0.0;
            for (int i=1; i<=4; i++) {
                float dist = float(i) * 2.0; 
                if (dist > currentDepth) break;
                
                vec3 p = rayPos + rayDir * dist;
                
                vec2 uv1 = vec2(p.y, p.z) * 0.8; 
                vec2 uv2 = vec2(p.x, p.z) * 0.8;
                
                float t = u_time * 2.0;
                uv1.y += t;
                uv2.y += t;
                
                uv1.x += sin(u_time + p.z) * 0.2;
                uv2.x += cos(u_time + p.z) * 0.2;
                
                float n1 = noise(uv1);
                float n2 = noise(uv2);
                
                float blend = abs(rayDir.x);
                float n = mix(n2, n1, blend);
                
                float s = smoothstep(0.95, 1.0, n);
                
                float fade = 1.0 - (dist / 10.0);
                if (fade < 0.0) fade = 0.0;
                
                snowVal += s * fade;
            }
            color = mix(color, vec3(1.0), snowVal * u_snow_intensity * 0.8);
        }

        gl_FragColor = vec4(color, 1.0);
    """)

    renpy.register_shader("stein.motion_blur", variables="""
        uniform sampler2D tex0;
        uniform float u_blur_amount;
        varying vec2 v_tex_coord;
    """, fragment_200="""
        vec2 stein_mb_uv = v_tex_coord;
        vec4 mb_color = texture2D(tex0, stein_mb_uv);
        
        if (abs(u_blur_amount) > 0.001) {
            float blur = u_blur_amount * 0.02;
            vec4 sum = vec4(0.0);
            
            // 5-tap optimization
            sum += texture2D(tex0, vec2(stein_mb_uv.x - blur * 2.0, stein_mb_uv.y)) * 0.1;
            sum += texture2D(tex0, vec2(stein_mb_uv.x - blur * 1.0, stein_mb_uv.y)) * 0.25;
            sum += texture2D(tex0, vec2(stein_mb_uv.x, stein_mb_uv.y)) * 0.3;
            sum += texture2D(tex0, vec2(stein_mb_uv.x + blur * 1.0, stein_mb_uv.y)) * 0.25;
            sum += texture2D(tex0, vec2(stein_mb_uv.x + blur * 2.0, stein_mb_uv.y)) * 0.1;
            
            gl_FragColor = sum;
        } else {
            gl_FragColor = mb_color;
        }
    """)

    renpy.register_shader("stein.weapon_fx", variables="""
        varying vec2 v_tex_coord;
        attribute vec2 a_tex_coord;
        uniform float u_flash_progress; 
        uniform float u_flash_angle;
        uniform vec3 u_flash_color;
        uniform float u_heat_distortion;
        uniform float u_enable_smoke;
    """, vertex_200="""
        v_tex_coord = a_tex_coord;
    """, fragment_200="""
        // Center UVs to [-1, 1] range
        vec2 stein_w_uv = (v_tex_coord - 0.5) * 2.0; 
        
        // Internal rotation
        float s = sin(u_flash_angle);
        float c = cos(u_flash_angle);
        vec2 rotated_uv = mat2(c, -s, s, c) * stein_w_uv;
        
        float dist = length(rotated_uv);
        float angle = atan(rotated_uv.y, rotated_uv.x);
        
        // MUZZLE FLASH
        // Flash happens in the first 4% of the duration (1.5s * 0.04 = 0.06s)
        float flash_p = u_flash_progress * 25.0; 
        float flash_intensity = 0.0;
        
        if (flash_p < 1.0) {
            float spikes = abs(sin(angle * 4.0)) * 0.4 + abs(sin(angle * 9.0)) * 0.6;
            float core = exp(-dist * 5.0) * 2.5;
            float rays = exp(-dist * (4.0 + 8.0 * (1.0 - spikes))) * 1.2;
            float mask = smoothstep(1.0, 0.2, dist);
            
            flash_intensity = (core + rays) * (1.0 - flash_p);
            flash_intensity = clamp(flash_intensity * mask, 0.0, 1.0);
        }

        // BARREL SMOKE
        // Simulates smoke emanating from the hot barrel and rising up
        float smoke_alpha = 0.0;
        if (u_enable_smoke > 0.5 && u_flash_progress > 0.02) {
            float smoke_p = (u_flash_progress - 0.02) / 0.98;
            
            // Use unrotated UV so smoke always rises UP relative to screen
            vec2 stream_uv = stein_w_uv;
            
            // Detach from bottom logic (Smoke moves up/away from barrel)
            // We mask out the bottom part, and this mask moves up over time
            // uv.y is negative for up, 0 is center
            float detach_y = -0.1 - (smoke_p * 1.2);
            
            // Mask: Visible if y < detach_y (above the cut-off point)
            // We use smoothstep for a soft bottom edge
            float detach_mask = smoothstep(detach_y + 0.3, detach_y, stream_uv.y);
            
            // Wiggle the stream (turbulence)
            float wiggle = sin(stream_uv.y * 12.0 + u_flash_progress * 15.0) * 0.04;
            stream_uv.x += wiggle;
            
            // Stream shape
            float stream_width = 0.04 + abs(stream_uv.y) * 0.15; 
            float stream_shape = smoothstep(stream_width, 0.0, abs(stream_uv.x));
            
            // Top fade
            float height_mask = smoothstep(-0.95, -0.2, stream_uv.y); 
            
            // Scroll noise up through the stream
            float noise_y = stein_w_uv.y + u_flash_progress * 3.0;
            float noise = sin(stein_w_uv.x * 40.0) * sin(noise_y * 12.0);
            
            // Overall fade out over time
            float fade_out = 1.0 - smoothstep(0.2, 0.9, smoke_p);
            
            smoke_alpha = stream_shape * detach_mask * height_mask * (0.6 + 0.4 * noise) * fade_out * 0.8;
        }

        // HEAT DISTORTION
        float heat_val = 0.0;
        /*
        if (u_heat_distortion > 0.5) {
            float heat_prog = u_flash_progress * 3.0;
            if (heat_prog < 1.0) {
                float wave = sin(rotated_uv.x * 10.0 + heat_prog * 10.0) * 0.1;
                float heat_d = length(rotated_uv + vec2(wave, heat_prog * 0.5));
                float heat_ring = smoothstep(0.05, 0.0, abs(heat_d - 0.4 - heat_prog * 0.3));
                float turb = sin(angle * 20.0 + heat_prog * 20.0);
                heat_val = heat_ring * 0.4 * (1.0 - heat_prog) * (0.5 + 0.5 * turb);
            }
        }
        
        heat_val *= (1.0 - smoke_alpha * 1.5);
        heat_val = max(0.0, heat_val);
        */

        // Combine
        vec3 final_color = u_flash_color * flash_intensity;
        float final_alpha = flash_intensity;
        
        // Add Heat
        final_color += vec3(heat_val);
        final_alpha = max(final_alpha, heat_val);
        
        // Add Smoke
        vec3 smoke_col = vec3(0.95, 0.95, 1.0); // White/Grey smoke
        
        // Mix Smoke
        final_color = mix(final_color, smoke_col, smoke_alpha);
        final_alpha = max(final_alpha, smoke_alpha);
        
        gl_FragColor = vec4(final_color, final_alpha);
    """)

    renpy.register_shader("stein.bloom", variables="""
        uniform sampler2D tex0;
        uniform vec2 u_resolution;
        varying vec2 v_tex_coord;
    """, fragment_200="""
        vec2 stein_bloom_uv = v_tex_coord;
        vec4 source = texture2D(tex0, stein_bloom_uv);
        
        float bloomSpread = 4.0;
        float threshold = 0.8;
        float intensity = 0.5;

        vec4 sum = vec4(0.0);
        vec2 size = vec2(1.0) / u_resolution;

        for (float i = -1.0; i <= 1.0; i++) {
            for (float j = -1.0; j <= 1.0; j++) {
                vec2 offset = vec2(i, j) * bloomSpread * size;
                vec4 col = texture2D(tex0, stein_bloom_uv + offset);
                
                float brightness = dot(col.rgb, vec3(0.2126, 0.7152, 0.0722));
                if (brightness > threshold) {
                    sum += col * brightness; 
                }
            }
        }
        
        sum = sum / 9.0;
        gl_FragColor = source + (sum * intensity);
    """)

    import math
    import pygame
    import time

    if renpy.android:
        simulate_touch = True
    else:
        simulate_touch = False

    config.pygame_events.extend([
        pygame.FINGERMOTION, pygame.FINGERDOWN, pygame.FINGERUP,
        pygame.JOYAXISMOTION, pygame.JOYBUTTONDOWN, pygame.JOYBUTTONUP,
        pygame.JOYHATMOTION, pygame.JOYDEVICEADDED, pygame.JOYDEVICEREMOVED
    ])

    renpy.music.register_channel("gun_sfx", mixer="sfx", loop=False)
    renpy.music.register_channel("shotgun_sfx", mixer="sfx", loop=False)
    renpy.music.register_channel("enemy_sfx", mixer="sfx", loop=False)

    texWidth = 64
    texHeight = 64
    twoPI = math.pi * 2

    class DamageIndicator(object):
        def __init__(self, angle, duration=2.0):
            self.angle = angle
            self.duration = duration
            self.max_duration = duration

    class Player(object):
        def __init__(self, wm, x, y, dirx, diry, planex, planey):
            self.wm = wm
            self.x = x; self.y = y
            self.dirx = float(dirx); self.diry = float(diry)
            self.planex = float(planex); self.planey = float(planey)
            self.health = 100
            self.pitch = 0.0
            self.current_weapon_name = "fist"
            self.rot = math.atan2(diry, dirx)
            self.planerot = math.atan2(planey, planex)
            self.dir = 0; self.speed = 0; self.strafe_speed = 0
            self.moveSpeed = 2.5; self.rotSpeed = 90 * math.pi / 180
            self.mapWidth = wm.mapWidth; self.mapHeight = wm.mapHeight
            self.z = 0.0; self.velocity_z = 0.0
            self.GRAVITY = 35.0; self.JUMP_FORCE = 8.5; self.CROUCH_DEPTH = -0.4
            self.is_grounded = True; self.is_crouching = False
            self.crouch_timer = 0.0; self.crouch_duration = 0.06
            self.fly_mode = False

        def get_ground_height_at(self, x, y, check_z=None):
            if check_z is None: check_z = self.z
            
            map_address, _ = self.wm.flat_map_buffer.buffer_info()
            
            return stein_core.get_map_height(
                x, y, check_z,
                map_address,
                self.wm.mapWidth, self.wm.mapHeight,
                self.wm.num_layers, self.wm.min_layer
            )

        def trigger_jump(self):
            if self.is_grounded and not self.is_crouching:
                self.is_crouching = True; self.crouch_timer = self.crouch_duration

        def update_physics(self, dt):
            if self.fly_mode:
                self.is_grounded = False
                self.velocity_z = 0.0
                
                fly_speed = 5.0
                if self.wm.kb_running: fly_speed = 10.0
                
                if self.wm.kb_fly_up:
                    self.z += fly_speed * dt
                if self.wm.kb_fly_down:
                    self.z -= fly_speed * dt
                return

            floor_h = self.get_ground_height_at(self.x, self.y)
            
            if self.is_crouching:
                self.crouch_timer -= dt
                progress = 1.0 - (self.crouch_timer / self.crouch_duration)
                target_z = floor_h + (self.CROUCH_DEPTH * math.sin(progress * math.pi))
                self.z = target_z 
                
                if self.crouch_timer <= 0:
                    self.is_crouching = False; self.is_grounded = False; self.velocity_z = self.JUMP_FORCE
                    self.z = max(self.z, floor_h)
            
            p_data = self.wm.player_data
            p_data.x = self.x
            p_data.y = self.y
            p_data.z = self.z
            p_data.vel_z = self.velocity_z
            p_data.rot = self.rot
            p_data.is_grounded = 1 if self.is_grounded else 0
            p_data.is_crouching = 1 if self.is_crouching else 0

        def resolve_wall_collision(self, radius):
            if self.fly_mode: return

            # Right
            if self.wm.isBlocking(math.floor(self.x + radius), math.floor(self.y), self.z):
                self.x = math.floor(self.x + radius) - radius - 0.001
            # Left
            elif self.wm.isBlocking(math.floor(self.x - radius), math.floor(self.y), self.z):
                self.x = math.floor(self.x - radius) + 1.0 + radius + 0.001
            
            # Down
            if self.wm.isBlocking(math.floor(self.x), math.floor(self.y + radius), self.z):
                self.y = math.floor(self.y + radius) - radius - 0.001
            # Up
            elif self.wm.isBlocking(math.floor(self.x), math.floor(self.y - radius), self.z):
                self.y = math.floor(self.y - radius) + 1.0 + radius + 0.001

        def move(self, dt):
            self.update_physics(dt)

            if self.fly_mode:
                moveStep = self.speed * self.moveSpeed * dt
                strafeStep = self.strafe_speed * self.moveSpeed * dt
                self.rot += self.dir * self.rotSpeed * dt
                self.rot %= twoPI
                
                vx = math.cos(self.rot) * moveStep + math.sin(self.rot) * strafeStep
                vy = math.sin(self.rot) * moveStep - math.cos(self.rot) * strafeStep
                
                self.x += vx
                self.y += vy
            else:
                # Use the new C implementation
                map_address, _ = self.wm.flat_map_buffer.buffer_info()
                
                SteinWrapper.update_player_complete(
                    self.wm.player_ptr,
                    dt,
                    float(self.speed),        # input_speed
                    float(self.strafe_speed), # input_strafe
                    float(self.dir),          # input_turn
                    float(self.moveSpeed),
                    float(self.rotSpeed),
                    map_address,
                    self.wm.mapWidth, self.wm.mapHeight,
                    self.wm.num_layers, self.wm.min_layer
                )
                
                p_data = self.wm.player_data
                self.x = p_data.x
                self.y = p_data.y
                self.z = p_data.z
                self.velocity_z = p_data.vel_z
                self.rot = p_data.rot
                self.is_grounded = (p_data.is_grounded == 1)
                
                if self.z < -25.0:
                    self.z = 10.0; self.velocity_z = 0.0

            self.dirx = math.cos(self.rot)
            self.diry = math.sin(self.rot)
            
            # Preserve FOV
            current_fov = math.sqrt(self.planex**2 + self.planey**2)
            if current_fov < 0.01: current_fov = 0.66
            
            self.planex = math.cos(self.rot - 1.5708) * current_fov
            self.planey = math.sin(self.rot - 1.5708) * current_fov

    class Projectile(object):
        def __init__(self, wm, x, y, dir_x, dir_y, texture_index, damage, fired_by_player=False, is_invisible=False, pitch=0.0):
            self.wm = wm
            self.x = x
            self.y = y
            self.dir_x = dir_x
            self.dir_y = dir_y
            self.texture_index = texture_index
            self.damage = damage
            self.fired_by_player = fired_by_player
            self.is_invisible = is_invisible
            self.pitch = pitch
            
            if self.fired_by_player:
                self.speed = 100.0 
                self.z = self.wm.player.z + 1.5
                self.dir_z = (pitch / float(self.wm.height))
            else:
                self.speed = 12.0
                ground_h = self.wm.player.get_ground_height_at(x, y, check_z=self.wm.player.z)
                self.z = ground_h + 0.5
                
                p_x = self.wm.player.x
                p_y = self.wm.player.y
                p_z = self.wm.player.z + 1.0
                
                dist_2d = math.sqrt((p_x - x)**2 + (p_y - y)**2)
                if dist_2d > 0:
                    self.dir_z = (p_z - self.z) / dist_2d
                else:
                    self.dir_z = 0.0

        def update(self, dt):
            distance_to_travel = self.speed * dt
            
            step_size = 0.4
            dist_traveled = 0.0

            while dist_traveled < distance_to_travel:
                step = min(step_size, distance_to_travel - dist_traveled)
                
                self.x += self.dir_x * step
                self.y += self.dir_y * step
                self.z += self.dir_z * step
                dist_traveled += step

                if self.wm.isBlocking(math.floor(self.x), math.floor(self.y), self.z): 
                    return False
                
                ground_h = self.wm.player.get_ground_height_at(self.x, self.y, check_z=self.z)
                if self.z < ground_h:
                    return False

                if not self.fired_by_player:
                    player = self.wm.player
                    if math.sqrt((player.x - self.x)**2 + (player.y - self.y)**2) < 0.5:
                        if self.z >= player.z and self.z <= player.z + 0.9:
                            if not self.wm.builder_mode:
                                player.health -= self.damage
                                self.wm.add_damage_indicator(-self.dir_x, -self.dir_y)
                                self.wm.damage_flash_timer = 0.2
                                self.wm.time_since_last_damage = 0.0
                                renpy.sound.play("sounds/ow.ogg", channel="audio")
                            return False
                else:
                    for enemy in list(self.wm.enemies):
                        if math.sqrt((enemy.x - self.x)**2 + (enemy.y - self.y)**2) < 0.5:
                            e_ground = self.wm.player.get_ground_height_at(enemy.x, enemy.y, check_z=enemy.y) # Enemy doesnt have Z, assume ground
                            e_ground = self.wm.player.get_ground_height_at(enemy.x, enemy.y, check_z=self.z) 
                            
                            if self.z >= e_ground and self.z <= e_ground + 0.9:
                                if hasattr(self, 'pitch'):
                                    pass

                                taken = True
                                if hasattr(enemy, 'take_damage'): 
                                    taken = enemy.take_damage(self.damage)
                                else:
                                    enemy.health -= self.damage
                                
                                if taken:
                                    self.wm.hit_marker_timer = 0.15
                                    renpy.sound.play("sounds/ow.ogg", channel="audio")
                                    if enemy.health <= 0:
                                        if self.wm.is_arena_mode: persistent.stein_kills += 1
                                        if enemy in self.wm.enemies: 
                                            self.wm.enemies.remove(enemy)
                                            # Clean up Voxel Visuals
                                            if hasattr(enemy, 'visual') and enemy.visual in self.wm.scene_objects:
                                                self.wm.scene_objects.remove(enemy.visual)

                                        if getattr(enemy, 'texture_index', 0) != 255:
                                            self.wm.sprite_positions.append((enemy.x, enemy.y, enemy.destroyed_texture_index))
                                        
                                        if self.wm.is_arena_mode:
                                            drop_prob = 1.0 if enemy.coin_index == 12 else 0.35
                                            if renpy.random.random() < drop_prob:
                                                self.wm.sprite_positions.append((enemy.x, enemy.y, enemy.coin_index)) # Coins

                                        # Weapon drops removed as per request (by Fran)
                                        # if not renpy.store.stein_has_shotgun:
                                        #     if renpy.random.random() < (0.25 if enemy.coin_index == 12 else 0.10):
                                        #         self.wm.sprite_positions.append((enemy.x, enemy.y, 13)) # Shotgun
                                        
                                        # if not renpy.store.stein_has_minigun:
                                        #     if renpy.random.random() < 0.10:
                                        #         self.wm.sprite_positions.append((enemy.x, enemy.y, 15)) # Minigun

                                    return False
            return True

    class BaseEnemy(object):
        def __init__(self, wm, x, y, health=100):
            self.wm = wm
            self.x = x; self.y = y; self.health = health
            self.state = 'idle'
            self.last_known_x = None; self.last_known_y = None
            self.texture_index = 0; self.destroyed_texture_index = 0
            self.moveSpeed = 1.5; self.rotSpeed = 75 * math.pi / 180
            self.attack_range = 8.0; self.sight_range = 15.0
            if self.wm.is_arena_mode: self.attack_range = 24.0; self.sight_range = 30.0
            self.attack_cooldown = 1.5; self.damage = 10; self.coin_index = 11
            self.attack_timer = 1.0
            self.mapWidth = wm.mapWidth; self.mapHeight = wm.mapHeight

        def update(self, dt, player):
            self.attack_timer = max(0, self.attack_timer - dt)
            player_x, player_y = player.x, player.y
            dist_to_player = math.sqrt((player_x - self.x)**2 + (player_y - self.y)**2)
            has_los = self.has_line_of_sight(player_x, player_y)

            if has_los: self.last_known_x = player_x; self.last_known_y = player_y

            if self.state == 'idle':
                if dist_to_player < self.sight_range and has_los: self.state = 'chasing'
            elif self.state == 'chasing':
                target_x, target_y = player_x, player_y
                if not has_los:
                    if self.last_known_x is not None:
                        target_x, target_y = self.last_known_x, self.last_known_y
                        if math.sqrt((target_x - self.x)**2 + (target_y - self.y)**2) < 1.0:
                            self.state = 'idle'; self.last_known_x = None; return
                    else: self.state = 'idle'; return
                
                should_move = True
                if has_los:
                    if dist_to_player < self.attack_range:
                        if dist_to_player < self.attack_range * 0.5: should_move = False
                        if self.attack_timer == 0: self.attack(player)
                    else: should_move = True
                if should_move: self.move(dt, target_x, target_y)

        def attack(self, player): self.attack_timer = self.attack_cooldown

        def check_wall_collision(self, x, y, radius=0.3):
            if self.wm.isBlocking(x, y): return True
            if self.wm.isBlocking(x + radius, y): return True
            if self.wm.isBlocking(x - radius, y): return True
            if self.wm.isBlocking(x, y + radius): return True
            if self.wm.isBlocking(x, y - radius): return True
            return False

        def move(self, dt, target_x, target_y):
            dx = target_x - self.x; dy = target_y - self.y
            angle = math.atan2(dy, dx)
            look_dist = 1.2; radius = 0.35
            ahead_x = self.x + math.cos(angle) * look_dist
            ahead_y = self.y + math.sin(angle) * look_dist
            
            if self.check_wall_collision(ahead_x, ahead_y, radius):
                offsets = [-0.785, 0.785, -1.57, 1.57]
                found_path = False
                for off in offsets:
                    test_angle = angle + off
                    tx = self.x + math.cos(test_angle) * look_dist
                    ty = self.y + math.sin(test_angle) * look_dist
                    if not self.check_wall_collision(tx, ty, radius):
                        angle = test_angle; found_path = True; break
                if not found_path: angle += 2.0

            moveStep = self.moveSpeed * dt
            vx = math.cos(angle) * moveStep; vy = math.sin(angle) * moveStep
            if not self.check_wall_collision(self.x + vx, self.y, radius): self.x += vx
            if not self.check_wall_collision(self.x, self.y + vy, radius): self.y += vy

        def has_line_of_sight(self, target_x, target_y):
            map_address, _ = self.wm.flat_map_buffer.buffer_info()
            
            
            check_z = self.wm.player.z + 1.6
            
            return stein_core.check_line_of_sight(
                self.x, self.y, check_z,
                target_x, target_y,
                map_address,
                self.wm.mapWidth, self.wm.mapHeight, 
                self.wm.num_layers, self.wm.min_layer
            )

    class Guard(BaseEnemy):
        def __init__(self, wm, x, y, texture_index, destroyed_texture_index, health=100):
            super(Guard, self).__init__(wm, x, y, health)
            self.texture_index = texture_index; self.destroyed_texture_index = destroyed_texture_index
            self.moveSpeed = 1.5; self.damage = 10; self.bullet_texture_index = 6

        def attack(self, player):
            super(Guard, self).attack(player)
            
            dir_x = player.x - self.x
            dir_y = player.y - self.y
            dist = math.sqrt(dir_x**2 + dir_y**2)
            
            if dist > 0:
                dir_x /= dist
                dir_y /= dist
            
            self.wm.spawn_projectile(
                self.x, self.y, self.wm.player.z + 1.0, 
                dir_x, dir_y, 0.0,
                12.0, 
                self.bullet_texture_index, 
                self.damage, 
                False
            )
            
            renpy.sound.play("sounds/e-gunshot.ogg", channel="audio")

    class VoxelEnemy(Guard):
        def __init__(self, wm, x, y, filename, health=100):
            super(VoxelEnemy, self).__init__(wm, x, y, 255, 0, health=health)
            self.filename = filename
            
            # Load model parts (voxel model)
            parts = wm.loaded_models.get(filename, [])
            if isinstance(parts, int): parts = [(0,0,0, parts)]
            
            # Create the SceneObject for visual representation
            self.visual = SceneObject(x, y, 0.0, filename, model_parts=parts)
            
            # Register it with the renderer's scene_objects list so it gets drawn
            wm.scene_objects.append(self.visual)

        def update(self, dt, player):
            # Guard.update logic (movement, attack)
            super(VoxelEnemy, self).update(dt, player)
            
            # Sync visual position with logical position
            self.visual.x = self.x
            self.visual.y = self.y
            
            ground_z = self.wm.player.get_ground_height_at(self.x, self.y)
            self.visual.z = ground_z

    class Yuritler(Guard):
        def __init__(self, wm, x, y, health=150):
            super(Yuritler, self).__init__(wm, x, y, 9, 10, health)
            self.damage = 5; self.moveSpeed = 1.8; self.attack_cooldown = 1.0; self.coin_index = 12
        
        def attack(self, player):
            self.attack_timer = self.attack_cooldown
            dir_x = player.x - self.x
            dir_y = player.y - self.y
            dist = math.sqrt(dir_x**2 + dir_y**2)
            
            if dist > 0:
                base_angle = math.atan2(dir_y, dir_x)
                for i in range(4):
                    offset = (i / 3.0 - 0.5) * 0.2
                    p_dirx = math.cos(base_angle + offset)
                    p_diry = math.sin(base_angle + offset)
                    
                    self.wm.spawn_projectile(
                        self.x, self.y, self.wm.player.z + 1.0,
                        p_dirx, p_diry, 0.0,
                        12.0,
                        self.bullet_texture_index, 
                        self.damage, 
                        False
                    )
            
            renpy.sound.play("sounds/e-gunshot.ogg", channel="audio")

    class EliteGuard(Guard):
        def __init__(self, wm, x, y, health=100):
            super(EliteGuard, self).__init__(wm, x, y, 4, 5, health)
            self.damage = 3; self.attack_cooldown = 0.1
            self.burst_limit = 10; self.shots_fired_in_burst = 0
            self.is_reloading = False; self.reload_time = 5.0; self.reload_timer = 0.0

        def update(self, dt, player):
            if self.is_reloading:
                self.reload_timer -= dt
                if self.reload_timer <= 0: self.is_reloading = False; self.shots_fired_in_burst = 0; self.attack_timer = 0.5
            super(EliteGuard, self).update(dt, player)

        def attack(self, player):
            if self.is_reloading: return
            self.attack_timer = self.attack_cooldown
            dir_x = player.x - self.x; dir_y = player.y - self.y
            dist = math.sqrt(dir_x**2 + dir_y**2)
            if dist > 0: dir_x /= dist; dir_y /= dist
            
            self.wm.spawn_projectile(self.x, self.y, self.wm.player.z + 1.0, dir_x, dir_y, 0.0, 12.0, self.bullet_texture_index, self.damage, False)
            
            renpy.sound.play("sounds/e-gunshot.ogg", channel="audio")
            self.shots_fired_in_burst += 1
            if self.shots_fired_in_burst >= self.burst_limit: self.is_reloading = True; self.reload_timer = self.reload_time

    class Sniper(Guard):
        def __init__(self, wm, x, y, health=100):
            super(Sniper, self).__init__(wm, x, y, 4, 5, health)
            self.damage = 20; self.attack_cooldown = 1.5; self.moveSpeed = 3.0; self.bullet_texture_index = 14
            self.dodge_cooldown = 4.0; self.dodge_timer = 0.0

        def update(self, dt, player):
            self.dodge_timer = max(0, self.dodge_timer - dt)
            super(Sniper, self).update(dt, player)

        def take_damage(self, amount):
            if self.dodge_timer <= 0:
                self.dodge_timer = self.dodge_cooldown
                player = self.wm.player
                dx = player.x - self.x; dy = player.y - self.y
                dist = math.sqrt(dx*dx + dy*dy)
                if dist > 0:
                    ndx = dx / dist; ndy = dy / dist
                    strafe_x = -ndy; strafe_y = ndx
                    dodge_distance = 1.5
                    tx = self.x + strafe_x * dodge_distance; ty = self.y + strafe_y * dodge_distance
                    if not self.check_wall_collision(tx, ty, 0.35): self.x = tx; self.y = ty
                    else:
                        tx = self.x - strafe_x * dodge_distance; ty = self.y - strafe_y * dodge_distance
                        if not self.check_wall_collision(tx, ty, 0.35): self.x = tx; self.y = ty
                return False
            self.health -= amount
            return True

    class Weapon(object):
        def __init__(self, name, category, 
            normal_frameCount=5, normal_fps=15, normal_flash_frame=0, normal_name=None,
            ads_enter_frameCount=0, ads_enter_fps=20, ads_enter_name=None,
            ads_fire_frameCount=0, ads_fire_fps=15, ads_fire_flash_frame=0, ads_fire_name=None,
            run_enter_frameCount=0, run_enter_fps=15, run_enter_flash_frame=0, run_enter_name=None,
            zoom_factor=11, damage=25, projectile_type=None, cooldown=0.5, 
            ads_idle=None, ads_fire=None, loop_frames=None, 
            flash_offset=(0,0), flash_ads_offset=(0,0), flash_size=1.0, flash_color=(1.0, 0.9, 0.7),
            frameCount=None, ads_name=None, ads_frameCount=None 
            ):
            
            self.name = name
            self.category = category
            
            if frameCount is not None: normal_frameCount = frameCount
            if ads_frameCount is not None: ads_fire_frameCount = ads_frameCount
            if ads_name is not None: ads_fire_name = ads_name

            self.damage = damage; self.projectile_type = projectile_type; self.cooldown = cooldown
            self.loop_frames = loop_frames
            
            self.flash_config = {
                'offset_normal': flash_offset,
                'offset_ads': flash_ads_offset,
                'size': flash_size,
                'color': flash_color,
                'frame_normal': normal_flash_frame,
                'frame_ads': ads_fire_flash_frame,
                'frame_run': run_enter_flash_frame
            }
            
            self.playing = False
            self.frame_index = 0
            self.oldst = None
            self.last_fired = 0.0
            self.current_flash_rot = 0.0
            
            # --- Animation Data ---
            self.anims = {
                'normal': [],
                'ads_enter': [],
                'ads_fire': [],
                'run_enter': []
            }
            
            self.fps = {
                'normal': normal_fps,
                'ads_enter': ads_enter_fps,
                'ads_fire': ads_fire_fps,
                'run_enter': run_enter_fps
            }
            
            # Load Normal
            base_normal = normal_name if normal_name else name
            for i in range(normal_frameCount): 
                self.anims['normal'].append(Transform("pics/weapons/%s%s.webp" % (base_normal, i+1), xysize=(1280, 720)))
                
            # Load ADS Enter
            if ads_enter_frameCount > 0:
                base_enter = ads_enter_name if ads_enter_name else (name + "_ads_enter")
                for i in range(ads_enter_frameCount):
                    self.anims['ads_enter'].append(Transform("pics/weapons/%s%s.webp" % (base_enter, i+1), xysize=(1280, 720)))

            # Load ADS Fire
            if ads_fire_frameCount > 0:
                base_ads_fire = ads_fire_name if ads_fire_name else (name + "_ads")
                for i in range(ads_fire_frameCount):
                    self.anims['ads_fire'].append(Transform("pics/weapons/%s%s.webp" % (base_ads_fire, i+1), xysize=(1280, 720)))
            
            # Load Run Enter
            if run_enter_frameCount > 0:
                base_run = run_enter_name if run_enter_name else (name + "_run")
                for i in range(run_enter_frameCount):
                    self.anims['run_enter'].append(Transform("pics/weapons/%s%s.webp" % (base_run, i+1), xysize=(1280, 720)))
            
            self.ads_idle_img = Transform(ads_idle, xysize=(1280, 720)) if ads_idle else None
            self.ads_fire_static = Transform(ads_fire, xysize=(1280, 720)) if ads_fire else None
            
            # State: 'hip', 'entering_ads', 'ads'
            self.aim_state = 'hip'
            self.anim_state = 'idle' # 'idle', 'playing'
            
            self.flash_base = Transform(Image("pics/items/sight.webp"), size=(512, 512))

        def play(self):
            if self.anim_state != 'playing':
                self.anim_state = 'playing'
                self.frame_index = 0
                self.oldst = None
                self.current_flash_rot = renpy.random.random() * math.pi * 2.0

        def render_to(self, r, width, height, st, at, is_ads=False, is_firing=False, movement_state=None):
            if self.oldst is None: self.oldst = st
            dt = st - self.oldst
            
            is_running = movement_state.get('is_running', False) if movement_state else False

            if is_firing:
                is_running = False
            
            if is_ads:
                if self.aim_state in ('entering_run', 'running', 'exiting_run'):
                    self.aim_state = 'hip'

                if self.aim_state == 'hip':
                    if self.anims['ads_enter']:
                        self.aim_state = 'entering_ads'
                        self.frame_index = 0
                        self.anim_state = 'idle'
                        self.oldst = st
                    else:
                        self.aim_state = 'ads'
            elif is_running and self.anims.get('run_enter'):
                if self.aim_state in ('hip', 'exiting_run'):
                    if self.aim_state == 'hip' and self.anim_state == 'playing':
                        pass
                    else:
                        self.aim_state = 'entering_run'
                        self.frame_index = 0
                        self.anim_state = 'idle'
                        self.oldst = st
                elif self.aim_state in ('ads', 'entering_ads'):
                    self.aim_state = 'hip'
            else:
                if is_firing and self.aim_state in ('running', 'entering_run', 'exiting_run'):
                    self.aim_state = 'hip'
                elif self.aim_state in ('running', 'entering_run'):
                    self.aim_state = 'exiting_run'
                    self.frame_index = 0
                    self.oldst = st

                if self.aim_state != 'hip' and self.aim_state != 'exiting_run':
                    self.aim_state = 'hip'

            current_img = None
            frame_duration = 0.1
            active_anim_list = []
            
            # Determine which animation list to use and frame duration
            if self.aim_state == 'entering_ads':
                active_anim_list = self.anims['ads_enter']
                frame_duration = 1.0 / self.fps['ads_enter']
                
                if dt >= frame_duration:
                    self.oldst = st
                    self.frame_index += 1
                    if self.frame_index >= len(active_anim_list):
                        self.aim_state = 'ads'
                        self.frame_index = 0
            
            if self.aim_state == 'entering_run':
                active_anim_list = self.anims['run_enter']
                frame_duration = 1.0 / self.fps['run_enter']
                
                if dt >= frame_duration:
                    self.oldst = st
                    self.frame_index += 1
                    if self.frame_index >= len(active_anim_list):
                        self.aim_state = 'running'
                        self.frame_index = len(active_anim_list) - 1
            
            if self.aim_state == 'exiting_run':
                active_anim_list = self.anims['run_enter']
                frame_duration = 1.0 / self.fps['run_enter']
                
                if dt >= frame_duration:
                    self.oldst = st
                    self.frame_index += 1
                    if self.frame_index >= len(active_anim_list):
                        self.aim_state = 'hip'
                        self.frame_index = 0
            
            if self.aim_state == 'hip':
                if self.anim_state == 'playing':
                    active_anim_list = self.anims['normal']
                    frame_duration = 1.0 / self.fps['normal']
                    
                    if dt >= frame_duration:
                        self.oldst = st
                        if self.loop_frames and is_firing:
                            if self.frame_index == self.loop_frames[-1]: self.frame_index = self.loop_frames[0]
                            else: self.frame_index += 1
                        else:
                            self.frame_index += 1
                        
                        if self.frame_index >= len(active_anim_list):
                            self.frame_index = 0
                            self.anim_state = 'idle'
                    
                    if active_anim_list:
                        safe_idx = min(self.frame_index, len(active_anim_list)-1)
                        current_img = active_anim_list[safe_idx]
                else:
                    if self.anims['normal']:
                        current_img = self.anims['normal'][0]
            
            elif self.aim_state == 'ads':
                if self.anim_state == 'playing':
                    active_anim_list = self.anims['ads_fire']
                    if active_anim_list:
                        frame_duration = 1.0 / self.fps['ads_fire']
                        if dt >= frame_duration:
                            self.oldst = st
                            self.frame_index += 1
                            if self.frame_index >= len(active_anim_list):
                                self.frame_index = 0
                                self.anim_state = 'idle'
                        
                        safe_idx = min(self.frame_index, len(active_anim_list)-1)
                        current_img = active_anim_list[safe_idx]
                    else:
                        current_img = self.ads_fire_static if (self.ads_fire_static and is_firing) else self.ads_idle_img
                else:
                    current_img = self.ads_idle_img
            
            elif self.aim_state == 'entering_ads':
                if active_anim_list:
                    safe_idx = min(self.frame_index, len(active_anim_list)-1)
                    current_img = active_anim_list[safe_idx]

            elif self.aim_state == 'entering_run':
                if active_anim_list:
                    safe_idx = min(self.frame_index, len(active_anim_list)-1)
                    current_img = active_anim_list[safe_idx]

            elif self.aim_state == 'exiting_run':
                run_list = self.anims['run_enter']
                if run_list:
                    rev_idx = len(run_list) - 1 - self.frame_index
                    safe_idx = max(0, min(rev_idx, len(run_list)-1))
                    current_img = run_list[safe_idx]
            
            elif self.aim_state == 'running':
                if self.anims['run_enter']:
                    current_img = self.anims['run_enter'][-1]

            # Render Weapon
            if current_img:
                eileen = renpy.render(current_img, 1280, 720, st, at)
                ew, eh = eileen.get_size()
                
                # Bobbing & Breathing Logic
                offset_x = 0; offset_y = 0
                is_moving = movement_state and movement_state.get('is_moving', False)
                
                if is_moving and self.aim_state in ('hip', 'entering_run', 'running', 'exiting_run'):
                    bob_speed = 15.0 if movement_state.get('is_running', False) else 10.0
                    bob_amp_x = 50.0 if movement_state.get('is_running', False) else 20.0
                    offset_x = math.sin(st * bob_speed) * bob_amp_x
                    offset_y = abs(math.cos(st * bob_speed)) * (bob_amp_x / 2.0)
                
                elif self.aim_state == 'ads':
                    # ADS Breathing
                    breath_speed = 1.5
                    breath_amp_x = 1.5
                    breath_amp_y = 2.5
                    offset_x = math.sin(st * breath_speed) * breath_amp_x
                    # Ensure y offset is always positive (moves down) to avoid revealing bottom cut
                    offset_y = (math.sin(st * breath_speed * 1.1) + 1.0) * 0.5 * breath_amp_y
                    
                elif self.aim_state == 'hip' and not is_moving:
                    # Idle Breathing
                    breath_speed = 2.0
                    breath_amp_x = 4.0
                    breath_amp_y = 6.0
                    offset_x = math.sin(st * breath_speed) * breath_amp_x
                    # Ensure y offset is always positive
                    offset_y = (math.sin(st * breath_speed * 0.95) + 1.0) * 0.5 * breath_amp_y
                
                if self.projectile_type and self.anim_state == 'playing':
                    should_flash = False
                    flash_config_key = 'normal'
                    
                    if self.aim_state == 'hip':
                        if self.frame_index == self.flash_config['frame_normal']:
                            should_flash = True
                            flash_config_key = 'normal'
                    elif self.aim_state == 'ads':
                        if self.frame_index == self.flash_config['frame_ads']:
                            should_flash = True
                            flash_config_key = 'ads'
                    
                    import time
                    time_diff = time.time() - self.last_fired
                    flash_dur = 1.0
                    
                    if should_flash or (time_diff < flash_dur): 
                        base_x = self.flash_config['offset_ads'][0] if (self.aim_state == 'ads') else self.flash_config['offset_normal'][0]
                        base_y = self.flash_config['offset_ads'][1] if (self.aim_state == 'ads') else self.flash_config['offset_normal'][1]
                        
                        fx = base_x + offset_x
                        fy = base_y + offset_y
                        
                        progress = time_diff / flash_dur
                        
                        f_t = Transform(
                            child=self.flash_base,
                            shader="stein.weapon_fx",
                            u_flash_progress=progress,
                            u_flash_color=self.flash_config['color'],
                            u_flash_angle=self.current_flash_rot,
                            u_heat_distortion=1.0 if getattr(persistent, "stein_heat_distortion", True) else 0.0,
                            u_enable_smoke=1.0 if getattr(persistent, "stein_lighting_quality", 0) == 0 else 0.0,
                            zoom=self.flash_config['size'],
                            additive=1.0
                        )
                        f_r = renpy.render(f_t, width, height, st, at)
                        fw, fh = f_r.get_size()
                        r.blit(f_r, (width/2 + fx - fw/2, height + fy - fh/2))

                r.blit(eileen, (width/2 - ew/2 + offset_x, height - eh + offset_y))

    class RaycastLayer(renpy.Displayable):
        def __init__(self, controller, **kwargs):
            super(RaycastLayer, self).__init__(**kwargs)
            self.c = controller
            # We use an Image instead of Solid to ensure a_tex_coord attributes are generated for the shader
            self.base_displayable = Transform(Image("pics/background.webp"), size=(self.c.internal_width, self.c.internal_height))

        def render(self, width, height, st, at):
            c = self.c
            
            # Bobbing Logic
            bob_offset = 0.0
            
            fl_bob_x = 0.0
            fl_bob_y = 0.0
            
            is_moving = abs(c.player.speed) > 0.1 or abs(c.player.strafe_speed) > 0.1
            is_running = c.kb_running or c.gp_running
            effective_aiming = c.is_aiming or c.gp_aiming
            
            if is_moving and c.player.is_grounded and not effective_aiming:
                bob_speed = 10.0
                bob_amp = 0.01
                
                fl_amp_x = 0.05
                fl_amp_y = 0.03
                
                if is_running:
                    bob_speed = 15.0
                    bob_amp = 0.02
                    fl_amp_x = 0.08 
                    fl_amp_y = 0.05

                bob_offset = math.sin(st * bob_speed) * bob_amp
                
                fl_bob_x = math.sin(st * bob_speed) * fl_amp_x
                fl_bob_y = abs(math.cos(st * bob_speed)) * fl_amp_y

            renderer = renpy.render(self.base_displayable, width, height, st, at)
            renderer.add_shader("stein.raycaster")

            
            static_count = 0
            for i, sp in enumerate(c.sprite_positions):
                if i >= 50: break
                idx = i * 4
                c.static_data_buffer[idx] = sp[0]
                c.static_data_buffer[idx+1] = sp[1]
                c.static_data_buffer[idx+2] = float(sp[2])
                c.static_data_buffer[idx+3] = 0.0
                static_count += 1

            active_sprites = SteinWrapper.prepare_scene_sprites(
                c.player.x, c.player.y,
                c.proj_ptr, c.MAX_PROJECTILES,
                c.enemy_ptr, len(c.enemies), # Use the main EnemyData* array
                c.static_data_ptr, static_count,
                c.shader_sprite_ptr, 64
            )

            renderer.add_uniform("u_num_active_sprites", active_sprites)
            renderer.add_uniform("u_sprites", c.shader_sprite_buffer)

            # Pass Objects (Voxel Models)
            active_objects = []
            active_origins = []
            active_rots = [] # Euler angles in radians
            active_scales = []
            
            # Rig Groups (Dynamic Bone Objects)
            if c.editor_mode:
                for gname, gdata in c.voxel_groups.items():
                    # Get accumulated world transform for this bone
                    wt = c.get_group_accumulated_transform(gname)
                    # Get the virtual model parts for this group
                    parts = c.loaded_models.get(gname, [])
                    
                    # Rotations (Degrees to Radians)
                    rad_x = math.radians(wt.get('rx', 0.0))
                    rad_y = math.radians(wt.get('ry', 0.0))
                    rad_z = math.radians(wt.get('rz', 0.0))
                    
                    # Scales
                    sx = wt.get('sx', 1.0)
                    sy = wt.get('sy', 1.0)
                    sz = wt.get('sz', 1.0)
                    
                    # Pre-calc Rotation for Rig
                    cx, sx_sin = math.cos(rad_x), math.sin(rad_x)
                    cy, sy_sin = math.cos(rad_y), math.sin(rad_y)
                    cz, sz_sin = math.cos(rad_z), math.sin(rad_z)

                    for ox, oy, oz, mid in parts:
                        if len(active_objects) >= 128: 
                            print("WARNING: Max render objects (128) reached! Some chunks will be invisible.")
                            break
                        
                        # Calculate Local Center (Offset + Half Scale)
                        lcx = float(ox) * sx + (0.5 * sx)
                        lcy = float(oy) * sy + (0.5 * sy)
                        lcz = float(oz) * sz + (0.5 * sz)
                        
                        # Rotate Center (Orbit)
                        # Rot X
                        y1 = lcy * cx - lcz * sx_sin
                        z1 = lcy * sx_sin + lcz * cx
                        lcy, lcz = y1, z1
                        # Rot Y
                        x1 = lcx * cy + lcz * sy_sin
                        z1 = -lcx * sy_sin + lcz * cy
                        lcx, lcz = x1, z1
                        # Rot Z
                        x1 = lcx * cz - lcy * sz_sin
                        y1 = lcx * sz_sin + lcy * cz
                        lcx, lcy = x1, y1
                        
                        # Translate to Global Corner
                        editor_spread = 16.0
                        lcx = (float(ox) * editor_spread) * sx + (0.5 * sx * editor_spread)
                        lcy = (float(oy) * editor_spread) * sy + (0.5 * sy * editor_spread)
                        lcz = (float(oz) * editor_spread) * sz + (0.5 * sz * editor_spread)
                        
                        # Rotate
                        y1 = lcy * cx - lcz * sx_sin; z1 = lcy * sx_sin + lcz * cx; lcy, lcz = y1, z1
                        x1 = lcx * cy + lcz * sy_sin; z1 = -lcx * sy_sin + lcz * cy; lcx, lcz = x1, z1
                        x1 = lcx * cz - lcy * sz_sin; y1 = lcx * sz_sin + lcy * cz; lcx, lcy = x1, y1
                        
                        # Translate
                        wx = float(wt['x']) + lcx - (0.5 * sx * editor_spread)
                        wy = float(wt['y']) + lcy - (0.5 * sy * editor_spread)
                        wz = float(wt['z']) + lcz - (0.5 * sz * editor_spread)

                        active_objects.append((wx, wy, wz, float(mid)))
                        active_origins.append((float(ox)*16.0, float(oy)*16.0, float(oz)*16.0, 0.0))
                        active_rots.append((rad_x, rad_y, rad_z, 0.0))
                        
                        # Apply Editor Scale (x16)
                        active_scales.append((sx * 16.0, sy * 16.0, sz * 16.0, 0.0))

            # Scene Objects (Standard Decoration)
            source_objects = getattr(c, 'scene_objects', [])
            if source_objects:
                for obj in source_objects:
                    if len(active_objects) >= 128: break
                    if not getattr(obj, 'visible', True): continue
                    parts = getattr(obj, 'model_parts', [])
                    
                    rad_x = math.radians(getattr(obj, 'rot_x', 0.0))
                    rad_y = math.radians(getattr(obj, 'rot_y', 0.0))
                    rad_z = math.radians(getattr(obj, 'rot_z', 0.0))
                    
                    sx = getattr(obj, 'scale_x', 1.0)
                    sy = getattr(obj, 'scale_y', 1.0)
                    sz = getattr(obj, 'scale_z', 1.0)
                    
                    # Pre-calc Rotation
                    cx, sx_sin = math.cos(rad_x), math.sin(rad_x)
                    cy, sy_sin = math.cos(rad_y), math.sin(rad_y)
                    cz, sz_sin = math.cos(rad_z), math.sin(rad_z)
                    
                    for ox, oy, oz, mid in parts:
                        if len(active_objects) >= 128: 
                            print("WARNING: Max render objects (128) reached! Chunks culled.")
                            break
                        
                        # Calculate Local Center (Offset + Half Scale)
                        lcx = float(ox) * sx + (0.5 * sx)
                        lcy = float(oy) * sy + (0.5 * sy)
                        lcz = float(oz) * sz + (0.5 * sz)
                        
                        # Rotate Center (Orbit)
                        # Rot X
                        y1 = lcy * cx - lcz * sx_sin
                        z1 = lcy * sx_sin + lcz * cx
                        lcy, lcz = y1, z1
                        # Rot Y
                        x1 = lcx * cy + lcz * sy_sin
                        z1 = -lcx * sy_sin + lcz * cy
                        lcx, lcz = x1, z1
                        # Rot Z
                        x1 = lcx * cz - lcy * sz_sin
                        y1 = lcx * sz_sin + lcy * cz
                        lcx, lcy = x1, y1
                        
                        # Translate to Global Corner
                        wx = obj.x + lcx - (0.5 * sx)
                        wy = obj.y + lcy - (0.5 * sy)
                        wz = obj.z + lcz - (0.5 * sz)
                        
                        active_objects.append((wx, wy, wz, float(mid)))
                        
                        # Static Origin for highlighting
                        # We use the unrotated relative chunk index * 16.0 for mapping
                        active_origins.append((float(ox)*16.0, float(oy)*16.0, float(oz)*16.0, 0.0))
                        
                        active_rots.append((rad_x, rad_y, rad_z, 0.0))
                        active_scales.append((sx, sy, sz, 0.0))
            
            num_valid_objects = len(active_objects)
            
            # Pad to 128
            while len(active_objects) < 128:
                active_objects.append((0.0, 0.0, 0.0, -1.0))
                active_origins.append((0.0, 0.0, 0.0, 0.0))
                active_rots.append((0.0, 0.0, 0.0, 0.0))
                active_scales.append((1.0, 1.0, 1.0, 0.0))

            renderer.add_uniform("u_objects", active_objects)
            renderer.add_uniform("u_obj_origins", active_origins)
            renderer.add_uniform("u_obj_rots", active_rots)
            renderer.add_uniform("u_obj_scales", active_scales)
            renderer.add_uniform("u_num_objects", float(num_valid_objects))

            if hasattr(c, 'model_atlas'):
                renderer.add_uniform("u_model_atlas", c.model_atlas)
                renderer.add_uniform("u_num_models", float(c.num_models))

            # ADS Zoom Logic
            is_aiming = c.is_aiming or c.gp_aiming
            zoom_factor = 0.6 if is_aiming else 1.0
            
            aspect_ratio = float(width) / float(height)
            plane_len = math.sqrt(c.player.planex**2 + c.player.planey**2)
            if plane_len == 0: plane_len = 0.66
            vertical_scale = (aspect_ratio / plane_len) / zoom_factor
            
            plane_x = c.player.planex * zoom_factor
            plane_y = c.player.planey * zoom_factor

            # Calculate Camera Position (Inverse logic for Editor)
            cam_x = c.player.x
            cam_y = c.player.y
            cam_z = c.player.z
            cam_rot = c.player.rot
            
            if hasattr(c, 'editor_target') and c.editor_target:
                # Apply Position Offsets
                cam_x -= c.editor_target.x
                cam_y -= c.editor_target.y
                cam_z -= c.editor_target.z
                
                # Apply Rotation Orbit (Inverse RZ)
                # Since the object is the map, we orbit the camera around map center
                center_x = c.mapWidth / 2.0
                center_y = c.mapHeight / 2.0
                
                # Use RZ for horizontal rotation (Yaw)
                rz_rad = math.radians(c.editor_target.rz)
                
                # Rotate player position relative to center
                rel_x = cam_x - center_x
                rel_y = cam_y - center_y
                
                # 2D Rotation matrix
                s_rot = math.sin(-rz_rad)
                c_rot = math.cos(-rz_rad)
                
                cam_x = center_x + (rel_x * c_rot - rel_y * s_rot)
                cam_y = center_y + (rel_x * s_rot + rel_y * c_rot)
                
                # Offset player rotation
                cam_rot -= rz_rad

            renderer.add_uniform('u_resolution', (float(width), float(height)))
            renderer.add_uniform('u_time', st)
            renderer.add_uniform('u_player_pos', (cam_x, cam_y))
            renderer.add_uniform('u_player_dir', (math.cos(cam_rot), math.sin(cam_rot)))
            renderer.add_uniform('u_player_plane', (plane_x, plane_y))
            renderer.add_uniform('u_pitch', (c.player.pitch / float(height)) + bob_offset)
            renderer.add_uniform('u_z_offset', cam_z)
            renderer.add_uniform('u_vertical_scale', vertical_scale)
            renderer.add_uniform('u_sky_texture', c.sky_texture)
            renderer.add_uniform('u_volumetric_clouds', 1.0 if persistent.stein_volumetric_clouds else 0.0)
            
            rain_int = 0.0; snow_int = 0.0
            if hasattr(c, 'weather_state'):
                if c.weather_state == "rain": rain_int = 1.0
                elif c.weather_state == "snow": snow_int = 1.0
            renderer.add_uniform('u_rain_intensity', rain_int)
            renderer.add_uniform('u_snow_intensity', snow_int)
            renderer.add_uniform('u_wetness', getattr(c, 'wetness', 0.0))
            
            current_hour = 0.0
            current_ambient = c.lighting_preset['ambient_base']
            current_ambient_near = c.lighting_preset['ambient_near']

            if c.is_arena_mode:
                elapsed_hours = st * 0.04
                current_hour = (c.arena_start_hour + elapsed_hours) % 24.0
                
                def lerp_col(c1, c2, t):
                    return (
                        c1[0] + (c2[0] - c1[0]) * t,
                        c1[1] + (c2[1] - c1[1]) * t,
                        c1[2] + (c2[2] - c1[2]) * t
                    )

                night_amb = (0.05, 0.05, 0.1)
                day_amb = (1.0, 1.0, 1.0)
                sunset_amb = (0.7, 0.6, 0.5)

                if current_hour < 5.0:
                    current_ambient = night_amb
                elif current_hour < 8.0:
                    p = (current_hour - 5.0) / 3.0
                    current_ambient = lerp_col(night_amb, day_amb, p)
                elif current_hour < 16.0:
                    current_ambient = day_amb
                elif current_hour < 19.0:
                    p = (current_hour - 16.0) / 3.0
                    current_ambient = lerp_col(day_amb, sunset_amb, p)
                elif current_hour < 21.0:
                    p = (current_hour - 19.0) / 2.0
                    current_ambient = lerp_col(sunset_amb, night_amb, p)
                else:
                    current_ambient = night_amb
                
                current_ambient_near = (0.0, 0.0, 0.0)
            else:
                current_hour = float(c.lighting_preset.get('time_id', 0.0))
            renderer.add_uniform('u_time_of_day', current_hour)

            renderer.add_uniform('u_ambient_color', current_ambient)
            renderer.add_uniform('u_ambient_near_color', current_ambient_near)
            renderer.add_uniform('u_highlight_pos', getattr(c, 'highlight_pos', (-1.0, -1.0, -1.0)))
            renderer.add_uniform('u_pivot_pos', getattr(c, 'current_pivot', (-1.0, -1.0, -1.0)))
            renderer.add_uniform('u_group_offsets', getattr(c, 'shader_group_offsets', [(0.0,0.0,0.0)] * 16))
            renderer.add_uniform('u_group_rots', getattr(c, 'shader_group_rots', [0.0] * 16))
            renderer.add_uniform('u_group_pivots', getattr(c, 'shader_group_pivots', [(0.0,0.0,0.0)] * 16))
            renderer.add_uniform('u_obj_scale', 16.0 if c.editor_mode else 1.0)

            renderer.add_uniform('u_map_size', (float(c.map_w), float(c.map_h)))
            renderer.add_uniform('u_map_uv_scale', c.map_uv_scale)
            renderer.add_uniform('u_map_texture', c.map_texture)
            
            # Selection Map
            if getattr(c, 'selection_texture', None) is None:
                c.update_selection_texture()
            renderer.add_uniform('u_selection_texture', c.selection_texture)

            renderer.add_uniform('u_map_size', (float(c.map_w), float(c.map_h)))
            renderer.add_uniform('u_map_layer_base_y', float(c.min_layer))
            renderer.add_uniform('u_map_layer_count', float(c.num_layers))
            
            # Grid Packing Uniforms
            norm_size = getattr(c, 'map_layer_norm_size', (1.0, 1.0))
            cols = getattr(c, 'map_grid_cols', 1.0)
            
            renderer.add_uniform('u_map_layer_norm_size', norm_size)
            renderer.add_uniform('u_map_grid_cols', cols)
            renderer.add_uniform('u_map_tex_pixel_size', c.map_tex_pixel_size)
            renderer.add_uniform('u_map_uv_scale', c.map_uv_scale)
            renderer.add_uniform('u_wall_atlas', c.wall_atlas)
            renderer.add_uniform('u_floor_texture', c.floor_texture)
            renderer.add_uniform('u_num_textures', float(c.num_textures))
            renderer.add_uniform('u_sprite_atlas', c.sprite_atlas)
            renderer.add_uniform('u_num_sprite_textures', float(c.num_sprite_textures))

            renderer.add_uniform('u_flashlight_active', 1.0 if c.flashlight_on else 0.0)
            renderer.add_uniform('u_flashlight_bob', (fl_bob_x, fl_bob_y))
            
            renderer.add_uniform('u_soft_shadows', 1.0 if getattr(persistent, "stein_soft_shadows", True) else 0.0)
            renderer.add_uniform('u_enable_shadows', 1.0 if getattr(persistent, "stein_enable_shadows", True) else 0.0)
            renderer.add_uniform('u_max_dist', 500.0 if c.builder_mode else 250.0)
            renderer.add_uniform('u_simple_floor', 1.0 if getattr(persistent, "stein_simple_floor", False) else 0.0)
            
            # Flash
            import time
            current_weapon = c.weapons[c.player.current_weapon_name]
            flash_intensity = 0.0
            if current_weapon.projectile_type and (time.time() - current_weapon.last_fired) < 0.1:
                flash_intensity = 1.0 - ((time.time() - current_weapon.last_fired) / 0.1)
            renderer.add_uniform('u_flash_intensity', flash_intensity)
            renderer.add_uniform('u_flash_color', (1.0, 0.8, 0.4))

            renderer.add_uniform('u_light_positions', [0.0] * 64)
            renderer.add_uniform('u_num_active_lights', 0.0)

            renpy.redraw(self, 0.000001)
            return renderer

    def add_keyframe(anim_data, track, time, value, easing="linear"):
        """Inserts or updates a keyframe in the animation data."""
        if track not in anim_data["tracks"]:
            anim_data["tracks"][track] = []
        
        updated = False
        for k in anim_data["tracks"][track]:
            if abs(k["time"] - time) < 0.001:
                k["value"] = value
                k["easing"] = easing
                updated = True
                break
        
        if not updated:
            anim_data["tracks"][track].append({ "time": time, "value": value, "easing": easing })
        
        # Sort by time
        anim_data["tracks"][track].sort(key=lambda x: x["time"])

    def remove_keyframe(anim_data, track, time):
        """Removes a keyframe at specific time."""
        if track in anim_data["tracks"]:
            anim_data["tracks"][track] = [k for k in anim_data["tracks"][track] if abs(k["time"] - time) > 0.001]

    def get_anim_value_at_time(anim_data, track, time, default_val=0.0):
        """Calculates interpolated value for a track at a given time."""
        if track not in anim_data["tracks"] or not anim_data["tracks"][track]:
            return default_val
            
        keyframes = anim_data["tracks"][track]
        
        # Boundary checks
        if time <= keyframes[0]["time"]: return keyframes[0]["value"]
        if time >= keyframes[-1]["time"]: return keyframes[-1]["value"]
        
        # Interpolation
        for i in range(len(keyframes) - 1):
            k1 = keyframes[i]
            k2 = keyframes[i+1]
            
            if time >= k1["time"] and time < k2["time"]:
                duration = k2["time"] - k1["time"]
                if duration <= 0: return k1["value"]
                
                t = (time - k1["time"]) / duration
                
                # Linear Interpolation
                return k1["value"] + (k2["value"] - k1["value"]) * t
                
        return default_val

    def apply_animation_frame(anim_data, target_obj, time):
        """Updates the target object properties based on animation data at 'time'."""
        if not target_obj: return
        
        # Apply Global Tracks
        target_obj.x = get_anim_value_at_time(anim_data, "x", time, target_obj.x)
        target_obj.y = get_anim_value_at_time(anim_data, "y", time, target_obj.y)
        target_obj.z = get_anim_value_at_time(anim_data, "z", time, target_obj.z)
        
        target_obj.rx = get_anim_value_at_time(anim_data, "rx", time, getattr(target_obj, 'rx', 0.0))
        target_obj.ry = get_anim_value_at_time(anim_data, "ry", time, getattr(target_obj, 'ry', 0.0))
        target_obj.rz = get_anim_value_at_time(anim_data, "rz", time, getattr(target_obj, 'rz', 0.0))
        
        target_obj.sx = get_anim_value_at_time(anim_data, "sx", time, getattr(target_obj, 'sx', 1.0))
        target_obj.sy = get_anim_value_at_time(anim_data, "sy", time, getattr(target_obj, 'sy', 1.0))
        target_obj.sz = get_anim_value_at_time(anim_data, "sz", time, getattr(target_obj, 'sz', 1.0))

        # Apply Group Tracks
        # Scans JSON for tracks like "group:Arm:x"
        if "tracks" in anim_data:
            for track_name in anim_data["tracks"].keys():
                if track_name.startswith("group:"):
                    parts = track_name.split(":")
                    if len(parts) >= 3:
                        gname = parts[1]
                        field = parts[2]
                        # Update the target object's local group data
                        gdata = target_obj.get_group_data(gname)
                        gdata[field] = get_anim_value_at_time(anim_data, track_name, time, gdata.get(field, 0.0))

    class AnimationController(object):
        def __init__(self, owner):
            self.owner = owner
            self.anim_data = None
            self.anim_name = None
            self.rig_data = {} # Hierarchical bone data
            self.current_time = 0.0
            self.is_playing = False
            self.loop = False
            self.duration = 0.0
            # Global Offsets
            self.ox = 0.0; self.oy = 0.0; self.oz = 0.0
            self.orx = 0.0; self.ory = 0.0; self.orz = 0.0
            self.osx = 1.0; self.osy = 1.0; self.osz = 1.0

        def play(self, anim_name, loop=True):
            if hasattr(renpy.store, 'load_anim_json'):
                data = renpy.store.load_anim_json(anim_name + ".json")
                if data:
                    self.anim_data = data
                    self.anim_name = anim_name
                    
                    # Merge rig data (don't overwrite if missing in new anim)
                    new_rig = data.get("voxel_groups", {})
                    if new_rig:
                        self.rig_data.update(new_rig)
                        
                    self.current_time = 0.0
                    self.duration = float(data['meta'].get('duration', 1.0))
                    self.loop = loop 
                    self.is_playing = True
                    self.reset_offsets()
                else:
                    print(f"Animation {anim_name} not found.")

        def reset_offsets(self):
            self.ox = 0.0; self.oy = 0.0; self.oz = 0.0
            self.orx = 0.0; self.ory = 0.0; self.orz = 0.0
            self.osx = 1.0; self.osy = 1.0; self.osz = 1.0

        def stop(self):
            self.is_playing = False
            self.anim_name = None
            self.reset_offsets()

        def get_group_world_offset(self, gname):
            """Calculates the accumulated world offset for a bone in an animation."""
            if not self.anim_data or "tracks" not in self.anim_data:
                return (0.0, 0.0, 0.0)
            
            # Get local offsets for this group
            lx = get_anim_value_at_time(self.anim_data, f"group:{gname}:x", self.current_time, 0.0)
            ly = get_anim_value_at_time(self.anim_data, f"group:{gname}:y", self.current_time, 0.0)
            lz = get_anim_value_at_time(self.anim_data, f"group:{gname}:z", self.current_time, 0.0)
            
            # Add Parent Offsets (Recursively from the stored rig data)
            parent_name = self.rig_data.get(gname, {}).get("parent")
            
            if parent_name and parent_name in self.rig_data:
                px, py, pz = self.get_group_world_offset(parent_name)
                return (lx + px, ly + py, lz + pz)
            
            return (lx, ly, lz)

        def get_group_world_rotation(self, gname):
            """Calculates the accumulated world rotation for a bone."""
            if not self.anim_data or "tracks" not in self.anim_data:
                return (0.0, 0.0, 0.0)
            
            lrx = get_anim_value_at_time(self.anim_data, f"group:{gname}:rx", self.current_time, 0.0)
            lry = get_anim_value_at_time(self.anim_data, f"group:{gname}:ry", self.current_time, 0.0)
            lrz = get_anim_value_at_time(self.anim_data, f"group:{gname}:rz", self.current_time, 0.0)
            
            parent_name = self.rig_data.get(gname, {}).get("parent")
            
            if parent_name and parent_name in self.rig_data:
                prx, pry, prz = self.get_group_world_rotation(parent_name)
                return (lrx + prx, lry + pry, lrz + prz)
            
            return (lrx, lry, lrz)

        def get_group_world_scale(self, gname):
            """Calculates the accumulated world scale for a bone."""
            if not self.anim_data or "tracks" not in self.anim_data:
                return (1.0, 1.0, 1.0)
            
            lsx = get_anim_value_at_time(self.anim_data, f"group:{gname}:sx", self.current_time, 1.0)
            lsy = get_anim_value_at_time(self.anim_data, f"group:{gname}:sy", self.current_time, 1.0)
            lsz = get_anim_value_at_time(self.anim_data, f"group:{gname}:sz", self.current_time, 1.0)
            
            parent_name = self.rig_data.get(gname, {}).get("parent")
            
            if parent_name and parent_name in self.rig_data:
                psx, psy, psz = self.get_group_world_scale(parent_name)
                return (lsx * psx, lsy * psy, lsz * psz)
            
            return (lsx, lsy, lsz)

        def update(self, dt):
            if not self.is_playing or not self.anim_data:
                self.reset_offsets()
                return

            self.current_time += dt
            
            if self.current_time >= self.duration:
                if self.loop:
                    self.current_time %= self.duration
                else:
                    self.current_time = self.duration
                    self.is_playing = False
            
            # Global Entity Offsets
            self.ox = get_anim_value_at_time(self.anim_data, "x", self.current_time, 0.0)
            self.oy = get_anim_value_at_time(self.anim_data, "y", self.current_time, 0.0)
            self.oz = get_anim_value_at_time(self.anim_data, "z", self.current_time, 0.0)
            
            self.orx = get_anim_value_at_time(self.anim_data, "rx", self.current_time, 0.0)
            self.ory = get_anim_value_at_time(self.anim_data, "ry", self.current_time, 0.0)
            self.orz = get_anim_value_at_time(self.anim_data, "rz", self.current_time, 0.0)
            
            self.osx = get_anim_value_at_time(self.anim_data, "sx", self.current_time, 1.0)
            self.osy = get_anim_value_at_time(self.anim_data, "sy", self.current_time, 1.0)
            self.osz = get_anim_value_at_time(self.anim_data, "sz", self.current_time, 1.0)

    class SceneObject(object):
        def __init__(self, x, y, z, filename, model_parts=[]):
            self.x = float(x)
            self.y = float(y)
            self.z = float(z)
            self.filename = filename
            self.model_parts = model_parts # List of (offset_x, offset_y, offset_z, model_id)
            
            # Mutable Transform Properties
            self.scale_x = 1.0
            self.scale_y = 1.0
            self.scale_z = 1.0
            self.rot_x = 0.0
            self.rot_y = 0.0
            self.rot_z = 0.0
            self.visible = True

    class VoxelEntity(object):
        def __init__(self, wm, x, y, z, filename=MODEL_VOXEL_BASIC, health=100, damage=10, speed=2.0, attack_range=12.0, cooldown=1.5, walk_anim=ANIM_VOXEL_WALK, shoot_anim=ANIM_VOXEL_SHOOT):
            self.wm = wm
            self.x = float(x)
            self.y = float(y)
            self.z = float(z)
            self.health = health
            self.dead = False
            self.filename = filename
            
            # Animation Names
            self.anim_walk = walk_anim
            self.anim_shoot = shoot_anim
            
            # Combat Stats
            self.damage = damage
            self.move_speed = speed
            self.attack_range = attack_range
            self.attack_cooldown = cooldown
            
            self.attack_timer = 1.0
            self.bullet_texture_index = 6
            self.texture_index = 255 
            
            # Load model parts
            parts = wm.loaded_models.get(filename, [])
            if isinstance(parts, int): parts = [(0,0,0, parts)]
            
            self.model_parts = parts
            
            # Calculate AABB
            self.min_x = 0.0; self.min_y = 0.0; self.min_z = 0.0
            self.max_x = 1.0; self.max_y = 1.0; self.max_z = 1.0
            
            if parts:
                xs = [p[0] for p in parts]; ys = [p[1] for p in parts]; zs = [p[2] for p in parts]
                self.min_x = min(xs); self.min_y = min(ys); self.min_z = min(zs)
                self.max_x = max(xs) + 1.0; self.max_y = max(ys) + 1.0; self.max_z = max(zs) + 1.0
            
            # Animation
            self.anim_controller = AnimationController(self)
            
            # Rig init
            self.bone_visuals = {} # Map of BoneName is SceneObject
            self.voxel_groups = {}
            
            # Scan animations for rig definitions
            potential_anims = [self.anim_walk, self.anim_shoot]
            for anim_name in potential_anims:
                anim_data = renpy.store.load_anim_json(anim_name + ".json")
                if anim_data and "voxel_groups" in anim_data:
                    # Found a rig!
                    self.voxel_groups.update(anim_data["voxel_groups"])
            
            # Pass the complete rig definition to the controller
            if self.voxel_groups:
                print(f"DEBUG: VoxelEntity Init - Voxel Groups Found: {list(self.voxel_groups.keys())}")
                self.anim_controller.rig_data = self.voxel_groups.copy()
                
                for gname in self.voxel_groups.keys():
                    # Look for our unique model key: "filename:gname"
                    unique_key = f"{self.filename}:{gname}"
                    g_parts = wm.loaded_models.get(unique_key, [])
                    print(f"DEBUG: Looking for key '{unique_key}' -> Found parts: {len(g_parts)}")
                    
                    if g_parts:
                        sobj = SceneObject(x, y, z, gname, model_parts=g_parts)
                        self.bone_visuals[gname] = sobj
                        wm.scene_objects.append(sobj)
            
            # Base Visual (Only if no rig or for static parts)
            self.visual = SceneObject(x, y, z, filename, model_parts=parts)
            if not self.bone_visuals:
                wm.scene_objects.append(self.visual)
            else:
                # If rigged, the base model is hidden or only shows non-grouped voxels
                # (For now, we hide it and rely on bone visuals)
                self.visual.visible = False

        def get_world_aabb(self):
            return (
                self.x + self.min_x, self.y + self.min_y, self.z + self.min_z,
                self.x + self.max_x, self.y + self.max_y, self.z + self.max_z
            )

        def check_collision(self, px, py, pz):
            min_x, min_y, min_z, max_x, max_y, max_z = self.get_world_aabb()
            return (px >= min_x and px <= max_x and
                    py >= min_y and py <= max_y and
                    pz >= min_z and pz <= max_z)

        def has_line_of_sight(self, target_x, target_y):
            map_address, _ = self.wm.flat_map_buffer.buffer_info()
            check_z = self.wm.player.z + 1.6
            return stein_core.check_line_of_sight(
                self.x, self.y, check_z,
                target_x, target_y,
                map_address,
                self.wm.mapWidth, self.wm.mapHeight, 
                self.wm.num_layers, self.wm.min_layer
            )

        def attack(self, player):
            self.attack_timer = self.attack_cooldown
            dir_x = player.x - self.x
            dir_y = player.y - self.y
            dist = math.sqrt(dir_x**2 + dir_y**2)
            
            if dist > 0:
                dir_x /= dist; dir_y /= dist
            
            self.wm.spawn_projectile(self.x, self.y, self.z + 0.8, dir_x, dir_y, 0.0, 12.0, self.bullet_texture_index, self.damage, False)
            renpy.sound.play("sounds/e-gunshot.ogg", channel="audio")
            self.anim_controller.play(self.anim_shoot, loop=False)

        def take_damage(self, amount):
            self.health -= amount
            if self.health <= 0: self.die()
            return True

        def die(self):
            if not self.dead:
                self.dead = True
                if self.visual in self.wm.scene_objects: self.wm.scene_objects.remove(self.visual)
                for sobj in self.bone_visuals.values():
                    if sobj in self.wm.scene_objects: self.wm.scene_objects.remove(sobj)

        def update(self, dt, player):
            if self.dead: return
            self.attack_timer = max(0, self.attack_timer - dt)
            dx = player.x - self.x; dy = player.y - self.y
            dist = math.sqrt(dx*dx + dy*dy)
            
            # Vision and Attack
            if dist < self.attack_range and self.has_line_of_sight(player.x, player.y):
                if self.attack_timer <= 0: self.attack(player)
            
            # Movement
            is_moving = False
            if dist > 2.0 and dist < 25.0:
                speed = self.move_speed * dt
                try:
                    map_addr, _ = self.wm.flat_map_buffer.buffer_info()
                    nx, ny = SteinWrapper.resolve_movement(self.x, self.y, self.z, (dx/dist)*speed, (dy/dist)*speed, 0.4, map_addr, self.wm.mapWidth, self.wm.mapHeight, self.wm.num_layers, self.wm.min_layer)
                    self.x, self.y = nx, ny
                    is_moving = True
                except:
                    self.x += (dx/dist)*speed; self.y += (dy/dist)*speed; is_moving = True
            
            # Animation
            # DEBUG: Force play walking to test bones
            # if not self.anim_controller.is_playing:
            #    self.anim_controller.play(self.anim_walk, loop=True)
            
            if is_moving:
                if not self.anim_controller.is_playing or self.anim_controller.anim_name == self.anim_walk:
                    if self.anim_controller.anim_name != self.anim_walk: self.anim_controller.play(self.anim_walk, loop=True)
            else:
                if self.anim_controller.is_playing and self.anim_controller.anim_name == self.anim_walk: self.anim_controller.stop()

            self.anim_controller.update(dt)
            
            # Sync visuals (logic position + animation offset)
            # Global Body Pos
            bx, by, bz = self.x + self.anim_controller.ox, self.y + self.anim_controller.oy, self.z + self.anim_controller.oz
            
            if not self.bone_visuals:
                self.visual.x, self.visual.y, self.visual.z = bx, by, bz
            else:
                # Update each bone
                for gname, sobj in self.bone_visuals.items():
                    # Get hierarchical world offset from animation (in voxel units)
                    ox, oy, oz = self.anim_controller.get_group_world_offset(gname)
                    # Convert to world scale (1:16)
                    sobj.x = bx + (ox / 16.0)
                    sobj.y = by + (oy / 16.0)
                    sobj.z = bz + (oz / 16.0)
                    
                    # if gname == "body":
                    #     # print(f"DEBUG POS: EntityX={self.x:.2f} BoneX={sobj.x:.2f}")
                    #     pass

                    # Sync rotation/scale
                    grx, gry, grz = self.anim_controller.get_group_world_rotation(gname)
                    
                    sobj.rot_x = grx + self.anim_controller.orx
                    sobj.rot_y = gry + self.anim_controller.ory
                    sobj.rot_z = grz + self.anim_controller.orz
                    
                    gsx, gsy, gsz = self.anim_controller.get_group_world_scale(gname)
                    sobj.scale_x = gsx * self.anim_controller.osx
                    sobj.scale_y = gsy * self.anim_controller.osy
                    sobj.scale_z = gsz * self.anim_controller.osz

    class VoxelSniper(VoxelEntity):
        def __init__(self, wm, x, y, z, filename=MODEL_VOXEL_SNIPER, health=80):
            super(VoxelSniper, self).__init__(wm, x, y, z, filename, health, 
                damage=25, speed=3.5, attack_range=20.0, cooldown=2.0,
                walk_anim=ANIM_VOXEL_SNIPER_WALK, shoot_anim=ANIM_VOXEL_SNIPER_SHOOT)
            self.dodge_cooldown = 4.0
            self.dodge_timer = 0.0
            self.bullet_texture_index = 14 # Sniper bullet

        def update(self, dt, player):
            self.dodge_timer = max(0, self.dodge_timer - dt)
            super(VoxelSniper, self).update(dt, player)

        def take_damage(self, amount):
            if self.dodge_timer <= 0:
                self.dodge_timer = self.dodge_cooldown
                
                # Dodge Logic (basic)
                dx = self.wm.player.x - self.x
                dy = self.wm.player.y - self.y
                dist = math.sqrt(dx*dx + dy*dy)
                
                if dist > 0:
                    ndx = dx / dist
                    ndy = dy / dist
                    # Strafe vector
                    strafe_x = -ndy
                    strafe_y = ndx
                    
                    # Randomize direction
                    if renpy.random.random() < 0.5:
                        strafe_x = -strafe_x
                        strafe_y = -strafe_y
                    
                    dodge_dist = 2.5
                    
                    self.x += strafe_x * dodge_dist
                    self.y += strafe_y * dodge_dist
                    
                    # Instant visual update
                    self.visual.x = self.x
                    self.visual.y = self.y
                    
                    renpy.sound.play("sounds/pew.ogg", channel="audio") # Dash sound
                    return False # Dodged
            
            return super(VoxelSniper, self).take_damage(amount)

    class VoxelElite(VoxelEntity):
        def __init__(self, wm, x, y, z, filename=MODEL_VOXEL_ELITE, health=100):
            super(VoxelElite, self).__init__(wm, x, y, z, filename, health, 
                damage=3, speed=2.5, attack_range=15.0, cooldown=0.1,
                walk_anim=ANIM_VOXEL_ELITE_WALK, shoot_anim=ANIM_VOXEL_ELITE_SHOOT)
            self.burst_limit = 10
            self.shots_fired_in_burst = 0
            self.is_reloading = False
            self.reload_time = 5.0
            self.reload_timer = 0.0

        def update(self, dt, player):
            if self.is_reloading:
                self.reload_timer -= dt
                if self.reload_timer <= 0:
                    self.is_reloading = False
                    self.shots_fired_in_burst = 0
                    self.attack_timer = 0.5
            super(VoxelElite, self).update(dt, player)

        def attack(self, player):
            if self.is_reloading: return
            
            # Call base attack
            super(VoxelElite, self).attack(player)
            
            # Burst Logic
            self.shots_fired_in_burst += 1
            if self.shots_fired_in_burst >= self.burst_limit:
                self.is_reloading = True
                self.reload_timer = self.reload_time

    class VoxelYuritler(VoxelEntity):
        def __init__(self, wm, x, y, z, filename=MODEL_VOXEL_YURITLER, health=150):
            super(VoxelYuritler, self).__init__(wm, x, y, z, filename, health, 
                damage=5, speed=1.8, attack_range=12.0, cooldown=1.0,
                walk_anim=ANIM_VOXEL_YURITLER_WALK, shoot_anim=ANIM_VOXEL_YURITLER_SHOOT)
            self.coin_index = 12


    class GPURenpystein(renpy.Displayable):
        def __init__(self, width, height, worldMap, exits=[], objects=[], internal_width=None, internal_height=None, lighting_preset=None, editor_mode=False, **kwargs):
            super(GPURenpystein, self).__init__(**kwargs)
            self.width = width
            self.height = height
            self.map_data = worldMap
            self.worldMap = worldMap
            self.editor_mode = editor_mode 
            self.is_arena_mode = getattr(renpy.store, 'is_arena_mode', False)
            
            self.editor_target = None # For Editor Inverse Camera logic
            self.highlight_pos = (-1.0, -1.0, -1.0) # Voxel selection coordinates
            self.current_pivot = (-1.0, -1.0, -1.0) # Pivot point for current selection
            self.selected_group = "None" # Currently active vertex group
            self.selection_map = {} # Map of (x,y,z) is bool
            self.voxel_groups = {} # Map of "GroupName" is {voxels, pivot, parent}
            self.master_voxels = [] # Original model voxels (x, y, z, id)
            self.last_rig_state = None # For optimization
            self.show_bones = True # Visual toggle for skeleton
            self.selection_texture = None
            self.objects_def = objects # List of (x, y, z, filename) 
            
            if isinstance(worldMap, dict) or hasattr(worldMap, 'items'):
                max_x = 0
                max_y = 0
                for grid in worldMap.values():
                    if len(grid) > max_x: max_x = len(grid)
                    if len(grid) > 0 and len(grid[0]) > max_y: max_y = len(grid[0])
                self.mapWidth = max_x
                self.mapHeight = max_y
            else:
                s_mapWidth = len(worldMap)
                if s_mapWidth > 0:
                    self.mapWidth = s_mapWidth
                    self.mapHeight = len(worldMap[0])
                else:
                    self.mapWidth = 0
                    self.mapHeight = 0
            
            self.map_w = self.mapWidth
            self.map_h = self.mapHeight
            
            self.lighting_preset = lighting_preset if lighting_preset else {
                'ambient_base': (0.02, 0.02, 0.05),
                'ambient_near': (0.05, 0.05, 0.08),
                'sky_texture': "pics/background.webp",
                'time_id': 0.0
            }

            self.is_arena_mode = getattr(renpy.store, 'is_arena_mode', False)

            self.arena_start_hour = 12.0
            if self.is_arena_mode:
                roll = renpy.random.random()
                if roll < 0.33:
                    self.arena_start_hour = 12.0 # Day
                elif roll < 0.66:
                    self.arena_start_hour = 18.0 # Sunset
                else:
                    self.arena_start_hour = 2.0 # Night

            self.weather_state = "none"
            self.weather_timer = 0.0
            self.next_weather_check = 5.0
            self.wetness = 0.0

            self.fps_frame_count = 0
            self.fps_timer_accum = 0.0

            self.exits = exits
            
            self.internal_width = internal_width if internal_width is not None else width
            self.internal_height = internal_height if internal_height is not None else height
            self.damage_flash_timer = 0.0
            self.return_value = None
            self.heal_flash_timer = 0.0
            self.hit_marker_timer = 0.0
            self.damage_indicators = []
            self.time_since_last_damage = 0.0
            
            self.pickup_msg = ""
            self.pickup_msg_timer = 0.0
            
            self.map_texture = self.create_map_texture()
            self.wall_atlas, self.num_textures = self.create_wall_atlas()
            
            # Prepare objects list for atlas generation (models)
            atlas_objects = list(objects)
            self.pending_rigs = {}

            # Pre-scan enemies to include their models and rig chunks in atlas generation
            if hasattr(renpy.store, 'stein_enemies'):
                for e_data in renpy.store.stein_enemies:
                    type_id = e_data[5] if len(e_data) > 5 else 0
                    
                    if type_id >= 100:
                        model_file = e_data[2] if len(e_data) > 2 else ""
                        if model_file:
                            atlas_objects.append((0,0,0, model_file))
                            
                            # Check for Rigs in default animations
                            # Logic: Find the walk_anim name for this type
                            w_anim = renpy.store.ANIM_VOXEL_WALK
                            if type_id == renpy.store.ENEMY_TYPE_VOXEL_SNIPER: w_anim = renpy.store.ANIM_VOXEL_SNIPER_WALK
                            elif type_id == renpy.store.ENEMY_TYPE_VOXEL_ELITE: w_anim = renpy.store.ANIM_VOXEL_ELITE_WALK
                            elif type_id == renpy.store.ENEMY_TYPE_VOXEL_YURITLER: w_anim = renpy.store.ANIM_VOXEL_YURITLER_WALK
                            
                            a_data = renpy.store.load_anim_json(w_anim + ".json")
                            if a_data and "voxel_groups" in a_data:
                                # Need model data for texture ID lookup
                                m_data = renpy.store.load_object_json(model_file)
                                id_map = {}
                                if m_data:
                                    for mz, grid in m_data.items():
                                        for mx, row in enumerate(grid):
                                            for my, tid in enumerate(row):
                                                if tid > 0: id_map[(int(mx), int(my), int(mz))] = int(tid)
                                
                                for gname, gdata in a_data["voxel_groups"].items():
                                    # Create a unique key for this bone model in the atlas
                                    unique_bone_key = f"{model_file}:{gname}"
                                    print(f"DEBUG PRE-SCAN: Baking rig for {unique_bone_key}")
                                    self.pending_rigs[unique_bone_key] = {'voxels': gdata.get('voxels', []), 'id_lookup': id_map}

            # Pre-load arena models if in Arena Mode
            if self.is_arena_mode:
                arena_types = [
                    (renpy.store.MODEL_VOXEL_BASIC, renpy.store.ANIM_VOXEL_WALK),
                    (renpy.store.MODEL_VOXEL_SNIPER, renpy.store.ANIM_VOXEL_SNIPER_WALK),
                    (renpy.store.MODEL_VOXEL_ELITE, renpy.store.ANIM_VOXEL_ELITE_WALK),
                    (renpy.store.MODEL_VOXEL_YURITLER, renpy.store.ANIM_VOXEL_YURITLER_WALK)
                ]
                
                for model_file, anim_file in arena_types:
                    if not model_file: continue
                    atlas_objects.append((0,0,0, model_file))
                    
                    if anim_file:
                        a_data = renpy.store.load_anim_json(anim_file + ".json")
                        if a_data and "voxel_groups" in a_data:
                            m_data = renpy.store.load_object_json(model_file)
                            id_map = {}
                            if m_data:
                                for mz, grid in m_data.items():
                                    for mx, row in enumerate(grid):
                                        for my, tid in enumerate(row):
                                            if tid > 0: id_map[(int(mx), int(my), int(mz))] = int(tid)
                            
                            for gname, gdata in a_data["voxel_groups"].items():
                                unique_bone_key = f"{model_file}:{gname}"
                                # print(f"DEBUG ARENA: Baking {unique_bone_key}")
                                self.pending_rigs[unique_bone_key] = {'voxels': gdata.get('voxels', []), 'id_lookup': id_map}

            self.model_atlas, self.num_models = self.create_model_atlas(atlas_objects)


            self.scene_objects = []
            if objects:
                for obj_def in objects:
                    # obj_def is (x, y, z, filename)
                    if len(obj_def) >= 4:
                        x, y, z, fname = obj_def
                        
                        # Resolve parts from loaded models
                        parts = self.loaded_models.get(fname, [])
                        if isinstance(parts, int):
                            parts = [(0,0,0, parts)]
                        
                        # Create SceneObject
                        sobj = SceneObject(x, y, z, fname, model_parts=parts)
                        self.scene_objects.append(sobj)

            self.floor_texture = self.load_floor_texture()
            self.sprite_atlas, self.num_sprite_textures = self.create_sprite_atlas()
            self.solid_base = renpy.display.imagelike.Solid("#000", xsize=width, ysize=height)
            
            self.raycast_layer = RaycastLayer(self, xsize=self.internal_width, ysize=self.internal_height)
            
            sky_path = self.lighting_preset.get('sky_texture', "pics/background.webp")
            try:
                with renpy.open_file(sky_path) as f:
                    bg_surf = pygame.image.load(f).convert_alpha()
            except:
                # Fallback
                with renpy.open_file("pics/background.webp") as f:
                    bg_surf = pygame.image.load(f).convert_alpha()
            
            bg_surf = pygame.transform.scale(bg_surf, (width, height))
            self.sky_texture = renpy.display.draw.load_texture(bg_surf)

            self.player = Player(self, renpy.store.player_x, renpy.store.player_y, renpy.store.player_dirx, renpy.store.player_diry, renpy.store.player_planex, renpy.store.player_planey)
            
            self.oldst = None
            self.last_rot = None
            self.active_fingers = {}
            self.mouse_initialized = False
            
            # Inputs
            self.kb_speed = 0.0
            self.kb_strafe = 0.0
            self.kb_dir = 0.0
            self.kb_fly_up = False
            self.kb_fly_down = False
            self.builder_mode = False
            self.lock_map_expansion = False
            self.selected_voxel = 1
            
            if config.developer:
                self.builder_mode = True
                self.player.fly_mode = True
                self.pickup_msg = "BUILDER MODE ON (DEV)"
                self.pickup_msg_timer = 3.0
            
            self.gp_speed = 0.0
            self.gp_strafe = 0.0
            self.gp_dir = 0.0
            self.touch_speed = 0.0
            self.touch_strafe = 0.0
            self.touch_dir = 0.0
            
            self.is_aiming = False
            self.gp_aiming = False
            self.gp_firing = False
            self.mouse_firing = False
            self.gp_running = False
            self.kb_running = False
            
            self.flashlight_on = False 
            self.prev_btn_flashlight = False
            
            # self.raycast_layer = RaycastLayer(self) # Now initialized earlier
            
            pygame.joystick.init()
            self.joysticks = [pygame.joystick.Joystick(x) for x in range(pygame.joystick.get_count())]
            for joy in self.joysticks:
                joy.init()

            self.gun_dmg = 50; self.shotgun_dmg = 35; self.minigun_dmg = 40
            # Damage upgrades removed as per request
            # if self.is_arena_mode:
            #     self.gun_dmg += 50 * (persistent.stein_pistol_level * 0.01)
            #     self.shotgun_dmg += 35 * (persistent.stein_shotgun_level * 0.01)
            #     self.minigun_dmg += 3 * (persistent.stein_minigun_level * 0.10)

            self.weapon_library = {}
            
            def register_weapon(w_obj):
                self.weapon_library[w_obj.name] = w_obj

            ### example of new guns registrations

            # register_weapon(Weapon("gun", SLOT_HANDGUN, damage=self.gun_dmg, projectile_type='bullet', cooldown=0.38, flash_offset=(0, -170), flash_ads_offset=(0, -360), flash_size=1.0, ads_idle="pics/weapons/gun_ads1.webp",
            #     # Normal configs
            #     normal_frameCount=11,
            #     normal_fps=60,
            #     normal_flash_frame=2,
            
            #     # ADS transition
            #     ads_enter_frameCount=14,
            #     ads_enter_fps=60,
            #     ads_enter_name="gun_raise",
        
            #     # ADS shooting animation
            #     ads_fire_frameCount=9,
            #     ads_fire_fps=60,
            #     ads_fire_flash_frame=1,
            # ))

            register_weapon(Weapon("gun", SLOT_HANDGUN, damage=self.gun_dmg, projectile_type='bullet', cooldown=0.38, flash_offset=(0, -170), flash_ads_offset=(0, -360), flash_size=1.0, ads_idle="pics/weapons/gun_ads1.webp",
                # Normal configs
                normal_frameCount=11,
                normal_fps=60,
                normal_flash_frame=2,
            
                # ADS transition
                ads_enter_frameCount=14,
                ads_enter_fps=60,
                ads_enter_name="gun_raise",
        
                # ADS shooting animation
                ads_fire_frameCount=9,
                ads_fire_fps=60,
                ads_fire_flash_frame=1,
            ))

            register_weapon(Weapon("shotgun", SLOT_LONG, damage=self.shotgun_dmg, projectile_type='shotgun', cooldown=1.4, flash_offset=(75, -260), flash_ads_offset=(0, -340), flash_size=1.0, ads_idle="pics/weapons/shotgun_ads1.webp",
                # Normal configs
                normal_frameCount=39,
                normal_fps=60,
                normal_flash_frame=1,
            
                # ADS transition (normal-ads)
                ads_enter_frameCount=5,
                ads_enter_fps=60,
                ads_enter_name="shotgun_raised",
        
                # ADS shooting animation
                ads_fire_frameCount=45,
                ads_fire_fps=60,
                ads_fire_flash_frame=1,

                # Run enter (normal-running)
                run_enter_frameCount=5,
                run_enter_fps=60,
                run_enter_name="shotgun_run",
            ))

            register_weapon(Weapon("fist", SLOT_MELEE, 5, 1, damage=25, cooldown=0.5))

            # register_weapon(Weapon("gun", SLOT_HANDGUN, 5, 1, damage=self.gun_dmg, projectile_type='bullet', cooldown=0.6, 
            #     ads_idle="pics/weapons/beta_gun_s.png", ads_fire="pics/weapons/beta_gun_s_f.png", 
            #     flash_offset=(0, -170), flash_ads_offset=(0, -360), flash_size=1.0))

            # register_weapon(Weapon("shotgun", SLOT_LONG, 5, 1, damage=self.shotgun_dmg, projectile_type='shotgun', cooldown=1.0, 
            #     flash_offset=(0, -170), flash_ads_offset=(0, -170), flash_size=1.5, flash_color=(1.0, 0.6, 0.2)))
            
            register_weapon(Weapon("minigun", SLOT_SPECIAL, 5, 1, damage=self.minigun_dmg, projectile_type='bullet', cooldown=0.05, 
                loop_frames=[2, 3], flash_offset=(0, -180), flash_ads_offset=(0, -180)))
            
            self.inventory = [None, None, None, None] # [Melee, Handgun, Long, Special]
            
            self.weapons = self.weapon_library

            self.current_slot_index = SLOT_MELEE

            self.equip_weapon("fist")
            self.equip_weapon("gun")
            
            if renpy.store.stein_has_shotgun:
                self.equip_weapon("shotgun")
            
            if renpy.store.stein_has_minigun:
                self.equip_weapon("minigun")

            self.current_slot_index = SLOT_HANDGUN
            self.update_current_weapon_ref()
            
            self.bullet_texture_index = 6
            self.sight_d = Image("pics/items/sight.webp")
            with renpy.open_file("pics/gui/damage_x.webp") as f:
                self.hit_marker_img = pygame.image.load(f).convert_alpha()
            with renpy.open_file("pics/gui/arrow_d.webp") as f:
                arrow_surf = pygame.image.load(f).convert_alpha()
            self.arrow_img = pygame.transform.scale(arrow_surf, (30, 30))

            self.max_entities = 1024
            
            self.max_enemies = 1024
            self.enemy_array = (EnemyData * self.max_enemies)()
            self.enemy_ptr = ctypes.addressof(self.enemy_array)
            ctypes.memset(self.enemy_ptr, 0, ctypes.sizeof(self.enemy_array))

            self.player_data = PlayerData()
            self.player_ptr = ctypes.addressof(self.player_data)

            self.sort_buffer = (ctypes.c_int * self.max_entities)()
            
            self.shader_sprite_buffer = (ctypes.c_float * 256)()
            
            self.entities_buffer = (ctypes.c_double * (self.max_entities * 4))()
            self.entities_ptr = ctypes.addressof(self.entities_buffer)
            
            self.shader_sprite_ptr = ctypes.addressof(self.shader_sprite_buffer)

            self.sort_ptr = ctypes.addressof(self.sort_buffer)

            self.MAX_PROJECTILES = 256
            self.proj_array = (ProjectileData * self.MAX_PROJECTILES)()
            self.proj_ptr = ctypes.addressof(self.proj_array)

            self.enemy_data_buffer = (ctypes.c_double * (50 * 4))() 
            self.enemy_data_ptr = ctypes.addressof(self.enemy_data_buffer)
            
            self.static_data_buffer = (ctypes.c_double * (50 * 4))()
            self.static_data_ptr = ctypes.addressof(self.static_data_buffer)
            
            for i in range(self.MAX_PROJECTILES):
                self.proj_array[i].active = 0
                self.proj_array[i].hit_target = -1

            self.projectiles = []
            self.enemies = []
            self.voxel_entities = []
            self.sprite_positions = renpy.store.stein_sprites
            
            self.inter_round_timer = getattr(renpy.store, 'stein_inter_round_timer', 0.0)
            self.current_round = getattr(renpy.store, 'stein_current_round', 0)
            self.sniper_count = getattr(renpy.store, 'stein_sniper_count', 0)
            self.yuritler_count = getattr(renpy.store, 'stein_yuritler_count', 0)
            self.spawn_points = getattr(renpy.store, 'arena_spawn_points', [])
            
            if hasattr(renpy.store, 'stein_enemies'):
                for e_data in renpy.store.stein_enemies:
                    x, y = e_data[0], e_data[1]
                    tex = e_data[2] if len(e_data) > 2 else 0
                    dead_tex = e_data[3] if len(e_data) > 3 else 0
                    health = e_data[4] if len(e_data) > 4 else 100
                    type_id = e_data[5] if len(e_data) > 5 else 0
                    
                    if type_id == ENEMY_TYPE_VOXEL_BASIC:
                        # Voxel Entity
                        filename = tex 
                        new_ve = VoxelEntity(self, x, y, 0.0, filename, health=health)
                        self.voxel_entities.append(new_ve)
                    
                    elif type_id == ENEMY_TYPE_VOXEL_SNIPER:
                        # Voxel Sniper
                        filename = tex
                        new_ve = VoxelSniper(self, x, y, 0.0, filename, health=health)
                        self.voxel_entities.append(new_ve)

                    elif type_id == ENEMY_TYPE_VOXEL_ELITE:
                        filename = tex
                        new_ve = VoxelElite(self, x, y, 0.0, filename, health=health)
                        self.voxel_entities.append(new_ve)

                    elif type_id == ENEMY_TYPE_VOXEL_YURITLER:
                        filename = tex
                        new_ve = VoxelYuritler(self, x, y, 0.0, filename, health=health)
                        self.voxel_entities.append(new_ve)
                    
                    # elif type_id == ENEMY_TYPE_YURITLER: 
                    #     self.enemies.append(Yuritler(self, x, y, health=health))
                    # elif type_id == ENEMY_TYPE_ELITE: 
                    #     self.enemies.append(EliteGuard(self, x, y, health=health))
                    # elif type_id == ENEMY_TYPE_SNIPER: 
                    #     self.enemies.append(Sniper(self, x, y, health=health))
                    # else: 
                    #     self.enemies.append(Guard(self, x, y, tex, dead_tex, health=health))

            if self.is_arena_mode and self.current_round == 0:
                self.start_next_round()

        def spawn_projectile(self, x, y, z, dx, dy, dz, speed, tex_id, damage, is_player, pitch=0.0):
            for i in range(self.MAX_PROJECTILES):
                if self.proj_array[i].active == 0:
                    p = self.proj_array[i]
                    p.x = x; p.y = y; p.z = z
                    p.dir_x = dx; p.dir_y = dy; p.dir_z = dz
                    p.speed = speed
                    p.texture_idx = tex_id
                    p.damage = damage
                    p.from_player = 1 if is_player else 0
                    p.pitch = pitch
                    p.active = 1
                    p.hit_target = -1
                    return

        def equip_weapon(self, weapon_name):
            if weapon_name in self.weapon_library:
                w_obj = self.weapon_library[weapon_name]
                self.inventory[w_obj.category] = w_obj
                if self.inventory[self.current_slot_index] == w_obj:
                    self.update_current_weapon_ref()

        def update_current_weapon_ref(self):
            weapon = self.inventory[self.current_slot_index]
            if weapon:
                self.player.current_weapon_name = weapon.name
            else:
                self.current_slot_index = SLOT_MELEE
                self.player.current_weapon_name = self.inventory[SLOT_MELEE].name

        def switch_to_slot(self, slot_idx):
            if 0 <= slot_idx < 4:
                if self.inventory[slot_idx] is not None:
                    self.current_slot_index = slot_idx
                    self.update_current_weapon_ref()

        def cycle_weapon(self):
            start_idx = self.current_slot_index
            for i in range(1, 4):
                next_idx = (start_idx + i) % 4
                if self.inventory[next_idx] is not None:
                    self.switch_to_slot(next_idx)
                    return

        def start_next_round(self):
            self.current_round += 1
            
            # Clean up bodies
            self.sprite_positions = [s for s in self.sprite_positions if s[2] not in (5, 10)]
            
            self.enemies = [e for e in self.enemies if e.health > 0]
            self.voxel_entities = [ve for ve in self.voxel_entities if ve.health > 0]
            
            if not self.spawn_points:
                self.spawn_points = [(1.5, 1.5), (self.mapWidth-1.5, 1.5), (self.mapWidth/2.0, self.mapHeight/2.0)]

            # Spawn Standard Guards
            for _ in range(self.current_round):
                if not self.spawn_points: break
                sx, sy = renpy.random.choice(self.spawn_points)
                x = sx + 0.5 + (renpy.random.random() - 0.5) * 0.6
                y = sy + 0.5 + (renpy.random.random() - 0.5) * 0.6
                
                new_enemy = VoxelEntity(self, x, y, 0.0, MODEL_VOXEL_BASIC, health=100)
                new_enemy.state = 'chasing'
                new_enemy.move_speed += (renpy.random.random() - 0.5) * 0.2
                self.voxel_entities.append(new_enemy)

            # Spawn Yuritler
            spawn_yuritler = False
            if self.current_round % 10 == 0:
                spawn_yuritler = True
            elif self.current_round % 2 == 0:
                if renpy.random.random() < 0.15:
                    spawn_yuritler = True
            
            if spawn_yuritler:
                if self.spawn_points:
                    self.yuritler_count += 1
                    sx, sy = renpy.random.choice(self.spawn_points)
                    x = sx + 0.5 + (renpy.random.random() - 0.5) * 0.6
                    y = sy + 0.5 + (renpy.random.random() - 0.5) * 0.6
                    
                    boss_hp = 150 + ((self.yuritler_count - 1) * 50)
                    boss = VoxelYuritler(self, x, y, 0.0, MODEL_VOXEL_YURITLER, health=boss_hp)
                    boss.state = 'chasing'
                    self.voxel_entities.append(boss)

            # pawn Elite Guards (Every 5 Rounds)
            if self.current_round % 5 == 0:
                num_elites = self.current_round // 5
                for _ in range(num_elites):
                    if not self.spawn_points: break
                    sx, sy = renpy.random.choice(self.spawn_points)
                    x = sx + 0.5 + (renpy.random.random() - 0.5) * 0.6
                    y = sy + 0.5 + (renpy.random.random() - 0.5) * 0.6
                    
                    elite = VoxelElite(self, x, y, 0.0, MODEL_VOXEL_ELITE, health=100)
                    elite.state = 'chasing'
                    elite.move_speed += (renpy.random.random() - 0.5) * 0.2
                    self.voxel_entities.append(elite)

            # Spawn Snipers (Odd Rounds, 50% chance)
            if self.current_round % 2 != 0:
                if renpy.random.random() < 0.50:
                    self.sniper_count += 1
                    for _ in range(self.sniper_count):
                        if not self.spawn_points: break
                        sx, sy = renpy.random.choice(self.spawn_points)
                        x = sx + 0.5 + (renpy.random.random() - 0.5) * 0.6
                        y = sy + 0.5 + (renpy.random.random() - 0.5) * 0.6
                        
                        sniper = VoxelSniper(self, x, y, 0.0, MODEL_VOXEL_SNIPER, health=100)
                        sniper.state = 'chasing'
                        self.voxel_entities.append(sniper)
            
            self.inter_round_timer = 0.0

        def create_wall_atlas(self):
            image_paths = [  
                "pics/walls/eagle.webp", "pics/walls/redbrick.webp",
                "pics/walls/purplestone.webp", "pics/walls/greystone.webp",
                "pics/walls/bluestone.webp", "pics/walls/mossy.webp",
                "pics/walls/wood.webp", "pics/walls/colorstone.webp",
                "pics/walls/cement.webp",
                "pics/walls/black.webp", # 10
                "pics/walls/gray.webp", # 11
                "pics/walls/red.webp", # 12
                "pics/walls/orange.webp", # 13
                "pics/walls/yellow.webp", # 14
                "pics/walls/light_green.webp", # 15
                "pics/walls/green.webp", # 16
                "pics/walls/green_blue.webp", # 17
                "pics/walls/light_blue.webp", # 18
                "pics/walls/blue.webp", # 19
                "pics/walls/purple.webp", # 20
                "pics/walls/light_purple.webp", # 21
                "pics/walls/pink.webp", # 22
            ]
            
            surfaces = []
            for path in image_paths:
                with renpy.open_file(path) as f:
                    surf = pygame.image.load(f).convert_alpha()
                    surf = pygame.transform.scale(surf, (64, 64))
                    surfaces.append(surf)
            
            if not surfaces:
                # fallback por si acaso
                fallback = pygame.Surface((64, 64)); fallback.fill((255,0,255))
                return renpy.display.draw.load_texture(fallback), 1.0

            num_tex = len(surfaces)
            w, h = surfaces[0].get_size()
            atlas_w = w * num_tex
            atlas_h = h
            
            # Atlas surface (RGBA 32bit)
            atlas = pygame.Surface((atlas_w, atlas_h), flags=pygame.SRCALPHA, depth=32)
            
            # DEBUG
            atlas.fill((255, 255, 255, 255))
            
            for i, surf in enumerate(surfaces):
                atlas.blit(surf, (i * w, 0))
            
            print(f"RenPyStein GPU: Wall Atlas Created. Size: {atlas_w}x{atlas_h}. Textures: {num_tex}")
            return renpy.display.draw.load_texture(atlas), float(num_tex)

        def load_floor_texture(self):
            try:
                with renpy.open_file("pics/walls/cement.webp") as f:
                    surf = pygame.image.load(f).convert_alpha()
                    surf = pygame.transform.scale(surf, (64, 64))
                    return renpy.display.draw.load_texture(surf)
            except:
                fallback = pygame.Surface((64, 64))
                fallback.fill((100, 100, 100))
                return renpy.display.draw.load_texture(fallback)

        def create_sprite_atlas(self):
            sprite_paths = [  
                "pics/items/barrel.webp", "pics/items/pillar.webp",
                "pics/items/greenlight.webp", "pics/items/pillar_destroyed.webp",
                "pics/enemies/guard.webp",
                "pics/enemies/guard_d.webp",
                "pics/items/bullet.webp",
                "pics/items/medkit.webp",
                "pics/items/cookie.webp",
                "pics/enemies/yuritler.webp",
                "pics/enemies/yuritler_d.webp",
                "pics/items/coins.webp",
                "pics/items/coins.webp", 
                "pics/items/random_gun_i.webp",
                "pics/items/bullet_red.webp",
                "pics/items/minigun.webp",
            ]
            
            surfaces = []
            for path in sprite_paths:
                with renpy.open_file(path) as f:
                    surf = pygame.image.load(f).convert_alpha()
                    surf = pygame.transform.scale(surf, (64, 128))
                    surfaces.append(surf)
            
            if not surfaces:
                fallback = pygame.Surface((64, 128)); fallback.fill((0,255,0))
                return renpy.display.draw.load_texture(fallback), 1.0

            num_tex = len(surfaces)
            w, h = surfaces[0].get_size()
            atlas_w = w * num_tex
            atlas_h = h
            
            atlas = pygame.Surface((atlas_w, atlas_h), flags=pygame.SRCALPHA, depth=32)
            atlas.fill((0,0,0,0))
            
            for i, surf in enumerate(surfaces):
                atlas.blit(surf, (i * w, 0))
            
            print(f"RenPyStein GPU: Sprite Atlas Created. Size: {atlas_w}x{atlas_h}. Textures: {num_tex}")
            return renpy.display.draw.load_texture(atlas), float(num_tex)

        def create_model_atlas(self, objects_def):
            self.loaded_models = {}
            if not objects_def and not getattr(self, 'voxel_groups', None):
                s = pygame.Surface((1,1), flags=pygame.SRCALPHA, depth=32)
                return renpy.display.draw.load_texture(s), 0.0

            unique_files = sorted(list(set([o[3] for o in objects_def])))
            all_chunks = []
            
            # Load Standard Files
            for filename in unique_files:
                try:
                    data = renpy.store.load_object_json(filename)
                except:
                    data = None

                if data:
                    model_chunks = {} 
                    layers = {}
                    try:
                        iterator = data.items() if hasattr(data, 'items') else []
                        for k, v in iterator:
                            layers[int(k)] = v
                    except: pass

                    for lz, grid in layers.items():
                        for lx, row in enumerate(grid):
                            for ly, tile in enumerate(row):
                                if tile > 0:
                                    cx, cy, cz = lx // 16, ly // 16, lz // 16
                                    chunk_key = (cx, cy, cz)
                                    if chunk_key not in model_chunks:
                                        model_chunks[chunk_key] = {z: [[0 for _ in range(16)] for _ in range(16)] for z in range(16)}
                                    model_chunks[chunk_key][lz%16][lx%16][ly%16] = tile
                    
                    self.loaded_models[filename] = []
                    for (cx, cy, cz), chunk_grid in model_chunks.items():
                        atlas_id = len(all_chunks)
                        all_chunks.append(chunk_grid)
                        # Use float coordinates (1 chunk = 1.0 unit)
                        self.loaded_models[filename].append((float(cx), float(cy), float(cz), atlas_id))

            # Load Rig Groups as Virtual Models (Editor & In-Game)
            rigs_to_process = getattr(self, 'pending_rigs', {})
            
            # If in editor mode, we also include current session groups
            if self.editor_mode and getattr(self, 'voxel_groups', None):
                id_lookup = {}
                if hasattr(self, 'master_voxels'):
                    for v in self.master_voxels: id_lookup[(int(v[0]), int(v[1]), int(v[2]))] = int(v[3])
                
                for gname, gdata in self.voxel_groups.items():
                    rigs_to_process[gname] = {'voxels': gdata.get('voxels', []), 'id_lookup': id_lookup}

            for gname, rdata in rigs_to_process.items():
                model_chunks = {}
                id_lookup = rdata.get('id_lookup', {})
                for pos in rdata.get('voxels', []):
                    vx, vy, vz = int(pos[0]), int(pos[1]), int(pos[2])
                    tid = id_lookup.get((vx, vy, vz), 1)
                    
                    cx, cy, cz = vx // 16, vy // 16, vz // 16
                    chunk_key = (cx, cy, cz)
                    if chunk_key not in model_chunks:
                        model_chunks[chunk_key] = {z: [[0 for _ in range(16)] for _ in range(16)] for z in range(16)}
                    model_chunks[chunk_key][vz % 16][vx % 16][vy % 16] = tid
                
                self.loaded_models[gname] = []
                for (cx, cy, cz), chunk_grid in model_chunks.items():
                    atlas_id = len(all_chunks)
                    all_chunks.append(chunk_grid)
                    # Use float coordinates (1 chunk = 1.0 unit)
                    self.loaded_models[gname].append((float(cx), float(cy), float(cz), atlas_id))
            # Setup Atlas Surface
            num_total_chunks = len(all_chunks)
            if num_total_chunks == 0:
                s = pygame.Surface((1,1), flags=pygame.SRCALPHA, depth=32)
                return renpy.display.draw.load_texture(s), 0.0

            tex_width = 256
            tex_height = num_total_chunks * 16
            
            surf = pygame.Surface((tex_width, tex_height), flags=pygame.SRCALPHA, depth=32)
            
            # Fill Atlas
            for i, chunk_layers in enumerate(all_chunks):
                base_y_atlas = i * 16
                for z, rows in chunk_layers.items():
                    if z < 0 or z > 15: continue
                    base_x_atlas = z * 16
                    for x in range(16):
                        for y in range(16):
                            tile = rows[x][y]
                            if tile > 0:
                                surf.set_at((base_x_atlas + x, base_y_atlas + y), (255, tile, 0, 255))

            return renpy.display.draw.load_texture(surf), float(num_total_chunks)

        def create_map_texture(self):
            def next_power_of_two(n):
                if n == 0: return 1
                return 2**math.ceil(math.log(n, 2))
            
            if isinstance(self.worldMap, list):
                layers = {0: self.worldMap}
            else:
                layers = {}
                for k, v in self.worldMap.items():
                    try:
                        layers[int(k)] = v
                    except:
                        pass
            
            # Determine dimensions
            min_z = 0 if not layers else min(layers.keys())
            max_z = 0 if not layers else max(layers.keys())
            max_x = 0; max_y = 0
            for grid in layers.values():
                if len(grid) > max_x: max_x = len(grid)
                if len(grid) > 0 and len(grid[0]) > max_y: max_y = len(grid[0])
            
            self.map_w = max_x; self.map_h = max_y; self.min_layer = min_z; self.max_layer = max_z; self.num_layers = max_z - min_z + 1
            
            # Sync physics dimensions
            self.mapWidth = self.map_w
            self.mapHeight = self.map_h
            
            # Grid Packing Logic
            # Find a POT size for a single layer
            layer_w_pot = max(64, next_power_of_two(max_x))
            layer_h_pot = max(64, next_power_of_two(max_y))
            
            # Target Atlas Size (Square is best for GPU)
            # Try to fit all layers into 4096 (Safe Limit) or 8192
            # Total Area needed = layer_area * num_layers
            total_area = layer_w_pot * layer_h_pot * self.num_layers
            target_dim = next_power_of_two(int(math.sqrt(total_area)))
            target_dim = max(target_dim, layer_w_pot, layer_h_pot)
            
            # Clamp to safe max (e.g. 4096) if possible, else go higher and pray
            MAX_TEX_SIZE = 4096
            if target_dim < MAX_TEX_SIZE and (target_dim * target_dim) < total_area:
                target_dim *= 2 # Grow if needed
            
            atlas_w = target_dim
            atlas_h = target_dim
            
            # Calculate Columns and Rows
            cols = atlas_w // layer_w_pot
            rows = atlas_h // layer_h_pot
            
            # If it doesn't fit, grow height
            while (cols * rows) < self.num_layers:
                atlas_h *= 2
                rows = atlas_h // layer_h_pot
                if atlas_h > 16384: # Hard limit
                    print("CRITICAL WARNING: Map is too massive for GPU texture limits!")
                    break

            surf = pygame.Surface((atlas_w, atlas_h), flags=pygame.SRCALPHA, depth=32)
            surf.fill((0,0,0,255))
            
            # Identify ALL voxels that belong to any group
            grouped_lookup = set()
            for gdata in self.voxel_groups.values():
                for v in gdata.get('voxels', []):
                    grouped_lookup.add((int(v[0]), int(v[1]), int(v[2])))

            for z, grid in layers.items():
                layer_idx = z - min_z
                
                # Grid Coords
                col = layer_idx % cols
                row = layer_idx // cols
                
                base_x = col * layer_w_pot
                base_y = row * layer_h_pot
                
                for map_x, grid_row in enumerate(grid):
                    for map_y, tile in enumerate(grid_row):
                        if tile > 0:
                            if (int(map_x), int(map_y), int(z)) in grouped_lookup:
                                continue
                            surf.set_at((base_x + map_x, base_y + map_y), (255, tile, 0, 255))
            
            self.flat_map_buffer = flatten_world_map(
                self.worldMap, self.map_w, self.map_h, 
                self.min_layer, self.max_layer
            )
            
            # Calculate uniforms
            # u_map_grid_layout: (cols, layer_w_norm, layer_h_norm)
            self.map_layer_norm_size = (float(layer_w_pot) / float(atlas_w), float(layer_h_pot) / float(atlas_h))
            self.map_grid_cols = float(cols)
            self.map_tex_pixel_size = (1.0 / float(atlas_w), 1.0 / float(atlas_h))
            self.map_uv_scale = (float(max_x) / float(layer_w_pot), float(max_y) / float(layer_h_pot)) # Scale UV within the layer cell
            
            return renpy.display.draw.load_texture(surf)

        def update_selection_texture(self):
            """Updates the selection texture based on selection_map and bones."""
            def next_power_of_two(n):
                if n == 0: return 1
                return 2**math.ceil(math.log(n, 2))
            
            # Use same dimensions as map texture to ensure alignment
            layer_w_pot = max(64, next_power_of_two(self.map_w))
            layer_h_pot = max(64, next_power_of_two(self.map_h))
            
            # Recalculate Atlas Size
            total_area = layer_w_pot * layer_h_pot * self.num_layers
            target_dim = next_power_of_two(int(math.sqrt(total_area)))
            target_dim = max(target_dim, layer_w_pot, layer_h_pot)
            MAX_TEX_SIZE = 4096
            if target_dim < MAX_TEX_SIZE and (target_dim * target_dim) < total_area:
                target_dim *= 2
            
            atlas_w = target_dim
            atlas_h = target_dim
            
            cols = atlas_w // layer_w_pot
            rows = atlas_h // layer_h_pot
            while (cols * rows) < self.num_layers:
                atlas_h *= 2
                rows = atlas_h // layer_h_pot
                if atlas_h > 16384: break

            surf = pygame.Surface((atlas_w, atlas_h), flags=pygame.SRCALPHA, depth=32)
            surf.fill((0,0,0,0))
            
            # Helper to get pixel coords
            def get_pixel_coords(mx, my, mz):
                l_idx = int(mz) - self.min_layer
                if l_idx < 0 or l_idx >= self.num_layers: return None
                
                col = l_idx % cols
                row = l_idx // cols
                
                bx = col * layer_w_pot
                by = row * layer_h_pot
                
                px = bx + mx
                py = by + my
                if 0 <= px < atlas_w and 0 <= py < atlas_h:
                    return (px, py)
                return None

            # Draw Selection (Red Channel)
            for pos in self.selection_map.keys():
                mx, my, mz = pos
                coords = get_pixel_coords(mx, my, mz)
                if coords:
                    surf.set_at(coords, (255, 0, 0, 255))
            
            # Draw Bones (Green Channel)
            if self.show_bones:
                for gname, data in self.voxel_groups.items():
                    pname = data.get("parent")
                    if pname and pname in self.voxel_groups:
                        p1 = data.get("pivot") # [x, y, z]
                        p2 = self.voxel_groups[pname].get("pivot")
                        
                        if p1 and p2 and p1[0] >= 0 and p2[0] >= 0:
                            # Distance-based interpolation for line points
                            dist = math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2 + (p1[2]-p2[2])**2)
                            steps = int(dist * 2.0)
                            for s in range(steps + 1):
                                t = float(s) / max(1, steps)
                                lx, ly, lz = p1[0] + (p2[0]-p1[0])*t, p1[1] + (p2[1]-p1[1])*t, p1[2] + (p2[2]-p1[2])*t
                                
                                coords = get_pixel_coords(int(lx), int(ly), int(lz))
                                if coords:
                                    c = surf.get_at(coords)
                                    surf.set_at(coords, (c[0], 255, 0, 255))

            self.selection_texture = renpy.display.draw.load_texture(surf)

        def assign_to_group(self, name):
            """Assigns currently selected voxels to a group, removing them from any other group."""
            if not name: return
            
            selected_coords = [list(pos) for pos in self.selection_map.keys()]
            
            # Update the group data
            old_parent = self.voxel_groups.get(name, {}).get("parent")
            self.voxel_groups[name] = {
                "voxels": selected_coords,
                "pivot": list(self.current_pivot),
                "parent": old_parent
            }
            
            # Clean overlaps and refresh textures
            self.clean_and_bake_rig()
            renpy.notify(f"Assigned {len(selected_coords)} voxels to '{name}'")

        def clean_and_bake_rig(self):
            """Ensures each voxel belongs to only one group and refreshes all textures."""
            if not self.editor_mode: return
            
            used_voxels = set()
            # Process groups in reverse order (newest/child-most groups first usually)
            for gname in sorted(self.voxel_groups.keys(), reverse=True):
                gdata = self.voxel_groups[gname]
                new_voxels = []
                for v in gdata.get("voxels", []):
                    pos = (int(v[0]), int(v[1]), int(v[2]))
                    if pos not in used_voxels:
                        new_voxels.append(list(pos))
                        used_voxels.add(pos)
                gdata["voxels"] = new_voxels

            # Re-generate everything to ensure visual consistency
            self.model_atlas, self.num_models = self.create_model_atlas(self.objects_def)
            self.map_texture = self.create_map_texture()
            self.selection_texture = None
            renpy.restart_interaction()

        def set_group_parent(self, name, parent_name):
            """Sets the parent for a group."""
            if name not in self.voxel_groups: return
            if parent_name == "None": parent_name = None
            if name == parent_name: return # Prevent self-parenting
            
            self.voxel_groups[name]["parent"] = parent_name
            renpy.notify(f"Set parent of '{name}' to '{parent_name}'")
            renpy.restart_interaction()

        def select_group(self, name):
            """Selects all voxels and pivot belonging to a group."""
            if name not in self.voxel_groups: return
            group = self.voxel_groups[name]
            self.selected_group = name
            
            self.selection_map.clear()
            # Handle legacy list storage vs new dict storage
            voxels = group if isinstance(group, list) else group.get("voxels", [])
            pivot = (-1.0, -1.0, -1.0) if isinstance(group, list) else group.get("pivot", (-1.0, -1.0, -1.0))
            
            for pos in voxels:
                self.selection_map[tuple(pos)] = True
            
            self.current_pivot = tuple(pivot)
            self.selection_texture = None # Force update
            renpy.restart_interaction()

        def select_all_voxels(self):
            """Selects ALL voxels in the current model."""
            if not self.master_voxels: return
            
            self.selection_map.clear()
            for v in self.master_voxels:
                # v is (x, y, z, id)
                self.selection_map[(int(v[0]), int(v[1]), int(v[2]))] = True
            
            self.selection_texture = None
            renpy.notify(f"Selected all {len(self.master_voxels)} voxels")
            renpy.restart_interaction()

        def set_group_pivot(self, name):
            """Sets current highlight_pos as pivot for the specified group."""
            if name not in self.voxel_groups: return
            if self.highlight_pos[0] < 0:
                renpy.notify("Select a voxel first to set as pivot")
                return
            
            self.voxel_groups[name]["pivot"] = list(self.highlight_pos)
            self.current_pivot = tuple(self.highlight_pos)
            renpy.notify(f"Pivot set for '{name}'")
            renpy.restart_interaction()

        def delete_group(self, name):
            """Deletes a voxel group."""
            if name in self.voxel_groups:
                del self.voxel_groups[name]
                renpy.restart_interaction()

        def get_group_accumulated_transform(self, gname):
            """Recursively calculates the world transform for a group based on its parents."""
            if gname not in self.voxel_groups:
                return {'x': 0.0, 'y': 0.0, 'z': 0.0, 'rx': 0.0, 'ry': 0.0, 'rz': 0.0, 'sx': 1.0, 'sy': 1.0, 'sz': 1.0}
            
            gdata = self.voxel_groups[gname]
            local_t = self.editor_target.get_group_data(gname)
            
            pname = gdata.get("parent")
            if pname and pname in self.voxel_groups:
                pt = self.get_group_accumulated_transform(pname)
                # Position is simple additive for now (Translation)
                # Scale is multiplicative
                return {
                    'x': pt['x'] + local_t.get('x', 0.0),
                    'y': pt['y'] + local_t.get('y', 0.0),
                    'z': pt['z'] + local_t.get('z', 0.0),
                    'rx': pt.get('rx', 0.0) + local_t.get('rx', 0.0),
                    'ry': pt.get('ry', 0.0) + local_t.get('ry', 0.0),
                    'rz': pt.get('rz', 0.0) + local_t.get('rz', 0.0),
                    'sx': pt.get('sx', 1.0) * local_t.get('sx', 1.0),
                    'sy': pt.get('sy', 1.0) * local_t.get('sy', 1.0),
                    'sz': pt.get('sz', 1.0) * local_t.get('sz', 1.0)
                }
            
            return {
                'x': local_t.get('x', 0.0),
                'y': local_t.get('y', 0.0),
                'z': local_t.get('z', 0.0),
                'rx': local_t.get('rx', 0.0),
                'ry': local_t.get('ry', 0.0),
                'rz': local_t.get('rz', 0.0),
                'sx': local_t.get('sx', 1.0),
                'sy': local_t.get('sy', 1.0),
                'sz': local_t.get('sz', 1.0)
            }

        def refresh_rig_visuals(self):
            """Prepares the rig for shader-based rendering.
                Vertex Groups are converted into dynamic shader objects for smooth movement."""
            if not self.editor_mode: return
            
            # Signature check to only rebuild if groups change
            sig = sum([len(g.get('voxels', [])) for g in self.voxel_groups.values()]) + len(self.voxel_groups)
            if getattr(self, '_last_rig_sig', -1) != sig:
                # Re-bake static map (excludes grouped voxels)
                self.map_texture = self.create_map_texture()
                
                # Create Dynamic Chunks for each group
                rig_objects_def = []
                for gname, gdata in self.voxel_groups.items():
                    # Create a virtual filename for the chunk
                    vname = f"chunk_{gname}"
                    
                    # Group voxels into a dict structure for the loader
                    layers = {}
                    for vx, vy, vz in gdata.get('voxels', []):
                        if vz not in layers:
                            # 16x16 is the standard chunk size
                            layers[vz] = [[0 for _ in range(16)] for _ in range(16)]
                        # Voxel local coords (mod 16 since chunks are 16x16)
                        # For simplicity in editor, we use absolute coords and let create_model_atlas chunk it
                        pass 
                    
                self._last_rig_sig = sig

        def render(self, width, height, st, at):
            if self.oldst is None: self.oldst = st
            dtime = st - self.oldst
            self.oldst = st

            # When groups change, we must update both the Static Map (to hide voxels) 
            # and the Model Atlas (to include the new bone chunks).
            if self.editor_mode:
                # sum of voxels across all groups + group count
                sig = sum([len(g.get('voxels', [])) for g in self.voxel_groups.values()]) + len(self.voxel_groups)
                if getattr(self, '_last_rig_sig', -1) != sig:
                    # Update Atlas first so groups are available as models
                    self.model_atlas, self.num_models = self.create_model_atlas(self.objects_def)
                    # Then update Map to exclude those voxels
                    self.map_texture = self.create_map_texture()
                    self._last_rig_sig = sig
            # -------------------------

            if dtime > 0.0:
                inst_fps = 1.0 / dtime
                
                current_fps = getattr(renpy.store, 'stein_current_fps', 60)
                new_fps = (current_fps * 0.9) + (inst_fps * 0.1)
                renpy.store.stein_current_fps = int(new_fps)

            if simulate_touch: self.update_player_from_touch_state()
            else: self.touch_speed = 0.0; self.touch_strafe = 0.0; self.touch_dir = 0.0
            self.poll_gamepad()

            total_speed = self.kb_speed + self.gp_speed + self.touch_speed
            total_strafe = self.kb_strafe + self.gp_strafe + self.touch_strafe
            total_dir = self.kb_dir + self.gp_dir + self.touch_dir
            
            effective_aiming = self.is_aiming or self.gp_aiming
            is_running = self.kb_running or self.gp_running
            if effective_aiming: is_running = False
            
            if is_running: self.player.moveSpeed = 4.0 
            elif effective_aiming: self.player.moveSpeed = 1.5 
            else: self.player.moveSpeed = 2.5 

            self.player.speed = max(-1.0, min(1.0, total_speed))
            self.player.strafe_speed = max(-1.0, min(1.0, total_strafe))
            self.player.dir = total_dir 
            self.player.move(dtime)
            
            group_offsets = [(0.0, 0.0, 0.0)] * 16
            group_rots = [0.0] * 16
            group_pivots = [(0.0, 0.0, 0.0)] * 16
            
            if self.editor_mode:
                for gname, gid in getattr(self, 'group_to_id', {}).items():
                    if gid < 16:
                        wt = self.get_group_accumulated_transform(gname)
                        group_offsets[gid] = (wt['x'], wt['y'], wt['z'])
                        group_rots[gid] = math.radians(wt['rz'])
                        
                        gdata = self.voxel_groups.get(gname, {})
                        pivot = gdata.get('pivot', (0.0, 0.0, 0.0))
                        group_pivots[gid] = (float(pivot[0]), float(pivot[1]), float(pivot[2]))
            
            self.shader_group_offsets = group_offsets
            self.shader_group_rots = group_rots
            self.shader_group_pivots = group_pivots

            self.update_logic(dtime)

            renpy.store.player_x = self.player.x
            renpy.store.player_y = self.player.y
            renpy.store.player_dirx = self.player.dirx
            renpy.store.player_diry = self.player.diry
            renpy.store.player_planex = self.player.planex
            renpy.store.player_planey = self.player.planey

            # RENDER
            retro_w = self.internal_width
            retro_h = self.internal_height
            
            scale = float(width) / float(self.internal_width)

            if self.last_rot is None:
                self.last_rot = self.player.rot

            diff_rot = self.player.rot - self.last_rot
            
            if diff_rot > math.pi: 
                diff_rot -= (math.pi * 2)
            elif diff_rot < -math.pi: 
                diff_rot += (math.pi * 2)

            mb_strength = getattr(persistent, "stein_motion_blur_strength", 0.0)
            
            blur_amount = -diff_rot * mb_strength * 10.0 

            self.last_rot = self.player.rot

            # Flatten the raycast layer
            flat_layer = renpy.display.layout.Flatten(self.raycast_layer)
            
            args_blur = { 'child': flat_layer, 'zoom': 1.0 } 
            
            if abs(blur_amount) > 0.005:
                args_blur['shader'] = "stein.motion_blur"
                args_blur['u_blur_amount'] = blur_amount
            
            blur_transform = Transform(**args_blur)

            if abs(blur_amount) > 0.005:
                blur_transform = renpy.display.layout.Flatten(blur_transform)

            use_bloom = getattr(persistent, "stein_enable_bloom", True)
            
            args_bloom = { 'child': blur_transform, 'zoom': scale, 'nearest': True }
            
            if use_bloom:
                args_bloom['shader'] = "stein.bloom"
                args_bloom['u_resolution'] = (float(width), float(height))

            final_transform = Transform(**args_bloom)
            
            main_scene_render = renpy.render(final_transform, width, height, st, at)
            
            r = renpy.Render(width, height)
            r.blit(main_scene_render, (0,0))
            
            # Damage flash + Low Health Tint
            if self.damage_flash_timer > 0:
                self.damage_flash_timer = max(0, self.damage_flash_timer - dtime)

            flash_alpha = 0
            if self.damage_flash_timer > 0:
                flash_alpha = int(140 * (self.damage_flash_timer / 0.2))
            
            health_alpha = 0
            if self.player.health < 70:
                severity = (70.0 - self.player.health) / 70.0
                health_alpha = int(severity * 160)
            
            final_red_alpha = min(255, max(flash_alpha, health_alpha))

            if final_red_alpha > 0:
                flash_d = renpy.display.imagelike.Solid((255, 0, 0, final_red_alpha))
                flash_r = renpy.render(flash_d, width, height, st, at)
                r.blit(flash_r, (0,0))

            if self.heal_flash_timer > 0:
                self.heal_flash_timer = max(0, self.heal_flash_timer - dtime)
                alpha = int(128 * (self.heal_flash_timer / 0.2))
                if alpha > 0:
                    heal_d = renpy.display.imagelike.Solid((0, 255, 0, alpha))
                    heal_r = renpy.render(heal_d, width, height, st, at)
                    r.blit(heal_r, (0,0))

            # Crosshair
            sight_r = renpy.render(self.sight_d, width, height, st, at)
            sw, sh = sight_r.get_size()
            r.blit(sight_r, (width/2 - sw/2, height/2 - sh/2))
            
            if not self.editor_mode:
                # Hit Marker
                if self.hit_marker_timer > 0:
                    hm_w, hm_h = self.hit_marker_img.get_size()
                    hm_tex = renpy.display.draw.load_texture(self.hit_marker_img)
                    r.blit(hm_tex, (width/2 - hm_w/2, height/2 - hm_h/2))

            if self.pickup_msg_timer > 0:
                self.pickup_msg_timer -= dtime 
                
                alpha_val = 255
                if self.pickup_msg_timer < 0.5:
                    alpha_val = int(255 * (self.pickup_msg_timer / 0.5))
                
                if alpha_val > 0:
                    pickup_text = Text(self.pickup_msg, size=40, color="#FFFF00", outlines=[(3, "#000", 0, 0)])
                    pt_render = renpy.render(pickup_text, width, height, st, at)
                    pw, ph = pt_render.get_size()
                    
                    r.blit(pt_render, (width/2 - pw/2, height * 0.20))

            # hp_color = "#FFF"
            # if self.player.health < 30: hp_color = "#F00"
            # elif self.player.health < 60: hp_color = "#FF0"
            
            # hud_text = Text(_("HP: {}%  |  WEAPON: {}").format(int(self.player.health), self.player.current_weapon_name.upper()), size=36, color=hp_color, outlines=[(2, "#000", 0, 0)])
            # hud_r = renpy.render(hud_text, width, height, st, at)
            # r.blit(hud_r, (30, height - 60))



            # Damage indicators
            center_x = width / 2; center_y = height / 2; indicator_radius = 200
            for ind in list(self.damage_indicators):
                ind.duration -= dtime
                if ind.duration <= 0: self.damage_indicators.remove(ind); continue
                diff = self.player.rot - ind.angle
                ix = center_x + indicator_radius * math.sin(diff)
                iy = center_y - indicator_radius * math.cos(diff)
                rot_img = pygame.transform.rotate(self.arrow_img, -math.degrees(diff))
                rot_img.set_alpha(int(255 * (ind.duration / ind.max_duration)))
                ind_tex = renpy.display.draw.load_texture(rot_img)
                iw, ih = ind_tex.get_size()
                r.blit(ind_tex, (ix - iw/2, iy - ih/2))

            # Game over checks
            if self.player.health <= 0:
                self.player.health = 0
                pygame.mouse.set_visible(True); pygame.event.set_grab(False)
                if self.return_value is None:
                    if self.is_arena_mode:
                        renpy.store.last_arena_round = self.current_round
                        renpy.store.new_highscore = False
                        if self.current_round > persistent.sayoristein_arena_highscore:
                            persistent.sayoristein_arena_highscore = self.current_round
                            renpy.store.new_highscore = True
                        self.return_value = 'game_over_arena'
                    else:
                        self.return_value = 'game_over'

            for e in self.exits:
                if math.fabs(e[0] - self.player.x) < 0.5 and math.fabs(e[1] - self.player.y) < 0.5:
                    pygame.mouse.set_visible(True); pygame.event.set_grab(False)
                    if self.return_value is None:
                        self.return_value = e[2]

            # Weapon
            if not self.editor_mode:
                movement_state = {
                    'is_moving': abs(self.player.speed) > 0.1 or abs(self.player.strafe_speed) > 0.1, 
                    'is_running': self.kb_running or self.gp_running
                }
                is_firing = self.mouse_firing or self.gp_firing
                current_weapon_obj = self.weapons[self.player.current_weapon_name]
                current_weapon_obj.render_to(r, width, height, st, at, is_ads=self.is_aiming or self.gp_aiming, is_firing=is_firing, movement_state=movement_state)

            if self.is_arena_mode:
                arena_text = Text(_("ROUND: {}  |  KILLS: {}  |  COINS: {}").format(self.current_round, persistent.stein_kills, renpy.store.stein_session_coins), size=28, color="#FFD700", outlines=[(2, "#000", 0, 0)])
                arena_r = renpy.render(arena_text, width, height, st, at)
                aw, ah = arena_r.get_size()
                r.blit(arena_r, (width - aw - 30, height - 60))
                
                # Next Round Timer
                if self.inter_round_timer > 0 and self.current_round > 0:
                    timer_text = Text(_("NEXT ROUND IN: {:.1f}").format(self.inter_round_timer), size=48, color="#F00", outlines=[(2, "#000", 0, 0)])
                    timer_r = renpy.render(timer_text, width, height, st, at)
                    tw, th = timer_r.get_size()
                    r.blit(timer_r, (width/2 - tw/2, 100))
            
            if self.builder_mode:
                info_str = f"BUILDER MODE ON [[VOXEL: {self.selected_voxel}]]\COORDS: {self.player.x:.2f}, {self.player.y:.2f}, {self.player.z:.2f}"
                b_text = Text(info_str, size=30, color="#00FF00", outlines=[(2, "#000", 0, 0)])
                b_r = renpy.render(b_text, width, height, st, at)
                r.blit(b_r, (20, 20))

            if self.return_value:
                renpy.timeout(0)

            renpy.redraw(self, 0.01) 
            return r

        def update_weather(self, dt):
            if not hasattr(self, 'weather_state'):
                self.weather_state = "none"
                self.weather_timer = 0.0
                self.next_weather_check = 5.0
                self.wetness = 0.0

            if not self.is_arena_mode: return
            
            if not persistent.stein_volumetric_clouds or not getattr(persistent, "stein_enable_weather", True):
                self.weather_state = "none"
                self.wetness = max(0.0, self.wetness - dt * 0.1)
                return

            game_hours_passed = dt * 0.04
            
            if self.weather_state != "none":
                self.weather_timer -= game_hours_passed
                self.wetness = min(1.0, self.wetness + dt * 0.2)
                
                if self.weather_timer <= 0:
                    self.weather_state = "none"
            else:
                self.wetness = max(0.0, self.wetness - dt * 0.05)
            
            self.next_weather_check -= game_hours_passed
            if self.next_weather_check <= 0:
                if config.developer:
                    self.next_weather_check = 1.0
                else:
                    self.next_weather_check = 5.0 
                
                if self.weather_state == "none":
                    prob = 0.10
                    if config.developer: prob = 1.0
                    
                    if renpy.random.random() < prob:
                        if renpy.random.random() < 0.5:
                            self.weather_state = "rain"
                        else:
                            self.weather_state = "snow"
                        
                        self.weather_timer = 6.0

        def update_logic(self, dt):
            self.time_since_last_damage += dt
            if self.time_since_last_damage > 2.5 and self.player.health < 100 and self.player.health > 0:
                # Regenerate 95 HP in 3 seconds, like 31.67 hp/sec
                heal_rate = 31.67
                self.player.health = min(100, self.player.health + heal_rate * dt)

            self.update_weather(dt)
            self.hit_marker_timer = max(0, self.hit_marker_timer - dt)
            self.check_item_pickup()
            
            c_enemies = self.enemy_array
            active_count = 0
            state_map = {'idle': 0, 'chasing': 1, 'attacking': 2, 'dying': 3, 'dead': 4}

            for i, e in enumerate(self.enemies):
                if i >= self.max_enemies: break
                c_enemies[i].x = e.x
                c_enemies[i].y = e.y
                
                # Update Z from floor if not present on python object
                ground_z = self.player.get_ground_height_at(e.x, e.y)
                if not hasattr(e, 'z'):
                    e.z = ground_z
                else:
                    e.z = ground_z

                c_enemies[i].z = e.z

                c_enemies[i].hp = e.health
                c_enemies[i].state = state_map.get(e.state, 0)
                c_enemies[i].texture_idx = e.texture_index
                c_enemies[i].move_speed = e.moveSpeed
                c_enemies[i].enemy_type = 0 
                active_count += 1

            map_addr, _ = self.flat_map_buffer.buffer_info()
            SteinWrapper.stein_lib.update_enemies_c(
                self.enemy_ptr,
                active_count,
                self.player.x, self.player.y, self.player.z,
                dt,
                map_addr,
                self.mapWidth, self.mapHeight, self.num_layers, self.min_layer
            )

            state_map_inv = {0: 'idle', 1: 'chasing', 2: 'attacking', 3: 'dying', 4: 'dead'}
            
            for i in range(active_count):
                e = self.enemies[i]
                c_e = c_enemies[i]
                
                e.x = c_e.x
                e.y = c_e.y
                e.health = c_e.hp
                e.state = state_map_inv.get(c_e.state, 'idle')
                
                if c_e.state == 2 and e.attack_timer <= 0:
                    pass

                if e.state == 'attacking':
                    if e.attack_timer <= 0:
                        e.attack(self.player)

            for e in self.enemies:
                if e.attack_timer > 0:
                    e.attack_timer -= dt
            
            SteinWrapper.update_projectiles_native(
                self.proj_ptr, self.MAX_PROJECTILES, 
                self.enemy_ptr, active_count,
                self.player_ptr,
                dt,
                map_addr, self.mapWidth, self.mapHeight, 
                self.num_layers, self.min_layer
            )
            
            if hasattr(self, 'voxel_entities'):
                for ve in self.voxel_entities:
                    ve.update(dt, self.player)
                
                for i in range(self.MAX_PROJECTILES):
                    p = self.proj_array[i]
                    if p.active == 1 and p.from_player == 1:
                        for ve in self.voxel_entities:
                            if ve.dead: continue
                            if ve.check_collision(p.x, p.y, p.z):
                                p.active = 0 # Destroy projectile
                                
                                self.hit_marker_timer = 0.15
                                renpy.sound.play("sounds/ow.ogg", channel="audio")
                                
                                ve.take_damage(p.damage)
                                break
                
                # Remove dead voxel entities from the active list
                self.voxel_entities = [ve for ve in self.voxel_entities if not ve.dead]

            dead_enemies = set()

            for i in range(self.MAX_PROJECTILES):
                p = self.proj_array[i]
                
                if p.hit_target != -1:
                    if p.hit_target == -2:
                        # Player Hit
                        if not self.builder_mode:
                            self.player.health -= p.damage
                            self.add_damage_indicator(-p.dir_x, -p.dir_y)
                            self.damage_flash_timer = 0.2
                            self.time_since_last_damage = 0.0
                            renpy.sound.play("sounds/ow.ogg", channel="audio")
                    
                    elif p.hit_target >= 0:
                        # Enemy Hit
                        if p.hit_target < len(self.enemies):
                            e = self.enemies[p.hit_target]
                            
                            self.hit_marker_timer = 0.15
                            renpy.sound.play("sounds/ow.ogg", channel="audio")

                            taken = True
                            if hasattr(e, 'take_damage'): 
                                taken = e.take_damage(p.damage)
                            else:
                                e.health -= p.damage
                            
                            if e.health <= 0:
                                dead_enemies.add(e)
                    
                    p.hit_target = -1

            for e in dead_enemies:
                if e in self.enemies:
                    self.enemies.remove(e)
                self.sprite_positions.append((e.x, e.y, e.destroyed_texture_index))

                if self.is_arena_mode:
                    drop_prob = 1.0 if e.coin_index == 12 else 0.35
                    if renpy.random.random() < drop_prob:
                        self.sprite_positions.append((e.x, e.y, e.coin_index))
                    
                    if not renpy.store.stein_has_shotgun:
                        shotgun_prob = 0.25 if e.coin_index == 12 else 0.10
                        if renpy.random.random() < shotgun_prob:
                            self.sprite_positions.append((e.x, e.y, 13))
                            
                    if not renpy.store.stein_has_minigun:
                        if renpy.random.random() < 0.10:
                            self.sprite_positions.append((e.x, e.y, 15))

            if self.mouse_firing or self.gp_firing: self.shoot_weapon()

            if self.is_arena_mode:
                if self.inter_round_timer > 0:
                    self.inter_round_timer -= dt
                    if self.inter_round_timer <= 0:
                        self.start_next_round()
                # Check both sprite enemies and voxel enemies
                elif len(self.enemies) == 0 and len(self.voxel_entities) == 0 and self.current_round > 0:
                    self.inter_round_timer = 10.0

            renpy.store.stein_current_round = self.current_round
            renpy.store.stein_inter_round_timer = self.inter_round_timer
            renpy.store.stein_sniper_count = self.sniper_count
            renpy.store.stein_yuritler_count = self.yuritler_count

        def check_item_pickup(self):
            for sprite in list(self.sprite_positions):
                sprite_x, sprite_y, texture_index = sprite
                dist = math.sqrt((self.player.x - sprite_x)**2 + (self.player.y - sprite_y)**2)
                if dist < 0.8:
                    picked = False
                    if texture_index == 7 and self.player.health < 100:
                        self.player.health = min(100, self.player.health + 25); picked = True
                        self.heal_flash_timer = 0.2
                    elif texture_index in (11, 12):
                        renpy.store.stein_session_coins += 100; picked = True
                    elif texture_index == 13:
                        w_obj = self.weapon_library["shotgun"]
                        has_shotgun = renpy.store.stein_has_shotgun or (self.inventory[w_obj.category] and self.inventory[w_obj.category].name == "shotgun")
                        
                        if not has_shotgun:
                            if self.is_arena_mode:
                                self.equip_weapon("shotgun")
                            else:
                                renpy.store.stein_has_shotgun = True
                            
                            picked = True
                            self.pickup_msg = "SHOTGUN ACQUIRED"
                            self.pickup_msg_timer = 3.0

                    elif texture_index == 15:
                        w_obj = self.weapon_library["minigun"]
                        has_minigun = renpy.store.stein_has_minigun or (self.inventory[w_obj.category] and self.inventory[w_obj.category].name == "minigun")
                        
                        if not has_minigun:
                            if self.is_arena_mode:
                                self.equip_weapon("minigun")
                            else:
                                renpy.store.stein_has_minigun = True
                            
                            picked = True
                            self.pickup_msg = "MINIGUN ACQUIRED"
                            self.pickup_msg_timer = 3.0
                    if picked: self.sprite_positions.remove(sprite)

        def shoot_weapon(self):
            weapon = self.weapons[self.player.current_weapon_name]
            if time.time() - weapon.last_fired < weapon.cooldown: return
            weapon.last_fired = time.time()
            weapon.play()
            
            dx = self.player.dirx
            dy = self.player.diry 
            pitch = self.player.pitch
            is_ads = self.is_aiming or self.gp_aiming
            
            speed = 100.0
            dz = pitch / float(self.height)
            z_start = self.player.z + 0.5

            if weapon.projectile_type == 'shotgun':
                import random
                spread_mult = 0.1 if is_ads else 0.2
                for _ in range(5):
                    spread = (random.random() - 0.5) * spread_mult
                    angle = self.player.rot + spread
                    pdx = math.cos(angle)
                    pdy = math.sin(angle)
                    self.spawn_projectile(self.player.x, self.player.y, z_start, pdx, pdy, dz, speed, self.bullet_texture_index, weapon.damage, True, pitch=pitch)
                renpy.sound.play("sounds/shotgun.ogg", channel="audio")
            elif weapon.projectile_type == 'bullet':
                self.spawn_projectile(self.player.x, self.player.y, z_start, dx, dy, dz, speed, self.bullet_texture_index, weapon.damage, True, pitch=pitch)
                renpy.sound.play("sounds/gunshot.ogg", channel="audio")
            else:
                dir_z = -math.sin(self.player.pitch / float(self.height)) # Approximation
                dir_z = (self.player.pitch / float(self.height)) 

                hit_index = SteinWrapper.stein_lib.check_hitscan_c(
                    self.player.x, self.player.y, self.player.z + 1.6,
                    dx, dy, dir_z,
                    self.enemy_ptr,
                    len(self.enemies),
                    100.0,
                    float(weapon.damage)
                )

                if hit_index != -1:
                    e = self.enemies[hit_index]
                    
                    c_enemies = self.enemy_array
                    e.health = c_enemies[hit_index].hp
                    
                    self.hit_marker_timer = 0.15
                    
                    if e.health <= 0:
                        renpy.sound.play("sounds/ow.ogg", channel="audio")
                        if self.is_arena_mode:
                            persistent.stein_kills += 1
                        
                        if e in self.enemies:
                            self.enemies.remove(e)
                        
                        self.sprite_positions.append((e.x, e.y, e.destroyed_texture_index))
                        
                                    
                        # Arena Mode Drops
                        if self.is_arena_mode:
                            drop_prob = 1.0 if e.coin_index == 12 else 0.35
                            if renpy.random.random() < drop_prob:
                                self.sprite_positions.append((e.x, e.y, e.coin_index))
                            
                            if not renpy.store.stein_has_shotgun:
                                shotgun_prob = 0.25 if e.coin_index == 12 else 0.10
                                if renpy.random.random() < shotgun_prob:
                                    self.sprite_positions.append((e.x, e.y, 13))
                                    
                            if not renpy.store.stein_has_minigun:
                                if renpy.random.random() < 0.10:
                                    self.sprite_positions.append((e.x, e.y, 15))

        def add_damage_indicator(self, source_dir_x, source_dir_y):
            angle = math.atan2(source_dir_y, source_dir_x)
            self.damage_indicators.append(DamageIndicator(angle))

        def isBlocking(self, x, y, z=0.0):
            if x < 0 or x >= self.mapWidth or y < 0 or y >= self.mapHeight: return True
            
            layer = int(math.floor(z))
            tile = 0
            
            if isinstance(self.worldMap, dict):
                if layer in self.worldMap:
                    grid = self.worldMap[layer]
                    if int(x) < len(grid) and int(y) < len(grid[int(x)]):
                        tile = grid[int(x)][int(y)]
            else:
                if layer == 0:
                    tile = self.worldMap[int(x)][int(y)]
            
            if tile == 0: return False
            
            h = 1.0
            
            local_z = z - float(layer)
            if local_z >= h: return False
            
            return True

        def checkCollision(self, fromX, fromY, toX, toY, radius, z=0.0):
            # Check center
            if self.isBlocking(math.floor(toX), math.floor(toY), z):
                return [fromX, fromY]
            
            # Check radius
            points = [
                (toX + radius, toY), (toX - radius, toY),
                (toX, toY + radius), (toX, toY - radius)
            ]
            
            for px, py in points:
                if self.isBlocking(math.floor(px), math.floor(py), z):
                    return [fromX, fromY]
            
            return [toX, toY]

        def isVoxel(self, x, y, z):
            if x < 0 or x >= self.mapWidth or y < 0 or y >= self.mapHeight: return False
            
            layer = int(math.floor(z))
            tile = 0
            
            if isinstance(self.worldMap, dict):
                if layer in self.worldMap:
                    grid = self.worldMap[layer]
                    if int(x) < len(grid) and int(y) < len(grid[int(x)]):
                        tile = grid[int(x)][int(y)]
            else:
                if layer == 0:
                    tile = self.worldMap[int(x)][int(y)]
            
            return tile > 0

        def cast_ray(self, start_x, start_y, start_z, dir_x, dir_y, dir_z, max_dist=10.0):
            map_address, _ = self.flat_map_buffer.buffer_info()
            
            # Call to cpp
            return stein_core.cast_ray_fast(
                start_x, start_y, start_z, 
                dir_x, dir_y, dir_z, 
                map_address, 
                self.mapWidth, self.mapHeight, self.num_layers, self.min_layer,
                max_dist
            )

        def handle_builder_action(self, action):
            rdx = self.player.dirx
            rdy = self.player.diry
            
            h_div = float(self.internal_height) if self.internal_height else float(self.height)
            rdz = self.player.pitch / h_div
            
            # Normalize
            rlen = math.sqrt(rdx*rdx + rdy*rdy + rdz*rdz)
            if rlen > 0:
                rdx /= rlen
                rdy /= rlen
                rdz /= rlen
            
            res = self.cast_ray(self.player.x, self.player.y, self.player.z + 1.6, rdx, rdy, rdz, max_dist=100.0)
            
            if res[0]: 
                mx, my, mz, side, sx, sy, sz = res[1:]
                
                if action == 'remove':
                    self.set_voxel(mx, my, mz, 0)
                elif action == 'place':
                    nx, ny, nz = mx, my, mz
                    if side == 0: nx -= sx
                    elif side == 1: ny -= sy
                    elif side == 2: nz -= sz
                    
                    if math.floor(self.player.x) == nx and math.floor(self.player.y) == ny and math.floor(self.player.z) == nz:
                        return
                    
                    self.set_voxel(nx, ny, nz, self.selected_voxel)
            else:
                if action == 'place':
                    nx = int(math.floor(self.player.x))
                    ny = int(math.floor(self.player.y))
                    nz = int(math.floor(self.player.z))
                    self.set_voxel(nx, ny, nz, self.selected_voxel)

        def shift_map(self, off_x, off_y):
            self.mapWidth += off_x
            self.mapHeight += off_y
            self.map_w = self.mapWidth
            self.map_h = self.mapHeight
            
            for z, grid in self.worldMap.items():
                curr_w = len(grid)
                curr_h = len(grid[0]) if curr_w > 0 else 0
                
                if off_x > 0:
                    new_cols = [[0] * curr_h for _ in range(off_x)]
                    for col in reversed(new_cols):
                        grid.insert(0, col)
                
                if off_y > 0:
                    for col in grid:
                        for _ in range(off_y):
                            col.insert(0, 0)
            
            self.player.x += off_x
            self.player.y += off_y
            
            for e in self.enemies:
                e.x += off_x
                e.y += off_y
                if hasattr(e, 'last_known_x') and e.last_known_x is not None: e.last_known_x += off_x
                if hasattr(e, 'last_known_y') and e.last_known_y is not None: e.last_known_y += off_y
            
            for p in self.projectiles:
                p.x += off_x
                p.y += off_y
            
            new_sprites = []
            for s in self.sprite_positions:
                l = list(s)
                l[0] += off_x
                l[1] += off_y
                new_sprites.append(tuple(l))
            self.sprite_positions = new_sprites
            
            new_spawns = []
            for s in self.spawn_points:
                new_spawns.append((s[0] + off_x, s[1] + off_y))
            self.spawn_points = new_spawns
            
            new_exits = []
            for e in self.exits:
                l = list(e)
                l[0] += off_x
                l[1] += off_y
                new_exits.append(tuple(l))
            self.exits = new_exits
            
            self.pickup_msg = f"MAP SHIFTED BY {off_x}, {off_y}"
            self.pickup_msg_timer = 2.0

        def set_voxel(self, x, y, z, val):
            map_changed = False
            if not isinstance(self.worldMap, dict):
                new_map = {0: [row[:] for row in self.worldMap]}
                self.worldMap = new_map
                self.map_data = new_map
            
            off_x = 0
            off_y = 0
            if x < 0:
                off_x = abs(x)
                x = 0
            if y < 0:
                off_y = abs(y)
                y = 0
            
            if off_x > 0 or off_y > 0:
                if self.lock_map_expansion:
                    self.pickup_msg = "MAP EXPANSION LOCKED"
                    self.pickup_msg_timer = 1.0
                    return
                self.shift_map(off_x, off_y)
                map_changed = True
            
            # Check for expansion
            if x >= self.mapWidth or y >= self.mapHeight:
                if self.lock_map_expansion:
                    self.pickup_msg = "MAP EXPANSION LOCKED"
                    self.pickup_msg_timer = 1.0
                    return
                new_w = max(self.mapWidth, x + 1)
                new_h = max(self.mapHeight, y + 1)
                self.expand_map(new_w, new_h)
                map_changed = True

            if z not in self.worldMap:
                if val == 0: 
                    if map_changed: self.map_texture = self.create_map_texture()
                    return 
                self.worldMap[z] = [[0 for _ in range(self.mapHeight)] for _ in range(self.mapWidth)]
            
            grid = self.worldMap[z]
            if 0 <= x < len(grid) and 0 <= y < len(grid[0]):
                grid[x][y] = val
                map_changed = True

                if 0 <= x < self.mapWidth and 0 <= y < self.mapHeight:
                    layer_idx = z - self.min_layer
                    if 0 <= layer_idx < self.num_layers:
                        idx = (layer_idx * self.mapWidth * self.mapHeight) + (x * self.mapHeight) + y
                        if idx < len(self.flat_map_buffer):
                            self.flat_map_buffer[idx] = val
                
            if map_changed:
                self.map_texture = self.create_map_texture()

        def expand_map(self, new_w, new_h):
            self.mapWidth = new_w
            self.mapHeight = new_h
            self.map_w = new_w
            self.map_h = new_h
            
            for z, grid in self.worldMap.items():
                current_w = len(grid)
                current_h = len(grid[0]) if current_w > 0 else 0
                
                # Resize width
                if new_w > current_w:
                    for _ in range(new_w - current_w):
                        grid.append([0] * current_h)
                
                # Resize height
                for row in grid:
                    if new_h > len(row):
                        row.extend([0] * (new_h - len(row)))
            
            self.pickup_msg = f"MAP EXPANDED TO {new_w}x{new_h}"
            self.pickup_msg_timer = 2.0

        # EVENT HANDLING
        def event(self, ev, x, y, st):
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_LCTRL or ev.key == pygame.K_RCTRL:
                    self.kb_running = True
                    raise renpy.IgnoreEvent()
            
            if ev.type == pygame.KEYUP:
                if ev.key == pygame.K_LCTRL or ev.key == pygame.K_RCTRL:
                    self.kb_running = False
                    raise renpy.IgnoreEvent()

            if self.return_value:
                return self.return_value

            global simulate_touch
            if not self.mouse_initialized and not simulate_touch and not self.editor_mode:
                pygame.mouse.set_visible(False); pygame.event.set_grab(True); self.mouse_initialized = True
            if simulate_touch:
                if ev.type in (pygame.FINGERDOWN, pygame.FINGERMOTION, pygame.FINGERUP): self.handle_multitouch_events(ev)
                elif ev.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEMOTION, pygame.MOUSEBUTTONUP): self.handle_mouse_simulation(ev, x, y)
            else: self.handle_pc_input(ev)
            if ev.type in (pygame.JOYBUTTONDOWN, pygame.JOYBUTTONUP, pygame.JOYHATMOTION, pygame.JOYDEVICEADDED, pygame.JOYDEVICEREMOVED): self.handle_gamepad_input(ev)
            renpy.retain_after_load()

        def handle_multitouch_events(self, ev):
            LOOK_THRESHOLD_X = 0.5; finger_id = ev.finger_id; event_x = ev.x * self.width; event_y = ev.y * self.height
            if ev.type == pygame.FINGERDOWN:
                action = None
                if ev.x <= LOOK_THRESHOLD_X: action = 'move'
                elif ev.x > LOOK_THRESHOLD_X: action = 'look'
                if action: self.active_fingers[finger_id] = {'action': action, 'start_pos': (event_x, event_y), 'current_pos': (event_x, event_y), 'dx_accum': 0.0}
            elif ev.type == pygame.FINGERMOTION:
                if finger_id in self.active_fingers:
                    info = self.active_fingers[finger_id]
                    if info['action'] == 'move': info['current_pos'] = (event_x, event_y)
                    elif info['action'] == 'look': info['dx_accum'] += ev.dx * self.width
            elif ev.type == pygame.FINGERUP:
                if finger_id in self.active_fingers: del self.active_fingers[finger_id]

        def raycast_objects(self, ro, rd):
            """Raycasts against cached active objects to find the closest voxel."""
            objects = getattr(self, 'last_active_objects', [])
            origins = getattr(self, 'last_active_origins', [])
            
            closest_dist = 100.0
            hit_voxel = None
            
            obj_scale = 16.0 if self.editor_mode else 1.0
            
            for i, obj in enumerate(objects):
                if i >= len(origins): break
                if obj[3] < 0: continue
                
                box_min = (obj[0], obj[1], obj[2])
                box_max = (obj[0]+obj_scale, obj[1]+obj_scale, obj[2]+obj_scale)
                
                t_min_x = (box_min[0] - ro[0]) / (rd[0] if abs(rd[0])>1e-5 else 1e-5)
                t_max_x = (box_max[0] - ro[0]) / (rd[0] if abs(rd[0])>1e-5 else 1e-5)
                t1 = min(t_min_x, t_max_x); t2 = max(t_min_x, t_max_x)
                
                t_min_y = (box_min[1] - ro[1]) / (rd[1] if abs(rd[1])>1e-5 else 1e-5)
                t_max_y = (box_max[1] - ro[1]) / (rd[1] if abs(rd[1])>1e-5 else 1e-5)
                t1 = max(t1, min(t_min_y, t_max_y)); t2 = min(t2, max(t_min_y, t_max_y))
                
                t_min_z = (box_min[2] - ro[2]) / (rd[2] if abs(rd[2])>1e-5 else 1e-5)
                t_max_z = (box_max[2] - ro[2]) / (rd[2] if abs(rd[2])>1e-5 else 1e-5)
                t1 = max(t1, min(t_min_z, t_max_z)); t2 = min(t2, max(t_min_z, t_max_z))
                
                if t2 >= t1 and t2 > 0:
                    dist = t1 if t1 > 0 else 0
                    if dist < closest_dist:
                        hit_point = (ro[0] + rd[0]*dist + rd[0]*0.01, ro[1] + rd[1]*dist + rd[1]*0.01, ro[2] + rd[2]*dist + rd[2]*0.01)
                        
                        local_x = (hit_point[0] - obj[0]) * (16.0 / obj_scale)
                        local_y = (hit_point[1] - obj[1]) * (16.0 / obj_scale)
                        local_z = (hit_point[2] - obj[2]) * (16.0 / obj_scale)
                        
                        vx, vy, vz = math.floor(local_x), math.floor(local_y), math.floor(local_z)
                        
                        if 0 <= vx < 16 and 0 <= vy < 16 and 0 <= vz < 16:
                            # Handle vec4 origin unpacking (x, y, z, padding)
                            ox, oy, oz, _ = origins[i]
                            hit_voxel = (ox + vx, oy + vy, oz + vz)
                            closest_dist = dist

            return hit_voxel, closest_dist

        def update_player_from_touch_state(self):
            self.touch_speed = 0.0; self.touch_strafe = 0.0; self.touch_dir = 0.0
            for finger_id, info in list(self.active_fingers.items()):
                if info['action'] == 'move':
                    dx = info['current_pos'][0] - info['start_pos'][0]; dy = info['current_pos'][1] - info['start_pos'][1]
                    self.touch_speed += -dy / 80.0; self.touch_strafe += dx / 80.0
                elif info['action'] == 'look':
                    self.touch_dir += (info['dx_accum'] / self.width) * 25.0; info['dx_accum'] = 0.0

        def handle_mouse_simulation(self, ev, x, y):
            LOOK_THRESHOLD_PIXELS = self.width * 0.5; button_id = getattr(ev, 'button', None)
            if ev.type == pygame.MOUSEBUTTONDOWN:
                if button_id == 1 and x > LOOK_THRESHOLD_PIXELS: self.active_fingers[1] = {'action': 'look', 'dx_accum': 0.0}
                elif button_id == 3 and x <= LOOK_THRESHOLD_PIXELS: self.active_fingers[3] = {'action': 'move', 'start_pos':(x,y), 'current_pos':(x,y)}
            elif ev.type == pygame.MOUSEMOTION:
                if ev.buttons[0] and 1 in self.active_fingers: self.active_fingers[1]['dx_accum'] += ev.rel[0]
                if ev.buttons[2] and 3 in self.active_fingers: self.active_fingers[3]['current_pos'] = (x, y)
            elif ev.type == pygame.MOUSEBUTTONUP:
                if button_id in self.active_fingers: del self.active_fingers[button_id]

        def handle_pc_input(self, ev):
            if self.editor_mode:
                rmb_down = pygame.mouse.get_pressed()[2]
                if rmb_down:
                    if not self.mouse_initialized:
                        pygame.mouse.set_visible(False); pygame.event.set_grab(True); self.mouse_initialized = True
                else:
                    if self.mouse_initialized:
                        pygame.mouse.set_visible(True); pygame.event.set_grab(False); self.mouse_initialized = False
                        self.kb_speed = 0.0; self.kb_strafe = 0.0; self.kb_dir = 0.0; self.kb_fly_up = False; self.kb_fly_down = False
                    
                    # Allow Builder actions (Click) or KeyUp cleanup, otherwise block
                    if self.builder_mode and (ev.type == pygame.MOUSEBUTTONDOWN or ev.type == pygame.MOUSEBUTTONUP):
                        pass
                    elif ev.type != pygame.KEYUP:
                        return

                # If RMB is held, we consume the event so it doesn't reach the UI (inputs)
                if rmb_down and ev.type in (pygame.KEYDOWN, pygame.KEYUP, pygame.MOUSEMOTION):
                    pass 

            # Handle mouse look
            if ev.type == pygame.MOUSEMOTION:
                base_sens = 0.003
                base_pitch = 0.8
                
                sensitivity = base_sens * persistent.stein_mouse_sens
                pitch_sensitivity = base_pitch * persistent.stein_mouse_sens

                if self.is_aiming:
                    sensitivity *= 0.25
                    pitch_sensitivity *= 0.5

                self.player.rot -= ev.rel[0] * sensitivity
                self.player.planerot -= ev.rel[0] * sensitivity
                
                # Pitch (vertical look)
                self.player.pitch -= ev.rel[1] * pitch_sensitivity
                self.player.pitch = max(-50000.0, min(50000.0, self.player.pitch))
                
                if self.editor_mode and pygame.mouse.get_pressed()[2]:
                    raise renpy.IgnoreEvent()

            if ev.type == pygame.KEYDOWN:
                if self.editor_mode and not pygame.mouse.get_pressed()[2]: return 

                if config.developer:
                    if ev.key == pygame.K_o:
                        self.builder_mode = not self.builder_mode
                        self.player.fly_mode = self.builder_mode
                        if self.builder_mode:
                            self.pickup_msg = "BUILDER MODE ON"
                            self.pickup_msg_timer = 2.0
                        else:
                            self.pickup_msg = "BUILDER MODE OFF"
                            self.pickup_msg_timer = 2.0

                    if ev.key == pygame.K_p:
                        renpy.store.save_level_json(self.worldMap)
                        self.pickup_msg = "LEVEL DATA SAVED"
                        self.pickup_msg_timer = 2.0

                    if ev.key == pygame.K_l:
                        self.lock_map_expansion = not self.lock_map_expansion
                        state = "LOCKED" if self.lock_map_expansion else "UNLOCKED"
                        self.pickup_msg = f"MAP EXPANSION: {state}"
                        self.pickup_msg_timer = 2.0
                
                # We need to capture the movement keys before they reach the UI
                if ev.key in (pygame.K_w, pygame.K_s, pygame.K_a, pygame.K_d, pygame.K_SPACE, pygame.K_n, pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT):
                    # Process movement
                    if ev.key == pygame.K_w or ev.key == pygame.K_UP: self.kb_speed = 1.0
                    if ev.key == pygame.K_s or ev.key == pygame.K_DOWN: self.kb_speed = -1.0
                    if ev.key == pygame.K_a: self.kb_strafe = -1.0
                    if ev.key == pygame.K_d: self.kb_strafe = 1.0
                    if ev.key == pygame.K_LEFT: self.kb_dir = 1.0
                    if ev.key == pygame.K_RIGHT: self.kb_dir = -1.0
                    
                    if ev.key == pygame.K_SPACE: 
                        if self.player.fly_mode: self.kb_fly_up = True
                        else: self.player.trigger_jump()
                    if ev.key == pygame.K_n:
                        if self.player.fly_mode: self.kb_fly_down = True
                        
                    if self.editor_mode and pygame.mouse.get_pressed()[2]:
                        raise renpy.IgnoreEvent()

                # Process other keys (non-movement)
                if ev.key == pygame.K_ESCAPE:
                    pygame.mouse.set_visible(True)
                    pygame.event.set_grab(False)
                    self.mouse_initialized = False
                    return

                if ev.key == pygame.K_1: self.switch_to_slot(SLOT_MELEE)
                if ev.key == pygame.K_2: self.switch_to_slot(SLOT_HANDGUN)
                if ev.key == pygame.K_3: self.switch_to_slot(SLOT_LONG)
                if ev.key == pygame.K_4: self.switch_to_slot(SLOT_SPECIAL)
                if ev.key == pygame.K_f:
                    self.flashlight_on = not self.flashlight_on

                if self.editor_mode and ev.key == pygame.K_y:
                    # Raycast from camera center to find voxel
                    px, py, pz = self.player.x, self.player.y, self.player.z
                    rot, pitch = self.player.rot, self.player.pitch / float(self.height)
                    
                    if self.editor_target:
                        px -= self.editor_target.x; py -= self.editor_target.y; pz -= self.editor_target.z
                        cx, cy = self.mapWidth / 2.0, self.mapHeight / 2.0
                        rz_rad = math.radians(self.editor_target.rz)
                        rx, ry = px - cx, py - cy
                        s, c_val = math.sin(-rz_rad), math.cos(-rz_rad)
                        px, py = cx + (rx * c_val - ry * s), cy + (rx * s + ry * c_val)
                        rot -= rz_rad

                    # Map Picking
                    map_addr, _ = self.flat_map_buffer.buffer_info()
                    hit, mx, my, mz, side, sx, sy, sz = SteinWrapper.cast_ray_fast(
                        px, py, 1.6 + pz, math.cos(rot), math.sin(rot), pitch,
                        map_addr, self.mapWidth, self.mapHeight, self.num_layers, self.min_layer, 100.0
                    )
                    
                    dist_map = 1000.0
                    if hit:
                        dist_map = math.sqrt((mx + 0.5 - px)**2 + (my + 0.5 - py)**2 + (mz + 0.5 - (1.6+pz))**2)

                    # Object Picking
                    rd_x = math.cos(rot); rd_y = math.sin(rot); rd_z = pitch
                    l = math.sqrt(rd_x*rd_x + rd_y*rd_y + rd_z*rd_z)
                    rd = (rd_x/l, rd_y/l, rd_z/l)
                    
                    obj_voxel, dist_obj = self.raycast_objects((px, py, 1.6+pz), rd)
                    
                    final_voxel = None
                    if obj_voxel and dist_obj < dist_map:
                        final_voxel = obj_voxel
                        print(f"DEBUG PICK: Hit Object Voxel {final_voxel} at dist {dist_obj:.2f}")
                    elif hit:
                        final_voxel = (float(mx), float(my), float(mz))
                        print(f"DEBUG PICK: Hit Map Voxel {final_voxel} at dist {dist_map:.2f}")

                    if final_voxel:
                        self.highlight_pos = (float(final_voxel[0]), float(final_voxel[1]), float(final_voxel[2]))
                        
                        # Multi-selection toggle
                        pos = (int(final_voxel[0]), int(final_voxel[1]), int(final_voxel[2]))
                        if pos in self.selection_map:
                            del self.selection_map[pos]
                            self.highlight_pos = (-1.0, -1.0, -1.0)
                            self.pickup_msg = f"VOXEL DESELECTED: {pos}"
                        else:
                            self.selection_map[pos] = True
                            self.pickup_msg = f"VOXEL SELECTED: {pos}"
                        
                        self.selection_texture = None
                        self.pickup_msg_timer = 2.0
                        renpy.restart_interaction()
                    else:
                        self.highlight_pos = (-1.0, -1.0, -1.0)

                if ev.key == pygame.K_w: self.kb_speed = 1.0
                if ev.key == pygame.K_LCTRL or ev.key == pygame.K_RCTRL: self.kb_running = True

            if ev.type == pygame.KEYUP:
                if ev.key == pygame.K_SPACE: self.kb_fly_up = False
                if ev.key in (pygame.K_w, pygame.K_s, pygame.K_UP, pygame.K_DOWN): self.kb_speed = 0.0
                if ev.key in (pygame.K_a, pygame.K_d): self.kb_strafe = 0.0
                if ev.key in (pygame.K_LEFT, pygame.K_RIGHT): self.kb_dir = 0.0
                if ev.key in (pygame.K_LCTRL, pygame.K_RCTRL): self.kb_running = False
                if ev.key == pygame.K_n: self.kb_fly_down = False
                
                if self.editor_mode and pygame.mouse.get_pressed()[2]:
                    raise renpy.IgnoreEvent()

            if ev.type == pygame.MOUSEBUTTONDOWN:
                if self.builder_mode:
                    if not self.editor_mode:
                        if ev.button == 1: # Left Click - Place
                            self.handle_builder_action('place')
                        elif ev.button == 3: # Right Click - Remove
                            self.handle_builder_action('remove')
                        elif ev.button == 4: # Wheel Up
                            self.selected_voxel = (self.selected_voxel % int(self.num_textures)) + 1
                            self.pickup_msg = f"VOXEL: {self.selected_voxel}"
                            self.pickup_msg_timer = 1.0
                        elif ev.button == 5: # Wheel Down
                            self.selected_voxel = ((self.selected_voxel - 2) % int(self.num_textures)) + 1
                            self.pickup_msg = f"VOXEL: {self.selected_voxel}"
                            self.pickup_msg_timer = 1.0
                    
                    # Always return if builder mode is on to suppress weapons
                    return 

                if ev.button == 1: # Left mouse button
                    self.mouse_firing = True
                elif ev.button == 3: # Right mouse button (Aim)
                    self.is_aiming = True
            
            if ev.type == pygame.MOUSEBUTTONUP:
                if ev.button == 1:
                    self.mouse_firing = False
                elif ev.button == 3:
                    self.is_aiming = False

        def poll_gamepad(self):
            self.gp_speed = 0.0; self.gp_strafe = 0.0; self.gp_dir = 0.0
            self.gp_aiming = False; self.gp_firing = False; self.gp_running = False
            DEADZONE = 0.25; TRIGGER_THRESHOLD = 0.6 
            is_switch_held = False

            for joy in self.joysticks:
                try:
                    if not joy.get_init(): continue
                    name = joy.get_name().lower()
                    if "accelerometer" in name or "gyro" in name: continue
                    
                    if joy.get_numaxes() > 4 and joy.get_axis(4) > TRIGGER_THRESHOLD: self.gp_aiming = True
                    if renpy.android:
                        if joy.get_numbuttons() > 9 and joy.get_button(9): self.gp_running = True
                    else:
                        if joy.get_numbuttons() > 4 and joy.get_button(4): self.gp_running = True

                    if joy.get_numaxes() > 0:
                        x = joy.get_axis(0)
                        if abs(x) > DEADZONE: self.gp_strafe += x 
                    if joy.get_numaxes() > 1:
                        y = joy.get_axis(1)
                        if abs(y) > DEADZONE: self.gp_speed -= y 
                    if joy.get_numaxes() > 2:
                        rx = joy.get_axis(2)
                        if abs(rx) > DEADZONE:
                            sens = 2.5 * persistent.stein_gamepad_sens_x
                            if self.is_aiming or self.gp_aiming: sens *= 0.25
                            self.gp_dir -= rx * sens
                    if joy.get_numaxes() > 3:
                        ry = joy.get_axis(3)
                        if abs(ry) > DEADZONE:
                            p_speed = 19.0 * persistent.stein_gamepad_sens_y
                            if self.is_aiming or self.gp_aiming: p_speed *= 0.5
                            self.player.pitch -= ry * p_speed
                            self.player.pitch = max(-50000.0, min(50000.0, self.player.pitch))

                    if joy.get_numaxes() > 5 and joy.get_axis(5) > TRIGGER_THRESHOLD: self.gp_firing = True
                    if joy.get_numbuttons() > 5 and joy.get_button(5): self.gp_firing = True
                    if joy.get_numbuttons() > 0 and joy.get_button(0): self.player.trigger_jump()
                    if joy.get_numbuttons() > 3 and joy.get_button(3): is_switch_held = True

                    btn_flashlight_held = False

                    if renpy.android:
                        if joy.get_numbuttons() > 11 and joy.get_button(11):
                            btn_flashlight_held = True
                    elif joy.get_numhats() > 0:
                        hat_x, hat_y = joy.get_hat(0)
                        if hat_y == 1: 
                            btn_flashlight_held = True
                    
                    if btn_flashlight_held and not self.prev_btn_flashlight:
                        self.flashlight_on = not self.flashlight_on
                    
                    self.prev_btn_flashlight = btn_flashlight_held

                except pygame.error: continue
            
            if is_switch_held and not getattr(self, 'prev_btn_weapon_switch', False):
                self.cycle_weapon()
            
            self.prev_btn_weapon_switch = is_switch_held

        def handle_gamepad_input(self, ev):
            if ev.type == pygame.JOYDEVICEADDED or ev.type == pygame.JOYDEVICEREMOVED:
                pygame.joystick.quit()
                pygame.joystick.init()
                self.joysticks = [pygame.joystick.Joystick(x) for x in range(pygame.joystick.get_count())]
                for joy in self.joysticks: 
                    try: joy.init()
                    except: pass
