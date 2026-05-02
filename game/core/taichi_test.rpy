# init python:
#     import taichi as ti
#     import numpy as np
#     import pygame_sdl2 as pygame
#     import time
#     import math

#     try:
#         ti.init(arch=ti.vulkan)
#     except:
#         ti.init(arch=ti.gpu) # Fallback

#     res_x, res_y = 1066, 600
#     pixels = ti.Vector.field(n=4, dtype=ti.u8, shape=(res_y, res_x))

#     num_vertices = 24
#     num_triangles = 12

#     vertices = ti.Vector.field(3, dtype=ti.f32, shape=num_vertices)
#     normals = ti.Vector.field(3, dtype=ti.f32, shape=num_vertices)
#     uvs = ti.Vector.field(2, dtype=ti.f32, shape=num_vertices)
#     indices = ti.field(dtype=ti.i32, shape=num_triangles * 3)

#     # projected_vertices: [px, py, 1/z, u/z, v/z, intensity] -> length 6
#     projected_vertices = ti.Vector.field(6, dtype=ti.f32, shape=num_vertices)
    
#     tex_w, tex_h = 256, 256
#     texture_data = ti.Vector.field(3, dtype=ti.u8, shape=(tex_w, tex_h))

#     @ti.kernel
#     def init_texture():
#         for i, j in texture_data:
#             c_x = i // 32
#             c_y = j // 32
#             if (c_x + c_y) % 2 == 0:
#                 texture_data[i, j] = [ti.cast(255, ti.u8), ti.cast(255, ti.u8), ti.cast(255, ti.u8)]
#             else:
#                 texture_data[i, j] = [ti.cast(150, ti.u8), ti.cast(0, ti.u8), ti.cast(0, ti.u8)]

#     init_texture()

#     @ti.kernel
#     def init_mesh():
#         # Face 0: Frontal
#         vertices[0] = [-1.0, -1.0, -1.0]; uvs[0] = [0.0, 0.0]; normals[0] = [0.0, 0.0, -1.0]
#         vertices[1] = [ 1.0, -1.0, -1.0]; uvs[1] = [1.0, 0.0]; normals[1] = [0.0, 0.0, -1.0]
#         vertices[2] = [ 1.0,  1.0, -1.0]; uvs[2] = [1.0, 1.0]; normals[2] = [0.0, 0.0, -1.0]
#         vertices[3] = [-1.0,  1.0, -1.0]; uvs[3] = [0.0, 1.0]; normals[3] = [0.0, 0.0, -1.0]
#         indices[0], indices[1], indices[2] = 0, 1, 2
#         indices[3], indices[4], indices[5] = 2, 3, 0

#         # Face 1: Back
#         vertices[4] = [ 1.0, -1.0,  1.0]; uvs[4] = [0.0, 0.0]; normals[4] = [0.0, 0.0, 1.0]
#         vertices[5] = [-1.0, -1.0,  1.0]; uvs[5] = [1.0, 0.0]; normals[5] = [0.0, 0.0, 1.0]
#         vertices[6] = [-1.0,  1.0,  1.0]; uvs[6] = [1.0, 1.0]; normals[6] = [0.0, 0.0, 1.0]
#         vertices[7] = [ 1.0,  1.0,  1.0]; uvs[7] = [0.0, 1.0]; normals[7] = [0.0, 0.0, 1.0]
#         indices[6], indices[7], indices[8] = 4, 5, 6
#         indices[9], indices[10], indices[11] = 6, 7, 4

#         # Face 2: Left
#         vertices[8] = [-1.0, -1.0,  1.0]; uvs[8] = [0.0, 0.0]; normals[8] = [-1.0, 0.0, 0.0]
#         vertices[9] = [-1.0, -1.0, -1.0]; uvs[9] = [1.0, 0.0]; normals[9] = [-1.0, 0.0, 0.0]
#         vertices[10]= [-1.0,  1.0, -1.0]; uvs[10]= [1.0, 1.0]; normals[10]= [-1.0, 0.0, 0.0]
#         vertices[11]= [-1.0,  1.0,  1.0]; uvs[11]= [0.0, 1.0]; normals[11]= [-1.0, 0.0, 0.0]
#         indices[12], indices[13], indices[14] = 8, 9, 10
#         indices[15], indices[16], indices[17] = 10, 11, 8

#         # Face 3: Right
#         vertices[12] = [ 1.0, -1.0, -1.0]; uvs[12] = [0.0, 0.0]; normals[12] = [1.0, 0.0, 0.0]
#         vertices[13] = [ 1.0, -1.0,  1.0]; uvs[13] = [1.0, 0.0]; normals[13] = [1.0, 0.0, 0.0]
#         vertices[14] = [ 1.0,  1.0,  1.0]; uvs[14] = [1.0, 1.0]; normals[14] = [1.0, 0.0, 0.0]
#         vertices[15] = [ 1.0,  1.0, -1.0]; uvs[15] = [0.0, 1.0]; normals[15] = [1.0, 0.0, 0.0]
#         indices[18], indices[19], indices[20] = 12, 13, 14
#         indices[21], indices[22], indices[23] = 14, 15, 12

#         # Face 4: Upper
#         vertices[16] = [-1.0,  1.0, -1.0]; uvs[16] = [0.0, 0.0]; normals[16] = [0.0, 1.0, 0.0]
#         vertices[17] = [ 1.0,  1.0, -1.0]; uvs[17] = [1.0, 0.0]; normals[17] = [0.0, 1.0, 0.0]
#         vertices[18] = [ 1.0,  1.0,  1.0]; uvs[18] = [1.0, 1.0]; normals[18] = [0.0, 1.0, 0.0]
#         vertices[19] = [-1.0,  1.0,  1.0]; uvs[19] = [0.0, 1.0]; normals[19] = [0.0, 1.0, 0.0]
#         indices[24], indices[25], indices[26] = 16, 17, 18
#         indices[27], indices[28], indices[29] = 18, 19, 16

#         # Face 5: Bottom
#         vertices[20] = [-1.0, -1.0,  1.0]; uvs[20] = [0.0, 0.0]; normals[20] = [0.0, -1.0, 0.0]
#         vertices[21] = [ 1.0, -1.0,  1.0]; uvs[21] = [1.0, 0.0]; normals[21] = [0.0, -1.0, 0.0]
#         vertices[22] = [ 1.0, -1.0, -1.0]; uvs[22] = [1.0, 1.0]; normals[22] = [0.0, -1.0, 0.0]
#         vertices[23] = [-1.0, -1.0, -1.0]; uvs[23] = [0.0, 1.0]; normals[23] = [0.0, -1.0, 0.0]
#         indices[30], indices[31], indices[32] = 20, 21, 22
#         indices[33], indices[34], indices[35] = 22, 23, 20

#     init_mesh()

#     @ti.func
#     def edge_function(a, b, c):
#         return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

#     @ti.kernel
#     def process_vertices(cam_x: ti.f32, cam_y: ti.f32, cam_z: ti.f32, cam_yaw: ti.f32):
#         light_dir = ti.Vector([0.5, 0.8, -0.3])
#         l_len = ti.sqrt(light_dir[0]**2 + light_dir[1]**2 + light_dir[2]**2)
#         light_dir = ti.Vector([light_dir[0]/l_len, light_dir[1]/l_len, light_dir[2]/l_len])

#         for i in range(num_vertices):
#             v = vertices[i]
#             n = normals[i]
#             u_v = uvs[i]
            
#             dot_l = n[0] * light_dir[0] + n[1] * light_dir[1] + n[2] * light_dir[2]
#             # Mapear la luz (Ambient light de 0.3, max 1.0)
#             intensity = ti.max(0.0, dot_l) * 0.7 + 0.3
            
#             tx = v[0] - cam_x
#             ty = v[1] - cam_y
#             tz = v[2] - cam_z
            
#             c_y = ti.cos(-cam_yaw)
#             s_y = ti.sin(-cam_yaw)
#             rx = tx * c_y - tz * s_y
#             rz = tx * s_y + tz * c_y
#             ry = ty
            
#             fov = res_y * 0.8
#             px = 0.0
#             py = 0.0
#             inv_z = 0.0
            
#             if rz > 0.1:
#                 inv_z = 1.0 / rz
#                 px = rx * fov * inv_z + res_x * 0.5
#                 py = ry * fov * inv_z + res_y * 0.5
            
#             projected_vertices[i] = ti.Vector([px, py, inv_z, u_v[0] * inv_z, u_v[1] * inv_z, intensity])

#     @ti.kernel
#     def render_3d():
#         for j, i in pixels:
#             math_y = float(res_y - 1 - j)
#             p = ti.Vector([float(i), math_y])
            
#             closest_z = 1e10
#             hit = False
#             tex_u, tex_v = 0.0, 0.0
#             final_intensity = 0.0
            
#             for t_idx in range(num_triangles):
#                 i0 = indices[t_idx * 3]
#                 i1 = indices[t_idx * 3 + 1]
#                 i2 = indices[t_idx * 3 + 2]
                
#                 v0 = projected_vertices[i0]
#                 v1 = projected_vertices[i1]
#                 v2 = projected_vertices[i2]
                
#                 if v0[2] > 0.0 and v1[2] > 0.0 and v2[2] > 0.0:
#                     area = edge_function(v0, v1, v2)
#                     if area > 0.0:
#                         w0 = edge_function(v1, v2, p)
#                         w1 = edge_function(v2, v0, p)
#                         w2 = edge_function(v0, v1, p)
                        
#                         if w0 >= 0.0 and w1 >= 0.0 and w2 >= 0.0:
#                             w0_n = w0 / area
#                             w1_n = w1 / area
#                             w2_n = w2 / area
                            
#                             inv_z = w0_n * v0[2] + w1_n * v1[2] + w2_n * v2[2]
#                             z = 1.0 / inv_z
                            
#                             if z < closest_z and z > 0.1:
#                                 closest_z = z
#                                 hit = True
                                
#                                 u_z = w0_n * v0[3] + w1_n * v1[3] + w2_n * v2[3]
#                                 v_z = w0_n * v0[4] + w1_n * v1[4] + w2_n * v2[4]
                                
#                                 tex_u = u_z * z
#                                 tex_v = v_z * z
#                                 final_intensity = w0_n * v0[5] + w1_n * v1[5] + w2_n * v2[5]
            
#             if hit:
#                 tu_abs = ti.abs(tex_u)
#                 tv_abs = ti.abs(tex_v)
                
#                 tu_idx = ti.cast(tu_abs * float(tex_w - 1), ti.i32) % tex_w
#                 tv_idx = ti.cast(tv_abs * float(tex_h - 1), ti.i32) % tex_h
                
#                 color = texture_data[tu_idx, tv_idx]
                
#                 pixels[j, i] = [
#                     ti.cast(float(color[0]) * final_intensity, ti.u8), 
#                     ti.cast(float(color[1]) * final_intensity, ti.u8), 
#                     ti.cast(float(color[2]) * final_intensity, ti.u8), 
#                     ti.cast(255, ti.u8)]
#             else:
#                 pixels[j, i] = [ti.cast(20, ti.u8), ti.cast(20, ti.u8), ti.cast(25, ti.u8), ti.cast(255, ti.u8)]


#     class TaichiDisplayable(renpy.Displayable):
#         def __init__(self, **kwargs):
#             super(TaichiDisplayable, self).__init__(**kwargs)
#             self.last_print = time.time()
#             self.frame_count = 0
#             self.accumulated_ms = 0.0
            
#         def render(self, width, height, st, at):
#             start_time = time.time()
            
#             cam_x = math.sin(st * 0.8) * 5.0
#             cam_y = math.sin(st * 0.5) * 1.5
#             cam_z = math.cos(st * 0.8) * 5.0
            
#             cam_yaw = math.atan2(cam_x, -cam_z)
            
#             process_vertices(cam_x, cam_y, cam_z, cam_yaw)
#             render_3d()
            
#             raw_bytes = pixels.to_numpy().tobytes()
            
#             pg_surf = pygame.Surface((res_x, res_y), 0, 32)
#             pg_surf.from_data(raw_bytes)
            
#             if (width, height) != (res_x, res_y):
#                 pg_surf = pygame.transform.scale(pg_surf, (width, height))
                
#             r = renpy.Render(width, height)
#             tex = renpy.display.draw.load_texture(pg_surf)
#             r.blit(tex, (0, 0))
            
#             end_time = time.time()
#             transfer_ms = (end_time - start_time) * 1000.0
            
#             self.accumulated_ms += transfer_ms
#             self.frame_count += 1
#             if time.time() - self.last_print > 1.0:
#                 avg_ms = self.accumulated_ms / max(1, self.frame_count)
#                 print("[Taichi 3D/Cam+Light] Frame: {:.2f} ms (promedio)".format(avg_ms))
#                 self.accumulated_ms = 0.0
#                 self.frame_count = 0
#                 self.last_print = time.time()
            
#             renpy.redraw(self, 0.0)
#             return r

# screen taichi_test():
#     add TaichiDisplayable()

# label start_taichi_test:
#     show screen taichi_test
#     "Hola mundo"
#     hide screen taichi_test
#     return
