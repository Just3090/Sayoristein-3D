init -10 python:
    import pygame
    import sys
    import io
    import subprocess
    import struct
    import threading
    import os
    import math

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
                        'space':False, 'shift':False, 'ctrl':False, 'shoot':False}
            
            self.event_queue = []
            
            self.mouse_grabbed = False
            self.mouse_dx = 0.0
            self.mouse_dy = 0.0
            
            exe_name = "raylib_server.exe" if renpy.windows else "raylib_server"
            exe_path = os.path.join(config.gamedir, "core", exe_name)
            
            try:
                log_path = os.path.join(config.gamedir, "core", "server_log.txt")
                self.log_file = open(log_path, "w")
                self.process = subprocess.Popen(
                    [exe_path], 
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE, 
                    stderr=self.log_file, 
                    cwd=config.basedir,
                    bufsize=0
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
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if not self.mouse_grabbed:
                    self.mouse_grabbed = True
                    pygame.mouse.set_visible(False)
                    pygame.event.set_grab(True)
                else:
                    self.keys['shoot'] = True
            elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
                self.keys['shoot'] = False
            elif ev.type == pygame.MOUSEMOTION and self.mouse_grabbed:
                sens = getattr(persistent, "stein_mouse_sens", 1.0)
                dx, dy = ev.rel
                self.mouse_dx += dx * 0.2 * sens
                self.mouse_dy -= dy * 0.2 * sens
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
                elif ev.key == pygame.K_ESCAPE:
                    if self.mouse_grabbed:
                        self.mouse_grabbed = False
                        pygame.mouse.set_visible(True)
                        pygame.event.set_grab(False)
                    else:
                        self.destroy()
                        return "quit"
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
            return None

        def render(self, width, height, st, at):
            if self.running and self.process.stdin:
                try:
                    time_of_day = getattr(renpy.store, "u_time_of_day", 12.0)
                    light_quality = getattr(persistent, "stein_lighting_quality", 0)
                    shadows_en = 1 if getattr(persistent, "stein_enable_shadows", False) else 0
                    
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
                    
                    data = struct.pack("iiii iiii iiii ff f i i", 
                                        w_key, s_key, a_key, d_key,
                                        left_key, right_key, up_key, down_key,
                                        space_key, shift_key, ctrl_key, shoot_key,
                                        float(self.mouse_dx), float(self.mouse_dy),
                                        float(time_of_day), int(light_quality), int(shadows_en))
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
                        renpy.sound.play("sounds/pew.ogg", channel="sound")
                    elif ev_val == 11 or ev_val == 12: # coins
                        renpy.store.stein_session_coins += 1
                        renpy.sound.play("sounds/pew.ogg", channel="sound")
                    elif ev_val == 13 or ev_val == 15: # weapons
                        renpy.sound.play("sounds/pew.ogg", channel="sound")
                elif ev_id == 10: # enemy hit
                    pass
                elif ev_id == 11: # enemy dead
                    renpy.store.persistent.stein_kills += 1
                    renpy.sound.play("sounds/ow.ogg", channel="sound")
                elif ev_id == 12: # enemy attack
                    renpy.sound.play("sounds/e-gunshot.ogg", channel="sound")
                    renpy.store.stein_player_health -= 10
                    if renpy.store.stein_player_health < 0:
                        renpy.store.stein_player_health = 0

            render = renpy.Render(self.width, self.height)
            if self.surface:
                scaled = pygame.transform.scale(self.surface, (self.width, self.height))
                render.blit(scaled, (0, 0))
                
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
