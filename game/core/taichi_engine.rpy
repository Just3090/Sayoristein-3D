init -5 python:
    import taichi as ti
    import numpy as np
    import pygame_sdl2 as pygame
    import time
    import math
    import ctypes
    import os

    try:
        ti.init(arch=ti.vulkan)
    except Exception:
        ti.init(arch=ti.gpu)

    if "stein_core" in sys.modules:
        SteinWrapper = sys.modules["stein_core"]
    else:
        SteinWrapper = None

    class Taichi3DEngine:
        def __init__(self, res_x=1066, res_y=600):
            self.res_x = res_x
            self.res_y = res_y
            self.pixels = ti.Vector.field(n=4, dtype=ti.u8, shape=(res_y, res_x))
            
            self.num_vertices = 0
            self.num_triangles = 0
            
            self.vertices = None
            self.normals = None
            self.uvs = None
            self.indices = None
            self.projected_vertices = None
            
            self.tex_w = 256
            self.tex_h = 256
            self.texture_data = ti.Vector.field(3, dtype=ti.u8, shape=(self.tex_w, self.tex_h))
            self.init_texture()
            
    T_pixels = ti.Vector.field(n=4, dtype=ti.u8, shape=(600, 1066))
    T_zbuffer = ti.field(dtype=ti.f32, shape=(600, 1066))
    T_vertices = ti.Vector.field(3, dtype=ti.f32, shape=1)
    T_normals = ti.Vector.field(3, dtype=ti.f32, shape=1)
    T_uvs = ti.Vector.field(2, dtype=ti.f32, shape=1)
    T_indices = ti.field(dtype=ti.i32, shape=1)
    T_projected = ti.Vector.field(6, dtype=ti.f32, shape=1)
    global_num_vertices = 0
    global_num_triangles = 0

    def taichi_init_texture():
        return

    @ti.func
    def edge_function(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

    @ti.kernel
    def taichi_process_vertices(cam_x: ti.f32, cam_y: ti.f32, cam_z: ti.f32, cam_yaw: ti.f32, cam_pitch: ti.f32, res_x: ti.f32, res_y: ti.f32, total_verts: ti.i32):
        light_dir = ti.Vector([0.5, 0.8, -0.3])
        l_len = ti.sqrt(light_dir[0]**2 + light_dir[1]**2 + light_dir[2]**2)
        light_dir = ti.Vector([light_dir[0]/l_len, light_dir[1]/l_len, light_dir[2]/l_len])
        c_y = ti.cos(-cam_yaw)
        s_y = ti.sin(-cam_yaw)
        c_p = ti.cos(cam_pitch)
        s_p = ti.sin(cam_pitch)
        fov = res_y * 0.8

        for i in range(total_verts):
            v = T_vertices[i]
            n = T_normals[i]
            u_v = T_uvs[i]
            
            dot_l = n[0] * light_dir[0] + n[1] * light_dir[1] + n[2] * light_dir[2]
            intensity = ti.max(0.0, dot_l) * 0.7 + 0.3
            
            tx = v[0] - cam_x
            ty = v[1] - cam_y
            tz = v[2] - cam_z
            
            rx = tx * c_y - tz * s_y
            z1 = tx * s_y + tz * c_y
            y1 = ty

            ry = y1 * c_p - z1 * s_p
            rz = y1 * s_p + z1 * c_p
            
            px = 0.0
            py = 0.0
            inv_z = 0.0
            
            if rz > 0.1:
                inv_z = 1.0 / rz
                px = rx * fov * inv_z + res_x * 0.5
                py = ry * fov * inv_z + res_y * 0.5
            
            T_projected[i] = ti.Vector([px, py, inv_z, u_v[0] * inv_z, u_v[1] * inv_z, intensity])

    @ti.kernel
    def taichi_clear_buffers(res_x: ti.i32, res_y: ti.i32):
        for j, i in ti.ndrange(res_y, res_x):
            T_pixels[j, i] = [
                ti.cast(20, ti.u8),
                ti.cast(20, ti.u8),
                ti.cast(25, ti.u8),
                ti.cast(255, ti.u8)
            ]
            T_zbuffer[j, i] = 1e10

    @ti.kernel
    def taichi_render_3d(res_x: ti.i32, res_y: ti.i32, total_tris: ti.i32):
        for t_idx in range(total_tris):
            i0 = T_indices[t_idx * 3]
            i1 = T_indices[t_idx * 3 + 1]
            i2 = T_indices[t_idx * 3 + 2]

            v0 = T_projected[i0]
            v1 = T_projected[i2]
            v2 = T_projected[i1]

            if v0[2] > 0.0 and v1[2] > 0.0 and v2[2] > 0.0:
                area = edge_function(v0, v1, v2)
                if area > 0.0:
                    min_x = ti.max(0, ti.cast(ti.floor(ti.min(ti.min(v0[0], v1[0]), v2[0])), ti.i32))
                    max_x = ti.min(res_x - 1, ti.cast(ti.ceil(ti.max(ti.max(v0[0], v1[0]), v2[0])), ti.i32))
                    min_y = ti.max(0, ti.cast(ti.floor(ti.min(ti.min(v0[1], v1[1]), v2[1])), ti.i32))
                    max_y = ti.min(res_y - 1, ti.cast(ti.ceil(ti.max(ti.max(v0[1], v1[1]), v2[1])), ti.i32))

                    for px in range(min_x, max_x + 1):
                        for py in range(min_y, max_y + 1):
                            p = ti.Vector([float(px), float(py)])
                            w0 = edge_function(v1, v2, p)
                            w1 = edge_function(v2, v0, p)
                            w2 = edge_function(v0, v1, p)

                            if w0 >= 0.0 and w1 >= 0.0 and w2 >= 0.0:
                                w0_n = w0 / area
                                w1_n = w1 / area
                                w2_n = w2 / area
                                inv_z = w0_n * v0[2] + w1_n * v1[2] + w2_n * v2[2]
                                z = 1.0 / inv_z
                                j = res_y - 1 - py

                                if z > 0.1:
                                    old_z = ti.atomic_min(T_zbuffer[j, px], z)
                                    if z <= old_z:
                                        u_z = w0_n * v0[3] + w1_n * v1[3] + w2_n * v2[3]
                                        v_z = w0_n * v0[4] + w1_n * v1[4] + w2_n * v2[4]
                                        tex_u = u_z * z
                                        tex_v = v_z * z
                                        final_intensity = w0_n * v0[5] + w1_n * v1[5] + w2_n * v2[5]

                                        tu_abs = ti.abs(tex_u)
                                        tv_abs = ti.abs(tex_v)
                                        tu_idx = ti.cast(tu_abs * 255.0, ti.i32) % 256
                                        tv_idx = ti.cast(tv_abs * 255.0, ti.i32) % 256
                                        checker = (tu_idx // 32 + tv_idx // 32) % 2
                                        base = 255.0
                                        if checker != 0:
                                            base = 100.0

                                        T_pixels[j, px] = [
                                            ti.cast(base * final_intensity, ti.u8),
                                            ti.cast(base * final_intensity, ti.u8),
                                            ti.cast(base * final_intensity, ti.u8),
                                            ti.cast(255, ti.u8)
                                        ]

    
    def _sorted_numeric_keys(d):
        return sorted(d.keys(), key=lambda k: int(k) if str(k).lstrip("-").isdigit() else str(k))

    def _to_plane_rows(rows_obj):
        if isinstance(rows_obj, dict):
            rows_iter = [rows_obj[k] for k in _sorted_numeric_keys(rows_obj)]
        else:
            rows_iter = rows_obj

        if not isinstance(rows_iter, (list, tuple)):
            return []

        out = []
        for row in rows_iter:
            if isinstance(row, dict):
                row_vals = [row[k] for k in _sorted_numeric_keys(row)]
            else:
                row_vals = row

            if not isinstance(row_vals, (list, tuple)):
                continue

            out_row = []
            for v in row_vals:
                try:
                    out_row.append(int(v))
                except Exception:
                    out_row.append(0)
            out.append(out_row)
        return out

    def _deep_find_plane(obj, depth=0):
        if depth > 8:
            return []

        if isinstance(obj, (list, tuple)) and obj:
            if all(isinstance(r, (list, tuple)) for r in obj):
                plane = _to_plane_rows(obj)
                if plane and len(plane[0]) > 0:
                    return plane

            if all(isinstance(r, dict) for r in obj):
                plane = _to_plane_rows(obj)
                if plane and len(plane[0]) > 0:
                    return plane

            for item in obj:
                plane = _deep_find_plane(item, depth + 1)
                if plane:
                    return plane

            return []

        if isinstance(obj, dict):
            for k in ("worldMap", "map", "grid", "layer", "layers", "voxels", "data"):
                if k in obj:
                    plane = _deep_find_plane(obj[k], depth + 1)
                    if plane:
                        return plane

            plane = _to_plane_rows(obj)
            if plane and len(plane[0]) > 0:
                return plane

            for k in _sorted_numeric_keys(obj):
                plane = _deep_find_plane(obj[k], depth + 1)
                if plane:
                    return plane

        return []

    def normalize_worldmap_plane(world_map):
        if isinstance(world_map, dict):
            if not world_map:
                return []

            first_key = _sorted_numeric_keys(world_map)[0]
            first_val = world_map[first_key]

            if isinstance(first_val, (list, tuple)) and first_val and isinstance(first_val[0], (list, tuple, dict)):
                return _to_plane_rows(first_val)
            if isinstance(first_val, dict):
                fv_keys = _sorted_numeric_keys(first_val)
                if fv_keys and isinstance(first_val[fv_keys[0]], (list, tuple, dict)):
                    return _to_plane_rows(first_val)

            plane = _to_plane_rows(world_map)
            if plane and len(plane[0]) > 0:
                return plane

            return _deep_find_plane(world_map)

        plane = _to_plane_rows(world_map)
        if plane and len(plane[0]) > 0:
            return plane
        return _deep_find_plane(world_map)

    def load_level_to_taichi(map_grid):
        global T_vertices, T_normals, T_uvs, T_indices, T_projected
        global global_num_vertices, global_num_triangles
        map_grid = normalize_worldmap_plane(map_grid)

        w = len(map_grid)
        h = len(map_grid[0]) if w > 0 else 0
        
        def is_solid(x, y):
            if x < 0 or x >= w or y < 0 or y >= h:
                return False
            return map_grid[x][y] > 0

        v_list = []
        n_list = []
        u_list = []
        i_list = []
        
        v_count = 0
        
        def add_face(p0, p1, p2, p3, normal):
            nonlocal v_count
            v_list.extend([p0, p1, p2, p3])
            n_list.extend([normal, normal, normal, normal])
            u_list.extend([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]])
            i_list.extend([v_count, v_count+1, v_count+2, v_count+2, v_count+3, v_count])
            v_count += 4

        for x in range(w):
            for y in range(h):
                if is_solid(x, y):
                    bx0 = float(x)
                    bx1 = float(x + 1)
                    by0 = 0.0
                    by1 = 1.0
                    bz0 = float(y)
                    bz1 = float(y + 1)
                    
                    if not is_solid(x, y-1):
                        add_face(
                            [bx0, by0, bz0], [bx1, by0, bz0], [bx1, by1, bz0], [bx0, by1, bz0],
                            [0.0, 0.0, -1.0]
                        )
                    if not is_solid(x, y+1):
                        add_face(
                            [bx1, by0, bz1], [bx0, by0, bz1], [bx0, by1, bz1], [bx1, by1, bz1],
                            [0.0, 0.0, 1.0]
                        )
                    if not is_solid(x-1, y):
                        add_face(
                            [bx0, by0, bz1], [bx0, by0, bz0], [bx0, by1, bz0], [bx0, by1, bz1],
                            [-1.0, 0.0, 0.0]
                        )
                    if not is_solid(x+1, y):
                        add_face(
                            [bx1, by0, bz0], [bx1, by0, bz1], [bx1, by1, bz1], [bx1, by1, bz0],
                            [1.0, 0.0, 0.0]
                        )
                    add_face(
                        [bx0, by1, bz0], [bx1, by1, bz0], [bx1, by1, bz1], [bx0, by1, bz1],
                        [0.0, 1.0, 0.0]
                    )
                    add_face(
                        [bx0, by0, bz1], [bx1, by0, bz1], [bx1, by0, bz0], [bx0, by0, bz0],
                        [0.0, -1.0, 0.0]
                    )

        num_verts = len(v_list)
        num_tris = len(i_list) // 3
        global_num_vertices = num_verts
        global_num_triangles = num_tris

        if num_verts > 0:
            T_vertices = ti.Vector.field(3, dtype=ti.f32, shape=num_verts)
            T_normals = ti.Vector.field(3, dtype=ti.f32, shape=num_verts)
            T_uvs = ti.Vector.field(2, dtype=ti.f32, shape=num_verts)
            T_indices = ti.field(dtype=ti.i32, shape=num_tris * 3)
            T_projected = ti.Vector.field(6, dtype=ti.f32, shape=num_verts)
            
            T_vertices.from_numpy(np.array(v_list, dtype=np.float32))
            T_normals.from_numpy(np.array(n_list, dtype=np.float32))
            T_uvs.from_numpy(np.array(u_list, dtype=np.float32))
            T_indices.from_numpy(np.array(i_list, dtype=np.int32))
            
            taichi_init_texture()
            print(f"Debug: Nivel 3D with {num_verts} vertices & {num_tris} triangles.")
        else:
            print("Debug: Clean map.")

    def _obj_idx(tok, count):
        if not tok:
            return None
        try:
            i = int(tok)
        except Exception:
            return None
        return i - 1 if i > 0 else count + i

    def load_obj_to_taichi(obj_path, scale=1.0):
        global T_vertices, T_normals, T_uvs, T_indices, T_projected
        global global_num_vertices, global_num_triangles

        if not obj_path or (not os.path.exists(obj_path)):
            print(f"Sayoristein: OBJ not present: {obj_path}")
            global_num_vertices = 0
            global_num_triangles = 0
            return False

        positions = []
        texcoords = []
        normals = []

        v_list = []
        n_list = []
        u_list = []
        i_list = []
        cache = {}

        def get_vertex(tok):
            parts = tok.split("/")
            vi = _obj_idx(parts[0] if len(parts) > 0 else "", len(positions))
            vti = _obj_idx(parts[1] if len(parts) > 1 else "", len(texcoords))
            vni = _obj_idx(parts[2] if len(parts) > 2 else "", len(normals))
            key = (vi, vti, vni)
            if key in cache:
                return cache[key]
            if vi is None or vi < 0 or vi >= len(positions):
                return None

            p = positions[vi]
            uv = [0.0, 0.0]
            if vti is not None and 0 <= vti < len(texcoords):
                uv = texcoords[vti]

            nrm = [0.0, 1.0, 0.0]
            if vni is not None and 0 <= vni < len(normals):
                nrm = normals[vni]

            idx = len(v_list)
            v_list.append([p[0], p[1], p[2]])
            n_list.append([nrm[0], nrm[1], nrm[2]])
            u_list.append([uv[0], uv[1]])
            cache[key] = idx
            return idx

        try:
            with open(obj_path, "r", encoding="utf-8", errors="ignore") as f:
                for raw in f:
                    line = raw.strip()
                    if (not line) or line.startswith("#"):
                        continue
                    parts = line.split()
                    tag = parts[0]
                    if tag == "v" and len(parts) >= 4:
                        positions.append([float(parts[1]), float(parts[2]), float(parts[3])])
                    elif tag == "vt" and len(parts) >= 3:
                        texcoords.append([float(parts[1]), float(parts[2])])
                    elif tag == "vn" and len(parts) >= 4:
                        normals.append([float(parts[1]), float(parts[2]), float(parts[3])])
                    elif tag == "f" and len(parts) >= 4:
                        face = []
                        for tok in parts[1:]:
                            idx = get_vertex(tok)
                            if idx is not None:
                                face.append(idx)
                        if len(face) >= 3:
                            for k in range(1, len(face) - 1):
                                i_list.extend([face[0], face[k], face[k + 1]])
        except Exception as e:
            print(f"Sayoristein: Error leyendo OBJ '{obj_path}': {e}")
            global_num_vertices = 0
            global_num_triangles = 0
            return False

        num_tris = len(i_list) // 3

        num_verts = len(v_list)
        num_tris = len(i_list) // 3
        if num_verts <= 0 or num_tris <= 0:
            print(f"Sayoristein: OBJ sin geometría útil: {obj_path}")
            global_num_vertices = 0
            global_num_triangles = 0
            return False

        v_np = np.array(v_list, dtype=np.float32)
        min_v = v_np.min(axis=0)
        max_v = v_np.max(axis=0)
        center = (min_v + max_v) * 0.5

        v_np[:, 0] = (v_np[:, 0] - center[0]) * scale
        v_np[:, 1] = (v_np[:, 1] - min_v[1]) * scale
        v_np[:, 2] = (v_np[:, 2] - center[2]) * scale

        global_num_vertices = num_verts
        global_num_triangles = num_tris

        T_vertices = ti.Vector.field(3, dtype=ti.f32, shape=num_verts)
        T_normals = ti.Vector.field(3, dtype=ti.f32, shape=num_verts)
        T_uvs = ti.Vector.field(2, dtype=ti.f32, shape=num_verts)
        T_indices = ti.field(dtype=ti.i32, shape=num_tris * 3)
        T_projected = ti.Vector.field(6, dtype=ti.f32, shape=num_verts)

        T_vertices.from_numpy(v_np)
        T_normals.from_numpy(np.array(n_list, dtype=np.float32))
        T_uvs.from_numpy(np.array(u_list, dtype=np.float32))
        T_indices.from_numpy(np.array(i_list, dtype=np.int32))
        taichi_init_texture()

        print(f"Sayoristein: OBJ loaded '{obj_path}' with {num_verts} vertices & {num_tris} triangles.")
        return True


    class TaichiEngineDisplayable(renpy.Displayable):
        def __init__(self, map_grid=None, model_path=None, **kwargs):
            super(TaichiEngineDisplayable, self).__init__(**kwargs)
            qmode = getattr(persistent, "stein_quality_mode", 1)
            if qmode == 0:
                self.render_scale = 0.75
            elif qmode == 1:
                self.render_scale = 0.5
            elif qmode == 2:
                self.render_scale = 0.4
            elif qmode == 3:
                self.render_scale = 0.3
            else:
                self.render_scale = 0.25

            if model_path:
                if qmode == 0:
                    self.render_scale = min(self.render_scale, 0.20)
                elif qmode == 1:
                    self.render_scale = min(self.render_scale, 0.18)
                elif qmode == 2:
                    self.render_scale = min(self.render_scale, 0.16)
                elif qmode == 3:
                    self.render_scale = min(self.render_scale, 0.14)
                else:
                    self.render_scale = min(self.render_scale, 0.12)
            self.res_x = int(1066 * self.render_scale)
            self.res_y = int(600 * self.render_scale)
            
            global T_pixels, T_zbuffer
            T_pixels = ti.Vector.field(n=4, dtype=ti.u8, shape=(self.res_y, self.res_x))
            T_zbuffer = ti.field(dtype=ti.f32, shape=(self.res_y, self.res_x))

            loaded_model = False
            if model_path:
                loaded_model = load_obj_to_taichi(model_path, scale=1.0)
            if not loaded_model:
                load_level_to_taichi(map_grid)
            
            self.player_x = 0.0 if loaded_model else 2.0
            self.player_y = 1.8 if loaded_model else 0.5
            self.player_z = -5.0 if loaded_model else 2.0
            self.player_yaw = 0.0
            self.free_fly = True
            
            self.move_speed = 3.0
            self.rot_speed = 2.0
            self.input_y = 0.0 # Forward/back (-1 to 1)
            self.input_x = 0.0 # Strafe (-1 to 1)
            self.input_r = 0.0 # Turn (-1 to 1)
            self.input_v = 0.0 # Vertical move (-1 to 1)
            self.input_pitch = 0.0 # Look up/down (-1 to 1)
            self.mouse_dx = 0.0
            self.mouse_dy = 0.0
            self.mouse_initialized = False
            self.skip_mouse = False
            self.mouse_sens = 0.10
            self.mouse_pitch_sens = 0.0030
            self.vertical_speed = 3.0
            self.pitch_speed = 1.5
            self.player_pitch = 0.0
            
            self.last_time = time.time()
            self.accumulated_ms = 0.0
            self.frame_count = 0
            self.last_print = time.time()
            
            self.map_w = 0
            self.map_h = 0
            
        def event(self, ev, x, y, st):
            import pygame_sdl2 as pygame
            if not self.mouse_initialized:
                pygame.mouse.set_visible(False)
                pygame.event.set_grab(True)
                pygame.mouse.get_rel() # reset relative delta accumulator
                self.mouse_initialized = True
                self.skip_mouse = True
                return

            if ev.type == pygame.MOUSEMOTION and self.mouse_initialized:
                if getattr(self, "skip_mouse", False):
                    self.skip_mouse = False
                    return
                self.mouse_dx += ev.rel[0]
                self.mouse_dy += ev.rel[1]
                return

            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE and self.mouse_initialized:
                pygame.mouse.set_visible(True)
                pygame.event.set_grab(False)
                self.mouse_initialized = False
                self.mouse_dx = 0.0
                return

        def render(self, width, height, st, at):
            keys = pygame.key.get_pressed()
            self.input_y = 0.0
            self.input_x = 0.0
            self.input_r = 0.0
            self.input_v = 0.0
            self.input_pitch = 0.0
            if keys[pygame.K_w] or keys[pygame.K_UP]: self.input_y -= 1.0
            if keys[pygame.K_s] or keys[pygame.K_DOWN]: self.input_y += 1.0
            if keys[pygame.K_a]: self.input_x += 1.0
            if keys[pygame.K_d]: self.input_x -= 1.0
            if keys[pygame.K_LEFT]: self.input_r += 1.0
            if keys[pygame.K_RIGHT]: self.input_r -= 1.0
            if keys[pygame.K_SPACE]: self.input_v += 1.0
            if keys[pygame.K_LCTRL] or keys[pygame.K_RCTRL]: self.input_v -= 1.0
            if keys[pygame.K_PAGEUP]: self.input_pitch += 1.0
            if keys[pygame.K_PAGEDOWN]: self.input_pitch -= 1.0
            if self.mouse_initialized:
                self.input_r += -(self.mouse_dx * self.mouse_sens)
                self.player_pitch -= (self.mouse_dy * self.mouse_pitch_sens)
            self.mouse_dx = 0.0
            self.mouse_dy = 0.0

            start_time = time.time()
            dt = start_time - self.last_time
            if dt > 0.1: dt = 0.1
            self.last_time = start_time
            
            self.player_yaw += self.input_r * self.rot_speed * dt
            move = self.input_y * self.move_speed * dt
            strafe = self.input_x * self.move_speed * dt
            self.player_x += math.cos(self.player_yaw) * move + math.sin(self.player_yaw) * strafe
            self.player_z += math.sin(self.player_yaw) * move - math.cos(self.player_yaw) * strafe

            self.player_y += self.input_v * self.vertical_speed * dt
            self.player_pitch += self.input_pitch * self.pitch_speed * dt
            max_pitch = 1.20
            if self.player_pitch > max_pitch:
                self.player_pitch = max_pitch
            elif self.player_pitch < -max_pitch:
                self.player_pitch = -max_pitch
            
            if global_num_vertices > 0:
                eye_y = self.player_y + 0.6
                render_yaw = self.player_yaw + (math.pi * 0.5)
                taichi_clear_buffers(self.res_x, self.res_y)
                taichi_process_vertices(self.player_x, eye_y, self.player_z, render_yaw, self.player_pitch,
                                        float(self.res_x), float(self.res_y), global_num_vertices)
                taichi_render_3d(self.res_x, self.res_y, global_num_triangles)
                
            raw_bytes = T_pixels.to_numpy().tobytes()
            
            pg_surf = pygame.Surface((self.res_x, self.res_y), 0, 32)
            pg_surf.from_data(raw_bytes)
            
            if (width, height) != (self.res_x, self.res_y):
                pg_surf = pygame.transform.scale(pg_surf, (width, height))
                
            r = renpy.Render(width, height)
            tex = renpy.display.draw.load_texture(pg_surf)
            r.blit(tex, (0, 0))
            
            end_time = time.time()
            self.accumulated_ms += (end_time - start_time) * 1000.0
            self.frame_count += 1
            if time.time() - self.last_print > 1.0:
                print(f"[Taichi Engine] Frame: {self.accumulated_ms / max(1, self.frame_count):.2f} ms")
                self.accumulated_ms = 0.0
                self.frame_count = 0
                self.last_print = time.time()
            
            renpy.redraw(self, 0.016)
            return r

init python:
    class SteinContainer:
        engine = None

screen taichi_engine_test():
    predict False
    modal True
    key "s" action None
    key "alt_s" action None
    key "K_f" action None
    key "K_LSHIFT" action None
    key "K_RSHIFT" action None
    key "K_LCTRL" action None
    key "K_RCTRL" action None
    key "mouseup_3" action None
    key "K_ESCAPE" action Return("exit")
    
    add SteinContainer.engine

label start_taichi_engine:
    python:
        model_candidates = [
            os.path.join(config.gamedir, "models", "taichi_test.obj"),
            os.path.join(config.gamedir, "models", "sketchfab.obj"),
            os.path.join(config.gamedir, "models", "taichi_test", "scene.obj"),
        ]
        model_path = None
        for p in model_candidates:
            if os.path.exists(p):
                model_path = p
                break

        if not model_path:
            models_root = os.path.join(config.gamedir, "models")
            if os.path.isdir(models_root):
                obj_files = []
                for root, _, files in os.walk(models_root):
                    for fn in files:
                        if fn.lower().endswith(".obj"):
                            obj_files.append(os.path.join(root, fn))
                obj_files.sort()
                if obj_files:
                    model_path = obj_files[0]

        qmode = getattr(persistent, "stein_quality_mode", 1)

        map_source = "none"
        wm = None
        test_level = []
        tried = []

        level_data = getattr(renpy.store, "level4_data", None)
        if model_path:
            map_source = "obj-model"
        else:
            candidates = []
            wm_store = getattr(renpy.store, "worldMap", None)
            if wm_store is not None:
                candidates.append(("store.worldMap", wm_store))

            if isinstance(level_data, dict):
                candidates.append(("store.level4_data", level_data.get("worldMap", None)))

            if hasattr(renpy.store, "load_level_json"):
                candidates.append(("load_level_json(arena.json)", renpy.store.load_level_json("arena.json")))

            for src, candidate in candidates:
                if candidate is None:
                    tried.append((src, "None", 0))
                    continue
                plane = normalize_worldmap_plane(candidate)
                tried.append((src, type(candidate).__name__, len(plane)))
                if plane:
                    wm = candidate
                    test_level = plane
                    map_source = src
                    break

            if map_source == "load_level_json(arena.json)" and isinstance(level_data, dict):
                level_data["worldMap"] = wm

        print("Taichi Engine: map source =", map_source)
        print("Taichi Engine: map attempts =", tried)
        print("Taichi Engine: raw wm type =", type(wm).__name__ if wm is not None else "None")
        if isinstance(wm, dict):
            print("Taichi Engine: raw wm top keys =", list(wm.keys())[:5])
        print("Taichi Engine: normalized rows =", len(test_level))
        if model_path:
            print("Taichi Engine: OBJ model path =", model_path)

        if (not test_level) and (not model_path):
            print("Taichi Engine: clean worldMap/level4_data, using fallback for testing.")
            test_level = [
                [1, 1, 1, 1, 1, 1, 1, 1],
                [1, 0, 0, 0, 0, 0, 0, 1],
                [1, 0, 1, 0, 0, 1, 0, 1],
                [1, 0, 0, 0, 0, 0, 0, 1],
                [1, 0, 0, 0, 0, 0, 0, 1],
                [1, 0, 1, 0, 0, 1, 0, 1],
                [1, 0, 0, 0, 0, 0, 0, 1],
                [1, 1, 1, 1, 1, 1, 1, 1],
            ]

        SteinContainer.engine = TaichiEngineDisplayable(
            map_grid=test_level,
            model_path=model_path
        )

    window hide
    call screen taichi_engine_test()
    window show
    
    python:
        SteinContainer.engine = None
        
    return
