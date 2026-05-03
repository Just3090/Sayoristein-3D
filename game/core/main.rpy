# RenPyStein - Main Script and Data File

# --- Persistent Data ---
default persistent.stein_quality_mode = 1  # 0=High, 1=Low, 2=Ultra Low, 3=MS Paint is Better
default persistent.sayoristein_arena_highscore = 0
default persistent.stein_kills = 0
default persistent.tradu_coins = 0
default persistent.stein_pistol_level = 0
default persistent.stein_shotgun_level = 0
default persistent.stein_minigun_level = 0
default persistent.stein_shotgun_unlocked = False
default persistent.stein_minigun_unlocked = False
default persistent.stein_level1_cleared = False
default persistent.stein_level2_cleared = False
default persistent.stein_level3_cleared = False

# --- Save-Specific Data ---
# These variables hold the LIVE game state. They are initialized by reset_stein_state.
default player_x = 22.0
default player_y = 11.5
default player_dirx = -1.0
default player_diry = 0.0
default player_planex = 0.0
default player_planey = 0.66
default stein_enemies = []
default stein_sprites = []
default stein_session_coins = 0
default stein_has_shotgun = False
default stein_has_minigun = False
default stein_current_round = 0
default stein_inter_round_timer = 0.0
default stein_sniper_count = 0
default stein_yuritler_count = 0
default worldMap = []
default meshMap = {"version": "1.0", "type": "mesh_map", "instances": []}
default stein_map_backend = "voxel" # Can be "voxel" or "mesh"
default exits = []
default stein_objects = [] # List of (x, y, z, "filename.json")

default stein_current_fps = 60
default stein_current_lighting = None

default persistent.stein_mouse_sens = 1.0
default persistent.stein_gamepad_sens_x = 1.0
default persistent.stein_gamepad_sens_y = 1.0
default persistent.stein_show_fps = True
default persistent.stein_enable_bloom = True

init python:
    import json
    import os
    import time

    def save_level_json(world_map, name=None):
        """
        Saves the current voxel map (worldMap) to a JSON file.
        worldMap structure: { z_level (int): [ [row1...], [row2...] ... ], ... }
        The function saves it to game/saved_maps/name.json or game/saved_maps/level_TIMESTAMP.json
        """
        if name is None:
            name = "level_{}".format(int(time.time()))
        
        if name.endswith(".json"):
            name = name[:-5]

        save_dir = os.path.join(config.gamedir, "saved_maps")
        if not os.path.exists(save_dir):
            try:
                os.makedirs(save_dir)
            except:
                pass
        
        filename = name + ".json"
        full_path = os.path.join(save_dir, filename)
        
        try:
            with open(full_path, "w") as f:
                json.dump(world_map, f, separators=(',', ':'))
            renpy.notify("Map saved: " + filename)
            print("Map saved to " + full_path)
        except Exception as e:
            renpy.notify("Error saving map!")
            print("Error saving map: " + str(e))

    def load_level_json(filename):
        """
        Loads a voxel map from game/saved_maps/filename.
        Returns the data structure (converting string keys back to int if they look like ints).
        """
        save_dir = os.path.join(config.gamedir, "saved_maps")
        full_path = os.path.join(save_dir, filename)
        
        if not os.path.exists(full_path):
            if os.path.exists(filename):
                full_path = filename
            else:
                print("File not found: " + full_path)
                return {} # Return empty dict instead of None
                
        try:
            with open(full_path, "r") as f:
                data = json.load(f)
            
            if isinstance(data, dict):
                new_data = {}
                is_z_level_map = True
                
                # Check for conversion validity
                for k in data.keys():
                    try:
                        int(k)
                    except:
                        print("load_level_json: Key '{}' is not an integer.".format(k))
                        is_z_level_map = False
                        break
                
                if is_z_level_map:
                    for k, v in data.items():
                        new_data[int(k)] = v
                    return new_data
                else:
                    pass
            return data
        except Exception as e:
            print("Error loading map: " + str(e))
            return {}

    MESH_MAP_SCHEMA_VERSION = "1.0"

    def empty_mesh_map():
        # rotation in degrees, order [yaw, pitch, roll]
        # obj_path is relative to game/models/
        return {"version": MESH_MAP_SCHEMA_VERSION, "type": "mesh_map", "instances": []}

    def validate_mesh_map(data):
        clean_data = empty_mesh_map()
        errors = []
        warnings = []
        
        if not hasattr(data, "get"):
            errors.append("Map data is not a dictionary. Got: {}".format(type(data)))
            return clean_data, errors, warnings
            
        if data.get("type") != "mesh_map":
            errors.append("Invalid map type. Expected 'mesh_map'.")
            
        version = data.get("version", "1.0")
        if version != MESH_MAP_SCHEMA_VERSION:
            warnings.append("Unknown map version: {}".format(version))
            clean_data["version"] = version
            
        instances = data.get("instances", [])
        if not hasattr(instances, "__iter__") or hasattr(instances, "keys"):
            errors.append("instances is not a valid list.")
            return clean_data, errors, warnings
            
        for i, inst in enumerate(instances):
            if not hasattr(inst, "get"):
                warnings.append("Instance {} is not a dict, skipping.".format(i))
                continue
                
            obj_path = inst.get("obj_path", "")
            if not obj_path or not isinstance(obj_path, str):
                warnings.append("Instance {} missing valid 'obj_path', skipping.".format(i))
                continue
                
            full_path = os.path.join(config.gamedir, "models", obj_path)
            if not os.path.exists(full_path):
                errors.append("Path does not exist: models/{}".format(obj_path))
                
            clean_inst = {
                "obj_path": obj_path,
                "position": [0.0, 0.0, 0.0],
                "rotation": [0.0, 0.0, 0.0],
                "scale": [1.0, 1.0, 1.0],
                "collision_enabled": bool(inst.get("collision_enabled", True)),
                "visible": bool(inst.get("visible", True))
            }
            
            for key in ["position", "rotation", "scale"]:
                val = inst.get(key)
                try:
                    if len(val) == 3 and not hasattr(val, "keys"):
                        clean_inst[key] = [float(val[0]), float(val[1]), float(val[2])]
                    else:
                        warnings.append("Instance {} has missing/malformed {}, using defaults.".format(i, key))
                except (ValueError, TypeError, KeyError, IndexError, AttributeError):
                    warnings.append("Instance {} has missing/malformed {}, using defaults.".format(i, key))
                    
            clean_data["instances"].append(clean_inst)
            
        return clean_data, errors, warnings

    def save_mesh_map_json(mesh_data, name=None):
        if name is None:
            name = "mesh_map_{}".format(int(time.time()))
        if name.endswith(".json"):
            name = name[:-5]

        save_dir = os.path.join(config.gamedir, "saved_mesh_maps")
        if not os.path.exists(save_dir):
            try:
                os.makedirs(save_dir)
            except:
                pass

        filename = name + ".json"
        full_path = os.path.join(save_dir, filename)

        try:
            clean_data, errors, warnings = validate_mesh_map(mesh_data)
            if errors:
                renpy.notify("Error: Map has fatal errors, cannot save.")
                print("Cannot save mesh map due to errors:", errors)
                return
            with open(full_path, "w") as f:
                json.dump(clean_data, f, indent=4)
            renpy.notify("Mesh map saved: " + filename)
            print("Mesh map saved to " + full_path)
        except Exception as e:
            renpy.notify("Error saving mesh map!")
            print("Error saving mesh map: " + str(e))

    def delete_mesh_map_json(name):
        if name.endswith(".json"):
            name = name[:-5]
        save_dir = os.path.join(config.gamedir, "saved_mesh_maps")
        filename = name + ".json"
        full_path = os.path.join(save_dir, filename)
        if os.path.exists(full_path):
            try:
                os.remove(full_path)
                renpy.notify("Map deleted.")
            except Exception as e:
                renpy.notify("Error deleting map!")
                print("Error deleting map: " + str(e))

    def load_mesh_map_json(filename):
        save_dir = os.path.join(config.gamedir, "saved_mesh_maps")
        full_path = os.path.join(save_dir, filename)
        
        if not os.path.exists(full_path):
            if os.path.exists(filename):
                full_path = filename
            else:
                print("Mesh map not found: " + full_path)
                return empty_mesh_map()
                
        try:
            with open(full_path, "r") as f:
                data = json.load(f)
            clean_data, errors, warnings = validate_mesh_map(data)
            if errors:
                print("Errors loading mesh map: {}".format(errors))
            if warnings:
                renpy.notify("Map loaded with warnings.")
                print("Warnings loading mesh map: {}".format(warnings))
            return clean_data
        except Exception as e:
            print("Error loading mesh map: " + str(e))
            return empty_mesh_map()

    def get_mesh_map_files():
        save_dir = os.path.join(config.gamedir, "saved_mesh_maps")
        files = []
        if os.path.exists(save_dir):
            for f in os.listdir(save_dir):
                if f.endswith(".json"):
                    files.append(f)
        return sorted(files)

    def get_obj_files():
        models_dir = os.path.join(config.gamedir, "models")
        files = []
        if os.path.exists(models_dir):
            for root, _, filenames in os.walk(models_dir):
                for f in filenames:
                    if f.lower().endswith(".obj"):
                        rel_path = os.path.relpath(os.path.join(root, f), models_dir)
                        files.append(rel_path)
        return sorted(files)

    def load_object_json(filename):
        """
        Loads a voxel model from game/save_objects/filename.
        Similar to load_level_json but for object models.
        """
        save_dir = os.path.join(config.gamedir, "save_objects")
        full_path = os.path.join(save_dir, filename)
        
        if not os.path.exists(full_path):
            if os.path.exists(filename):
                full_path = filename
            else:
                print("Object file not found: " + full_path)
                return None
                
        try:
            with open(full_path, "r") as f:
                data = json.load(f)
            
            # Post-process: Convert keys back to int if they represent Z levels
            if isinstance(data, dict):
                new_data = {}
                is_z_level_map = True
                
                for k in data.keys():
                    try:
                        int(k)
                    except:
                        # print(f"DEBUG: Key {k} is not int in {filename}")
                        is_z_level_map = False
                        break
                
                if is_z_level_map:
                    for k, v in data.items():
                        new_data[int(k)] = v
                    return new_data
                else:
                    return data
            return data
        except Exception as e:
            print("Error loading object: " + str(e))
            return None

    def save_anim_json(anim_data, name="anim"):
        """
        Saves animation data to game/save_anims/name.json.
        Expects anim_data to be a dictionary with 'meta' and 'tracks'.
        """
        if name is None:
            name = "anim_{}".format(int(time.time()))
        
        if name.endswith(".json"):
            name = name[:-5]

        save_dir = os.path.join(config.gamedir, "save_anims")
        if not os.path.exists(save_dir):
            try:
                os.makedirs(save_dir)
            except:
                pass
        
        filename = name + ".json"
        full_path = os.path.join(save_dir, filename)
        
        try:
            with open(full_path, "w") as f:
                json.dump(anim_data, f, indent=4)
            renpy.notify("Anim saved: " + filename)
            print("Animation saved to " + full_path)
        except Exception as e:
            renpy.notify("Error saving animation!")
            print("Error saving animation: " + str(e))

    def load_anim_json(filename):
        """
        Loads animation data from game/save_anims/filename.
        Returns a dictionary or None on error.
        """
        save_dir = os.path.join(config.gamedir, "save_anims")
        full_path = os.path.join(save_dir, filename)
        
        if not os.path.exists(full_path):
            if os.path.exists(filename):
                full_path = filename
            else:
                print("Anim file not found: " + full_path)
                return None
                
        try:
            with open(full_path, "r") as f:
                data = json.load(f)
            return data
        except Exception as e:
            print("Error loading animation: " + str(e))
            return None

    def get_anim_files():
        """Returns a sorted list of .json files in game/save_anims/"""
        save_dir = os.path.join(config.gamedir, "save_anims")
        if not os.path.exists(save_dir):
            try: os.makedirs(save_dir)
            except: pass
            return []
        
        try:
            files = [f for f in os.listdir(save_dir) if f.endswith(".json")]
            return sorted(files)
        except:
            return []

    def get_object_files():
        """Returns a sorted list of .json files in game/save_objects/"""
        save_dir = os.path.join(config.gamedir, "save_objects")
        if not os.path.exists(save_dir):
            try: os.makedirs(save_dir)
            except: pass
            return []
        
        try:
            files = [f for f in os.listdir(save_dir) if f.endswith(".json")]
            return sorted(files)
        except:
            return []

    class FloatInputValue(InputValue):
        def __init__(self, object, field):
            self.object = object
            self.field = field

        def get_text(self):
            val = getattr(self.object, self.field)
            return "{:.2f}".format(val)

        def set_text(self, text):
            try:
                val = float(text)
                setattr(self.object, self.field, val)
            except ValueError:
                pass # Ignore invalid float input

        def enter(self):
            return getattr(self.object, self.field)

    class GroupFloatInputValue(InputValue):
        def __init__(self, transform_obj, gname, field):
            self.data = transform_obj.get_group_data(gname)
            self.field = field

        def get_text(self):
            val = self.data.get(self.field, 0.0)
            return "{:.2f}".format(val)

        def set_text(self, text):
            try:
                self.data[self.field] = float(text)
            except ValueError:
                pass

        def enter(self):
            return self.data.get(self.field, 0.0)

    class EditorTransform(object):
        def __init__(self):
            self.x = 0.0; self.y = 0.0; self.z = 0.0
            self.rx = 0.0; self.ry = 0.0; self.rz = 0.0
            self.sx = 1.0; self.sy = 1.0; self.sz = 1.0
            self.group_transforms = {} # Map of "GroupName" is { 'x': 0.0, ... }

        def get_group_data(self, gname):
            if gname not in self.group_transforms:
                self.group_transforms[gname] = {
                    'x': 0.0, 'y': 0.0, 'z': 0.0,
                    'rx': 0.0, 'ry': 0.0, 'rz': 0.0,
                    'sx': 1.0, 'sy': 1.0, 'sz': 1.0
                }
            return self.group_transforms[gname]

    def load_object_into_editor(renderer_obj, filename):
        """
        Loads an object file AS A MAP (Scale 1:1) for visual editing.
        Uses Inverse Camera logic for animation preview.
        """
        import math
        data = load_object_json(filename)
        
        if data:
            # 1. Load as World Map
            renderer_obj.worldMap = data
            renderer_obj.map_data = data
            
            # Recalculate Dimensions
            if isinstance(data, dict) or hasattr(data, 'items'):
                max_x = 0
                max_y = 0
                for grid in data.values():
                    if len(grid) > max_x: max_x = len(grid)
                    if len(grid) > 0 and len(grid[0]) > max_y: max_y = len(grid[0])
                renderer_obj.mapWidth = max_x
                renderer_obj.mapHeight = max_y
            else:
                s_mapWidth = len(data)
                if s_mapWidth > 0:
                    renderer_obj.mapWidth = s_mapWidth
                    renderer_obj.mapHeight = len(data[0])
                else:
                    renderer_obj.mapWidth = 0
                    renderer_obj.mapHeight = 0
            
            renderer_obj.map_w = renderer_obj.mapWidth
            renderer_obj.map_h = renderer_obj.mapHeight
            
            # Populate Master Voxels for Rigging
            renderer_obj.master_voxels = []
            for z_key, grid in data.items():
                try:
                    z = int(z_key) # Ensure Z is an integer
                    for x, row in enumerate(grid):
                        for y, tid in enumerate(row):
                            if tid > 0:
                                renderer_obj.master_voxels.append((x, y, z, tid))
                except:
                    pass
            
            # Regenerate Texture
            renderer_obj.map_texture = renderer_obj.create_map_texture()
            
            # Rebuild Model Atlas (Empty - we are rendering walls)
            renderer_obj.model_atlas, renderer_obj.num_models = renderer_obj.create_model_atlas([])
            
            # Create Editor Target (Dummy for Animation Data)
            renderer_obj.editor_target = EditorTransform()
            
            # Clear Scene Objects
            renderer_obj.scene_objects = []
            
            # Reset Camera
            cx = renderer_obj.mapWidth / 2.0
            cy = renderer_obj.mapHeight / 2.0
            
            renderer_obj.player.x = cx
            renderer_obj.player.y = cy - 12.0
            renderer_obj.player.z = 4.0
            renderer_obj.player.rot = math.pi / 2.0 
            renderer_obj.player.pitch = 0.0
            renderer_obj.player.velocity_z = 0.0
            
            # Standard FOV
            renderer_obj.player.planex = 0.66
            renderer_obj.player.planey = 0.0
            
            renpy.restart_interaction()

    def add_keyframe_auto(target_type, active_gname, renderer, current_anim_data, current_time):
        if target_type == "global":
            for fld in ['x', 'y', 'z', 'rx', 'ry', 'rz', 'sx', 'sy', 'sz']:
                val = getattr(renderer.editor_target, fld)
                renpy.store.add_keyframe(current_anim_data, fld, current_time, val)
        else:
            gdata = renderer.editor_target.get_group_data(active_gname)
            for fld in ['x', 'y', 'z', 'rx', 'ry', 'rz', 'sx', 'sy', 'sz']:
                track_name = f"group:{active_gname}:{fld}"
                renpy.store.add_keyframe(current_anim_data, track_name, current_time, gdata[fld])

    def remove_keyframe_auto(target_type, active_gname, current_anim_data, current_time):
        if target_type == "global":
            for fld in ['x', 'y', 'z', 'rx', 'ry', 'rz', 'sx', 'sy', 'sz']:
                renpy.store.remove_keyframe(current_anim_data, fld, current_time)
        else:
            for fld in ['x', 'y', 'z', 'rx', 'ry', 'rz', 'sx', 'sy', 'sz']:
                track_name = f"group:{active_gname}:{fld}"
                renpy.store.remove_keyframe(current_anim_data, track_name, current_time)


    if 's' in config.keymap['screenshot']:
        config.keymap['screenshot'].remove('s')
    if 'alt_s' in config.keymap['screenshot']:
        config.keymap['screenshot'].remove('alt_s')

    stein_lighting_presets = {
        "night": {
            'ambient_base': (0.02, 0.02, 0.05),
            'ambient_near': (0.05, 0.05, 0.08),
            'sky_texture': "pics/background.webp",
            'time_id': 0.0
        },
        "day": {
            'ambient_base': (1.0, 1.0, 1.0),
            'ambient_near': (0.0, 0.0, 0.0),
            'sky_texture': "pics/background.webp",
            'time_id': 1.0
        },
        "afternoon": {
            'ambient_base': (0.6, 0.6, 0.7),
            'ambient_near': (0.1, 0.1, 0.1),
            'sky_texture': "pics/background.webp",
            'time_id': 2.0
        }
    }

    # --- Level 1 Data ---
    level1_data = {
        "lighting": "day",
        "worldMap": load_level_json("blender_import.json"),
        "player_x": 5.5, "player_y": 4.5,
        "player_dirx": -1.0, "player_diry": 0.0,
        "player_planex": 0.0, "player_planey": 0.66,
        "enemies": [
            # (X, Y, Filename/Tex, DeadTex, HP, TypeID)
            # Type ENEMY_TYPE_VOXEL_BASIC = Voxel Enemy
            # (8.0, 8.0, "template_16.json", 0, 100, ENEMY_TYPE_VOXEL_BASIC)
        ],
        "sprites": [
            # (20.5, 11.5, 2), (18.5,4.5, 2), (10.0,4.5, 2), (10.0,12.5,2),
            # (3.5, 6.5, 2), (3.5, 20.5,2), (3.5, 14.5,2), (14.5,20.5,2)
        ],
        "exits": [],
        "objects": [
            # (X, Y, Z, "Archivo")
            # (6.0, 8.0, 2.0, "test.json")
        ],
    }

    # --- Level 2 Data ---
    level2_data = {
        "lighting": "afternoon",
        "worldMap": [
            [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
            [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
            [1,0,2,2,2,0,0,3,3,0,0,2,2,2,0,1],
            [1,0,2,0,0,0,0,3,0,0,0,0,0,2,0,1],
            [1,0,2,0,0,5,5,5,5,5,5,0,0,2,0,1],
            [1,0,0,0,0,5,0,0,0,0,5,0,0,0,0,1],
            [1,0,3,3,0,5,0,4,4,0,5,0,3,3,0,1],
            [1,0,0,0,0,0,0,4,0,0,0,0,0,0,0,1],
            [1,0,0,0,0,0,0,4,0,0,0,0,0,0,0,1],
            [1,0,3,3,0,5,0,4,4,0,5,0,3,3,0,1],
            [1,0,0,0,0,5,0,0,0,0,5,0,0,0,0,1],
            [1,0,2,0,0,5,5,5,5,5,5,0,0,2,0,1],
            [1,0,2,0,0,0,0,3,0,0,0,0,0,2,0,1],
            [1,0,2,2,2,0,0,3,3,0,0,2,2,2,0,1],
            [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
            [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]
        ],
        "player_x": 8.0, "player_y": 8.0,
        "player_dirx": 0.0, "player_diry": 1.0,
        "player_planex": 0.66, "player_planey": 0.0,
        "enemies": [ (13.5, 2.5, 4, 5), (2.5, 13.5, 4, 5), (7.5, 13.5, 4, 5) ],
        "sprites": [],
        "exits": [ (1.5, 1.5, "Exit") ]
    }

    # --- Level 3 Data ---
    level3_data = {
        "worldMap": [
            [2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2],
            [2,0,0,0,0,0,0,0,2,0,0,0,0,0,0,0,0,0,0,5,0,0,0,0,0,0,0,0,0,0,0,2],
            [2,0,2,2,2,2,2,0,2,0,4,4,4,4,4,4,4,4,0,5,0,4,4,4,0,4,4,4,4,4,0,2],
            [2,0,2,0,0,0,2,0,2,0,4,0,0,0,0,0,0,4,0,5,0,4,0,0,0,0,0,0,0,4,0,2],
            [2,0,2,0,2,0,2,0,0,0,4,0,4,4,4,4,0,4,0,0,0,4,0,4,4,4,4,4,0,4,0,2],
            [2,0,2,0,2,0,2,2,2,0,4,0,4,0,0,4,0,4,4,4,4,4,0,4,0,0,0,0,0,4,0,2],
            [2,0,0,0,2,0,0,0,0,0,4,0,0,0,0,4,0,0,0,0,0,0,0,4,4,0,4,4,4,4,0,2],
            [2,2,2,2,2,2,2,2,2,5,5,5,5,0,5,5,5,5,5,5,5,5,0,4,0,0,0,0,0,4,0,2],
            [6,6,6,6,6,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,6,6,6,0,6,0,2],
            [6,0,0,0,0,0,6,0,6,0,6,6,6,6,6,6,0,6,6,6,6,6,6,6,0,6,0,0,0,6,0,2],
            [6,0,3,3,0,0,0,0,0,0,0,0,0,0,0,6,0,6,0,0,0,0,0,6,0,6,0,6,6,6,0,2],
            [6,0,3,3,0,0,6,0,6,0,6,6,6,6,0,6,0,6,0,6,6,6,0,6,0,0,0,0,0,0,0,2],
            [6,0,0,0,0,0,6,0,6,0,6,0,0,0,0,0,0,0,0,6,0,6,0,6,6,6,6,6,6,6,6,6],
            [6,6,6,6,6,6,6,0,6,0,6,0,6,6,6,6,6,6,6,6,0,6,0,0,0,0,0,0,0,0,0,1],
            [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1,0,1],
            [1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,1,0,0,0,0,0,0,0,1,0,1],
            [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,0,1,0,1,0,1],
            [1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,1,0,1,0,0,0,1,0,1,0,1],
            [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,1,0,1,1,1,0,1,0,1],
            [1,1,1,1,1,1,1,1,8,8,8,8,8,8,8,8,8,8,8,0,8,8,0,0,0,0,0,0,0,1,0,1],
            [3,3,3,3,3,3,3,3,8,0,0,0,8,0,0,0,0,0,8,0,8,0,0,1,1,1,1,1,0,0,0,1],
            [3,0,0,0,0,0,0,3,8,0,8,0,8,0,8,8,8,0,8,0,8,0,8,8,0,0,0,8,0,8,8,8],
            [3,0,3,3,3,3,0,3,8,0,0,0,0,0,8,0,0,0,0,0,0,0,0,0,0,8,0,0,0,0,0,8],
            [3,0,3,0,0,3,0,3,8,8,8,8,8,0,8,8,8,8,8,8,8,8,8,8,0,8,8,8,8,8,0,8],
            [3,0,3,0,0,3,0,3,3,3,3,3,8,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,8,0,8],
            [3,0,3,3,3,3,0,0,0,0,0,3,8,8,8,8,8,0,8,8,8,8,8,8,8,8,8,8,0,8,0,8],
            [3,0,0,0,0,0,0,3,3,3,0,3,7,7,7,7,8,0,8,7,7,7,7,7,7,7,0,0,0,8,0,8],
            [3,3,3,3,3,3,3,3,0,0,0,0,7,0,0,0,0,0,0,0,0,0,7,0,0,0,0,7,7,7,0,8],
            [7,7,7,7,7,7,7,7,0,7,7,7,7,0,7,7,7,7,7,7,7,0,7,0,7,7,7,7,0,0,0,8],
            [7,0,0,0,0,0,0,0,0,7,0,0,0,0,7,0,0,0,0,0,0,0,0,0,0,0,0,0,0,7,0,8],
            [7,0,7,7,7,7,7,7,7,7,0,7,7,7,7,0,7,7,7,7,7,7,7,7,7,7,7,7,0,0,0,8],
            [7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,8,8,8,8]
        ],
        "player_x": 1.5, "player_y": 1.5,
        "player_dirx": 0.0, "player_diry": 1.0,
        "player_planex": 0.66, "player_planey": 0.0,
        "enemies": [
            (3.5, 4.5, 4, 5, 100), (6.5, 7.5, 4, 5, 100),
            (7.5, 12.5, 4, 5, 100), (7.5, 20.5, 4, 5, 100),
            (10.5, 2.5, 4, 5, 100), (10.5, 5.5, 4, 5, 100), (11.5, 4.5, 4, 5, 100),
            (12.5, 15.5, 4, 5, 100), (12.5, 18.5, 4, 5, 100),
            (15.5, 3.5, 4, 5, 100), (15.5, 7.5, 4, 5, 100), (15.5, 11.5, 4, 5, 100),
            (16.5, 5.5, 4, 5, 100), (16.5, 9.5, 4, 5, 100),
            (21.5, 2.5, 4, 5, 100), (22.5, 12.5, 4, 5, 100), (24.5, 5.5, 4, 5, 100),
            (25.5, 28.5, 4, 5, 100), (20.5, 29.5, 4, 5, 100),
            (29.5, 25.5, 4, 5, 150), (29.5, 27.5, 4, 5, 150),
            (30.5, 28.5, 4, 5, 300)
        ],
        "sprites": [
            (10.5, 10.5, 1), (10.5, 20.5, 1), (12.5, 12.5, 1),
            (1.5, 10.5, 0), (1.5, 20.5, 0),
            (28.5, 28.5, 2), (28.5, 29.5, 2), (28.5, 27.5, 2)
        ],
        "exits": [
            (30.5, 30.5, "Level 3 Complete")
        ]
    }

    # --- Level 4 (Arena) Data ---
    level4_data = {
        "worldMap": load_level_json("arena.json"),
        "player_x": 15.0, "player_y": 15.0,
        "player_dirx": -1.0, "player_diry": 0.0,
        "player_planex": 0.0, "player_planey": 0.66,
        "enemies": [],
        "sprites": [],
        "exits": [],
        "spawn_points": [
            (2,2), (2,27), (27,2), (27,27),
            (5,5), (5,24), (24,5), (24,24),
            (15, 2), (15, 27), (2, 15), (27, 15),
            (12,12), (18,18), (12,18), (18,12)
        ],
        "objects": [
            # (X, Y, Z, "Archivo")
            (9.0, 12.0, 5.0, "template_16.json")
        ],
        "lighting": "day"
    }

    # --- Level 5 Data ---
    level5_data = {
        "lighting": "day",
        "worldMap": {
            0: [
                [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
                [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
                [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1]
            ],
            1: [
                [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
                [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
            ]
            # 2: [
            #     [0,0,0,0,0,0,0,0,0,0],
            #     [0,0,0,0,0,0,0,0,0,0],
            #     [0,0,0,0,0,0,0,0,0,0],
            #     [0,0,0,0,0,0,0,0,0,0],
            #     [0,0,0,0,0,0,0,0,0,0],
            #     [0,0,0,0,4,0,0,0,0,0],
            #     [0,0,0,0,0,0,0,0,0,0],
            #     [0,0,0,0,0,0,0,0,0,0],
            #     [0,0,0,0,0,0,0,0,0,0],
            #     [0,0,0,0,0,0,0,0,0,0]
            # ]
        },
        "player_x": 1.5, "player_y": 1.5,
        "player_dirx": 0.0, "player_diry": 1.0,
        "player_planex": 0.66, "player_planey": 0.0,
        "enemies": [],
        "sprites": [],
        "exits": []
    }

    def reset_stein_state(level=1, arena=False):
        """
        Initializes or resets the game state for a specific level.
        """

        store.is_arena_mode = arena
        
        if level == 2:
            level_data = level2_data
        elif level == 3:
            level_data = level3_data
        elif level == 4:
            level_data = level4_data
        elif level == 5:
            level_data = level5_data
        else: # Default to level 1
            level_data = level1_data

        renpy.store.worldMap = level_data.get("worldMap", [])
        if renpy.store.worldMap is None:
            print("reset_stein_state: worldMap was None, initializing empty map.")
            renpy.store.worldMap = {}
            
        renpy.store.meshMap = level_data.get("meshMap", empty_mesh_map())
        renpy.store.stein_map_backend = level_data.get("stein_map_backend", "voxel")
        
        renpy.store.exits = level_data["exits"]
        renpy.store.player_x = level_data["player_x"]
        renpy.store.player_y = level_data["player_y"]
        renpy.store.player_dirx = level_data["player_dirx"]
        renpy.store.player_diry = level_data["player_diry"]
        renpy.store.player_planex = level_data["player_planex"]
        renpy.store.player_planey = level_data["player_planey"]
        renpy.store.stein_player_health = 100
        renpy.store.stein_current_weapon = "fist"
        renpy.store.stein_enemies = list(level_data["enemies"])
        renpy.store.stein_session_coins = 0
        renpy.store.stein_current_round = 0
        renpy.store.stein_inter_round_timer = 0.0
        renpy.store.stein_sniper_count = 0
        renpy.store.stein_yuritler_count = 0
        
        # Set Lighting
        lighting_key = level_data.get("lighting", "night")
        renpy.store.stein_current_lighting = stein_lighting_presets.get(lighting_key, stein_lighting_presets["night"])

        # Initialize sprites list with defined sprites and add barrel for each exit
        temp_sprites = list(level_data["sprites"])
        for exit_coord in level_data["exits"]:
            temp_sprites.append((exit_coord[0], exit_coord[1], 0)) # 0 is the barrel sprite index
        renpy.store.stein_sprites = temp_sprites
        
        # Load Objects
        # objects defined as (x, y, z, "filename") in level_data["objects"]
        renpy.store.stein_objects = list(level_data.get("objects", []))

        # Pass arena data to the store
        renpy.store.is_arena_mode = arena
        if arena:
            renpy.store.persistent.stein_kills = 0
            renpy.store.arena_spawn_points = level_data.get("spawn_points", [])
            renpy.store.stein_has_shotgun = persistent.stein_shotgun_unlocked
            renpy.store.stein_has_minigun = persistent.stein_minigun_unlocked
        else:
            renpy.store.arena_spawn_points = []
            renpy.store.stein_has_shotgun = True # Always have weapons in story mode (for now)
            renpy.store.stein_has_minigun = True


# The screen that displays the main game engine.
screen stein:
    key "s" action None
    key "mouseup_3" action None
    key "K_LSHIFT" action None
    key "K_RSHIFT" action None
    key "K_LCTRL" action None
    key "K_RCTRL" action None
    key "K_f" action None

    python:
        # Quality settings: 0=High, 1=Low, 2=Ultra Low
        if persistent.stein_quality_mode == 0: # High
            internal_width = 960
            internal_height = 540 
        elif persistent.stein_quality_mode == 1: # Low
            internal_width = 640
            internal_height = 360
        elif persistent.stein_quality_mode == 2: # Ultra Low
            internal_width = 426
            internal_height = 240
        elif persistent.stein_quality_mode == 3: # MS Paint is Better
            internal_width = 213
            internal_height = 120
        else: # Bro, can you see?
            internal_width = 142
            internal_height = 80
        
        renderer_instance = GPURenpystein(
            1280, 720,
            worldMap=worldMap,
            exits=exits,
            objects=stein_objects,
            internal_width=internal_width,
            internal_height=internal_height,
            lighting_preset=stein_current_lighting
        )

    add renderer_instance
    
    # Compass Overlay
    if config.developer:
        add "pics/compass.webp":
            zoom 1.0
            align (0.02, 0.95)
            at compass_rot(renderer_instance)

label renpystein_game:
    hide black
    show screen stein_controls_overlay
    call screen stein
    
    if _return == 'game_over_arena':
        $ persistent.tradu_coins += stein_session_coins
        s "You survived [renpy.store.last_arena_round] rounds and collected [stein_session_coins] Coins."
        if persistent.stein_session_coins != 0:
            s "Now you have a total of [persistent.tradu_coins] Tradu-Coins."
        else:
            s "You have [persistent.tradu_coins] Tradu-Coins."

        if renpy.store.new_highscore:
            s "A new high score!"
        else:
            s "You have a high score of [persistent.sayoristein_arena_highscore]."
            s "Try next time!"
    elif _return == 'game_over':
        s "You died."
    else:
        if _return == "Exit 1" or _return == "Exit 2" or _return == "Exit 3" or _return == "Exit 4":
            $ persistent.stein_level1_cleared = True
        elif _return == "Exit":
            $ persistent.stein_level2_cleared = True
        elif _return == "Level 3 Complete":
            $ persistent.stein_level3_cleared = True
             
        s "You found exit [_return]!"
    hide screen stein_controls_overlay
    return

label start_level_1:
    $ js_stein_audio.play("level_1")
    $ reset_stein_state(level=1)
    jump renpystein_game

label start_level_2:
    $ js_stein_audio.play("level_2")
    $ reset_stein_state(level=2)
    jump renpystein_game

label start_level_3:
    $ js_stein_audio.play("level_3")
    $ reset_stein_state(level=3)
    jump renpystein_game

label start_level_4_arena:
    # call screen shader_warmup
    # $ js_stein_audio.play("arena")
    # $ reset_stein_state(level=4, arena=True)
    # jump renpystein_game
    jump start_taichi_engine

label start_level_5:
    # call screen shader_warmup
    $ reset_stein_state(level=5)
    jump renpystein_game

# This is for backwards compatibility / direct calls
label renpystein_demo:
    jump start_level_1

label sayoristein_main_menu(mg_obj=None):
    $ preferences.gl_powersave = False
    $ preferences.gl_framerate = 120
    $ js_stein_audio.enter_minigame()
    $ js_stein_audio.play("menu")
    show black zorder 99 with dissolve
    show chibi_dvd zorder 100 at t_chibi_dvd
    with dissolve
    pause 1.5
    hide chibi_dvd with dissolve
    call screen sayoristein_menu with dissolve
    show black zorder 99 with dissolve
    show chibi_dvd zorder 100 at t_chibi_dvd
    with dissolve
    pause 1.0
    $ js_stein_audio.exit_minigame()
    hide chibi_dvd with dissolve
    hide black with dissolve
    return

label test_gpu:
    $ reset_stein_state(level=1)
    call screen gpu_stein_test
    return

init python:
    def compass_updater(renderer):
        def _update(trans, st, at):
            if renderer and renderer.player:
                # East (X+) is North. Angle 0 radians = 0 degrees rotation.
                trans.rotate = -math.degrees(renderer.player.rot)
            return 0.01
        return _update

transform compass_rot(r):
    rotate_pad True
    function compass_updater(r)

screen animation_editor():
    # Variables for layout
    default editor_viewport_width = 1280 - 300
    default editor_viewport_height = 720 - 200
    
    # Variables for selected object transformation
    default obj_x = "0.0"
    default obj_y = "0.0"
    default obj_z = "0.0"
    
    default editing_field = None
    
    # Animation Editor State
    default current_anim_name = "new_anim"
    default current_anim_data = { "meta": { "name": "new_anim", "duration": 2.0, "loop": True }, "tracks": {} }
    default anim_file_list = get_anim_files()
    
    # Timeline State
    default current_time = 0.0
    default is_playing = False
    default last_preview_time = -1.0
    
    # Object Explorer State
    default explorer_tab = "anims" # "anims" or "objects"
    default object_file_list = get_object_files()
    default current_object_name = "None"

    default renderer = GPURenpystein(
        editor_viewport_width, editor_viewport_height,
        worldMap=worldMap,
        exits=exits,
        objects=stein_objects,
        internal_width=editor_viewport_width // 2,
        internal_height=editor_viewport_height // 2,
        lighting_preset=stein_current_lighting,
        editor_mode=True
    )

    python:
        # Realtime update: only force object state if playing or time moved, and not currently editing
        if renderer.editor_target and editing_field is None:
            if is_playing or current_time != last_preview_time:
                apply_animation_frame(current_anim_data, renderer.editor_target, current_time)
                last_preview_time = current_time
    
    # Voxel Selection State
    default new_group_name = "NewGroup"
    default edit_target_type = "global" # "global" or "group"
    
    # Background
    button:
        action SetScreenVariable("editing_field", None)
        background Solid("#111")
        xfill True yfill True

    key "K_ESCAPE" action SetScreenVariable("editing_field", None)

    # Main layout: hbox separating (viewport+bottom) from (right sidebar)
    hbox:
        # Left column: viewport + bottom toolbar
        vbox:
            # 3D viewport area
            frame:
                background Solid("#222")
                xsize editor_viewport_width
                ysize editor_viewport_height
                padding (0,0)
                
                fixed:
                    # The 3D renderer
                    add renderer
                    
                    # Overlay: tools
                    hbox:
                        align (0.02, 0.05) spacing 10
                        textbutton "Map Builder":
                            action ToggleField(renderer, "builder_mode")
                            background Solid("#0008")
                            padding (10, 5)
                            text_color ("#0F0" if renderer.builder_mode else "#AAA")
                            text_hover_color "#FFF"
                        
                        textbutton "Show Bones":
                            action [ToggleField(renderer, "show_bones"), SetField(renderer, "selection_texture", None)]
                            background Solid("#0008")
                            padding (10, 5)
                            text_color ("#0FF" if renderer.show_bones else "#AAA")
                            text_hover_color "#FFF"
                    
                    # Compass
                    add "pics/compass.webp":
                        zoom 1.0
                        align (0.02, 0.95)
                        at compass_rot(renderer)

            # Bottom Toolbar
            frame:
                background Solid("#333")
                xsize editor_viewport_width
                ysize 200
                padding (10, 10)
                
                hbox:
                    spacing 20
                    
                    # Left: timeline area
                    vbox:
                        xsize int(editor_viewport_width * 0.6)
                        spacing 10
                        
                        # Controls header
                        hbox:
                            spacing 15
                            text "Timeline" size 20 color "#FFF" yalign 0.5
                            
                            textbutton "|<":
                                action SetScreenVariable("current_time", 0.0) 
                                text_color "#DDD"
                            
                            textbutton ("Stop" if is_playing else "Play"):
                                action SetScreenVariable("is_playing", not is_playing)
                                text_color ("#F88" if is_playing else "#8F8")
                            
                            text "Time: [current_time:.2f]s / [current_anim_data['meta']['duration']]s" color "#AAA" yalign 0.5 size 16

                        if is_playing:
                            timer 0.016 repeat True action [
                                SetScreenVariable("current_time", (current_time + 0.016) % max(0.1, current_anim_data['meta']['duration'])),
                                Function(apply_animation_frame, current_anim_data, renderer.editor_target, current_time)
                            ]

                        # Scrubber bar
                        bar:
                            value ScreenVariableValue("current_time", range=current_anim_data['meta']['duration'])
                            xfill True
                            ysize 30
                        
                        # Keyframe markers
                        if current_anim_data.get("tracks"):
                            fixed:
                                ysize 12
                                xfill True
                                
                                # Use a set to get unique time markers
                                python:
                                    all_times = set()
                                    for track in current_anim_data["tracks"].values():
                                        for k in track:
                                            all_times.add(k["time"])
                                    sorted_times = sorted(list(all_times))

                                for kt in sorted_times:
                                    $ k_pos = (kt / max(0.1, current_anim_data['meta']['duration']))
                                    if k_pos <= 1.0:
                                        imagebutton:
                                            idle Solid("#FFFF00")
                                            hover Solid("#FFFFFF")
                                            xsize 6 ysize 10
                                            align (k_pos, 0.5)
                                            # Click to jump to keyframe
                                            action SetScreenVariable("current_time", kt)
                                            tooltip "Jump to [kt:.2f]s"
                    
                    # Separator
                    add Solid("#444") xsize 2 ysize 180
                    
                    # Right: tabbed file explorer
                    vbox:
                        spacing 5
                        
                        # Tabs
                        hbox:
                            spacing 0
                            textbutton "Animations":
                                background Solid("#333" if explorer_tab == "anims" else "#222")
                                xsize 100 ysize 25
                                text_size 14 text_color ("#FFF" if explorer_tab == "anims" else "#888") text_align 0.5
                                action SetScreenVariable("explorer_tab", "anims")
                            textbutton "Objects":
                                background Solid("#333" if explorer_tab == "objects" else "#222")
                                xsize 100 ysize 25
                                text_size 14 text_color ("#FFF" if explorer_tab == "objects" else "#888") text_align 0.5
                                action SetScreenVariable("explorer_tab", "objects")

                        # Content area
                        frame:
                            background Solid("#222")
                            xfill True
                            ysize 110 # Slightly taller to fit content
                            padding (5,5)
                            
                            if explorer_tab == "anims":
                                viewport:
                                    scrollbars "vertical"
                                    mousewheel True
                                    vbox:
                                        for f in anim_file_list:
                                            $ anim_content = load_anim_json(f)
                                            textbutton f:
                                                text_size 14 
                                                text_color "#CCC" 
                                                text_hover_color "#FFF" 
                                                action [
                                                    SetScreenVariable("current_anim_name", f.replace(".json", "")),
                                                    SetScreenVariable("current_anim_data", anim_content),
                                                    # Restore Groups to renderer
                                                    SetField(renderer, "voxel_groups", dict(anim_content.get("voxel_groups", {}))),
                                                    Function(renderer.clean_and_bake_rig),
                                                    Notify("Loaded animation and rig from [f]")
                                                ]
                            
                            elif explorer_tab == "objects":
                                viewport:
                                    scrollbars "vertical"
                                    mousewheel True
                                    vbox:
                                        for f in object_file_list:
                                            textbutton f:
                                                text_size 14 
                                                text_color "#CCC" 
                                                text_hover_color "#FFF" 
                                                action [
                                                    SetScreenVariable("current_object_name", f.replace(".json", "")),
                                                    SetScreenVariable("current_anim_name", "new_anim"),
                                                    SetScreenVariable("current_anim_data", { "meta": { "name": "new_anim", "duration": 2.0, "loop": True }, "tracks": {} }),
                                                    Function(load_object_into_editor, renderer, f)
                                                ]

                        # Footer Controls
                        if explorer_tab == "anims":
                            hbox:
                                spacing 10
                                text "Name:" color "#AAA" yalign 0.5 size 14
                                
                                if editing_field == "anim_name":
                                    input value ScreenVariableInputValue("current_anim_name") length 20 color "#FFF" pixel_width 120 action SetScreenVariable("editing_field", None)
                                else:
                                    textbutton "[current_anim_name]" action SetScreenVariable("editing_field", "anim_name") text_color "#FFF" text_size 14 yalign 0.5

                                textbutton "Save":
                                    action [
                                        SetDict(current_anim_data, "voxel_groups", dict(renderer.voxel_groups)),
                                        Function(save_anim_json, current_anim_data, current_anim_name),
                                        SetScreenVariable("anim_file_list", get_anim_files())
                                    ]
                                    text_color "#8F8" text_size 14 yalign 0.5
                                textbutton "Refresh" action SetScreenVariable("anim_file_list", get_anim_files()) text_color "#FF8" text_size 14 yalign 0.5
                        
                        elif explorer_tab == "objects":
                            hbox:
                                spacing 10
                                text "Selected:" color "#AAA" yalign 0.5 size 14
                                text "[current_object_name]" color "#FFF" yalign 0.5 size 14
                                
                                null width 20
                                textbutton "Refresh List" action SetScreenVariable("object_file_list", get_object_files()) text_color "#FF8" text_size 14 yalign 0.5

        # Right ridebar (properties / outliner)
        frame:
            background Solid("#2b2b2b")
            xsize 300
            ysize 720
            padding (5, 5)
            
            viewport:
                scrollbars "vertical"
                mousewheel True
                draggable True
                pagekeys True
                
                vbox:
                    xsize 280
                    spacing 10
                    
                    text "Properties" size 24 color "#FFF"
                    null height 10
                    
                    text "Selected Object:" size 18 color "#AAA"
                    text "[current_object_name]" size 16 color "#FFF"
                    
                    null height 5
                    
                    # Voxel Selection Info
                    text "Voxel Selection" size 18 color "#AAA"
                    hbox:
                        spacing 10
                        text "Count:" size 14 color "#AAA"
                        $ sel_count = len(renderer.selection_map)
                        text "[sel_count]" size 14 color "#0F0"
                        
                        null width 10
                        textbutton "All":
                            action Function(renderer.select_all_voxels)
                            text_size 14 text_color "#8AF"

                        textbutton "Clear":
                            action [
                                Function(renderer.selection_map.clear),
                                SetField(renderer, "selection_texture", None),
                                SetField(renderer, "highlight_pos", (-1.0, -1.0, -1.0)),
                                Notify("Selection cleared")
                            ]
                            text_size 14 text_color "#F88"
                    
                    hbox:
                        spacing 10
                        text "Last:" size 14 color "#AAA"
                        if renderer.highlight_pos[0] >= 0:
                            text "[renderer.highlight_pos[0]:.0f], [renderer.highlight_pos[1]:.0f], [renderer.highlight_pos[2]:.0f]" size 14 color "#FF0"
                        else:
                            text "None" size 14 color "#666"
                    
                    null height 5
                    
                    # Vertex Groups Section
                    text "Vertex Groups (Bones)" size 18 color "#AAA"
                    frame:
                        background Solid("#222")
                        xfill True
                        ysize 150
                        padding (5,5)
                        viewport:
                            scrollbars "vertical"
                            mousewheel True
                            vbox:
                                for gname in sorted(renderer.voxel_groups.keys()):
                                    $ g_data = renderer.voxel_groups[gname]
                                    $ is_list = isinstance(g_data, list)
                                    $ g_pivot = (-1,-1,-1) if is_list else g_data.get("pivot", (-1,-1,-1))
                                    
                                    vbox:
                                        hbox:
                                            xfill True
                                            textbutton gname:
                                                text_size 14 text_color ("#0FF" if tuple(g_pivot) == renderer.current_pivot and renderer.current_pivot[0] >= 0 else "#CCC")
                                                action Function(renderer.select_group, gname)
                                                xsize 180
                                            
                                            textbutton "Del":
                                                action Function(renderer.delete_group, gname)
                                                text_size 12 text_color "#F66"
                                        
                                        hbox:
                                            spacing 10
                                            text "Pivot: [g_pivot[0]:.0f], [g_pivot[1]:.0f], [g_pivot[2]:.0f]" size 10 color "#6AF"
                                            textbutton "Set":
                                                action Function(renderer.set_group_pivot, gname)
                                                text_size 10 text_color "#FFF"
                                                background Solid("#468")
                                                padding (4, 2)
                                            
                                            $ g_parent = g_data.get("parent", "None") if not is_list else "None"
                                            text "Parent:" size 10 color "#666"
                                            textbutton "[g_parent]":
                                                action Show("select_parent_menu", target_group=gname, renderer=renderer)
                                                text_size 10 text_color "#AAA"
                                                hover_background Solid("#444")

                    hbox:
                        spacing 10
                        if editing_field == "group_name":
                            input value ScreenVariableInputValue("new_group_name") length 15 color "#FFF" pixel_width 120 action SetScreenVariable("editing_field", None)
                        else:
                            textbutton "[new_group_name]" action SetScreenVariable("editing_field", "group_name") text_color "#FFF" text_size 14 yalign 0.5
                        
                        textbutton "Assign":
                            action Function(renderer.assign_to_group, new_group_name)
                            text_size 14 text_color "#8AF" yalign 0.5

                    null height 10
                    
                    null height 10
                    
                    null height 10
                    
                    if renderer.editor_target:
                        text "RIGGING CHANNELS" size 22 color "#FFF"
                        
                        frame:
                            background Solid("#333")
                            xfill True padding (10, 10)
                            vbox:
                                spacing 5
                                hbox:
                                    text "Global Transform" size 16 color "#AAA" yalign 0.5
                                    null width 10
                                    textbutton ("ACTIVE" if edit_target_type == "global" else "SELECT"):
                                        action SetScreenVariable("edit_target_type", "global")
                                        text_size 12 text_color ("#0F0" if edit_target_type == "global" else "#666")

                                if edit_target_type == "global":
                                    hbox:
                                        spacing 5
                                        vbox:
                                            xsize 80
                                            text "Position" size 12 color "#666"
                                            for fld in ['x', 'y', 'z']:
                                                hbox:
                                                    text "[fld!u]: " color "#AAA" yalign 0.5 size 12
                                                    if editing_field == fld:
                                                        input value FloatInputValue(renderer.editor_target, fld) length 12 color "#FFF" pixel_width 80 action SetScreenVariable("editing_field", None)
                                                    else:
                                                        textbutton "[getattr(renderer.editor_target, fld):.2f]" action SetScreenVariable("editing_field", fld) text_color "#FFF" text_size 12
                                        vbox:
                                            xsize 80
                                            text "Rotation" size 12 color "#666"
                                            for fld in ['rx', 'ry', 'rz']:
                                                hbox:
                                                    text "[fld!u]:" color "#AAA" yalign 0.5 size 12
                                                    if editing_field == fld:
                                                        input value FloatInputValue(renderer.editor_target, fld) length 12 color "#FFF" pixel_width 80 action SetScreenVariable("editing_field", None)
                                                    else:
                                                        textbutton "[getattr(renderer.editor_target, fld):.1f]" action SetScreenVariable("editing_field", fld) text_color "#FFF" text_size 12
                                        vbox:
                                            xsize 80
                                            text "Scale" size 12 color "#666"
                                            for fld in ['sx', 'sy', 'sz']:
                                                hbox:
                                                    text "[fld!u]:" color "#AAA" yalign 0.5 size 12
                                                    if editing_field == fld:
                                                        input value FloatInputValue(renderer.editor_target, fld) length 12 color "#FFF" pixel_width 80 action SetScreenVariable("editing_field", None)
                                                    else:
                                                        textbutton "[getattr(renderer.editor_target, fld):.2f]" action SetScreenVariable("editing_field", fld) text_color "#FFF" text_size 12
                                    
                                    hbox:
                                        spacing 10
                                        textbutton "Add Global Key":
                                            action [Function(add_keyframe_auto, "global", "None", renderer, current_anim_data, current_time), Notify("Global Keyframe added") ]
                                            text_size 14 text_color "#8AF"
                                        textbutton "Del":
                                            action [Function(remove_keyframe_auto, "global", "None", current_anim_data, current_time), Notify("Global Keyframe removed") ]
                                            text_size 14 text_color "#F66"

                        null height 10

                        $ active_gname = getattr(renderer, 'selected_group', "None")
                        frame:
                            background Solid("#333")
                            xfill True padding (10, 10)
                            vbox:
                                spacing 5
                                hbox:
                                    text "Bone: [active_gname]" size 16 color "#AAA" yalign 0.5
                                    null width 10
                                    textbutton ("ACTIVE" if edit_target_type == "group" else "SELECT"):
                                        action SetScreenVariable("edit_target_type", "group")
                                        text_size 12 text_color ("#0F0" if edit_target_type == "group" else "#666")

                                if edit_target_type == "group" and active_gname != "None":
                                    $ gdata_obj = renderer.editor_target.get_group_data(active_gname)
                                    hbox:
                                        spacing 5
                                        vbox:
                                            xsize 80
                                            text "Local Pos" size 12 color "#666"
                                            for fld in ['x', 'y', 'z']:
                                                hbox:
                                                    text "[fld!u]: " color "#AAA" yalign 0.5 size 12
                                                    if editing_field == fld:
                                                        input value GroupFloatInputValue(renderer.editor_target, active_gname, fld) length 12 color "#FFF" pixel_width 80 action SetScreenVariable("editing_field", None)
                                                    else:
                                                        textbutton "[gdata_obj.get(fld, 0.0):.2f]" action SetScreenVariable("editing_field", fld) text_color "#FFF" text_size 12
                                        vbox:
                                            xsize 80
                                            text "Local Rot" size 12 color "#666"
                                            for fld in ['rx', 'ry', 'rz']:
                                                hbox:
                                                    text "[fld!u]:" color "#AAA" yalign 0.5 size 12
                                                    if editing_field == fld:
                                                        input value GroupFloatInputValue(renderer.editor_target, active_gname, fld) length 12 color "#FFF" pixel_width 80 action SetScreenVariable("editing_field", None)
                                                    else:
                                                        textbutton "[gdata_obj.get(fld, 0.0):.1f]" action SetScreenVariable("editing_field", fld) text_color "#FFF" text_size 12
                                        vbox:
                                            xsize 80
                                            text "Local Scale" size 12 color "#666"
                                            for fld in ['sx', 'sy', 'sz']:
                                                hbox:
                                                    text "[fld!u]:" color "#AAA" yalign 0.5 size 12
                                                    if editing_field == fld:
                                                        input value GroupFloatInputValue(renderer.editor_target, active_gname, fld) length 12 color "#FFF" pixel_width 80 action SetScreenVariable("editing_field", None)
                                                    else:
                                                        textbutton "[gdata_obj.get(fld, 1.0):.2f]" action SetScreenVariable("editing_field", fld) text_color "#FFF" text_size 12
                                    
                                    hbox:
                                        spacing 10
                                        textbutton "Add Bone Key":
                                            action [Function(add_keyframe_auto, "group", active_gname, renderer, current_anim_data, current_time), Notify("Bone Keyframe added") ]
                                            text_size 14 text_color "#8AF"
                                        textbutton "Del":
                                            action [Function(remove_keyframe_auto, "group", active_gname, current_anim_data, current_time), Notify("Bone Keyframe removed") ]
                                            text_size 14 text_color "#F66"
                                elif active_gname == "None":
                                    text "Select a group to animate" size 12 color "#666" italic True


    textbutton "Exit Editor" action Return() align (1.0, 0.0) offset (-10, -10)

label start_animation_editor:
    $ reset_stein_state(level=5)
    call screen animation_editor
    jump sayoristein_main_menu

screen select_parent_menu(target_group, renderer):
    modal True
    zorder 100
    
    # Backdrop to close
    button:
        action Hide("select_parent_menu")
        background Solid("#0008")
        xfill True yfill True

    frame:
        align (0.5, 0.5)
        background Solid("#222")
        padding (20, 20)
        xsize 300
        
        vbox:
            spacing 10
            text "Select Parent for [target_group]" size 18 color "#FFF"
            null height 10
            
            # None option
            textbutton "None (Root)":
                action [Function(renderer.set_group_parent, target_group, "None"), Hide("select_parent_menu")]
                text_size 16 text_color "#AAA"
            
            # List of other groups
            viewport:
                scrollbars "vertical"
                mousewheel True
                ysize 300
                vbox:
                    for gname in sorted(renderer.voxel_groups.keys()):
                        if gname != target_group:
                            textbutton gname:
                                action [Function(renderer.set_group_parent, target_group, gname), Hide("select_parent_menu")]
                                text_size 16 text_color "#FFF"
                                text_hover_color "#8AF"
            
            null height 10
            textbutton "Cancel":
                action Hide("select_parent_menu")
                align (1.0, 0.0)
                text_color "#F66"
