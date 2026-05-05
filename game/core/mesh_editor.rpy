default mesh_editor_files = []
default mesh_editor_models = []
default mesh_editor_selected_idx = -1
default mesh_editor_tab = "scene"
default mesh_editor_filename = "new_mesh_map"

init python:
    def mesh_map_editor_init():
        store.stein_map_backend = "mesh"
        if not store.meshMap or "instances" not in store.meshMap:
            store.meshMap = empty_mesh_map()
            
        store.mesh_editor_files = get_mesh_map_files()
        store.mesh_editor_models = get_npz_files()
        store.mesh_editor_selected_idx = -1
        store.mesh_editor_tab = "scene"
        store.mesh_editor_filename = "new_mesh_map"
        
    def mesh_editor_add_instance(model_path):
        inst = {
            "model_path": model_path,
            "position": [0.0, 0.0, 0.0],
            "rotation": [0.0, 0.0, 0.0],
            "scale": [1.0, 1.0, 1.0],
            "collision_enabled": True
        }
        store.meshMap["instances"].append(inst)
        store.mesh_editor_selected_idx = len(store.meshMap["instances"]) - 1
        mesh_editor_refresh_engine()
        
    def mesh_editor_refresh_engine():
        store.meshMap_dirty = True
        if getattr(SteinContainer, "engine", None):
            SteinContainer.engine.load_mesh_map(store.meshMap)

    def mesh_editor_delete_instance(idx):
        if 0 <= idx < len(store.meshMap["instances"]):
            store.meshMap["instances"].pop(idx)
            store.mesh_editor_selected_idx = -1
            mesh_editor_refresh_engine()

    def mesh_editor_update_transform(idx, key, comp, value):
        if 0 <= idx < len(store.meshMap["instances"]):
            try:
                store.meshMap["instances"][idx][key][comp] = float(value)
                mesh_editor_refresh_engine()
            except ValueError:
                pass

    def _prompt_filename():
        res = renpy.input("Enter map name:", default=store.mesh_editor_filename)
        if res:
            store.mesh_editor_filename = res
            renpy.restart_interaction()

    def mesh_editor_prompt_filename():
        renpy.invoke_in_new_context(_prompt_filename)

    def mesh_editor_load_map(f):
        store.meshMap = load_mesh_map_json(f)
        store.mesh_editor_filename = f.replace(".json", "")
        mesh_editor_refresh_engine()
        renpy.restart_interaction()

    def _prompt_transform(idx, key, comp):
        val = store.meshMap["instances"][idx][key][comp]
        axes = ["X", "Y", "Z"]
        res = renpy.input("Enter new value for {} {}:".format(key.capitalize(), axes[comp]), default=str(val))
        try:
            new_val = float(res)
            store.meshMap["instances"][idx][key][comp] = new_val
            mesh_editor_refresh_engine()
            renpy.restart_interaction()
        except ValueError:
            pass

    def mesh_editor_prompt_transform(idx, key, comp):
        renpy.invoke_in_new_context(_prompt_transform, idx, key, comp)

    def mesh_editor_nudge_transform(idx, key, comp, sign, step=0.1):
        import pygame_sdl2 as pygame
        if pygame.key.get_pressed()[pygame.K_LSHIFT]:
            step = 1.0
        if 0 <= idx < len(store.meshMap["instances"]):
            val = store.meshMap["instances"][idx][key][comp]
            store.meshMap["instances"][idx][key][comp] = val + (sign * step)
            mesh_editor_refresh_engine()

    def mesh_editor_duplicate_instance(idx):
        if 0 <= idx < len(store.meshMap["instances"]):
            import copy
            new_inst = copy.deepcopy(store.meshMap["instances"][idx])
            store.meshMap["instances"].append(new_inst)
            store.mesh_editor_selected_idx = len(store.meshMap["instances"]) - 1
            mesh_editor_refresh_engine()

screen transform_field(idx, key, comp):
    hbox:
        spacing 2
        textbutton "-" action Function(mesh_editor_nudge_transform, idx, key, comp, -1) text_size 16 background Solid("#333") xsize 20 ysize 25 align (0.5, 0.5)
        
        $ val = store.meshMap["instances"][idx][key][comp]
        textbutton "{:.2f}".format(val):
            action Function(mesh_editor_prompt_transform, idx, key, comp)
            background Solid("#222") xsize 45 ysize 25
            text_size 14 text_align (0.5, 0.5)
            
        textbutton "+" action Function(mesh_editor_nudge_transform, idx, key, comp, 1) text_size 16 background Solid("#333") xsize 20 ysize 25 align (0.5, 0.5)

screen mesh_map_editor():
    predict False
    modal True
    default editor_viewport_width = 1280 - 300
    default editor_viewport_height = 720
    
    default mesh_engine = TaichiEngineDisplayable(mesh_map=store.meshMap)
    
    on "show" action Function(mesh_map_editor_init)
    
    python:
        SteinContainer.engine = mesh_engine
        mesh_engine.set_viewport_res(editor_viewport_width, editor_viewport_height)
            
    # background
    add Solid("#111")

    key "K_ESCAPE" action Return("exit")
    key "s" action None
    key "alt_s" action None
    key "K_f" action None
    key "K_LSHIFT" action None
    key "K_RSHIFT" action None
    key "K_LCTRL" action None
    key "K_RCTRL" action None
    key "mouseup_3" action None
    hbox:
        # viewport
        fixed:
            xsize editor_viewport_width
            ysize editor_viewport_height
            add mesh_engine
            
            text "+" align (0.5, 0.5) size 24 color "#FFF"
            
            vbox:
                align (0.01, 0.01)
                text "Mesh Map Editor" size 24 color "#FF0"
                text "Hold Right Click to move and look (WASD, Mouse)" size 14 color "#AAA"
                add DynamicDisplayable(lambda st, at: (Text("cam xyz: {:.2f}, {:.2f}, {:.2f}".format(SteinContainer.engine.loop.player_x, SteinContainer.engine.loop.player_y, SteinContainer.engine.loop.player_z), size=14, color="#9FE"), 0.1) if SteinContainer.engine else (Null(), 0.1))
                add DynamicDisplayable(lambda st, at: (Text("yaw/pitch: {:.3f}, {:.3f}".format(SteinContainer.engine.loop.player_yaw, SteinContainer.engine.loop.player_pitch), size=14, color="#9FE"), 0.1) if SteinContainer.engine else (Null(), 0.1))
                add DynamicDisplayable(lambda st, at: (Text("rmb/grab: {} / {}".format(SteinContainer.engine.loop.rmb_down, SteinContainer.engine.loop.mouse_initialized), size=14, color="#9FE"), 0.1) if SteinContainer.engine else (Null(), 0.1))
                add DynamicDisplayable(lambda st, at: (Text("geo v/t: {} / {}".format(SteinContainer.engine.scene.num_vertices, SteinContainer.engine.scene.num_triangles), size=14, color="#9FE"), 0.1) if SteinContainer.engine else (Null(), 0.1))

        # sidebar
        vbox:
            xsize 300
            ysize editor_viewport_height
            spacing 10
            xoffset 10
            
            # tabs
            hbox:
                spacing 5
                textbutton "Maps" action SetVariable("mesh_editor_tab", "maps") text_size 16
                textbutton "Models" action SetVariable("mesh_editor_tab", "models") text_size 16
                textbutton "Scene" action SetVariable("mesh_editor_tab", "scene") text_size 16
            
            null height 5
            
            if mesh_editor_tab == "maps":
                text "Save / Load Map" size 20 color "#FFF"
                hbox:
                    text "Name: " size 16 color "#AAA" yalign 0.5
                    textbutton "[mesh_editor_filename]":
                        action Function(mesh_editor_prompt_filename)
                        background Solid("#222")
                        ysize 25 xfill True
                        text_size 16
                
                hbox:
                    spacing 5
                    textbutton "Save Map":
                        action [Function(save_mesh_map_json, meshMap, mesh_editor_filename), Function(mesh_map_editor_init)]
                        background Solid("#282")
                        xfill True
                    textbutton "Save As":
                        action [Function(save_mesh_map_json, meshMap, mesh_editor_filename), Function(mesh_map_editor_init)]
                        background Solid("#258")
                        xfill True
                textbutton "New Map":
                    action [SetVariable("meshMap", empty_mesh_map()), SetVariable("mesh_editor_filename", "new_mesh_map"), SetVariable("mesh_editor_selected_idx", -1), Function(mesh_editor_refresh_engine)]
                    background Solid("#222")
                    xfill True
                
                null height 10
                text "Saved Maps:" size 16 color "#AAA"
                viewport:
                    scrollbars "vertical"
                    mousewheel True
                    vbox:
                        for f in mesh_editor_files:
                            hbox:
                                xfill True
                                textbutton f:
                                    action Function(mesh_editor_load_map, f)
                                    text_size 14
                                    xsize 200
                                textbutton "X":
                                    action Confirm("Delete map " + f + "?", [Function(delete_mesh_map_json, f), Function(mesh_map_editor_init)])
                                    text_size 14
                                    background Solid("#822")
            
            elif mesh_editor_tab == "models":
                text "Available Models (game/models)" size 20 color "#FFF"
                viewport:
                    scrollbars "vertical"
                    mousewheel True
                    vbox:
                        for f in mesh_editor_models:
                            textbutton f:
                                action [Function(mesh_editor_add_instance, f), SetVariable("mesh_editor_tab", "scene")]
                                text_size 14
                                
            elif mesh_editor_tab == "scene":
                text "Instances in Scene" size 20 color "#FFF"
                
                viewport:
                    ysize 200
                    scrollbars "vertical"
                    mousewheel True
                    vbox:
                        if "instances" in meshMap:
                            for idx, inst in enumerate(meshMap["instances"]):
                                $ is_sel = (idx == mesh_editor_selected_idx)
                                hbox:
                                    spacing 5
                                    textbutton "[idx]: [inst['model_path']]":
                                        action SetVariable("mesh_editor_selected_idx", idx)
                                        text_size 14
                                        text_color ("#FF0" if is_sel else "#FFF")
                                        xsize 200
                                    $ is_vis = inst.get("visible", True)
                                    textbutton ("V" if is_vis else "H"):
                                        action [
                                            SetDict(inst, "visible", not is_vis),
                                            Function(mesh_editor_refresh_engine)
                                        ]
                                        text_size 14
                                        text_color ("#FFF" if is_vis else "#888")
                
                null height 10
                
                if mesh_editor_selected_idx >= 0 and mesh_editor_selected_idx < len(meshMap["instances"]):
                    $ sel_inst = meshMap["instances"][mesh_editor_selected_idx]
                    text "Inspector - Instance [mesh_editor_selected_idx]" size 18 color "#FFF"
                    
                    vbox:
                        spacing 5
                        
                        text "Position (X, Y, Z)" size 14 color "#AAA"
                        hbox:
                            spacing 5
                            use transform_field(mesh_editor_selected_idx, "position", 0)
                            use transform_field(mesh_editor_selected_idx, "position", 1)
                            use transform_field(mesh_editor_selected_idx, "position", 2)
                                
                        text "Rotation (Yaw, Pitch, Roll)" size 14 color "#AAA"
                        hbox:
                            spacing 5
                            use transform_field(mesh_editor_selected_idx, "rotation", 0)
                            use transform_field(mesh_editor_selected_idx, "rotation", 1)
                            use transform_field(mesh_editor_selected_idx, "rotation", 2)
                                
                        text "Scale (X, Y, Z)" size 14 color "#AAA"
                        hbox:
                            spacing 5
                            use transform_field(mesh_editor_selected_idx, "scale", 0)
                            use transform_field(mesh_editor_selected_idx, "scale", 1)
                            use transform_field(mesh_editor_selected_idx, "scale", 2)
                                
                        null height 10
                        hbox:
                            spacing 5
                            textbutton "Duplicate":
                                action Function(mesh_editor_duplicate_instance, mesh_editor_selected_idx)
                                background Solid("#258")
                                xfill True
                            textbutton "Delete":
                                action Confirm("Delete Instance?", Function(mesh_editor_delete_instance, mesh_editor_selected_idx))
                                background Solid("#822")
                                xfill True

label start_mesh_editor:
    python:
        mesh_map_editor_init()
        reset_stein_state()
        
    call screen mesh_map_editor
    
    python:
        if getattr(SteinContainer, "engine", None):
            SteinContainer.engine = None
    return
