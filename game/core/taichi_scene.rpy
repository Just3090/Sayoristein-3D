# MeshScene uses: load_stein_model

# This shit does:
# Stores the mesh data like vertices, normals, uvs, indices
# Computes AABBs for collision
# Provides raycast interface for MeshGameLoop

init -5 python:
    import numpy as np
    import math
    import os

    class MeshScene(object):
        """
        Maintains the geometry and bounding boxes of the scene for the Taichi renderer.
        """
        def __init__(self, mesh_map=None, model_path=None, map_grid=None):
            self.mesh_map = None
            self.model_path = model_path

            self.raw_v_list = []
            self.raw_n_list = []
            self.raw_u_list = []
            self.raw_i_list = []

            self.instance_aabbs = []

            self.num_vertices = 0
            self.num_triangles = 0

            if mesh_map and mesh_map.get("instances"):
                self.load_mesh_map(mesh_map)
            elif model_path:
                tex_id = get_model_texture_id(model_path)
                v, n, u, i, j, w = load_stein_model(model_path, scale=1.0, tex_id=tex_id)
                self._set_geometry(v, n, u, i)
                self._compute_single_aabb_from_geometry(v, model_path)
            elif map_grid is not None:
                v, n, u, i = get_level_geometry(map_grid)
                self._set_geometry(v, n, u, i)

        def has_geometry(self):
            return len(self.raw_v_list) > 0

        def _set_geometry(self, v_list, n_list, u_list, i_list):
            self.raw_v_list = v_list
            self.raw_n_list = n_list
            self.raw_u_list = u_list
            self.raw_i_list = i_list

        def _compute_single_aabb_from_geometry(self, v_list, label):
            if not v_list:
                return
            v_np = np.array(v_list, dtype=np.float32)
            mn = [
                float(v_np[:, 0].min()),
                float(v_np[:, 1].min()),
                float(v_np[:, 2].min()),
            ]
            mx = [
                float(v_np[:, 0].max()),
                float(v_np[:, 1].max()),
                float(v_np[:, 2].max()),
            ]
            self.instance_aabbs = [(mn, mx, label)]

        def load_mesh_map(self, mesh_map):
            self.mesh_map = mesh_map
            self.raw_v_list = []
            self.raw_n_list = []
            self.raw_u_list = []
            self.raw_i_list = []
            self.instance_aabbs = []

            current_vertex_offset = 0

            for inst in mesh_map.get("instances", []):
                if not inst.get("visible", True):
                    continue

                model_rel_path = inst.get("model_path")
                if not model_rel_path:
                    continue

                model_path = os.path.join(config.gamedir, "models", model_rel_path)

                pos = inst.get("position", [0.0, 0.0, 0.0])
                rot = inst.get("rotation", [0.0, 0.0, 0.0])
                scale = inst.get("scale", [1.0, 1.0, 1.0])

                tex_id = get_model_texture_id(model_path)
                v, n, u, i, j, w = load_stein_model(model_path, scale=1.0, tex_id=tex_id)
                if not v:
                    continue

                v_np = np.array(v, dtype=np.float32)

                if isinstance(scale, (int, float)):
                    s_vec = np.array([scale, scale, scale], dtype=np.float32)
                else:
                    s_vec = np.array(scale, dtype=np.float32)
                v_np *= s_vec

                yaw = math.radians(rot[0])
                pitch = math.radians(rot[1])
                roll = math.radians(rot[2])

                # Roll (Z axis)
                if roll != 0.0:
                    cr = math.cos(roll)
                    sr = math.sin(roll)
                    x_old = v_np[:, 0].copy()
                    y_old = v_np[:, 1].copy()
                    v_np[:, 0] = x_old * cr - y_old * sr
                    v_np[:, 1] = x_old * sr + y_old * cr

                # Pitch (X axis)
                if pitch != 0.0:
                    cp = math.cos(pitch)
                    sp = math.sin(pitch)
                    y_old = v_np[:, 1].copy()
                    z_old = v_np[:, 2].copy()
                    v_np[:, 1] = y_old * cp - z_old * sp
                    v_np[:, 2] = y_old * sp + z_old * cp

                # Yaw (Y axis)
                if yaw != 0.0:
                    cy = math.cos(yaw)
                    sy = math.sin(yaw)
                    x_old = v_np[:, 0].copy()
                    z_old = v_np[:, 2].copy()
                    v_np[:, 0] = x_old * cy - z_old * sy
                    v_np[:, 2] = x_old * sy + z_old * cy

                v_np[:, 0] += pos[0]
                v_np[:, 1] += pos[1]
                v_np[:, 2] += pos[2]

                mn = [
                    float(v_np[:, 0].min()),
                    float(v_np[:, 1].min()),
                    float(v_np[:, 2].min()),
                ]
                mx = [
                    float(v_np[:, 0].max()),
                    float(v_np[:, 1].max()),
                    float(v_np[:, 2].max()),
                ]
                self.instance_aabbs.append((mn, mx, model_rel_path))

                self.raw_v_list.extend(v_np.tolist())
                self.raw_n_list.extend(n)
                self.raw_u_list.extend(u)

                offset_indices = [idx + current_vertex_offset for idx in i]
                self.raw_i_list.extend(offset_indices)

                current_vertex_offset += len(v)

        def raycast_instance(self, origin, direction):
            best_idx = -1
            best_t = float("inf")
            best_path = ""

            for idx, item in enumerate(self.instance_aabbs):
                mn, mx, path = item

                t_min = -float("inf")
                t_max = float("inf")
                hit = True

                for axis in range(3):
                    d = direction[axis]
                    o = origin[axis]
                    a_lo = mn[axis]
                    a_hi = mx[axis]

                    if abs(d) < 1e-8:
                        if o < a_lo or o > a_hi:
                            hit = False
                            break
                    else:
                        t1 = (a_lo - o) / d
                        t2 = (a_hi - o) / d
                        if t1 > t2:
                            t1, t2 = t2, t1
                        if t1 > t_min:
                            t_min = t1
                        if t2 < t_max:
                            t_max = t2
                        if t_min > t_max:
                            hit = False
                            break

                if not hit:
                    continue
                if t_max <= 0:
                    continue

                t_hit = t_min if t_min > 0 else t_max
                if 0.0 < t_hit < best_t:
                    best_t = t_hit
                    best_idx = idx
                    best_path = path

            if best_idx < 0:
                return None
            return (best_idx, best_t, best_path)
