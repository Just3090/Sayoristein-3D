# TaichiEngineDisplayable uses:
#     MeshGameLoop
#     MeshScene
#     TaichiRenderer
 
# This shit does:
#     Setup of Taichi compute kernels
#     Translating MeshScene into VRAM
#     Extracting rendered buffer back to renpy
#     Does not handle game logic

init -5 python:
    import taichi as ti
    import numpy as np
    import pygame_sdl2 as pygame
    import time
    import math
    import ctypes
    import os
    import json
    import struct

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
            
    MAX_RES_X = 1920
    MAX_RES_Y = 1080
    HARD_MAX_TRIS = 10000000
    MAX_TEXTURES = 64

    class TaichiBufferManager:
        def __init__(self):
            self.max_tris = 1000000
            self.max_verts = self.max_tris * 3
            self.fields = {}
            self._allocate_buffers()

        def _allocate_buffers(self):
            self.fields['T_vertices'] = ti.Vector.field(3, dtype=ti.f32, shape=self.max_verts)
            self.fields['T_normals'] = ti.Vector.field(3, dtype=ti.f32, shape=self.max_verts)
            self.fields['T_uvs'] = ti.Vector.field(3, dtype=ti.f32, shape=self.max_verts)
            self.fields['T_cam_space_verts'] = ti.Vector.field(7, dtype=ti.f32, shape=self.max_verts)
            self.fields['T_indices'] = ti.field(dtype=ti.i32, shape=self.max_tris * 3)
            self.fields['T_render_tris'] = ti.Vector.field(7, dtype=ti.f32, shape=self.max_tris * 6)
            self.fields['T_render_tris_count'] = ti.field(dtype=ti.i32, shape=())
            self.fields['T_tri_aabb'] = ti.Vector.field(4, dtype=ti.i32, shape=self.max_tris * 2)
            self.fields['T_tri_area'] = ti.field(dtype=ti.f32, shape=self.max_tris * 2)
            self.fields['T_large_tris'] = ti.field(dtype=ti.i32, shape=self.max_tris * 2)
            self.fields['T_large_tris_count'] = ti.field(dtype=ti.i32, shape=())

        def ensure_capacity(self, required_tris):
            required_verts = required_tris * 3
            if required_tris > self.max_tris or required_verts > self.max_verts:
                new_max_tris = max(required_tris, int(self.max_tris * 1.5))
                if new_max_tris > HARD_MAX_TRIS:
                    print(f"Taichi Engine: Requested tris {required_tris} exceeds HARD_MAX_TRIS {HARD_MAX_TRIS}")
                    new_max_tris = HARD_MAX_TRIS
                
                if new_max_tris == self.max_tris:
                    return

                print(f"Taichi Engine: Resizing buffers. {self.max_tris} -> {new_max_tris}")
                self.max_tris = new_max_tris
                self.max_verts = self.max_tris * 3
                self._allocate_buffers()

    buffer_manager = TaichiBufferManager()

    T_pixels = ti.Vector.field(n=4, dtype=ti.u8, shape=(MAX_RES_Y, MAX_RES_X))
    T_zbuffer = ti.field(dtype=ti.f32, shape=(MAX_RES_Y, MAX_RES_X))
    
    global_tex_w = 2048
    global_tex_h = 2048
    T_texture_data = ti.Vector.field(3, dtype=ti.u8, shape=(MAX_TEXTURES, global_tex_w, global_tex_h))
    
    _texture_registry = {}

    _next_tex_id = 0

    def get_fallback_texture_id():
        global _taichi_texture_loaded
        fallback_path = os.path.join(config.gamedir, "models", "texture.png")
        if fallback_path not in _texture_registry:
            load_texture_to_taichi(fallback_path)
            _taichi_texture_loaded = True
        return _texture_registry.get(fallback_path, 0)

    def load_texture_to_taichi(path):
        global global_tex_w, global_tex_h, _next_tex_id
        
        if path in _texture_registry:
            return _texture_registry[path]
            
        if _next_tex_id >= MAX_TEXTURES:
            print(f"Taichi Engine: Maximum number of textures ({MAX_TEXTURES}) reached. Cannot load {path}.")
            return 0
            
        tex_id = _next_tex_id
        _next_tex_id += 1
        _texture_registry[path] = tex_id
        
        if not os.path.exists(path):
            print(f"Taichi Engine: Texture not found: {path}. Using default gray color.")
            return tex_id
            
        try:
            surf = pygame.image.load(path).convert(24) 
            w, h = surf.get_size()
            
            if w != 2048 or h != 2048:
                surf = pygame.transform.scale(surf, (2048, 2048))
                w, h = 2048, 2048
            
            try:
                tex_data = pygame.image.tostring(surf, "RGB")
                tex_np = np.frombuffer(tex_data, dtype=np.uint8).reshape((h, w, 3))
                tex_np = np.transpose(tex_np, (1, 0, 2))
            except Exception:
                tex_np = np.zeros((w, h, 3), dtype=np.uint8)
                for x in range(w):
                    for y in range(h):
                        c = surf.get_at((x, y))
                        tex_np[x, y] = [c.r, c.g, c.b]
            
            taichi_upload_single_texture(tex_id, tex_np, w, h)
            
            print(f"Taichi Engine: Loaded texture {path} ({w}x{h}) at slot {tex_id}")
            return tex_id
        except Exception as e:
            print(f"Taichi Engine: Error loading texture {path}: {e}")
            return tex_id

            
        try:
            surf = pygame.image.load(path).convert(24) 
            w, h = surf.get_size()
            
            if w != 2048 or h != 2048:
                surf = pygame.transform.scale(surf, (2048, 2048))
                w, h = 2048, 2048
            
                try:
                    tex_data = pygame.image.tostring(surf, "RGB")
                    tex_np = np.frombuffer(tex_data, dtype=np.uint8).reshape((h, w, 3))
                    tex_np = np.transpose(tex_np, (1, 0, 2))
                except Exception:
                    tex_np = np.zeros((w, h, 3), dtype=np.uint8)
                    for x in range(w):
                        for y in range(h):
                            c = surf.get_at((x, y))
                            tex_np[x, y] = [c.r, c.g, c.b]
                
                taichi_upload_single_texture(tex_id, tex_np, w, h)
                
                print(f"Taichi Engine: Loaded texture {path} ({w}x{h}) at slot {tex_id}")
                return tex_id

        except Exception as e:
            print(f"Taichi Engine: Error loading texture {path}: {e}")
            return tex_id

    _taichi_texture_loaded = False

    def taichi_init_texture():
        global _taichi_texture_loaded
        if _taichi_texture_loaded:
            return
        get_fallback_texture_id()

    @ti.kernel
    def taichi_upload_single_texture(tex_id: ti.i32, img_data: ti.types.ndarray(), w: ti.i32, h: ti.i32):
        for x, y in ti.ndrange(2048, 2048):
            if x < w and y < h:
                T_texture_data[tex_id, x, y] = ti.Vector([img_data[x, y, 0], img_data[x, y, 1], img_data[x, y, 2]])
            else:
                T_texture_data[tex_id, x, y] = ti.Vector([ti.cast(200, ti.u8), ti.cast(200, ti.u8), ti.cast(200, ti.u8)])

    @ti.func
    def edge_function(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

    @ti.kernel
    def taichi_process_vertices(T_vertices: ti.template(), T_normals: ti.template(), T_uvs: ti.template(), T_cam_space_verts: ti.template(), cam_x: ti.f32, cam_y: ti.f32, cam_z: ti.f32, cam_yaw: ti.f32, cam_pitch: ti.f32, res_x: ti.f32, res_y: ti.f32, total_verts: ti.i32):
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
            
            T_cam_space_verts[i] = ti.Vector([rx, ry, rz, u_v[0], u_v[1], intensity, u_v[2]])

    @ti.kernel
    def taichi_clip_triangles(T_indices: ti.template(), T_cam_space_verts: ti.template(), T_render_tris_count: ti.template(), T_render_tris: ti.template(), res_x: ti.f32, res_y: ti.f32, total_tris: ti.i32):
        T_render_tris_count[None] = 0
        fov = res_y * 0.8
        near = 0.1
        
        for t_idx in range(total_tris):
            i0 = T_indices[t_idx * 3]
            i1 = T_indices[t_idx * 3 + 1]
            i2 = T_indices[t_idx * 3 + 2]
            
            v0 = T_cam_space_verts[i0]
            v1 = T_cam_space_verts[i2]
            v2 = T_cam_space_verts[i1]
            
            in_count = 0
            if v0[2] >= near: in_count += 1
            if v1[2] >= near: in_count += 1
            if v2[2] >= near: in_count += 1
            
            if in_count == 3:
                idx = ti.atomic_add(T_render_tris_count[None], 1)
                base = idx * 3
                
                inv_z0 = 1.0 / v0[2]; px0 = v0[0] * fov * inv_z0 + res_x * 0.5; py0 = v0[1] * fov * inv_z0 + res_y * 0.5
                inv_z1 = 1.0 / v1[2]; px1 = v1[0] * fov * inv_z1 + res_x * 0.5; py1 = v1[1] * fov * inv_z1 + res_y * 0.5
                inv_z2 = 1.0 / v2[2]; px2 = v2[0] * fov * inv_z2 + res_x * 0.5; py2 = v2[1] * fov * inv_z2 + res_y * 0.5
                
                T_render_tris[base] = ti.Vector([px0, py0, inv_z0, v0[3] * inv_z0, v0[4] * inv_z0, v0[5], v0[6]])
                T_render_tris[base+1] = ti.Vector([px1, py1, inv_z1, v1[3] * inv_z1, v1[4] * inv_z1, v1[5], v1[6]])
                T_render_tris[base+2] = ti.Vector([px2, py2, inv_z2, v2[3] * inv_z2, v2[4] * inv_z2, v2[5], v2[6]])
            
            elif in_count == 1:
                in_v = v0; out1 = v1; out2 = v2
                if v1[2] >= near:
                    in_v = v1; out1 = v2; out2 = v0
                elif v2[2] >= near:
                    in_v = v2; out1 = v0; out2 = v1
                
                t1 = (near - in_v[2]) / (out1[2] - in_v[2])
                t2 = (near - in_v[2]) / (out2[2] - in_v[2])
                
                new_v1 = in_v + t1 * (out1 - in_v)
                new_v2 = in_v + t2 * (out2 - in_v)
                
                idx = ti.atomic_add(T_render_tris_count[None], 1)
                base = idx * 3
                
                inv_z0 = 1.0 / in_v[2]; px0 = in_v[0] * fov * inv_z0 + res_x * 0.5; py0 = in_v[1] * fov * inv_z0 + res_y * 0.5
                inv_z1 = 1.0 / new_v1[2]; px1 = new_v1[0] * fov * inv_z1 + res_x * 0.5; py1 = new_v1[1] * fov * inv_z1 + res_y * 0.5
                inv_z2 = 1.0 / new_v2[2]; px2 = new_v2[0] * fov * inv_z2 + res_x * 0.5; py2 = new_v2[1] * fov * inv_z2 + res_y * 0.5
                
                T_render_tris[base] = ti.Vector([px0, py0, inv_z0, in_v[3] * inv_z0, in_v[4] * inv_z0, in_v[5], in_v[6]])
                T_render_tris[base+1] = ti.Vector([px1, py1, inv_z1, new_v1[3] * inv_z1, new_v1[4] * inv_z1, new_v1[5], in_v[6]])
                T_render_tris[base+2] = ti.Vector([px2, py2, inv_z2, new_v2[3] * inv_z2, new_v2[4] * inv_z2, new_v2[5], in_v[6]])
            
            elif in_count == 2:
                out_v = v0; in1 = v1; in2 = v2
                if v1[2] < near:
                    out_v = v1; in1 = v2; in2 = v0
                elif v2[2] < near:
                    out_v = v2; in1 = v0; in2 = v1
                
                t1 = (near - in1[2]) / (out_v[2] - in1[2])
                t2 = (near - in2[2]) / (out_v[2] - in2[2])
                
                new_v1 = in1 + t1 * (out_v - in1)
                new_v2 = in2 + t2 * (out_v - in2)
                
                idx = ti.atomic_add(T_render_tris_count[None], 2)
                base1 = idx * 3
                base2 = (idx + 1) * 3
                
                inv_z0 = 1.0 / in1[2]; px0 = in1[0] * fov * inv_z0 + res_x * 0.5; py0 = in1[1] * fov * inv_z0 + res_y * 0.5
                inv_z1 = 1.0 / new_v1[2]; px1 = new_v1[0] * fov * inv_z1 + res_x * 0.5; py1 = new_v1[1] * fov * inv_z1 + res_y * 0.5
                inv_z2 = 1.0 / in2[2]; px2 = in2[0] * fov * inv_z2 + res_x * 0.5; py2 = in2[1] * fov * inv_z2 + res_y * 0.5
                inv_z3 = 1.0 / new_v2[2]; px3 = new_v2[0] * fov * inv_z3 + res_x * 0.5; py3 = new_v2[1] * fov * inv_z3 + res_y * 0.5
                
                T_render_tris[base1]   = ti.Vector([px0, py0, inv_z0, in1[3] * inv_z0, in1[4] * inv_z0, in1[5], in1[6]])
                T_render_tris[base1+1] = ti.Vector([px2, py2, inv_z2, in2[3] * inv_z2, in2[4] * inv_z2, in2[5], in1[6]])
                T_render_tris[base1+2] = ti.Vector([px1, py1, inv_z1, new_v1[3] * inv_z1, new_v1[4] * inv_z1, new_v1[5], in1[6]])
                
                T_render_tris[base2]   = ti.Vector([px1, py1, inv_z1, new_v1[3] * inv_z1, new_v1[4] * inv_z1, new_v1[5], in1[6]])
                T_render_tris[base2+1] = ti.Vector([px2, py2, inv_z2, in2[3] * inv_z2, in2[4] * inv_z2, in2[5], in1[6]])
                T_render_tris[base2+2] = ti.Vector([px3, py3, inv_z3, new_v2[3] * inv_z3, new_v2[4] * inv_z3, new_v2[5], in1[6]])

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
    def taichi_render_small_tris(T_render_tris_count: ti.template(), T_render_tris: ti.template(), T_large_tris_count: ti.template(), T_large_tris: ti.template(), T_tri_aabb: ti.template(), T_tri_area: ti.template(), T_zbuffer: ti.template(), T_pixels: ti.template(), T_texture_data: ti.template(), res_x: ti.i32, res_y: ti.i32):
        T_large_tris_count[None] = 0
        
        for t_idx in range(T_render_tris_count[None]):
            v0 = T_render_tris[t_idx * 3]
            v1 = T_render_tris[t_idx * 3 + 1]
            v2 = T_render_tris[t_idx * 3 + 2]
            
            area = edge_function(v0, v1, v2)
            if area <= 0.0:
                continue
            
            min_x = ti.max(0, ti.cast(ti.floor(ti.min(ti.min(v0[0], v1[0]), v2[0])), ti.i32))
            max_x = ti.min(res_x - 1, ti.cast(ti.ceil(ti.max(ti.max(v0[0], v1[0]), v2[0])), ti.i32))
            min_y = ti.max(0, ti.cast(ti.floor(ti.min(ti.min(v0[1], v1[1]), v2[1])), ti.i32))
            max_y = ti.min(res_y - 1, ti.cast(ti.ceil(ti.max(ti.max(v0[1], v1[1]), v2[1])), ti.i32))
            
            box_w = max_x - min_x
            box_h = max_y - min_y
            
            if box_w < 0 or box_h < 0:
                continue
                
            if box_w * box_h > 10000:
                idx = ti.atomic_add(T_large_tris_count[None], 1)
                T_large_tris[idx] = t_idx
                T_tri_aabb[t_idx] = ti.Vector([min_x, max_x, min_y, max_y])
                T_tri_area[t_idx] = area
            else:
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
        
                            if z > 0.05:
                                old_z = ti.atomic_min(T_zbuffer[j, px], z)
                                if z <= old_z:
                                    u_z = w0_n * v0[3] + w1_n * v1[3] + w2_n * v2[3]
                                    v_z = w0_n * v0[4] + w1_n * v1[4] + w2_n * v2[4]
                                    tex_u = u_z * z
                                    tex_v = v_z * z
                                    final_intensity = w0_n * v0[5] + w1_n * v1[5] + w2_n * v2[5]
        
                                    u_frac = tex_u - ti.floor(tex_u)
                                    v_frac = tex_v - ti.floor(tex_v)
                                    
                                    tu_idx = ti.cast(u_frac * ti.cast(global_tex_w - 1, ti.f32), ti.i32)
                                    tv_idx = ti.cast((1.0 - v_frac) * ti.cast(global_tex_h - 1, ti.f32), ti.i32)
                                    tex_id = ti.cast(v0[6], ti.i32)
                                    
                                    color = T_texture_data[tex_id, tu_idx, tv_idx]
        
                                    T_pixels[j, px] = [
                                        ti.cast(ti.cast(color[0], ti.f32) * final_intensity, ti.u8),
                                        ti.cast(ti.cast(color[1], ti.f32) * final_intensity, ti.u8),
                                        ti.cast(ti.cast(color[2], ti.f32) * final_intensity, ti.u8),
                                        ti.cast(255, ti.u8)
                                    ]

    @ti.kernel
    def taichi_render_large_tris(T_large_tris_count: ti.template(), T_large_tris: ti.template(), T_tri_aabb: ti.template(), T_tri_area: ti.template(), T_render_tris: ti.template(), T_zbuffer: ti.template(), T_pixels: ti.template(), T_texture_data: ti.template(), res_x: ti.i32, res_y: ti.i32):
        num_large = T_large_tris_count[None]
        for px, py in ti.ndrange(res_x, res_y):
            j = res_y - 1 - py
            p = ti.Vector([float(px), float(py)])
            
            for l_i in range(num_large):
                t_idx = T_large_tris[l_i]
                
                aabb = T_tri_aabb[t_idx]
                if px < aabb[0] or px > aabb[1] or py < aabb[2] or py > aabb[3]:
                    continue
                    
                area = T_tri_area[t_idx]
                
                v0 = T_render_tris[t_idx * 3]
                v1 = T_render_tris[t_idx * 3 + 1]
                v2 = T_render_tris[t_idx * 3 + 2]
                
                w0 = edge_function(v1, v2, p)
                w1 = edge_function(v2, v0, p)
                w2 = edge_function(v0, v1, p)
                
                if w0 >= 0.0 and w1 >= 0.0 and w2 >= 0.0:
                    w0_n = w0 / area
                    w1_n = w1 / area
                    w2_n = w2 / area
                    inv_z = w0_n * v0[2] + w1_n * v1[2] + w2_n * v2[2]
                    z = 1.0 / inv_z
                    
                    if z > 0.05:
                        old_z = ti.atomic_min(T_zbuffer[j, px], z)
                        if z <= old_z:
                            u_z = w0_n * v0[3] + w1_n * v1[3] + w2_n * v2[3]
                            v_z = w0_n * v0[4] + w1_n * v1[4] + w2_n * v2[4]
                            tex_u = u_z * z
                            tex_v = v_z * z
                            final_intensity = w0_n * v0[5] + w1_n * v1[5] + w2_n * v2[5]
        
                            u_frac = tex_u - ti.floor(tex_u)
                            v_frac = tex_v - ti.floor(tex_v)
                            
                            tu_idx = ti.cast(u_frac * ti.cast(global_tex_w - 1, ti.f32), ti.i32)
                            tv_idx = ti.cast((1.0 - v_frac) * ti.cast(global_tex_h - 1, ti.f32), ti.i32)
                            tex_id = ti.cast(v0[6], ti.i32)
                            
                            color = T_texture_data[tex_id, tu_idx, tv_idx]
        
                            T_pixels[j, px] = [
                                ti.cast(ti.cast(color[0], ti.f32) * final_intensity, ti.u8),
                                ti.cast(ti.cast(color[1], ti.f32) * final_intensity, ti.u8),
                                ti.cast(ti.cast(color[2], ti.f32) * final_intensity, ti.u8),
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

    def get_level_geometry(map_grid):
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
            u_list.extend([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0]])
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
        
        return np.array(v_list, dtype=np.float32), np.array(n_list, dtype=np.float32), np.array(u_list, dtype=np.float32), np.array(i_list, dtype=np.int32)


    def get_model_texture_id(model_path):
        tex_path = os.path.join(os.path.dirname(model_path), "texture.png")
        if os.path.exists(tex_path):
            return float(load_texture_to_taichi(tex_path))
        return float(get_fallback_texture_id())

    _global_obj_geometry_cache = {}

    def load_stein_model(npz_path, scale=1.0, tex_id=0.0):
        """
        Load for pre compiled files in our numpy compressed method (.npz).
        """
        if not os.path.exists(npz_path):
            print(f"Taichi Engine: Model not found: {npz_path}")
            return np.array([]), np.array([]), np.array([]), np.array([]), np.array([]), np.array([])

        cache_key = (npz_path, scale, tex_id)
        if cache_key in _global_obj_geometry_cache:
            return _global_obj_geometry_cache[cache_key]

        try:
            data = np.load(npz_path)
            v_np = data["v"].copy().astype(np.float32)
            n_np = data["n"].copy().astype(np.float32)
            u_np = data["u"].copy().astype(np.float32)
            i_np = data["i"].copy().astype(np.int32)
            j_np = data["j"].copy().astype(np.int32)
            w_np = data["w"].copy().astype(np.float32)
            
            if scale != 1.0:
                min_v = v_np.min(axis=0)
                max_v = v_np.max(axis=0)
                center = (min_v + max_v) * 0.5
                v_np[:, 0] = (v_np[:, 0] - center[0]) * scale
                v_np[:, 1] = (v_np[:, 1] - min_v[1]) * scale
                v_np[:, 2] = (v_np[:, 2] - center[2]) * scale
                
            tex_col = np.full((u_np.shape[0], 1), tex_id, dtype=np.float32)
            u_np = np.hstack((u_np, tex_col))

            _global_obj_geometry_cache[cache_key] = (v_np, n_np, u_np, i_np, j_np, w_np)
            return v_np, n_np, u_np, i_np, j_np, w_np
    
        except Exception as e:
            print(f"Taichi Engine: Failed to load {npz_path}: {e}")
            return np.array([]), np.array([]), np.array([]), np.array([]), np.array([]), np.array([])


        cache_key = (npz_path, scale, tex_id)
        if cache_key in _global_obj_geometry_cache:
            c_v, c_n, c_u, c_i, c_j, c_w = _global_obj_geometry_cache[cache_key]
            return list(c_v), list(c_n), list(c_u), list(c_i), list(c_j), list(c_w)

        try:
            data = np.load(npz_path)
            v_np = data["v"].copy()
            n_list = data["n"].tolist()
            u_np = data["u"].copy()
            i_list = data["i"].tolist()
            j_list = data["j"].tolist()
            w_list = data["w"].tolist()
            
            if scale != 1.0:
                min_v = v_np.min(axis=0)
                max_v = v_np.max(axis=0)
                center = (min_v + max_v) * 0.5
                v_np[:, 0] = (v_np[:, 0] - center[0]) * scale
                v_np[:, 1] = (v_np[:, 1] - min_v[1]) * scale
                v_np[:, 2] = (v_np[:, 2] - center[2]) * scale
                
            tex_col = np.full((u_np.shape[0], 1), tex_id, dtype=np.float32)
            u_np = np.hstack((u_np, tex_col))

            v_list = v_np.tolist()
            u_list = u_np.tolist()

            _global_obj_geometry_cache[cache_key] = (v_np, n_np, u_np, i_np, j_np, w_np)
            return v_np, n_np, u_np, i_np, j_np, w_np

        except Exception as e:
            print(f"Taichi Engine: Failed to load {npz_path}: {e}")
            return [], [], [], [], [],[]

    TAICHI_DEBUG_CAMERA_INPUT = False


    class TaichiRenderer(object):
        """
        Handles the Taichi rasterization pipeline (GPU compute).
        """
        def __init__(self):
            self.res_x = 1066
            self.res_y = 600
            self.render_scale = 1.0
            self.editor_viewport_res = None
            self.last_qmode = getattr(persistent, "stein_quality_mode", 1)

        def reapply_quality(self, scene):
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

            if scene.model_path:
                if qmode == 0:
                    self.render_scale = min(self.render_scale, 1.0)
                elif qmode == 1:
                    self.render_scale = min(self.render_scale, 0.50)
                elif qmode == 2:
                    self.render_scale = min(self.render_scale, 0.25)
                elif qmode == 3:
                    self.render_scale = min(self.render_scale, 0.14)
                else:
                    self.render_scale = min(self.render_scale, 0.12)

            self.res_x = int(1066 * self.render_scale)
            self.res_y = int(600 * self.render_scale)

            ov = self.editor_viewport_res
            if ov is not None:
                ow, oh = ov
                if ow and oh:
                    self.res_x = int(ow)
                    self.res_y = int(oh)

            self._upload_scene_to_gpu(scene)
            self.last_qmode = qmode
            print("Taichi Engine: Applied quality mode {}, resolution {}x{}".format(qmode, self.res_x, self.res_y))

        def _upload_scene_to_gpu(self, scene):
            v_np = scene.raw_v
            n_np = scene.raw_n
            u_np = scene.raw_u
            i_np = scene.raw_i
            
            num_tris = len(i_np) // 3
            buffer_manager.ensure_capacity(num_tris)
            
            scene.num_vertices = len(v_np)
            scene.num_triangles = num_tris
            
            scene.v_np = v_np
            scene.i_np = i_np
            
            v_np_resized = np.zeros((buffer_manager.max_verts, 3), dtype=np.float32)
            n_np_resized = np.zeros((buffer_manager.max_verts, 3), dtype=np.float32)
            u_np_resized = np.zeros((buffer_manager.max_verts, 3), dtype=np.float32)
            i_np_resized = np.zeros((buffer_manager.max_tris * 3,), dtype=np.int32)
            
            if len(v_np) > 0:
                v_np_resized[:len(v_np)] = v_np
                n_np_resized[:len(n_np)] = n_np
                u_np_resized[:len(u_np)] = u_np
            if len(i_np) > 0:
                i_np_resized[:len(i_np)] = i_np
            
            buffer_manager.fields['T_vertices'].from_numpy(v_np_resized)
            buffer_manager.fields['T_normals'].from_numpy(n_np_resized)
            buffer_manager.fields['T_uvs'].from_numpy(u_np_resized)
            buffer_manager.fields['T_indices'].from_numpy(i_np_resized)
            
            taichi_init_texture()


        def draw(self, scene, pose, width, height):
            cur_q = getattr(persistent, "stein_quality_mode", 1)
            if cur_q != self.last_qmode:
                self.reapply_quality(scene)
            
            if scene.num_vertices > 0:
                eye_y = pose.player_y + 1.7
                render_yaw = pose.player_yaw + (math.pi * 0.5)
                taichi_clear_buffers(self.res_x, self.res_y)
                
                fields = buffer_manager.fields
                taichi_process_vertices(
                    fields['T_vertices'], fields['T_normals'], fields['T_uvs'], fields['T_cam_space_verts'],
                    pose.player_x, eye_y, pose.player_z, render_yaw, pose.player_pitch,
                    float(self.res_x), float(self.res_y), scene.num_vertices,
                )
                taichi_clip_triangles(
                    fields['T_indices'], fields['T_cam_space_verts'], fields['T_render_tris_count'], fields['T_render_tris'],
                    float(self.res_x), float(self.res_y), scene.num_triangles
                )
                taichi_render_small_tris(
                    fields['T_render_tris_count'], fields['T_render_tris'], fields['T_large_tris_count'], fields['T_large_tris'], 
                    fields['T_tri_aabb'], fields['T_tri_area'], T_zbuffer, T_pixels, T_texture_data,
                    self.res_x, self.res_y
                )
                taichi_render_large_tris(
                    fields['T_large_tris_count'], fields['T_large_tris'], fields['T_tri_aabb'], fields['T_tri_area'], 
                    fields['T_render_tris'], T_zbuffer, T_pixels, T_texture_data,
                    self.res_x, self.res_y
                )
            
            full_array = T_pixels.to_numpy()

            active_slice = full_array[:self.res_y, :self.res_x]
            contig_slice = np.ascontiguousarray(active_slice)
            raw_bytes = contig_slice.tobytes()

            pg_surf = pygame.Surface((self.res_x, self.res_y), 0, 32)
            try:
                pg_surf.from_data(raw_bytes)
            except Exception as e:
                print(
                    "Error in from_data! res_x={}, res_y={}, array shape={}, bytes len={}".format(
                        self.res_x, self.res_y, contig_slice.shape, len(raw_bytes),
                    )
                )
                raise e

            if (width, height) != (self.res_x, self.res_y):
                pg_surf = pygame.transform.scale(pg_surf, (width, height))

            r = renpy.Render(width, height)
            tex = renpy.display.draw.load_texture(pg_surf)
            r.blit(tex, (0, 0))
            return r

    class TaichiEngineDisplayable(renpy.Displayable):
        """
        RenPy displayable wrapper that ties together the Renderer, Scene, and GameLoop.
        """
        def __init__(self, map_grid=None, model_path=None, mesh_map=None, gameplay=False, **kwargs):
            super(TaichiEngineDisplayable, self).__init__(**kwargs)

            self.scene = MeshScene(mesh_map=mesh_map, model_path=model_path, map_grid=map_grid)
            self.renderer = TaichiRenderer()
            self.renderer.reapply_quality(self.scene)
            self.loop = MeshGameLoop(self.scene, gameplay=gameplay)

            self.last_time = time.time()
            self.accumulated_ms = 0.0
            self.frame_count = 0
            self.last_print = time.time()

        def load_mesh_map(self, mesh_map):
            self.scene.load_mesh_map(mesh_map)
            self.renderer.reapply_quality(self.scene)

        def reapply_quality(self):
            self.renderer.reapply_quality(self.scene)

        def set_viewport_res(self, w, h):
            new_tup = (int(w), int(h))
            if self.renderer.editor_viewport_res != new_tup:
                self.renderer.editor_viewport_res = new_tup
                self.renderer.reapply_quality(self.scene)

        def event(self, ev, x, y, st):
            return self.loop.event(ev, x, y, st)

        def render(self, width, height, st, at):
            start_time = time.time()
            dt = start_time - self.last_time
            if dt > 0.1:
                dt = 0.1
            self.last_time = start_time

            self.loop.update(dt)
            r = self.renderer.draw(self.scene, self.loop, width, height)

            end_time = time.time()
            self.accumulated_ms += (end_time - start_time) * 1000.0
            self.frame_count += 1
            if time.time() - self.last_print > 1.0:
                print("[Taichi Engine] Frame: {:.2f} ms".format(self.accumulated_ms / max(1, self.frame_count)))
                if TAICHI_DEBUG_CAMERA_INPUT:
                    gp_rmb = None
                    try:
                        gp_rmb = bool(pygame.mouse.get_pressed()[2])
                    except Exception as e:
                        gp_rmb = "err:{}".format(e)
                    print(
                        "[Taichi cam debug] render tick rmb_down={} mouse_init={} pygame_pressed_rmb={} yaw={:.4f} pitch={:.4f} xyz=({:.2f},{:.2f},{:.2f})".format(
                            self.loop.rmb_down, self.loop.mouse_initialized, gp_rmb,
                            self.loop.player_yaw, self.loop.player_pitch,
                            self.loop.player_x, self.loop.player_y, self.loop.player_z,
                        )
                    )
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
