init -10 python:
    import pygame
    import sys
    import io
    import subprocess
    import struct
    import threading
    import os
    import math
    import copy

    class GPURenpystein(renpy.Displayable):
        def __init__(self, width, height, worldMap=None, exits=[], internal_width=None, internal_height=None, lighting_preset=None, **kwargs):
            super(GPURenpystein, self).__init__(**kwargs)
            self.width = width
            self.height = height
            self.surface = None
            self.running = False
            
            import math
            import renpy.store as store
            self.is_arena_mode = getattr(store, 'is_arena_mode', False)

            self.x = float(getattr(store, "player_y", 11.5))
            self.z = float(getattr(store, "player_x", 22.0))
            
            dirx = float(getattr(store, "player_dirx", -1.0)) # Row direction (Z)
            diry = float(getattr(store, "player_diry", 0.0))  # Col direction (X)
            self.yaw = math.degrees(math.atan2(dirx, diry))
            
            self.pitch = 0.0
            self.y = 3.0
            
            self.keys = {'w':False, 's':False, 'a':False, 'd':False, 
                        'left':False, 'right':False, 'up':False, 'down':False,
                        'space':False, 'shift':False, 'ctrl':False, 'shoot':False, 'aim':False}
            self.active_weapon = 1
            
            self.event_queue = []
            
            self.mouse_grabbed = False
            self.mouse_dx = 0.0
            self.mouse_dy = 0.0
            self.flashlight_active = False
            
            self.time_since_last_damage = 0.0
            self.damage_flash_timer = 0.0
            self.heal_flash_timer = 0.0
            self.hit_marker_timer = 0.0
            self.pickup_msg = ""
            self.pickup_msg_timer = 0.0
            self.damage_indicators = []
            self.inter_round_timer = 0.0
            self.show_debug_overlay = False
            self.dev_edit_mode = 0 # 0: pos, 1: rot, 2: scale
            self.dev_edit_target = 'hip' # 'hip' or 'ads'
            
            self.weapon_offsets = {
                0: {'hip_x': 0.0, 'hip_y': 0.0, 'hip_z': 0.0, 'ads_x': 0.0, 'ads_y': 0.0, 'ads_z': 0.0, 'pitch': 0.0, 'yaw': 0.0, 'roll': 0.0, 'scale': 0.0},
                1: {'hip_x': 0.0, 'hip_y': 0.0, 'hip_z': 0.0, 'ads_x': 0.0, 'ads_y': 0.0, 'ads_z': 0.0, 'pitch': 0.0, 'yaw': 0.0, 'roll': 0.0, 'scale': 0.0},
                2: {'hip_x': 0.0, 'hip_y': 0.0, 'hip_z': 0.0, 'ads_x': 0.0, 'ads_y': 0.0, 'ads_z': 0.0, 'pitch': 0.0, 'yaw': 0.0, 'roll': 0.0, 'scale': 0.0},
                3: {'hip_x': 0.0, 'hip_y': 0.0, 'hip_z': 0.0, 'ads_x': 0.0, 'ads_y': 0.0, 'ads_z': 0.0, 'pitch': 0.0, 'yaw': 0.0, 'roll': 0.0, 'scale': 0.0},
            }
            
            self.return_value = None
            self.exits = exits if exits else []
            self.oldst = None
            
            renpy.store.stein_player_health = 100
            renpy.store.stein_session_coins = 0
            
            try:
                self.sight_img = pygame.image.load(os.path.join(config.gamedir, "pics", "gui", "sight.png")).convert_alpha()
                self.arrow_img = pygame.image.load(os.path.join(config.gamedir, "pics", "gui", "arrow_d.webp")).convert_alpha()
                self.hit_marker_img = pygame.image.load(os.path.join(config.gamedir, "pics", "gui", "damage_x.webp")).convert_alpha()
            except Exception as e:
                print(f"Failed to load images: {e}")
                self.sight_img = None
                self.arrow_img = None
                self.hit_marker_img = None
            
            exe_name = "raylib_server.exe" if renpy.windows else "raylib_server"
            exe_path = os.path.join(config.gamedir, "core", exe_name)
            
            try:
                log_path = os.path.join(config.gamedir, "core", "server_log.txt")
                self.log_file = open(log_path, "w")
                
                kwargs = {}
                if renpy.windows:
                    kwargs["creationflags"] = 0x08000000
                    
                self.process = subprocess.Popen(
                    [exe_path], 
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE, 
                    stderr=self.log_file, 
                    cwd=config.basedir,
                    bufsize=0,
                    **kwargs
                )
                self.running = True
            except Exception as e:
                print(f"Failed to start raylib_server: {e}")
                self.running = False
                
            if self.running:
                map_dict = {}
                if isinstance(worldMap, dict):
                    map_dict = worldMap
                elif isinstance(worldMap, list):
                    map_dict = {0: worldMap}
                
                if not map_dict:
                    map_dict = {0: [[1 if x == 0 or x == 9 or y == 0 or y == 9 else 0 for x in range(10)] for y in range(10)]}
                self.map_dict = map_dict
                
                min_layer = min(map_dict.keys())
                max_layer = max(map_dict.keys())
                self.layers = max_layer - min_layer + 1
                
                self.mapHeight = max(len(grid) for grid in map_dict.values())
                self.mapWidth = max((max(len(row) for row in grid) if grid else 0) for grid in map_dict.values())
                
                map_array = []
                for z in range(min_layer, max_layer + 1):
                    grid = map_dict.get(z, [])
                    for y in range(self.mapHeight):
                        row = grid[y] if y < len(grid) else []
                        for x in range(self.mapWidth):
                            val = row[x] if x < len(row) else 0
                            map_array.append(val)
                            
                qm = getattr(persistent, "stein_quality_mode", 1)
                w = internal_width if internal_width else width
                h = internal_height if internal_height else height
                
                if qm == 4:
                    rw, rh = int(w*1.5), int(h*1.5)
                elif qm == 0:
                    rw, rh = int(w), int(h)
                elif qm == 1:
                    rw, rh = int(w*0.5), int(h*0.5)
                elif qm == 2:
                    rw, rh = int(w*0.25), int(h*0.25)
                elif qm == 3:
                    rw, rh = int(w*0.1), int(h*0.1)
                else:
                    rw, rh = 64, 64
                
                self.render_width = max(64, rw)
                self.render_height = max(64, rh)
                            
                # format: render_width, render_height, map_width, map_height, layers, is_arena_mode, [map_array], start_x, start_y, start_z, start_pitch, start_yaw
                try:
                    arena_flag = 1 if self.is_arena_mode else 0
                    enemies = getattr(store, "stein_enemies", [])
                    sprites = getattr(store, "stein_sprites", [])
                    spawn_points = getattr(store, "arena_spawn_points", [])
                    
                    fmt = f"iiiiii{len(map_array)}i fffff i i i"
                    args = [self.render_width, self.render_height, self.mapWidth, self.mapHeight, self.layers, arena_flag]
                    args.extend(map_array)
                    args.extend([self.x, self.y, self.z, self.pitch, self.yaw])
                    args.extend([len(enemies), len(sprites), len(spawn_points)])
                    
                    for e in enemies:
                        fmt += "ffii"
                        args.extend([float(e[1]), float(e[0]), int(e[2]), int(e[3])])
                        
                    for s in sprites:
                        fmt += "ffi"
                        args.extend([float(s[1]), float(s[0]), int(s[2])])
                        
                    for sp in spawn_points:
                        fmt += "ff"
                        args.extend([float(sp[1]), float(sp[0])])
                        
                    init_data = struct.pack(fmt, *args)
                    self.process.stdin.write(init_data)
                    self.process.stdin.flush()
                except Exception as e:
                    print(f"Failed to send map init: {e}")
                    self.running = False
                    
            if self.running:
                self.thread = threading.Thread(target=self._read_loop)
                self.thread.daemon = True
                self.thread.start()
                
        def _read_loop(self):
            while self.running and self.process.poll() is None:
                try:
                    type_data = b""
                    while len(type_data) < 4:
                        chunk = self.process.stdout.read(4 - len(type_data))
                        if not chunk: break
                        type_data += chunk
                    if len(type_data) < 4: break
                    msg_type = struct.unpack("i", type_data)[0]
                    
                    if msg_type == 0:
                        size_data = b""
                        while len(size_data) < 4:
                            chunk = self.process.stdout.read(4 - len(size_data))
                            if not chunk: break
                            size_data += chunk
                        if len(size_data) < 4: break
                        size = struct.unpack("i", size_data)[0]
                        
                        img_data = b""
                        while len(img_data) < size:
                            chunk = self.process.stdout.read(size - len(img_data))
                            if not chunk: break
                            img_data += chunk
                        if len(img_data) < size: break
                            
                        surf = pygame.image.load(io.BytesIO(img_data), "frame.bmp")
                        self.surface = surf
                    elif msg_type == 1:
                        ev_data = b""
                        while len(ev_data) < 8:
                            chunk = self.process.stdout.read(8 - len(ev_data))
                            if not chunk: break
                            ev_data += chunk
                        if len(ev_data) < 8: break
                        event_id, event_val = struct.unpack("ii", ev_data)
                        self.event_queue.append((event_id, event_val))
                except Exception as e:
                    print(f"Read loop exception: {e}")
                    break
            self.running = False

        def event(self, ev, x, y, st):
            import pygame
            import copy
            if self.return_value is not None:
                rv = self.return_value
                self.return_value = None
                return rv

            if ev.type == pygame.MOUSEBUTTONDOWN:
                if ev.button == 1:
                    if not self.mouse_grabbed:
                        self.mouse_grabbed = True
                        pygame.mouse.set_visible(False)
                        pygame.event.set_grab(True)
                    else:
                        self.keys['shoot'] = True
                elif ev.button == 3:
                    self.keys['aim'] = True
            elif ev.type == pygame.MOUSEBUTTONUP:
                if ev.button == 1:
                    self.keys['shoot'] = False
                elif ev.button == 3:
                    self.keys['aim'] = False
            elif ev.type == pygame.MOUSEMOTION and self.mouse_grabbed:
                sens = getattr(persistent, "stein_mouse_sens", 1.0)
                dx, dy = ev.rel
                self.mouse_dx += dx * 0.2 * sens
                self.mouse_dy -= dy * 0.2 * sens
                self.yaw += dx * 0.2 * sens
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_w: self.keys['w'] = True
                elif ev.key == pygame.K_s: self.keys['s'] = True
                elif ev.key == pygame.K_a: self.keys['a'] = True
                elif ev.key == pygame.K_d: self.keys['d'] = True
                elif ev.key == pygame.K_LEFT: self.keys['left'] = True
                elif ev.key == pygame.K_RIGHT: self.keys['right'] = True
                elif ev.key == pygame.K_UP: self.keys['up'] = True
                elif ev.key == pygame.K_DOWN: self.keys['down'] = True
                elif ev.key == pygame.K_SPACE: self.keys['space'] = True
                elif ev.key == pygame.K_LSHIFT: self.keys['shift'] = True
                elif ev.key == pygame.K_LCTRL: self.keys['ctrl'] = True
                elif ev.key == pygame.K_f: self.flashlight_active = not self.flashlight_active
                elif ev.key == pygame.K_F3:
                    self.show_debug_overlay = not self.show_debug_overlay
                elif ev.key == pygame.K_1: self.active_weapon = 0
                elif ev.key == pygame.K_2: self.active_weapon = 1
                elif ev.key == pygame.K_3: self.active_weapon = 2
                elif ev.key == pygame.K_4: self.active_weapon = 3
                elif self.show_debug_overlay and getattr(config, 'developer', True) and ev.key == pygame.K_p:
                    wp_names = ["SWORD", "PISTOL", "SHOTGUN", "MINIGUN"]
                    cur_name = wp_names[self.active_weapon] if self.active_weapon < 4 else "UNKNOWN"
                    t = self.weapon_offsets[self.active_weapon]
                    print(f"\n")
                    print(f"// Weapon {self.active_weapon} ({cur_name}) delta offsets:")
                    print(f"Vector3 hip_offset = {{ {t['hip_x']:+.4f}f, {t['hip_y']:+.4f}f, {t['hip_z']:+.4f}f }};")
                    print(f"Vector3 ads_offset = {{ {t['ads_x']:+.4f}f, {t['ads_y']:+.4f}f, {t['ads_z']:+.4f}f }};")
                    print(f"float pitch_offset = {t['pitch']:+.2f}f;")
                    print(f"float yaw_offset   = {t['yaw']:+.2f}f;")
                    print(f"float roll_offset  = {t['roll']:+.2f}f;")
                    print(f"float scale_offset = {t['scale']:+.4f}f;")
                    print(f"\n")
                    self.pickup_msg = f"{cur_name} OFFSETS PRINTED TO LOG"
                    self.pickup_msg_timer = 2.0
                elif self.show_debug_overlay and getattr(config, 'developer', True):
                    t = self.weapon_offsets[self.active_weapon]
                    prefix = 'ads_' if self.dev_edit_target == 'ads' else 'hip_'
                    
                    pos_step = 0.001
                    rot_step = 0.5
                    scale_step = 0.001
                    
                    if self.keys['shift']:
                        pos_step *= 5.0
                        rot_step *= 4.0
                        scale_step *= 5.0
                    elif self.keys['ctrl']:
                        pos_step *= 0.2
                        rot_step *= 0.2
                        scale_step *= 0.2

                    if ev.key in (pygame.K_KP0, pygame.K_0):
                        self.dev_edit_mode = (self.dev_edit_mode + 1) % 3
                    elif ev.key in (pygame.K_KP_DIVIDE, pygame.K_KP_ENTER, pygame.K_TAB):
                        self.dev_edit_target = 'ads' if self.dev_edit_target == 'hip' else 'hip'
                    elif ev.key in (pygame.K_KP_PERIOD,):
                        self.weapon_offsets[self.active_weapon] = {'hip_x':0.0, 'hip_y':0.0, 'hip_z':0.0, 'ads_x':0.0, 'ads_y':0.0, 'ads_z':0.0, 'pitch':0.0, 'yaw':0.0, 'roll':0.0, 'scale':0.0}
                    elif ev.key in (pygame.K_KP_PLUS, pygame.K_PLUS, pygame.K_EQUALS):
                        t['scale'] += scale_step
                    elif ev.key in (pygame.K_KP_MINUS, pygame.K_MINUS):
                        t['scale'] = max(0.001, t['scale'] - scale_step)
                    elif self.dev_edit_mode == 0: # pos
                        if ev.key in (pygame.K_KP4,): t[prefix + 'x'] -= pos_step
                        elif ev.key in (pygame.K_KP6,): t[prefix + 'x'] += pos_step
                        elif ev.key in (pygame.K_KP8,): t[prefix + 'y'] += pos_step
                        elif ev.key in (pygame.K_KP2,): t[prefix + 'y'] -= pos_step
                        elif ev.key in (pygame.K_KP7,): t[prefix + 'z'] += pos_step
                        elif ev.key in (pygame.K_KP9,): t[prefix + 'z'] -= pos_step
                    elif self.dev_edit_mode == 1: # rot
                        if ev.key in (pygame.K_KP4,): t['yaw'] -= rot_step
                        elif ev.key in (pygame.K_KP6,): t['yaw'] += rot_step
                        elif ev.key in (pygame.K_KP8,): t['pitch'] += rot_step
                        elif ev.key in (pygame.K_KP2,): t['pitch'] -= rot_step
                        elif ev.key in (pygame.K_KP7,): t['roll'] += rot_step
                        elif ev.key in (pygame.K_KP9,): t['roll'] -= rot_step
                    elif self.dev_edit_mode == 2: # scale
                        if ev.key in (pygame.K_KP8, pygame.K_KP6): t['scale'] += scale_step
                        elif ev.key in (pygame.K_KP2, pygame.K_KP4): t['scale'] = max(0.001, t['scale'] - scale_step)
                elif ev.key == pygame.K_ESCAPE:
                    if self.mouse_grabbed:
                        self.mouse_grabbed = False
                        pygame.mouse.set_visible(True)
                        pygame.event.set_grab(False)
                    else:
                        self.destroy()
                        return "quit"
                if self.mouse_grabbed:
                    raise renpy.IgnoreEvent()
            elif ev.type == pygame.KEYUP:
                if ev.key == pygame.K_w: self.keys['w'] = False
                elif ev.key == pygame.K_s: self.keys['s'] = False
                elif ev.key == pygame.K_a: self.keys['a'] = False
                elif ev.key == pygame.K_d: self.keys['d'] = False
                elif ev.key == pygame.K_LEFT: self.keys['left'] = False
                elif ev.key == pygame.K_RIGHT: self.keys['right'] = False
                elif ev.key == pygame.K_UP: self.keys['up'] = False
                elif ev.key == pygame.K_DOWN: self.keys['down'] = False
                elif ev.key == pygame.K_SPACE: self.keys['space'] = False
                elif ev.key == pygame.K_LSHIFT: self.keys['shift'] = False
                elif ev.key == pygame.K_LCTRL: self.keys['ctrl'] = False
                if self.mouse_grabbed:
                    raise renpy.IgnoreEvent()
            return None

        def render(self, width, height, st, at):
            if self.oldst is None:
                self.oldst = st
            dt = st - self.oldst
            self.oldst = st
            if dt > 0.1:
                dt = 0.1

            if self.running and self.process.stdin:
                try:
                    time_of_day = getattr(renpy.store, "u_time_of_day", 12.0)
                    light_quality = getattr(persistent, "stein_lighting_quality", 0)
                    shadows_en = 1 if getattr(persistent, "stein_enable_shadows", False) else 0
                    bloom_en = 1 if getattr(persistent, "stein_enable_bloom", False) else 0
                    clouds_en = 1 if getattr(persistent, "stein_volumetric_clouds", False) else 0
                    soft_shadows = 1 if getattr(persistent, "stein_soft_shadows", False) else 0
                    
                    w_key = 1 if self.keys['w'] else 0
                    s_key = 1 if self.keys['s'] else 0
                    a_key = 1 if self.keys['a'] else 0
                    d_key = 1 if self.keys['d'] else 0
                    left_key = 1 if self.keys['left'] else 0
                    right_key = 1 if self.keys['right'] else 0
                    up_key = 1 if self.keys['up'] else 0
                    down_key = 1 if self.keys['down'] else 0
                    space_key = 1 if self.keys['space'] else 0
                    shift_key = 1 if self.keys['shift'] else 0
                    ctrl_key = 1 if self.keys['ctrl'] else 0
                    shoot_key = 1 if self.keys['shoot'] else 0
                    aim_key = 1 if (self.keys['aim'] or (self.show_debug_overlay and getattr(config, 'developer', True) and self.dev_edit_target == 'ads')) else 0
                    
                    p_lvl = int(getattr(persistent, "stein_pistol_level", 0))
                    s_lvl = int(getattr(persistent, "stein_shotgun_level", 0))
                    m_lvl = int(getattr(persistent, "stein_minigun_level", 0))
                    fl_val = 1 if self.flashlight_active else 0
                    
                    weather_en_toggle = getattr(persistent, "stein_enable_weather", False)
                    rain_intensity = float(getattr(renpy.store, "u_rain_intensity", 0.0))
                    if not weather_en_toggle:
                        rain_intensity = 0.0
                    
                    t = self.weapon_offsets.get(self.active_weapon, {'hip_x':0.0, 'hip_y':0.0, 'hip_z':0.0, 'ads_x':0.0, 'ads_y':0.0, 'ads_z':0.0, 'pitch':0.0, 'yaw':0.0, 'roll':0.0, 'scale':0.0})
                    wp_hip_x = float(t['hip_x'])
                    wp_hip_y = float(t['hip_y'])
                    wp_hip_z = float(t['hip_z'])
                    wp_ads_x = float(t['ads_x'])
                    wp_ads_y = float(t['ads_y'])
                    wp_ads_z = float(t['ads_z'])
                    wp_pitch = float(t['pitch'])
                    wp_yaw = float(t['yaw'])
                    wp_roll = float(t['roll'])
                    wp_scale = float(t['scale'])
                    mb_strength = float(getattr(persistent, "stein_motion_blur_strength", 0.3))
                    
                    data = struct.pack("iiii iiii iiii ff f i i i i i f i i iii i fff fff fff f f", 
                                        w_key, s_key, a_key, d_key,
                                        left_key, right_key, up_key, down_key,
                                        space_key, shift_key, ctrl_key, shoot_key,
                                        float(self.mouse_dx), float(self.mouse_dy),
                                        float(time_of_day), int(light_quality), int(shadows_en),
                                        int(self.active_weapon),
                                        bloom_en, clouds_en, rain_intensity, soft_shadows,
                                        aim_key, p_lvl, s_lvl, m_lvl, fl_val,
                                        wp_hip_x, wp_hip_y, wp_hip_z,
                                        wp_ads_x, wp_ads_y, wp_ads_z,
                                        wp_pitch, wp_yaw, wp_roll, wp_scale,
                                        mb_strength)
                    self.process.stdin.write(data)
                    self.process.stdin.flush()
                    self.mouse_dx = 0.0
                    self.mouse_dy = 0.0
                except Exception as e:
                    print(f"Failed to send frame packet: {e}")
            
            while len(self.event_queue) > 0:
                ev_id, ev_val = self.event_queue.pop(0)
                if ev_id == 1:
                    if ev_val == 7: # medkit
                        renpy.store.stein_player_health = min(100, getattr(renpy.store, "stein_player_health", 100) + 25)
                        self.heal_flash_timer = 0.2
                        self.pickup_msg = "+25 HEALTH"
                        self.pickup_msg_timer = 2.0
                        renpy.sound.play("sounds/pew.ogg", channel="sound")
                    elif ev_val == 8: # cookie
                        renpy.store.stein_player_health = 100
                        self.heal_flash_timer = 0.3
                        self.pickup_msg = "FULL HEALTH RESTORED"
                        self.pickup_msg_timer = 3.0
                        renpy.sound.play("sounds/pew.ogg", channel="sound")
                    elif ev_val == 11 or ev_val == 12: # coins
                        renpy.store.stein_session_coins += 100
                        self.pickup_msg = "+100 COINS"
                        self.pickup_msg_timer = 2.0
                        renpy.sound.play("sounds/pew.ogg", channel="sound")
                    elif ev_val == 13: # shotgun
                        renpy.store.stein_has_shotgun = True
                        self.pickup_msg = "SHOTGUN ACQUIRED"
                        self.pickup_msg_timer = 3.0
                        renpy.sound.play("sounds/pew.ogg", channel="sound")
                    elif ev_val == 15: # minigun
                        renpy.store.stein_has_minigun = True
                        self.pickup_msg = "MINIGUN ACQUIRED"
                        self.pickup_msg_timer = 3.0
                        renpy.sound.play("sounds/pew.ogg", channel="sound")
                elif ev_id == 20: # weapon fired
                    if ev_val == 0: renpy.sound.play("sounds/punch.ogg", channel="audio")
                    elif ev_val == 1: renpy.sound.play("sounds/gunshot.ogg", channel="audio")
                    elif ev_val == 2: renpy.sound.play("sounds/shotgun.ogg", channel="audio")
                    elif ev_val == 3: renpy.sound.play("sounds/gunshot.ogg", channel="audio")
                elif ev_id == 10: # enemy hit
                    self.hit_marker_timer = 0.15
                    renpy.sound.play("sounds/ow.ogg", channel="sound")
                elif ev_id == 11: # enemy dead
                    renpy.store.persistent.stein_kills += 1
                    renpy.sound.play("sounds/ow.ogg", channel="sound")
                elif ev_id == 12: # player damaged
                    self.damage_flash_timer = 0.2
                    self.time_since_last_damage = 0.0
                    renpy.sound.play("sounds/e-gunshot.ogg", channel="sound")
                    renpy.store.stein_player_health -= 10
                    if renpy.store.stein_player_health < 0:
                        renpy.store.stein_player_health = 0
                    self.damage_indicators.append({
                        'world_angle': float(ev_val),
                        'duration': 1.5,
                        'max_duration': 1.5
                    })
                elif ev_id == 30: # arena round update
                    renpy.store.stein_current_round = ev_val
                    self.inter_round_timer = 0.0
                elif ev_id == 31: # arena inter round break
                    self.inter_round_timer = float(ev_val)

            self.time_since_last_damage += dt
            if self.time_since_last_damage > 2.5 and renpy.store.stein_player_health < 100 and renpy.store.stein_player_health > 0:
                renpy.store.stein_player_health = min(100.0, renpy.store.stein_player_health + 31.67 * dt)

            if renpy.store.stein_player_health <= 0:
                renpy.store.stein_player_health = 0
                if self.return_value is None:
                    if self.is_arena_mode:
                        renpy.store.last_arena_round = getattr(renpy.store, "stein_current_round", 1)
                        renpy.store.new_highscore = False
                        if renpy.store.last_arena_round > getattr(persistent, "sayoristein_arena_highscore", 0):
                            persistent.sayoristein_arena_highscore = renpy.store.last_arena_round
                            renpy.store.new_highscore = True
                        self.return_value = 'game_over_arena'
                    else:
                        self.return_value = 'game_over'
                    pygame.mouse.set_visible(True)
                    pygame.event.set_grab(False)
                    self.destroy()
                    renpy.timeout(0)

            render = renpy.Render(self.width, self.height)
            if self.surface:
                scaled = pygame.transform.scale(self.surface, (self.width, self.height))
                render.blit(scaled, (0, 0))

            if self.damage_flash_timer > 0:
                self.damage_flash_timer = max(0, self.damage_flash_timer - dt)
            flash_alpha = int(140 * (self.damage_flash_timer / 0.2)) if self.damage_flash_timer > 0 else 0
            cur_hp = getattr(renpy.store, "stein_player_health", 100)
            health_alpha = int(((70.0 - cur_hp) / 70.0) * 160) if cur_hp < 70 else 0
            red_alpha = min(255, max(flash_alpha, health_alpha))
            if red_alpha > 0:
                flash_surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
                flash_surf.fill((255, 0, 0, red_alpha))
                render.blit(flash_surf, (0, 0))

            if self.heal_flash_timer > 0:
                self.heal_flash_timer = max(0, self.heal_flash_timer - dt)
                h_alpha = int(128 * (self.heal_flash_timer / 0.2))
                if h_alpha > 0:
                    heal_surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
                    heal_surf.fill((0, 255, 0, h_alpha))
                    render.blit(heal_surf, (0, 0))

            if self.sight_img:
                sw, sh = self.sight_img.get_size()
                render.blit(self.sight_img, (self.width / 2 - sw / 2, self.height / 2 - sh / 2))

            if self.hit_marker_timer > 0:
                self.hit_marker_timer = max(0, self.hit_marker_timer - dt)
                if self.hit_marker_img:
                    hw, hh = self.hit_marker_img.get_size()
                    render.blit(self.hit_marker_img, (self.width / 2 - hw / 2, self.height / 2 - hh / 2))

            center_x = self.width / 2
            center_y = self.height / 2
            indicator_radius = 200

            for ind in list(self.damage_indicators):
                ind['duration'] -= dt
                if ind['duration'] <= 0:
                    self.damage_indicators.remove(ind)
                    continue
                if self.arrow_img:
                    alpha_ratio = ind['duration'] / ind['max_duration']
                    diff_deg = ind['world_angle'] - self.yaw
                    diff_rad = math.radians(diff_deg)
                    
                    ix = center_x + indicator_radius * math.sin(diff_rad)
                    iy = center_y - indicator_radius * math.cos(diff_rad)
                    
                    rot_img = pygame.transform.rotate(self.arrow_img, -diff_deg)
                    rot_img.set_alpha(int(255 * alpha_ratio))
                    rw, rh = rot_img.get_size()
                    render.blit(rot_img, (ix - rw / 2, iy - rh / 2))

            if self.pickup_msg_timer > 0:
                self.pickup_msg_timer = max(0, self.pickup_msg_timer - dt)
                toast_alpha = int(255 * min(1.0, self.pickup_msg_timer / 0.5))
                if toast_alpha > 0:
                    p_txt = Text(self.pickup_msg, size=36, color="#FFFF00", outlines=[(3, "#000000", 0, 0)], font="mod_assets/fonts/BebasNeue-Regular.ttf", substitute=False)
                    pt_render = renpy.render(p_txt, self.width, self.height, st, at)
                    pw, ph = pt_render.get_size()
                    render.blit(pt_render, (self.width / 2 - pw / 2, int(self.height * 0.15)))

            if self.is_arena_mode and self.inter_round_timer > 0.0:
                self.inter_round_timer = max(0.0, self.inter_round_timer - dt)
                cur_rnd = getattr(renpy.store, "stein_current_round", 0)
                next_rnd = cur_rnd + 1
                b_txt = Text(f"ROUND {next_rnd} STARTING IN: {self.inter_round_timer:.1f}", size=36, color="#FFD700", outlines=[(3, "#000000", 0, 0)], font="mod_assets/fonts/BebasNeue-Regular.ttf", substitute=False)
                b_render = renpy.render(b_txt, self.width, self.height, st, at)
                bw, bh = b_render.get_size()
                render.blit(b_render, (self.width / 2 - bw / 2, 40))

            hp_int = int(cur_hp)
            hp_color = "#00FF00" if hp_int >= 60 else ("#FFFF00" if hp_int >= 30 else "#FF0000")
            wp_names = ["SWORD", "PISTOL", "SHOTGUN", "MINIGUN"]
            cur_wp_name = wp_names[self.active_weapon] if self.active_weapon < 4 else "PISTOL"
            hud_txt = Text(f"HP: {hp_int}%  |  WEAPON: {cur_wp_name}", size=32, color=hp_color, outlines=[(2, "#000000", 0, 0)], font="mod_assets/fonts/BebasNeue-Regular.ttf", substitute=False)
            hud_r = renpy.render(hud_txt, self.width, self.height, st, at)
            render.blit(hud_r, (30, self.height - 50))

            if self.is_arena_mode:
                cur_rnd = getattr(renpy.store, "stein_current_round", 1)
                kills = getattr(persistent, "stein_kills", 0)
                coins = getattr(renpy.store, "stein_session_coins", 0)
                arena_txt = Text(f"ROUND: {cur_rnd}  |  KILLS: {kills}  |  COINS: {coins}", size=32, color="#FFD700", outlines=[(2, "#000000", 0, 0)], font="mod_assets/fonts/BebasNeue-Regular.ttf", substitute=False)
                arena_r = renpy.render(arena_txt, self.width, self.height, st, at)
                aw, ah = arena_r.get_size()
                render.blit(arena_r, (self.width - aw - 30, self.height - 50))

            # F3 debug overlay
            if self.show_debug_overlay:
                p_x = getattr(self, 'x', 0.0)
                p_y = getattr(self, 'y', 0.0)
                p_z = getattr(self, 'z', 0.0)
                p_yaw = self.yaw % 360.0
                p_pitch = getattr(self, 'pitch', 0.0)
                
                left_lines = [
                    "DEBUG",
                    f"POS: X:{p_x:.2f}  Y:{p_y:.2f}  Z:{p_z:.2f}",
                    f"VIEW: YAW:{p_yaw:.1f}°  PITCH:{p_pitch:.1f}°",
                    f"KEYS: ({'W' if self.keys['w'] else '-'}) ({'A' if self.keys['a'] else '-'}) ({'S' if self.keys['s'] else '-'}) ({'D' if self.keys['d'] else '-'}) ({'SPACE' if self.keys['space'] else '-'}) ({'SHIFT' if self.keys['shift'] else '-'}) ({'CTRL' if self.keys['ctrl'] else '-'}) ({'AIM' if self.keys['aim'] else '-'})",
                    f"ENGINE: TIME:{time_of_day:.1f}h | FLASHLIGHT:{'ON' if self.flashlight_active else 'OFF'}",
                ]
                
                panel_w, panel_h = 420, 26 * len(left_lines) + 20
                bg_left = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
                bg_left.fill((0, 0, 0, 190))
                pygame.draw.rect(bg_left, (255, 215, 0, 220), (0, 0, panel_w, panel_h), 2)
                render.blit(bg_left, (20, 20))
                
                for idx, line in enumerate(left_lines):
                    color = "#FFFF00" if idx == 0 else "#FFFFFF"
                    l_txt = Text(line, size=20, color=color, outlines=[(1, "#000000", 0, 0)], font="mod_assets/fonts/BebasNeue-Regular.ttf", substitute=False)
                    l_render = renpy.render(l_txt, self.width, self.height, st, at)
                    render.blit(l_render, (30, 28 + idx * 24))

                if getattr(config, 'developer', True):
                    t = self.weapon_offsets.get(self.active_weapon, {'hip_x':0.0, 'hip_y':0.0, 'hip_z':0.0, 'ads_x':0.0, 'ads_y':0.0, 'ads_z':0.0, 'pitch':0.0, 'yaw':0.0, 'roll':0.0, 'scale':0.0})
                    mode_names = ["POSITION", "ROTATION", "SCALE"]
                    cur_mode_str = mode_names[self.dev_edit_mode]
                    cur_target_str = "HIPFIRE" if self.dev_edit_target == 'hip' else "ADS AIM"
                    
                    right_lines = [
                        "VIEWMODEL GIZMO (DEV MODE)",
                        f"ACTIVE WEAPON: {cur_wp_name} (ID: {self.active_weapon})",
                        f"EDIT TARGET: ({cur_target_str})  (Tab / Numpad /)",
                        f"EDIT MODE:   ({cur_mode_str})  (Numpad 0)",
                        f"OFFSET HIP: X:{t['hip_x']:+.4f}  Y:{t['hip_y']:+.4f}  Z:{t['hip_z']:+.4f}",
                        f"OFFSET ADS: X:{t['ads_x']:+.4f}  Y:{t['ads_y']:+.4f}  Z:{t['ads_z']:+.4f}",
                        f"OFFSET ROT: P:{t['pitch']:+.1f}°  Y:{t['yaw']:+.1f}°  R:{t['roll']:+.1f}°",
                        f"OFFSET SCALE: {t['scale']:+.4f}",
                        "(NUMPAD 4/6) +/- X/Yaw   (8/2) +/- Y/Pitch   (7/9) +/- Z/Roll",
                        "(NUMPAD +/-) Scale   (.) Reset        (P) Print to Log",
                        "(SHIFT: Fast 5x  |  CTRL: Ultra-Fine 0.2x)",
                    ]
                    
                    r_panel_w, r_panel_h = 440, 24 * len(right_lines) + 20
                    r_px = self.width - r_panel_w - 20
                    bg_right = pygame.Surface((r_panel_w, r_panel_h), pygame.SRCALPHA)
                    bg_right.fill((0, 0, 0, 190))
                    pygame.draw.rect(bg_right, (0, 255, 255, 220), (0, 0, r_panel_w, r_panel_h), 2)
                    render.blit(bg_right, (r_px, 20))
                    
                    for idx, line in enumerate(right_lines):
                        if idx == 0: color = "#00FFFF"
                        elif idx in (2, 3): color = "#FFD700"
                        elif idx >= 8: color = "#00FF88"
                        else: color = "#FFFFFF"
                        r_txt = Text(line, size=19, color=color, outlines=[(1, "#000000", 0, 0)], font="mod_assets/fonts/BebasNeue-Regular.ttf", substitute=False)
                        r_render = renpy.render(r_txt, self.width, self.height, st, at)
                        render.blit(r_render, (r_px + 12, 26 + idx * 23))

            if self.return_value:
                renpy.timeout(0)

            renpy.redraw(self, 0)
            return render
            
        def destroy(self):
            self.running = False
            if hasattr(self, 'process') and self.process:
                try:
                    self.process.terminate()
                    self.process.wait(timeout=1)
                except Exception:
                    pass

        def __del__(self):
            self.destroy()
