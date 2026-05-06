import bpy
import numpy as np

def export_sayoristein_npz(filepath):
    obj = bpy.context.active_object
    if not obj or obj.type != 'MESH':
        print("Please, select a mesh.")
        return

    armature_mods =[m for m in obj.modifiers if m.type == 'ARMATURE']
    for m in armature_mods: m.show_viewport = False
    
    dg = bpy.context.evaluated_depsgraph_get()
    mesh = obj.evaluated_get(dg).to_mesh()
    mesh.calc_loop_triangles()

    num_loops = len(mesh.loop_triangles) * 3
    
    verts = np.zeros((num_loops, 3), dtype=np.float32)
    norms = np.zeros((num_loops, 3), dtype=np.float32)
    uvs = np.zeros((num_loops, 2), dtype=np.float32)
    joints = np.zeros((num_loops, 4), dtype=np.int32)
    weights = np.zeros((num_loops, 4), dtype=np.float32)
    indices = np.arange(num_loops, dtype=np.int32)

    mat = obj.matrix_world
    rot_mat = mat.to_3x3()
    uv_layer = mesh.uv_layers.active.data if mesh.uv_layers.active else None

    vertex_groups = {}
    for v in mesh.vertices:
        g_w = sorted([(g.group, g.weight) for g in v.groups], key=lambda x: x[1], reverse=True)[:4]
        tot = sum([w for g, w in g_w])
        if tot > 0:
            vertex_groups[v.index] = (
                [g for g, w in g_w] + [0]*4, 
                [(w/tot) for g, w in g_w] + [0.0]*4
            )
        else:
            vertex_groups[v.index] = ([0]*4,[1.0, 0.0, 0.0, 0.0])

    i = 0
    for tri in mesh.loop_triangles:
        for loop_idx in tri.loops:
            loop = mesh.loops[loop_idx]
            v = mesh.vertices[loop.vertex_index]

            co = mat @ v.co
            no = rot_mat @ loop.normal
            
            verts[i] = (co.x, co.z, -co.y)
            norms[i] = (no.x, no.z, -no.y)
            
            if uv_layer:
                uvs[i] = (uv_layer[loop_idx].uv.x, uv_layer[loop_idx].uv.y)
            
            j, w = vertex_groups[v.index]
            joints[i] = j[:4]
            weights[i] = w[:4]

            i += 1

    obj.to_mesh_clear()
    for m in armature_mods: m.show_viewport = True

    np.savez_compressed(filepath, v=verts, n=norms, u=uvs, i=indices, j=joints, w=weights)
    print(f"Exported to: {filepath}!")

export_sayoristein_npz("your/path")
