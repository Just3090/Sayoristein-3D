init python:
    def mesh_map_editor_init():
        if "stein_map_backend" not in store.__dict__:
            store.stein_map_backend = "mesh"
        if not store.meshMap or "instances" not in store.meshMap:
            store.meshMap = {"version": "1.0", "type": "mesh_map", "instances": []}
            
        store.mesh_editor_files = get_mesh_map_files()
        store.mesh_editor_models = get_obj_files()
        store.mesh_editor_selected_idx = -1
        store.mesh_editor_tab = "scene"
        store.mesh_editor_filename = "new_mesh_map"
        
    def mesh_editor_add_instance(obj_path):
        inst = {
            "obj_path": obj_path,
            "position": [0.0, 0.0, 0.0],
            "rotation": [0.0, 0.0, 0.0],
            "scale": [1.0, 1.0, 1.0],
            "collision_enabled": True
        }
        store.meshMap["instances"].append(inst)
        store.mesh_editor_selected_idx = len(store.meshMap["instances"]) - 1
        mesh_editor_refresh_engine()
        
    def mesh_editor_refresh_engine():
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

screen mesh_map_editor():
    modal True
    default editor_viewport_width = 1280 - 300
    default editor_viewport_height = 720
    
    default mesh_engine = TaichiEngineDisplayable(mesh_map=store.meshMap)
    
    on "show" action Function(mesh_map_editor_init)
    
    python:
        SteinContainer.engine = mesh_engine
        ed_w, ed_h = int(editor_viewport_width), int(editor_viewport_height)
        ed_tup = (ed_w, ed_h)
        if getattr(mesh_engine, "editor_viewport_res", None) != ed_tup:
            mesh_engine.editor_viewport_res = ed_tup
            mesh_engine.reapply_quality()
            
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
            timer 0.05 repeat True action Function(renpy.restart_interaction)
            add mesh_engine
            
            text "+" align (0.5, 0.5) size 24 color "#FFF"
            
            vbox:
                align (0.01, 0.01)
                text "Mesh Map Editor" size 24 color "#FF0"
                text "Hold Right Click to move and look (WASD, Mouse)" size 14 color "#AAA"
                text "cam xyz: [mesh_engine.player_x:.2f], [mesh_engine.player_y:.2f], [mesh_engine.player_z:.2f]" size 14 color "#9FE"
                text "yaw/pitch: [mesh_engine.player_yaw:.3f], [mesh_engine.player_pitch:.3f]" size 14 color "#9FE"
                text "rmb/grab: [mesh_engine.rmb_down] / [mesh_engine.mouse_initialized]" size 14 color "#9FE"
                text "geo v/t: [global_num_vertices] / [global_num_triangles]" size 14 color "#9FE"

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
                    button:
                        action None
                        background Solid("#222")
                        ysize 25 xfill True
                        text "[mesh_editor_filename]" size 16
                
                textbutton "Save Map":
                    action [Function(save_mesh_map_json, meshMap, mesh_editor_filename), Function(mesh_map_editor_init)]
                    background Solid("#282")
                    xfill True
                
                null height 10
                text "Saved Maps:" size 16 color "#AAA"
                viewport:
                    scrollbars "vertical"
                    mousewheel True
                    vbox:
                        for f in mesh_editor_files:
                            textbutton f:
                                action [
                                    SetVariable("meshMap", load_mesh_map_json(f)),
                                    SetVariable("mesh_editor_filename", f.replace(".json", "")),
                                    Function(mesh_editor_refresh_engine)
                                ]
                                text_size 14
            
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
                                textbutton "[idx]: [inst['obj_path']]":
                                    action SetVariable("mesh_editor_selected_idx", idx)
                                    text_size 14
                                    text_color ("#FF0" if is_sel else "#FFF")
                
                null height 10
                
                if mesh_editor_selected_idx >= 0 and mesh_editor_selected_idx < len(meshMap["instances"]):
                    $ sel_inst = meshMap["instances"][mesh_editor_selected_idx]
                    text "Inspector - Instance [mesh_editor_selected_idx]" size 18 color "#FFF"
                    
                    vbox:
                        spacing 5
                        
                        text "Position (X, Y, Z)" size 14 color "#AAA"
                        hbox:
                            spacing 5
                            button:
                                background Solid("#333") xsize 80
                                text str(sel_inst["position"][0]) size 14
                            button:
                                background Solid("#333") xsize 80
                                text str(sel_inst["position"][1]) size 14
                            button:
                                background Solid("#333") xsize 80
                                text str(sel_inst["position"][2]) size 14
                                
                        text "Rotation (Yaw, Pitch, Roll)" size 14 color "#AAA"
                        hbox:
                            spacing 5
                            button:
                                background Solid("#333") xsize 80
                                text str(sel_inst["rotation"][0]) size 14
                            button:
                                background Solid("#333") xsize 80
                                text str(sel_inst["rotation"][1]) size 14
                            button:
                                background Solid("#333") xsize 80
                                text str(sel_inst["rotation"][2]) size 14
                                
                        text "Scale (X, Y, Z)" size 14 color "#AAA"
                        hbox:
                            spacing 5
                            button:
                                background Solid("#333") xsize 80
                                text str(sel_inst["scale"][0]) size 14
                            button:
                                background Solid("#333") xsize 80
                                text str(sel_inst["scale"][1]) size 14
                            button:
                                background Solid("#333") xsize 80
                                text str(sel_inst["scale"][2]) size 14
                                
                        null height 10
                        textbutton "Delete Instance":
                            action Function(mesh_editor_delete_instance, mesh_editor_selected_idx)
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
