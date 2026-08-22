init -10 python:
    import sys
    import os
    import ctypes
    import array

    core_path = os.path.join(config.gamedir, "core")
    if core_path not in sys.path:
        sys.path.append(core_path)

    try:
        import stein_core
        stein_native_available = True
        stein_native_error = None
    except ImportError as e:
        stein_core = None
        stein_native_available = False
        if not stein_native_error:
            stein_native_error = str(e)
        print("Sayoristein disabled: native stein_core library is not available.")


    def flatten_world_map(world_map, width, height, min_layer, max_layer):
        num_layers = max_layer - min_layer + 1
        total_size = width * height * num_layers
        
        flat = array.array('i', [0] * total_size)
        
        if isinstance(world_map, dict):
            for z, grid in world_map.items():
                layer_idx = z - min_layer
                if layer_idx < 0 or layer_idx >= num_layers: continue
                
                base_idx = layer_idx * width * height
                for x in range(min(len(grid), width)):
                    row = grid[x]
                    for y in range(min(len(row), height)):
                        if row[y] > 0:
                            flat[base_idx + (x * height) + y] = row[y]
                            
        elif isinstance(world_map, list):
            layer_idx = 0 - min_layer
            if 0 <= layer_idx < num_layers:
                base_idx = layer_idx * width * height
                for x in range(min(len(world_map), width)):
                    row = world_map[x]
                    for y in range(min(len(row), height)):
                        if row[y] > 0:
                            flat[base_idx + (x * height) + y] = row[y]

        return flat

    SLOT_MELEE   = 0
    SLOT_HANDGUN = 1
    SLOT_LONG    = 2
    SLOT_SPECIAL = 3

    class RaycastLayer(renpy.Displayable):
        def __init__(self, controller, **kwargs):
            super(RaycastLayer, self).__init__(**kwargs)
            self.c = controller
            # We use an Image instead of Solid to ensure a_tex_coord attributes are generated for the shader
            self.base_displayable = Transform(Image("pics/background.webp"), size=(self.c.internal_width, self.c.internal_height))

        def render(self, width, height, st, at):
            c = self.c
            
            # Bobbing Logic
            bob_offset = 0.0
            
            fl_bob_x = 0.0
            fl_bob_y = 0.0
            
            is_moving = abs(c.player.speed) > 0.1 or abs(c.player.strafe_speed) > 0.1
            is_running = c.kb_running or c.gp_running
            effective_aiming = c.is_aiming or c.gp_aiming
            
            if is_moving and c.player.is_grounded and not effective_aiming:
                bob_speed = 10.0
                bob_amp = 0.01
                
                fl_amp_x = 0.05
                fl_amp_y = 0.03
                
                if is_running:
                    bob_speed = 15.0
                    bob_amp = 0.02
                    fl_amp_x = 0.08 
                    fl_amp_y = 0.05

                bob_offset = math.sin(st * bob_speed) * bob_amp
                
                fl_bob_x = math.sin(st * bob_speed) * fl_amp_x
                fl_bob_y = abs(math.cos(st * bob_speed)) * fl_amp_y

            renderer = renpy.render(self.base_displayable, width, height, st, at)
            renderer.add_shader("stein.raycaster")

            
            static_count = 0
            for i, sp in enumerate(c.sprite_positions):
                if i >= 50: break
                idx = i * 4
                c.static_data_buffer[idx] = sp[0]
                c.static_data_buffer[idx+1] = sp[1]
                c.static_data_buffer[idx+2] = float(sp[2])
                c.static_data_buffer[idx+3] = 0.0
                static_count += 1

            active_sprites = SteinWrapper.prepare_scene_sprites(
                c.player.x, c.player.y,
                c.proj_ptr, c.MAX_PROJECTILES,
                c.enemy_ptr, len(c.enemies), # Use the main EnemyData* array
                c.static_data_ptr, static_count,
                c.shader_sprite_ptr, 64
            )

            renderer.add_uniform("u_num_active_sprites", active_sprites)
            renderer.add_uniform("u_sprites", c.shader_sprite_buffer)

            # ADS Zoom Logic
            is_aiming = c.is_aiming or c.gp_aiming
            zoom_factor = 0.6 if is_aiming else 1.0
            
            aspect_ratio = float(width) / float(height)
            plane_len = math.sqrt(c.player.planex**2 + c.player.planey**2)
            if plane_len == 0: plane_len = 0.66
            vertical_scale = (aspect_ratio / plane_len) / zoom_factor
            
            plane_x = c.player.planex * zoom_factor
            plane_y = c.player.planey * zoom_factor

            renderer.add_uniform('u_resolution', (float(width), float(height)))
            renderer.add_uniform('u_time', st)
            renderer.add_uniform('u_player_pos', (c.player.x, c.player.y))
            renderer.add_uniform('u_player_dir', (c.player.dirx, c.player.diry))
            renderer.add_uniform('u_player_plane', (plane_x, plane_y))
            renderer.add_uniform('u_pitch', (c.player.pitch / float(height)) + bob_offset)
            renderer.add_uniform('u_z_offset', c.player.z)
            renderer.add_uniform('u_vertical_scale', vertical_scale)
            renderer.add_uniform('u_sky_texture', c.sky_texture)
            renderer.add_uniform('u_volumetric_clouds', 1.0 if persistent.stein_volumetric_clouds else 0.0)
            
            rain_int = 0.0; snow_int = 0.0
            if hasattr(c, 'weather_state'):
                if c.weather_state == "rain": rain_int = 1.0
                elif c.weather_state == "snow": snow_int = 1.0
            renderer.add_uniform('u_rain_intensity', rain_int)
            renderer.add_uniform('u_snow_intensity', snow_int)
            renderer.add_uniform('u_wetness', getattr(c, 'wetness', 0.0))
            
            current_hour = 0.0
            current_ambient = c.lighting_preset['ambient_base']
            current_ambient_near = c.lighting_preset['ambient_near']

            if c.is_arena_mode:
                elapsed_hours = st * 0.04
                current_hour = (c.arena_start_hour + elapsed_hours) % 24.0
                
                def lerp_col(c1, c2, t):
                    return (
                        c1[0] + (c2[0] - c1[0]) * t,
                        c1[1] + (c2[1] - c1[1]) * t,
                        c1[2] + (c2[2] - c1[2]) * t
                    )

                night_amb = (0.05, 0.05, 0.1)
                day_amb = (1.0, 1.0, 1.0)
                sunset_amb = (0.7, 0.6, 0.5)

                if current_hour < 5.0:
                    current_ambient = night_amb
                elif current_hour < 8.0:
                    p = (current_hour - 5.0) / 3.0
                    current_ambient = lerp_col(night_amb, day_amb, p)
                elif current_hour < 16.0:
                    current_ambient = day_amb
                elif current_hour < 19.0:
                    p = (current_hour - 16.0) / 3.0
                    current_ambient = lerp_col(day_amb, sunset_amb, p)
                elif current_hour < 21.0:
                    p = (current_hour - 19.0) / 2.0
                    current_ambient = lerp_col(sunset_amb, night_amb, p)
                else:
                    current_ambient = night_amb
                
                current_ambient_near = (0.0, 0.0, 0.0)
            else:
                current_hour = float(c.lighting_preset.get('time_id', 0.0))
            renderer.add_uniform('u_time_of_day', current_hour)

            renderer.add_uniform('u_ambient_color', current_ambient)
            renderer.add_uniform('u_ambient_near_color', current_ambient_near)

            renderer.add_uniform('u_map_size', (float(c.map_w), float(c.map_h)))
            renderer.add_uniform('u_map_uv_scale', c.map_uv_scale)
            renderer.add_uniform('u_map_texture', c.map_texture)
            renderer.add_uniform('u_map_layer_norm_height', c.map_layer_norm_height)
            renderer.add_uniform('u_map_layer_base_y', float(c.min_layer))
            renderer.add_uniform('u_map_layer_count', float(c.num_layers))
            renderer.add_uniform('u_map_tex_pixel_size', c.map_tex_pixel_size)
            renderer.add_uniform('u_wall_atlas', c.wall_atlas)
            renderer.add_uniform('u_floor_texture', c.floor_texture)
            renderer.add_uniform('u_num_textures', float(c.num_textures))
            renderer.add_uniform('u_sprite_atlas', c.sprite_atlas)
            renderer.add_uniform('u_num_sprite_textures', float(c.num_sprite_textures))

            renderer.add_uniform('u_flashlight_active', 1.0 if c.flashlight_on else 0.0)
            renderer.add_uniform('u_flashlight_bob', (fl_bob_x, fl_bob_y))
            
            renderer.add_uniform('u_soft_shadows', 1.0 if getattr(persistent, "stein_soft_shadows", True) else 0.0)
            renderer.add_uniform('u_enable_shadows', 1.0 if getattr(persistent, "stein_enable_shadows", True) else 0.0)
            renderer.add_uniform('u_max_dist', 500.0 if c.builder_mode else 60.0)
            renderer.add_uniform('u_simple_floor', 1.0 if getattr(persistent, "stein_simple_floor", False) else 0.0)
            
            # Flash
            import time
            current_weapon = c.weapons[c.player.current_weapon_name]
            flash_intensity = 0.0
            if current_weapon.projectile_type and (time.time() - current_weapon.last_fired) < 0.1:
                flash_intensity = 1.0 - ((time.time() - current_weapon.last_fired) / 0.1)
            renderer.add_uniform('u_flash_intensity', flash_intensity)
            renderer.add_uniform('u_flash_color', (1.0, 0.8, 0.4))

            renderer.add_uniform('u_light_positions', [0.0] * 64)
            renderer.add_uniform('u_num_active_lights', 0.0)

            renpy.redraw(self, 0.000001)
            return renderer

    class GPURenpystein(renpy.Displayable):
        def __init__(self, width, height, worldMap, exits=[], internal_width=None, internal_height=None, lighting_preset=None, **kwargs):
            super(GPURenpystein, self).__init__(**kwargs)
            self.width = width
            self.height = height
            self.map_data = worldMap
            self.worldMap = worldMap 
            
            if isinstance(worldMap, dict):
                max_x = 0
                max_y = 0
                for grid in worldMap.values():
                    if len(grid) > max_x: max_x = len(grid)
                    if len(grid) > 0 and len(grid[0]) > max_y: max_y = len(grid[0])
                self.mapWidth = max_x
                self.mapHeight = max_y
            else:
                self.mapWidth = len(worldMap)
                self.mapHeight = len(worldMap[0]) if self.mapWidth > 0 else 0
            
            self.map_w = self.mapWidth
            self.map_h = self.mapHeight
            
            self.lighting_preset = lighting_preset if lighting_preset else {
                'ambient_base': (0.02, 0.02, 0.05),
                'ambient_near': (0.05, 0.05, 0.08),
                'sky_texture': "pics/background.webp",
                'time_id': 0.0
            }

            self.is_arena_mode = getattr(renpy.store, 'is_arena_mode', False)

            self.arena_start_hour = 12.0
            if self.is_arena_mode:
                roll = renpy.random.random()
                if roll < 0.33:
                    self.arena_start_hour = 12.0 # Day
                elif roll < 0.66:
                    self.arena_start_hour = 18.0 # Sunset
                else:
                    self.arena_start_hour = 2.0 # Night

            self.weather_state = "none"
            self.weather_timer = 0.0
            self.next_weather_check = 5.0
            self.wetness = 0.0

            self.fps_frame_count = 0
            self.fps_timer_accum = 0.0

            self.exits = exits
            
            self.internal_width = internal_width if internal_width is not None else width
            self.internal_height = internal_height if internal_height is not None else height
            self.damage_flash_timer = 0.0
            self.return_value = None
            self.heal_flash_timer = 0.0
            self.hit_marker_timer = 0.0
            self.damage_indicators = []
            self.time_since_last_damage = 0.0
            
            self.pickup_msg = ""
            self.pickup_msg_timer = 0.0
            
            self.map_texture = self.create_map_texture()
            self.wall_atlas, self.num_textures = self.create_wall_atlas()
            self.floor_texture = self.load_floor_texture()
            self.sprite_atlas, self.num_sprite_textures = self.create_sprite_atlas()
            self.solid_base = renpy.display.imagelike.Solid("#000", xsize=width, ysize=height)
            
            sky_path = self.lighting_preset.get('sky_texture', "pics/background.webp")
            try:
                with renpy.open_file(sky_path) as f:
                    bg_surf = pygame.image.load(f).convert_alpha()
            except:
                # Fallback
                with renpy.open_file("pics/background.webp") as f:
                    bg_surf = pygame.image.load(f).convert_alpha()
            
            bg_surf = pygame.transform.scale(bg_surf, (width, height))
            self.sky_texture = renpy.display.draw.load_texture(bg_surf)

            self.player = Player(self, renpy.store.player_x, renpy.store.player_y, renpy.store.player_dirx, renpy.store.player_diry, renpy.store.player_planex, renpy.store.player_planey)
            
            self.oldst = None
            self.last_rot = None
            self.active_fingers = {}
            self.mouse_initialized = False
            
            # Inputs
            self.kb_speed = 0.0
            self.kb_strafe = 0.0
            self.kb_dir = 0.0
            self.kb_fly_up = False
            self.kb_fly_down = False
            self.builder_mode = False
            self.selected_voxel = 1
            
            if config.developer:
                self.builder_mode = True
                self.player.fly_mode = True
                self.pickup_msg = "BUILDER MODE ON (DEV)"
                self.pickup_msg_timer = 3.0
            
            self.gp_speed = 0.0
            self.gp_strafe = 0.0
            self.gp_dir = 0.0
            self.touch_speed = 0.0
            self.touch_strafe = 0.0
            self.touch_dir = 0.0
            
            self.is_aiming = False
            self.gp_aiming = False
            self.gp_firing = False
            self.mouse_firing = False
            self.gp_running = False
            self.kb_running = False
            
            self.flashlight_on = False 
            self.prev_btn_flashlight = False
            
            self.raycast_layer = RaycastLayer(self)
            
            pygame.joystick.init()
            self.joysticks = [pygame.joystick.Joystick(x) for x in range(pygame.joystick.get_count())]
            for joy in self.joysticks:
                joy.init()

            self.gun_dmg = 50; self.shotgun_dmg = 35; self.minigun_dmg = 40
            # Damage upgrades removed as per request
            # if self.is_arena_mode:
            #     self.gun_dmg += 50 * (persistent.stein_pistol_level * 0.01)
            #     self.shotgun_dmg += 35 * (persistent.stein_shotgun_level * 0.01)
            #     self.minigun_dmg += 3 * (persistent.stein_minigun_level * 0.10)

            self.weapon_library = {}
            
            def register_weapon(w_obj):
                self.weapon_library[w_obj.name] = w_obj

            ### example of new guns registrations

            # register_weapon(Weapon("gun", SLOT_HANDGUN, damage=self.gun_dmg, projectile_type='bullet', cooldown=0.38, flash_offset=(0, -170), flash_ads_offset=(0, -360), flash_size=1.0, ads_idle="pics/weapons/gun_ads1.webp",
            #     # Normal configs
            #     normal_frameCount=11,
            #     normal_fps=60,
            #     normal_flash_frame=2,
            
            #     # ADS transition
            #     ads_enter_frameCount=14,
            #     ads_enter_fps=60,
            #     ads_enter_name="gun_raise",
        
            #     # ADS shooting animation
            #     ads_fire_frameCount=9,
            #     ads_fire_fps=60,
            #     ads_fire_flash_frame=1,
            # ))

            register_weapon(Weapon("gun", SLOT_HANDGUN, damage=self.gun_dmg, projectile_type='bullet', cooldown=0.38, flash_offset=(0, -170), flash_ads_offset=(0, -360), flash_size=1.0, ads_idle="pics/weapons/gun_ads1.webp",
                # Normal configs
                normal_frameCount=11,
                normal_fps=60,
                normal_flash_frame=2,
            
                # ADS transition
                ads_enter_frameCount=14,
                ads_enter_fps=60,
                ads_enter_name="gun_raise",
        
                # ADS shooting animation
                ads_fire_frameCount=9,
                ads_fire_fps=60,
                ads_fire_flash_frame=1,
            ))

            register_weapon(Weapon("shotgun", SLOT_LONG, damage=self.shotgun_dmg, projectile_type='shotgun', cooldown=1.4, flash_offset=(75, -260), flash_ads_offset=(0, -340), flash_size=1.0, ads_idle="pics/weapons/shotgun_ads1.webp",
                # Normal configs
                normal_frameCount=39,
                normal_fps=60,
                normal_flash_frame=1,
            
                # ADS transition (normal-ads)
                ads_enter_frameCount=5,
                ads_enter_fps=60,
                ads_enter_name="shotgun_raised",
        
                # ADS shooting animation
                ads_fire_frameCount=45,
                ads_fire_fps=60,
                ads_fire_flash_frame=1,

                # Run enter (normal-running)
                run_enter_frameCount=5,
                run_enter_fps=60,
                run_enter_name="shotgun_run",
            ))

            register_weapon(Weapon("fist", SLOT_MELEE, 5, 1, damage=25, cooldown=0.5))

            # register_weapon(Weapon("gun", SLOT_HANDGUN, 5, 1, damage=self.gun_dmg, projectile_type='bullet', cooldown=0.6, 
            #     ads_idle="pics/weapons/beta_gun_s.png", ads_fire="pics/weapons/beta_gun_s_f.png", 
            #     flash_offset=(0, -170), flash_ads_offset=(0, -360), flash_size=1.0))

            # register_weapon(Weapon("shotgun", SLOT_LONG, 5, 1, damage=self.shotgun_dmg, projectile_type='shotgun', cooldown=1.0, 
            #     flash_offset=(0, -170), flash_ads_offset=(0, -170), flash_size=1.5, flash_color=(1.0, 0.6, 0.2)))
            
            register_weapon(Weapon("minigun", SLOT_SPECIAL, 5, 1, damage=self.minigun_dmg, projectile_type='bullet', cooldown=0.05, 
                loop_frames=[2, 3], flash_offset=(0, -180), flash_ads_offset=(0, -180)))
            
            self.inventory = [None, None, None, None] # [Melee, Handgun, Long, Special]
            
            self.weapons = self.weapon_library

            self.current_slot_index = SLOT_MELEE

            self.equip_weapon("fist")
            self.equip_weapon("gun")
            
            if renpy.store.stein_has_shotgun:
                self.equip_weapon("shotgun")
            
            if renpy.store.stein_has_minigun:
                self.equip_weapon("minigun")

            self.current_slot_index = SLOT_HANDGUN
            self.update_current_weapon_ref()
            
            self.bullet_texture_index = 6
            self.sight_d = Image("pics/items/sight.webp")
            with renpy.open_file("pics/gui/damage_x.webp") as f:
                self.hit_marker_img = pygame.image.load(f).convert_alpha()
            with renpy.open_file("pics/gui/arrow_d.webp") as f:
                arrow_surf = pygame.image.load(f).convert_alpha()
            self.arrow_img = pygame.transform.scale(arrow_surf, (30, 30))

            self.max_entities = 1024
            
            self.max_enemies = 1024
            self.enemy_array = (EnemyData * self.max_enemies)()
            self.enemy_ptr = ctypes.addressof(self.enemy_array)
            ctypes.memset(self.enemy_ptr, 0, ctypes.sizeof(self.enemy_array))

            self.player_data = PlayerData()
            self.player_ptr = ctypes.addressof(self.player_data)

            self.sort_buffer = (ctypes.c_int * self.max_entities)()
            
            self.shader_sprite_buffer = (ctypes.c_float * 256)()
            
            self.entities_buffer = (ctypes.c_double * (self.max_entities * 4))()
            self.entities_ptr = ctypes.addressof(self.entities_buffer)
            
            self.shader_sprite_ptr = ctypes.addressof(self.shader_sprite_buffer)

            self.sort_ptr = ctypes.addressof(self.sort_buffer)

            self.MAX_PROJECTILES = 256
            self.proj_array = (ProjectileData * self.MAX_PROJECTILES)()
            self.proj_ptr = ctypes.addressof(self.proj_array)

            self.enemy_data_buffer = (ctypes.c_double * (50 * 4))() 
            self.enemy_data_ptr = ctypes.addressof(self.enemy_data_buffer)
            
            self.static_data_buffer = (ctypes.c_double * (50 * 4))()
            self.static_data_ptr = ctypes.addressof(self.static_data_buffer)
            
            for i in range(self.MAX_PROJECTILES):
                self.proj_array[i].active = 0

            self.projectiles = []
            self.enemies = []
            self.sprite_positions = renpy.store.stein_sprites
            
            self.inter_round_timer = getattr(renpy.store, 'stein_inter_round_timer', 0.0)
            self.current_round = getattr(renpy.store, 'stein_current_round', 0)
            self.sniper_count = getattr(renpy.store, 'stein_sniper_count', 0)
            self.yuritler_count = getattr(renpy.store, 'stein_yuritler_count', 0)
            self.spawn_points = getattr(renpy.store, 'arena_spawn_points', [])
            
            if hasattr(renpy.store, 'stein_enemies'):
                for e_data in renpy.store.stein_enemies:
                    x, y, tex, dead_tex = e_data[0], e_data[1], e_data[2], e_data[3]
                    health = e_data[4] if len(e_data) > 4 else 100
                    type_id = e_data[5] if len(e_data) > 5 else 0
                    
                    if type_id == 1: new_e = Yuritler(self, x, y, health=health)
                    elif type_id == 2: new_e = EliteGuard(self, x, y, health=health)
                    elif type_id == 3: new_e = Sniper(self, x, y, health=health)
                    else: new_e = Guard(self, x, y, tex, dead_tex, health=health)
                    
                    self.enemies.append(new_e)

            if self.is_arena_mode and self.current_round == 0:
                self.start_next_round()

        def spawn_projectile(self, x, y, z, dx, dy, dz, speed, tex_id, damage, is_player, pitch=0.0):
            for i in range(self.MAX_PROJECTILES):
                if self.proj_array[i].active == 0:
                    p = self.proj_array[i]
                    p.x = x; p.y = y; p.z = z
                    p.dir_x = dx; p.dir_y = dy; p.dir_z = dz
                    p.speed = speed
                    p.texture_idx = tex_id
                    p.damage = damage
                    p.from_player = 1 if is_player else 0
                    p.pitch = pitch
                    p.active = 1
                    return

        def equip_weapon(self, weapon_name):
            if weapon_name in self.weapon_library:
                w_obj = self.weapon_library[weapon_name]
                self.inventory[w_obj.category] = w_obj
                if self.inventory[self.current_slot_index] == w_obj:
                    self.update_current_weapon_ref()

        def update_current_weapon_ref(self):
            weapon = self.inventory[self.current_slot_index]
            if weapon:
                self.player.current_weapon_name = weapon.name
            else:
                self.current_slot_index = SLOT_MELEE
                self.player.current_weapon_name = self.inventory[SLOT_MELEE].name

        def switch_to_slot(self, slot_idx):
            if 0 <= slot_idx < 4:
                if self.inventory[slot_idx] is not None:
                    self.current_slot_index = slot_idx
                    self.update_current_weapon_ref()

        def cycle_weapon(self):
            start_idx = self.current_slot_index
            for i in range(1, 4):
                next_idx = (start_idx + i) % 4
                if self.inventory[next_idx] is not None:
                    self.switch_to_slot(next_idx)
                    return

        def start_next_round(self):
            self.current_round += 1
            # renpy.sound.play("sounds/music/round_start.ogg", channel="audio")
            
            # Clean up bodies
            # Original uses: [s for s in self.sprite_positions if s[2] != 5] (Guard dead texture is 5)
            # Guard/Elite/Sniper dead: 5. Yuritler dead: 10
            self.sprite_positions = [s for s in self.sprite_positions if s[2] not in (5, 10)]
            
            if not self.spawn_points:
                self.spawn_points = [(1.5, 1.5), (self.mapWidth-1.5, 1.5), (self.mapWidth/2.0, self.mapHeight/2.0)]

            # Spawn Standard Guards
            for _ in range(self.current_round):
                if not self.spawn_points: break
                sx, sy = renpy.random.choice(self.spawn_points)
                
                x = sx + 0.5 + (renpy.random.random() - 0.5) * 0.6
                y = sy + 0.5 + (renpy.random.random() - 0.5) * 0.6
                
                new_enemy = Guard(self, x, y, 4, 5, health=100)
                new_enemy.state = 'chasing'
                new_enemy.moveSpeed += (renpy.random.random() - 0.5) * 0.2
                self.enemies.append(new_enemy)

            # Spawn Yuritler
            spawn_yuritler = False
            if self.current_round % 10 == 0:
                spawn_yuritler = True
            elif self.current_round % 2 == 0:
                if renpy.random.random() < 0.15:
                    spawn_yuritler = True
            
            if spawn_yuritler:
                if self.spawn_points:
                    self.yuritler_count += 1
                    sx, sy = renpy.random.choice(self.spawn_points)
                    x = sx + 0.5 + (renpy.random.random() - 0.5) * 0.6
                    y = sy + 0.5 + (renpy.random.random() - 0.5) * 0.6
                    
                    boss_hp = 150 + ((self.yuritler_count - 1) * 50)
                    boss = Yuritler(self, x, y, health=boss_hp)
                    boss.state = 'chasing'
                    self.enemies.append(boss)

            # pawn Elite Guards (Every 5 Rounds)
            if self.current_round % 5 == 0:
                num_elites = self.current_round // 5
                for _ in range(num_elites):
                    if not self.spawn_points: break
                    sx, sy = renpy.random.choice(self.spawn_points)
                    x = sx + 0.5 + (renpy.random.random() - 0.5) * 0.6
                    y = sy + 0.5 + (renpy.random.random() - 0.5) * 0.6
                    
                    elite = EliteGuard(self, x, y, health=100)
                    elite.state = 'chasing'
                    elite.moveSpeed += (renpy.random.random() - 0.5) * 0.2
                    self.enemies.append(elite)

            # Spawn Snipers (Odd Rounds, 50% chance)
            if self.current_round % 2 != 0:
                if renpy.random.random() < 0.50:
                    self.sniper_count += 1
                    for _ in range(self.sniper_count):
                        if not self.spawn_points: break
                        sx, sy = renpy.random.choice(self.spawn_points)
                        x = sx + 0.5 + (renpy.random.random() - 0.5) * 0.6
                        y = sy + 0.5 + (renpy.random.random() - 0.5) * 0.6
                        
                        sniper = Sniper(self, x, y, health=100)
                        sniper.state = 'chasing'
                        self.enemies.append(sniper)
            
            self.inter_round_timer = 0.0

        def create_wall_atlas(self):
            image_paths = [  
                "pics/walls/eagle.png", "pics/walls/redbrick.png",
                "pics/walls/purplestone.png", "pics/walls/greystone.png",
                "pics/walls/bluestone.png", "pics/walls/mossy.png",
                "pics/walls/wood.png", "pics/walls/colorstone.png",
                "pics/walls/cement.png",
            ]
            
            surfaces = []
            for path in image_paths:
                with renpy.open_file(path) as f:
                    surf = pygame.image.load(f).convert_alpha()
                    surf = pygame.transform.scale(surf, (64, 64))
                    surfaces.append(surf)
            
            if not surfaces:
                # fallback por si acaso
                fallback = pygame.Surface((64, 64)); fallback.fill((255,0,255))
                return renpy.display.draw.load_texture(fallback), 1.0

            num_tex = len(surfaces)
            w, h = surfaces[0].get_size()
            atlas_w = w * num_tex
            atlas_h = h
            
            # Atlas surface (RGBA 32bit)
            atlas = pygame.Surface((atlas_w, atlas_h), flags=pygame.SRCALPHA, depth=32)
            
            # DEBUG
            atlas.fill((255, 255, 255, 255))
            
            for i, surf in enumerate(surfaces):
                atlas.blit(surf, (i * w, 0))
            
            print(f"RenPyStein GPU: Wall Atlas Created. Size: {atlas_w}x{atlas_h}. Textures: {num_tex}")
            return renpy.display.draw.load_texture(atlas), float(num_tex)

        def load_floor_texture(self):
            try:
                with renpy.open_file("pics/walls/cement.png") as f:
                    surf = pygame.image.load(f).convert_alpha()
                    surf = pygame.transform.scale(surf, (64, 64))
                    return renpy.display.draw.load_texture(surf)
            except:
                fallback = pygame.Surface((64, 64))
                fallback.fill((100, 100, 100))
                return renpy.display.draw.load_texture(fallback)

        def create_sprite_atlas(self):
            sprite_paths = [  
                "pics/items/barrel.webp", "pics/items/pillar.webp",
                "pics/items/greenlight.webp", "pics/items/pillar_destroyed.webp",
                "pics/enemies/guard.webp",
                "pics/enemies/guard_d.webp",
                "pics/items/bullet.webp",
                "pics/items/medkit.webp",
                "pics/items/cookie.webp",
                "pics/enemies/yuritler.webp",
                "pics/enemies/yuritler_d.webp",
                "pics/items/coins.webp",
                "pics/items/coins.webp", 
                "pics/items/random_gun_i.webp",
                "pics/items/bullet_red.webp",
                "pics/items/minigun.webp",
            ]
            
            surfaces = []
            for path in sprite_paths:
                with renpy.open_file(path) as f:
                    surf = pygame.image.load(f).convert_alpha()
                    surf = pygame.transform.scale(surf, (64, 64))
                    surfaces.append(surf)
            
            if not surfaces:
                fallback = pygame.Surface((64, 64)); fallback.fill((0,255,0))
                return renpy.display.draw.load_texture(fallback), 1.0

            num_tex = len(surfaces)
            w, h = surfaces[0].get_size()
            atlas_w = w * num_tex
            atlas_h = h
            
            atlas = pygame.Surface((atlas_w, atlas_h), flags=pygame.SRCALPHA, depth=32)
            atlas.fill((0,0,0,0))
            
            for i, surf in enumerate(surfaces):
                atlas.blit(surf, (i * w, 0))
            
            print(f"RenPyStein GPU: Sprite Atlas Created. Size: {atlas_w}x{atlas_h}. Textures: {num_tex}")
            return renpy.display.draw.load_texture(atlas), float(num_tex)

        def create_map_texture(self):
            def next_power_of_two(n):
                if n == 0: return 1
                return 2**math.ceil(math.log(n, 2))
            
            if isinstance(self.map_data, list):
                layers = {0: self.map_data}
            else:
                layers = self.map_data

            # Find max dimensions
            max_x = 0
            max_y = 0
            min_z = 0
            max_z = 0
            
            if layers:
                min_z = min(layers.keys())
                max_z = max(layers.keys())
                for z, grid in layers.items():
                    if len(grid) > max_x: max_x = len(grid)
                    if len(grid) > 0 and len(grid[0]) > max_y: max_y = len(grid[0])
            
            self.map_w = max_x
            self.map_h = max_y
            self.min_layer = min_z
            self.max_layer = max_z
            self.num_layers = max_z - min_z + 1

            self.flat_map_buffer = flatten_world_map(
                self.worldMap, self.mapWidth, self.mapHeight, 
                self.min_layer, self.max_layer
            )
            
            layer_h_pixels = next_power_of_two(max_y)
            w_pot = max(64, next_power_of_two(max_x))
            h_pot = max(64, next_power_of_two(layer_h_pixels * self.num_layers))

            surf = pygame.Surface((w_pot, h_pot), flags=pygame.SRCALPHA, depth=32)
            surf.fill((0,0,0,255))
            
            for z, grid in layers.items():
                layer_idx = z - min_z
                base_y = layer_idx * layer_h_pixels
                
                for map_x, row in enumerate(grid):
                    for map_y, tile in enumerate(row):
                        if tile > 0:
                            surf.set_at((map_x, base_y + map_y), (255, tile, 0, 255))
            
            tex = renpy.display.draw.load_texture(surf)
            
            # Calculate uniforms
            self.map_layer_norm_height = float(layer_h_pixels) / float(h_pot)
            self.map_tex_pixel_size = (1.0 / float(w_pot), 1.0 / float(h_pot))
            
            self.map_uv_scale = (float(max_x) / float(w_pot), float(max_y) / float(layer_h_pixels)) 
            
            return tex

        def render(self, width, height, st, at):
            if self.oldst is None: self.oldst = st
            dtime = st - self.oldst
            self.oldst = st

            if dtime > 0.0:
                inst_fps = 1.0 / dtime
                
                current_fps = getattr(renpy.store, 'stein_current_fps', 60)
                new_fps = (current_fps * 0.9) + (inst_fps * 0.1)
                renpy.store.stein_current_fps = int(new_fps)

            if simulate_touch: self.update_player_from_touch_state()
            else: self.touch_speed = 0.0; self.touch_strafe = 0.0; self.touch_dir = 0.0
            self.poll_gamepad()

            total_speed = self.kb_speed + self.gp_speed + self.touch_speed
            total_strafe = self.kb_strafe + self.gp_strafe + self.touch_strafe
            total_dir = self.kb_dir + self.gp_dir + self.touch_dir
            
            effective_aiming = self.is_aiming or self.gp_aiming
            is_running = self.kb_running or self.gp_running
            if effective_aiming: is_running = False
            
            if is_running: self.player.moveSpeed = 4.0 
            elif effective_aiming: self.player.moveSpeed = 1.5 
            else: self.player.moveSpeed = 2.5 

            self.player.speed = max(-1.0, min(1.0, total_speed))
            self.player.strafe_speed = max(-1.0, min(1.0, total_strafe))
            self.player.dir = total_dir 
            self.player.move(dtime)
            
            self.update_logic(dtime)

            renpy.store.player_x = self.player.x
            renpy.store.player_y = self.player.y
            renpy.store.player_dirx = self.player.dirx
            renpy.store.player_diry = self.player.diry
            renpy.store.player_planex = self.player.planex
            renpy.store.player_planey = self.player.planey

            # RENDER
            retro_w = self.internal_width
            retro_h = self.internal_height
            
            scale = float(width) / float(self.internal_width)

            if self.last_rot is None:
                self.last_rot = self.player.rot

            diff_rot = self.player.rot - self.last_rot
            
            if diff_rot > math.pi: 
                diff_rot -= (math.pi * 2)
            elif diff_rot < -math.pi: 
                diff_rot += (math.pi * 2)

            mb_strength = getattr(persistent, "stein_motion_blur_strength", 0.0)
            
            blur_amount = -diff_rot * mb_strength * 10.0 

            self.last_rot = self.player.rot

            # Flatten the raycast layer
            flat_layer = renpy.display.layout.Flatten(self.raycast_layer)
            
            args_blur = { 'child': flat_layer, 'zoom': 1.0 } 
            
            if abs(blur_amount) > 0.005:
                args_blur['shader'] = "stein.motion_blur"
                args_blur['u_blur_amount'] = blur_amount
            
            blur_transform = Transform(**args_blur)

            if abs(blur_amount) > 0.005:
                blur_transform = renpy.display.layout.Flatten(blur_transform)

            use_bloom = getattr(persistent, "stein_enable_bloom", True)
            
            args_bloom = { 'child': blur_transform, 'zoom': scale, 'nearest': True }
            
            if use_bloom:
                args_bloom['shader'] = "stein.bloom"
                args_bloom['u_resolution'] = (float(width), float(height))

            final_transform = Transform(**args_bloom)
            
            main_scene_render = renpy.render(final_transform, width, height, st, at)
            
            r = renpy.Render(width, height)
            r.blit(main_scene_render, (0,0))
            
            # Damage flash + Low Health Tint
            if self.damage_flash_timer > 0:
                self.damage_flash_timer = max(0, self.damage_flash_timer - dtime)

            flash_alpha = 0
            if self.damage_flash_timer > 0:
                flash_alpha = int(140 * (self.damage_flash_timer / 0.2))
            
            health_alpha = 0
            if self.player.health < 70:
                severity = (70.0 - self.player.health) / 70.0
                health_alpha = int(severity * 160)
            
            final_red_alpha = min(255, max(flash_alpha, health_alpha))

            if final_red_alpha > 0:
                flash_d = renpy.display.imagelike.Solid((255, 0, 0, final_red_alpha))
                flash_r = renpy.render(flash_d, width, height, st, at)
                r.blit(flash_r, (0,0))

            if self.heal_flash_timer > 0:
                self.heal_flash_timer = max(0, self.heal_flash_timer - dtime)
                alpha = int(128 * (self.heal_flash_timer / 0.2))
                if alpha > 0:
                    heal_d = renpy.display.imagelike.Solid((0, 255, 0, alpha))
                    heal_r = renpy.render(heal_d, width, height, st, at)
                    r.blit(heal_r, (0,0))

            # Crosshair
            sight_r = renpy.render(self.sight_d, width, height, st, at)
            sw, sh = sight_r.get_size()
            r.blit(sight_r, (width/2 - sw/2, height/2 - sh/2))
            
            # Hit Marker
            if self.hit_marker_timer > 0:
                hm_w, hm_h = self.hit_marker_img.get_size()
                hm_tex = renpy.display.draw.load_texture(self.hit_marker_img)
                r.blit(hm_tex, (width/2 - hm_w/2, height/2 - hm_h/2))

            if self.pickup_msg_timer > 0:
                self.pickup_msg_timer -= dtime 
                
                alpha_val = 255
                if self.pickup_msg_timer < 0.5:
                    alpha_val = int(255 * (self.pickup_msg_timer / 0.5))
                
                if alpha_val > 0:
                    pickup_text = Text(self.pickup_msg, size=40, color="#FFFF00", outlines=[(3, "#000", 0, 0)])
                    pt_render = renpy.render(pickup_text, width, height, st, at)
                    pw, ph = pt_render.get_size()
                    
                    r.blit(pt_render, (width/2 - pw/2, height * 0.20))

            # hp_color = "#FFF"
            # if self.player.health < 30: hp_color = "#F00"
            # elif self.player.health < 60: hp_color = "#FF0"
            
            # hud_text = Text(_("HP: {}%  |  WEAPON: {}").format(int(self.player.health), self.player.current_weapon_name.upper()), size=36, color=hp_color, outlines=[(2, "#000", 0, 0)])
            # hud_r = renpy.render(hud_text, width, height, st, at)
            # r.blit(hud_r, (30, height - 60))



            # Damage indicators
            center_x = width / 2; center_y = height / 2; indicator_radius = 200
            for ind in list(self.damage_indicators):
                ind.duration -= dtime
                if ind.duration <= 0: self.damage_indicators.remove(ind); continue
                diff = self.player.rot - ind.angle
                ix = center_x + indicator_radius * math.sin(diff)
                iy = center_y - indicator_radius * math.cos(diff)
                rot_img = pygame.transform.rotate(self.arrow_img, -math.degrees(diff))
                rot_img.set_alpha(int(255 * (ind.duration / ind.max_duration)))
                ind_tex = renpy.display.draw.load_texture(rot_img)
                iw, ih = ind_tex.get_size()
                r.blit(ind_tex, (ix - iw/2, iy - ih/2))

            # Game over checks
            if self.player.health <= 0:
                self.player.health = 0
                pygame.mouse.set_visible(True); pygame.event.set_grab(False)
                if self.return_value is None:
                    if self.is_arena_mode:
                        renpy.store.last_arena_round = self.current_round
                        renpy.store.new_highscore = False
                        if self.current_round > persistent.sayoristein_arena_highscore:
                            persistent.sayoristein_arena_highscore = self.current_round
                            renpy.store.new_highscore = True
                        self.return_value = 'game_over_arena'
                    else:
                        self.return_value = 'game_over'

            for e in self.exits:
                if math.fabs(e[0] - self.player.x) < 0.5 and math.fabs(e[1] - self.player.y) < 0.5:
                    pygame.mouse.set_visible(True); pygame.event.set_grab(False)
                    if self.return_value is None:
                        self.return_value = e[2]

            # Weapon
            movement_state = {
                'is_moving': abs(self.player.speed) > 0.1 or abs(self.player.strafe_speed) > 0.1, 
                'is_running': self.kb_running or self.gp_running
            }
            is_firing = self.mouse_firing or self.gp_firing
            current_weapon_obj = self.weapons[self.player.current_weapon_name]
            current_weapon_obj.render_to(r, width, height, st, at, is_ads=self.is_aiming or self.gp_aiming, is_firing=is_firing, movement_state=movement_state)

            if self.is_arena_mode:
                arena_text = Text(_("ROUND: {}  |  KILLS: {}  |  COINS: {}").format(self.current_round, persistent.stein_kills, renpy.store.stein_session_coins), size=28, color="#FFD700", outlines=[(2, "#000", 0, 0)])
                arena_r = renpy.render(arena_text, width, height, st, at)
                aw, ah = arena_r.get_size()
                r.blit(arena_r, (width - aw - 30, height - 60))
                
                # Next Round Timer
                if self.inter_round_timer > 0 and self.current_round > 0:
                    timer_text = Text(_("NEXT ROUND IN: {:.1f}").format(self.inter_round_timer), size=48, color="#F00", outlines=[(2, "#000", 0, 0)])
                    timer_r = renpy.render(timer_text, width, height, st, at)
                    tw, th = timer_r.get_size()
                    r.blit(timer_r, (width/2 - tw/2, 100))
            
            if self.builder_mode:
                info_str = f"BUILDER MODE ON [[VOXEL: {self.selected_voxel}]]\COORDS: {self.player.x:.2f}, {self.player.y:.2f}, {self.player.z:.2f}"
                b_text = Text(info_str, size=30, color="#00FF00", outlines=[(2, "#000", 0, 0)])
                b_r = renpy.render(b_text, width, height, st, at)
                r.blit(b_r, (20, 20))

            if self.return_value:
                renpy.timeout(0)

            renpy.redraw(self, 0.01) 
            return r

        def update_weather(self, dt):
            if not hasattr(self, 'weather_state'):
                self.weather_state = "none"
                self.weather_timer = 0.0
                self.next_weather_check = 5.0
                self.wetness = 0.0

            if not self.is_arena_mode: return
            
            if not persistent.stein_volumetric_clouds or not getattr(persistent, "stein_enable_weather", True):
                self.weather_state = "none"
                self.wetness = max(0.0, self.wetness - dt * 0.1)
                return

            game_hours_passed = dt * 0.04
            
            if self.weather_state != "none":
                self.weather_timer -= game_hours_passed
                self.wetness = min(1.0, self.wetness + dt * 0.2)
                
                if self.weather_timer <= 0:
                    self.weather_state = "none"
            else:
                self.wetness = max(0.0, self.wetness - dt * 0.05)
            
            self.next_weather_check -= game_hours_passed
            if self.next_weather_check <= 0:
                if config.developer:
                    self.next_weather_check = 1.0
                else:
                    self.next_weather_check = 5.0 
                
                if self.weather_state == "none":
                    prob = 0.10
                    if config.developer: prob = 1.0
                    
                    if renpy.random.random() < prob:
                        if renpy.random.random() < 0.5:
                            self.weather_state = "rain"
                        else:
                            self.weather_state = "snow"
                        
                        self.weather_timer = 6.0

        def update_logic(self, dt):
            self.time_since_last_damage += dt
            if self.time_since_last_damage > 2.5 and self.player.health < 100 and self.player.health > 0:
                # Regenerate 95 HP in 3 seconds, like 31.67 hp/sec
                heal_rate = 31.67
                self.player.health = min(100, self.player.health + heal_rate * dt)

            self.update_weather(dt)
            self.hit_marker_timer = max(0, self.hit_marker_timer - dt)
            self.check_item_pickup()
            
            c_enemies = self.enemy_array
            active_count = 0
            state_map = {'idle': 0, 'chasing': 1, 'attacking': 2, 'dying': 3, 'dead': 4}

            for i, e in enumerate(self.enemies):
                if i >= self.max_enemies: break
                c_enemies[i].x = e.x
                c_enemies[i].y = e.y
                c_enemies[i].z = getattr(e, 'z', 0.0) 
                c_enemies[i].hp = e.health
                c_enemies[i].state = state_map.get(e.state, 0)
                c_enemies[i].texture_idx = e.texture_index
                c_enemies[i].move_speed = e.moveSpeed
                c_enemies[i].enemy_type = 0 
                active_count += 1

            map_addr, _ = self.flat_map_buffer.buffer_info()
            SteinWrapper.stein_lib.update_enemies_c(
                self.enemy_ptr,
                active_count,
                self.player.x, self.player.y, self.player.z,
                dt,
                map_addr,
                self.mapWidth, self.mapHeight, self.num_layers, self.min_layer
            )

            state_map_inv = {0: 'idle', 1: 'chasing', 2: 'attacking', 3: 'dying', 4: 'dead'}
            
            for i in range(active_count):
                e = self.enemies[i]
                c_e = c_enemies[i]
                
                e.x = c_e.x
                e.y = c_e.y
                e.health = c_e.hp
                e.state = state_map_inv.get(c_e.state, 'idle')
                
                if c_e.state == 2 and e.attack_timer <= 0:
                    pass

                if e.state == 'attacking':
                    if e.attack_timer <= 0:
                        e.attack(self.player)

            for e in self.enemies:
                if e.attack_timer > 0:
                    e.attack_timer -= dt
            
            SteinWrapper.update_projectiles_native(
                self.proj_ptr, self.MAX_PROJECTILES, dt,
                map_addr, self.mapWidth, self.mapHeight, 
                self.num_layers, self.min_layer
            )

            for i in range(self.MAX_PROJECTILES):
                p = self.proj_array[i]
                if p.active == 0: continue
                
                if p.from_player == 1:
                    for e in list(self.enemies):
                        dist_sq = (e.x - p.x)**2 + (e.y - p.y)**2
                        if dist_sq < 0.25:
                            e.health -= p.damage
                            self.hit_marker_timer = 0.15
                            renpy.sound.play("sounds/ow.ogg", channel="audio")
                            p.active = 0 
                            
                            if e.health <= 0:
                                if e in self.enemies: self.enemies.remove(e)
                                self.sprite_positions.append((e.x, e.y, e.destroyed_texture_index))
                            break 
                else:
                    dx = self.player.x - p.x
                    dy = self.player.y - p.y
                    dist_sq = dx*dx + dy*dy
                    
                    if dist_sq < 0.25:
                        # Check Z height
                        if p.z >= self.player.z and p.z <= self.player.z + 1.0:
                            if not self.builder_mode:
                                self.player.health -= p.damage
                                self.add_damage_indicator(-p.dir_x, -p.dir_y)
                                self.damage_flash_timer = 0.2
                                self.time_since_last_damage = 0.0
                                renpy.sound.play("sounds/ow.ogg", channel="audio")
                            p.active = 0

            if self.mouse_firing or self.gp_firing: self.shoot_weapon()

            if self.is_arena_mode:
                if self.inter_round_timer > 0:
                    self.inter_round_timer -= dt
                    if self.inter_round_timer <= 0:
                        self.start_next_round()
                elif len(self.enemies) == 0 and self.current_round > 0:
                    self.inter_round_timer = 10.0

            renpy.store.stein_current_round = self.current_round
            renpy.store.stein_inter_round_timer = self.inter_round_timer
            renpy.store.stein_sniper_count = self.sniper_count
            renpy.store.stein_yuritler_count = self.yuritler_count

        def check_item_pickup(self):
            for sprite in list(self.sprite_positions):
                sprite_x, sprite_y, texture_index = sprite
                dist = math.sqrt((self.player.x - sprite_x)**2 + (self.player.y - sprite_y)**2)
                if dist < 0.8:
                    picked = False
                    if texture_index == 7 and self.player.health < 100:
                        self.player.health = min(100, self.player.health + 25); picked = True
                        self.heal_flash_timer = 0.2
                    elif texture_index in (11, 12):
                        renpy.store.stein_session_coins += 100; picked = True
                    elif texture_index == 13:
                        w_obj = self.weapon_library["shotgun"]
                        has_shotgun = renpy.store.stein_has_shotgun or (self.inventory[w_obj.category] and self.inventory[w_obj.category].name == "shotgun")
                        
                        if not has_shotgun:
                            if self.is_arena_mode:
                                self.equip_weapon("shotgun")
                            else:
                                renpy.store.stein_has_shotgun = True
                            
                            picked = True
                            self.pickup_msg = "SHOTGUN ACQUIRED"
                            self.pickup_msg_timer = 3.0

                    elif texture_index == 15:
                        w_obj = self.weapon_library["minigun"]
                        has_minigun = renpy.store.stein_has_minigun or (self.inventory[w_obj.category] and self.inventory[w_obj.category].name == "minigun")
                        
                        if not has_minigun:
                            if self.is_arena_mode:
                                self.equip_weapon("minigun")
                            else:
                                renpy.store.stein_has_minigun = True
                            
                            picked = True
                            self.pickup_msg = "MINIGUN ACQUIRED"
                            self.pickup_msg_timer = 3.0
                    if picked: self.sprite_positions.remove(sprite)

        def shoot_weapon(self):
            weapon = self.weapons[self.player.current_weapon_name]
            if time.time() - weapon.last_fired < weapon.cooldown: return
            weapon.last_fired = time.time()
            weapon.play()
            
            dx = self.player.dirx
            dy = self.player.diry 
            pitch = self.player.pitch
            is_ads = self.is_aiming or self.gp_aiming
            
            speed = 100.0
            dz = pitch / float(self.height)
            z_start = self.player.z + 0.5

            if weapon.projectile_type == 'shotgun':
                import random
                spread_mult = 0.1 if is_ads else 0.2
                for _ in range(5):
                    spread = (random.random() - 0.5) * spread_mult
                    angle = self.player.rot + spread
                    pdx = math.cos(angle)
                    pdy = math.sin(angle)
                    self.spawn_projectile(self.player.x, self.player.y, z_start, pdx, pdy, dz, speed, self.bullet_texture_index, weapon.damage, True, pitch=pitch)
                renpy.sound.play("sounds/shotgun.ogg", channel="audio")
            elif weapon.projectile_type == 'bullet':
                self.spawn_projectile(self.player.x, self.player.y, z_start, dx, dy, dz, speed, self.bullet_texture_index, weapon.damage, True, pitch=pitch)
                renpy.sound.play("sounds/gunshot.ogg", channel="audio")
            else:
                dir_z = -math.sin(self.player.pitch / float(self.height)) # Approximation
                dir_z = (self.player.pitch / float(self.height)) 

                hit_index = SteinWrapper.stein_lib.check_hitscan_c(
                    self.player.x, self.player.y, self.player.z + 0.5,
                    dx, dy, dir_z,
                    self.enemy_ptr,
                    len(self.enemies),
                    100.0,
                    float(weapon.damage)
                )

                if hit_index != -1:
                    e = self.enemies[hit_index]
                    
                    c_enemies = self.enemy_array
                    e.health = c_enemies[hit_index].hp
                    
                    self.hit_marker_timer = 0.15
                    
                    if e.health <= 0:
                        renpy.sound.play("sounds/ow.ogg", channel="audio")
                        if self.is_arena_mode:
                            persistent.stein_kills += 1
                        
                        if e in self.enemies:
                            self.enemies.remove(e)
                        
                        self.sprite_positions.append((e.x, e.y, e.destroyed_texture_index))
                        
                                    
                        # Arena Mode Drops
                        if self.is_arena_mode:
                            drop_prob = 1.0 if e.coin_index == 12 else 0.35
                            if renpy.random.random() < drop_prob:
                                self.sprite_positions.append((e.x, e.y, e.coin_index))
                            
                            if not renpy.store.stein_has_shotgun:
                                shotgun_prob = 0.25 if e.coin_index == 12 else 0.10
                                if renpy.random.random() < shotgun_prob:
                                    self.sprite_positions.append((e.x, e.y, 13))
                                    
                            if not renpy.store.stein_has_minigun:
                                if renpy.random.random() < 0.10:
                                    self.sprite_positions.append((e.x, e.y, 15))

        def add_damage_indicator(self, source_dir_x, source_dir_y):
            angle = math.atan2(source_dir_y, source_dir_x)
            self.damage_indicators.append(DamageIndicator(angle))

        def isBlocking(self, x, y, z=0.0):
            if x < 0 or x >= self.mapWidth or y < 0 or y >= self.mapHeight: return True
            
            layer = int(math.floor(z))
            tile = 0
            
            if isinstance(self.worldMap, dict):
                if layer in self.worldMap:
                    grid = self.worldMap[layer]
                    if int(x) < len(grid) and int(y) < len(grid[int(x)]):
                        tile = grid[int(x)][int(y)]
            else:
                if layer == 0:
                    tile = self.worldMap[int(x)][int(y)]
            
            if tile == 0: return False
            
            h = 1.0
            if tile == 20: h = 0.5
            
            local_z = z - float(layer)
            if local_z >= h: return False
            
            return True

        def checkCollision(self, fromX, fromY, toX, toY, radius, z=0.0):
            # Check center
            if self.isBlocking(math.floor(toX), math.floor(toY), z):
                return [fromX, fromY]
            
            # Check radius
            points = [
                (toX + radius, toY), (toX - radius, toY),
                (toX, toY + radius), (toX, toY - radius)
            ]
            
            for px, py in points:
                if self.isBlocking(math.floor(px), math.floor(py), z):
                    return [fromX, fromY]
            
            return [toX, toY]

        def isVoxel(self, x, y, z):
            if x < 0 or x >= self.mapWidth or y < 0 or y >= self.mapHeight: return False
            
            layer = int(math.floor(z))
            tile = 0
            
            if isinstance(self.worldMap, dict):
                if layer in self.worldMap:
                    grid = self.worldMap[layer]
                    if int(x) < len(grid) and int(y) < len(grid[int(x)]):
                        tile = grid[int(x)][int(y)]
            else:
                if layer == 0:
                    tile = self.worldMap[int(x)][int(y)]
            
            return tile > 0

        def cast_ray(self, start_x, start_y, start_z, dir_x, dir_y, dir_z, max_dist=10.0):
            map_address, _ = self.flat_map_buffer.buffer_info()
            
            # Call to cpp
            return stein_core.cast_ray_fast(
                start_x, start_y, start_z, 
                dir_x, dir_y, dir_z, 
                map_address, 
                self.mapWidth, self.mapHeight, self.num_layers, self.min_layer,
                max_dist
            )

        def handle_builder_action(self, action):
            u_pitch = self.player.pitch / float(self.height)
            pitch_angle = math.atan(u_pitch)
            
            cp = math.cos(pitch_angle)
            sp = math.sin(pitch_angle)
            
            px = self.player.planex
            py = self.player.planey
            plen = math.sqrt(px*px + py*py)
            if plen == 0: plen = 1.0
            rx = px / plen
            ry = py / plen
            
            bx = self.player.dirx
            by = self.player.diry
            
            cz = rx*by - ry*bx
            dot_rb = rx*bx + ry*by
            
            rdx = bx * cp + 0.0 * sp + rx * dot_rb * (1.0 - cp)
            rdy = by * cp + 0.0 * sp + ry * dot_rb * (1.0 - cp)
            rdz = 0.0 * cp + cz * sp + 0.0 * dot_rb * (1.0 - cp)
            
            rdx = bx * cp + 0.0 + rx * dot_rb * (1.0 - cp)
            rdy = by * cp + 0.0 + ry * dot_rb * (1.0 - cp)
            rdz = 0.0 + cz * sp + 0.0
            
            # Normalize
            rlen = math.sqrt(rdx*rdx + rdy*rdy + rdz*rdz)
            if rlen > 0:
                rdx /= rlen
                rdy /= rlen
                rdz /= rlen
            
            res = self.cast_ray(self.player.x, self.player.y, self.player.z + 0.5, rdx, rdy, rdz, max_dist=100.0)
            
            if res[0]: 
                mx, my, mz, side, sx, sy, sz = res[1:]
                
                if action == 'remove':
                    self.set_voxel(mx, my, mz, 0)
                elif action == 'place':
                    nx, ny, nz = mx, my, mz
                    if side == 0: nx -= sx
                    elif side == 1: ny -= sy
                    elif side == 2: nz -= sz
                    
                    if math.floor(self.player.x) == nx and math.floor(self.player.y) == ny and math.floor(self.player.z) == nz:
                        return
                    
                    self.set_voxel(nx, ny, nz, self.selected_voxel)
            else:
                if action == 'place':
                    nx = int(math.floor(self.player.x))
                    ny = int(math.floor(self.player.y))
                    nz = int(math.floor(self.player.z))
                    self.set_voxel(nx, ny, nz, self.selected_voxel)

        def shift_map(self, off_x, off_y):
            self.mapWidth += off_x
            self.mapHeight += off_y
            self.map_w = self.mapWidth
            self.map_h = self.mapHeight
            
            for z, grid in self.worldMap.items():
                curr_w = len(grid)
                curr_h = len(grid[0]) if curr_w > 0 else 0
                
                if off_x > 0:
                    new_cols = [[0] * curr_h for _ in range(off_x)]
                    for col in reversed(new_cols):
                        grid.insert(0, col)
                
                if off_y > 0:
                    for col in grid:
                        for _ in range(off_y):
                            col.insert(0, 0)
            
            self.player.x += off_x
            self.player.y += off_y
            
            for e in self.enemies:
                e.x += off_x
                e.y += off_y
                if hasattr(e, 'last_known_x') and e.last_known_x is not None: e.last_known_x += off_x
                if hasattr(e, 'last_known_y') and e.last_known_y is not None: e.last_known_y += off_y
            
            for p in self.projectiles:
                p.x += off_x
                p.y += off_y
            
            new_sprites = []
            for s in self.sprite_positions:
                l = list(s)
                l[0] += off_x
                l[1] += off_y
                new_sprites.append(tuple(l))
            self.sprite_positions = new_sprites
            
            new_spawns = []
            for s in self.spawn_points:
                new_spawns.append((s[0] + off_x, s[1] + off_y))
            self.spawn_points = new_spawns
            
            new_exits = []
            for e in self.exits:
                l = list(e)
                l[0] += off_x
                l[1] += off_y
                new_exits.append(tuple(l))
            self.exits = new_exits
            
            self.pickup_msg = f"MAP SHIFTED BY {off_x}, {off_y}"
            self.pickup_msg_timer = 2.0

        def set_voxel(self, x, y, z, val):
            map_changed = False
            if not isinstance(self.worldMap, dict):
                new_map = {0: [row[:] for row in self.worldMap]}
                self.worldMap = new_map
                self.map_data = new_map
            
            off_x = 0
            off_y = 0
            if x < 0:
                off_x = abs(x)
                x = 0
            if y < 0:
                off_y = abs(y)
                y = 0
            
            if off_x > 0 or off_y > 0:
                self.shift_map(off_x, off_y)
                map_changed = True
            
            # Check for expansion
            if x >= self.mapWidth or y >= self.mapHeight:
                new_w = max(self.mapWidth, x + 1)
                new_h = max(self.mapHeight, y + 1)
                self.expand_map(new_w, new_h)
                map_changed = True

            if z not in self.worldMap:
                if val == 0: 
                    if map_changed: self.map_texture = self.create_map_texture()
                    return 
                self.worldMap[z] = [[0 for _ in range(self.mapHeight)] for _ in range(self.mapWidth)]
            
            grid = self.worldMap[z]
            if 0 <= x < len(grid) and 0 <= y < len(grid[0]):
                grid[x][y] = val
                map_changed = True

                if 0 <= x < self.mapWidth and 0 <= y < self.mapHeight:
                    layer_idx = z - self.min_layer
                    if 0 <= layer_idx < self.num_layers:
                        idx = (layer_idx * self.mapWidth * self.mapHeight) + (x * self.mapHeight) + y
                        self.flat_map_buffer[idx] = val
                
            if map_changed:
                self.map_texture = self.create_map_texture()

        def expand_map(self, new_w, new_h):
            self.mapWidth = new_w
            self.mapHeight = new_h
            self.map_w = new_w
            self.map_h = new_h
            
            for z, grid in self.worldMap.items():
                current_w = len(grid)
                current_h = len(grid[0]) if current_w > 0 else 0
                
                # Resize width
                if new_w > current_w:
                    for _ in range(new_w - current_w):
                        grid.append([0] * current_h)
                
                # Resize height
                for row in grid:
                    if new_h > len(row):
                        row.extend([0] * (new_h - len(row)))
            
            self.pickup_msg = f"MAP EXPANDED TO {new_w}x{new_h}"
            self.pickup_msg_timer = 2.0

        # EVENT HANDLING
        def event(self, ev, x, y, st):
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_LCTRL or ev.key == pygame.K_RCTRL:
                    self.kb_running = True
                    raise renpy.IgnoreEvent()
            
            if ev.type == pygame.KEYUP:
                if ev.key == pygame.K_LCTRL or ev.key == pygame.K_RCTRL:
                    self.kb_running = False
                    raise renpy.IgnoreEvent()

            if self.return_value:
                return self.return_value

            global simulate_touch
            if not self.mouse_initialized and not simulate_touch:
                pygame.mouse.set_visible(False); pygame.event.set_grab(True); self.mouse_initialized = True
            if simulate_touch:
                if ev.type in (pygame.FINGERDOWN, pygame.FINGERMOTION, pygame.FINGERUP): self.handle_multitouch_events(ev)
                elif ev.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEMOTION, pygame.MOUSEBUTTONUP): self.handle_mouse_simulation(ev, x, y)
            else: self.handle_pc_input(ev)
            if ev.type in (pygame.JOYBUTTONDOWN, pygame.JOYBUTTONUP, pygame.JOYHATMOTION, pygame.JOYDEVICEADDED, pygame.JOYDEVICEREMOVED): self.handle_gamepad_input(ev)
            renpy.retain_after_load()

        def handle_multitouch_events(self, ev):
            LOOK_THRESHOLD_X = 0.5; finger_id = ev.finger_id; event_x = ev.x * self.width; event_y = ev.y * self.height
            if ev.type == pygame.FINGERDOWN:
                action = None
                if ev.x <= LOOK_THRESHOLD_X: action = 'move'
                elif ev.x > LOOK_THRESHOLD_X: action = 'look'
                if action: self.active_fingers[finger_id] = {'action': action, 'start_pos': (event_x, event_y), 'current_pos': (event_x, event_y), 'dx_accum': 0.0}
            elif ev.type == pygame.FINGERMOTION:
                if finger_id in self.active_fingers:
                    info = self.active_fingers[finger_id]
                    if info['action'] == 'move': info['current_pos'] = (event_x, event_y)
                    elif info['action'] == 'look': info['dx_accum'] += ev.dx * self.width
            elif ev.type == pygame.FINGERUP:
                if finger_id in self.active_fingers: del self.active_fingers[finger_id]

        def update_player_from_touch_state(self):
            self.touch_speed = 0.0; self.touch_strafe = 0.0; self.touch_dir = 0.0
            for finger_id, info in list(self.active_fingers.items()):
                if info['action'] == 'move':
                    dx = info['current_pos'][0] - info['start_pos'][0]; dy = info['current_pos'][1] - info['start_pos'][1]
                    self.touch_speed += -dy / 80.0; self.touch_strafe += dx / 80.0
                elif info['action'] == 'look':
                    self.touch_dir += (info['dx_accum'] / self.width) * 25.0; info['dx_accum'] = 0.0

        def handle_mouse_simulation(self, ev, x, y):
            LOOK_THRESHOLD_PIXELS = self.width * 0.5; button_id = getattr(ev, 'button', None)
            if ev.type == pygame.MOUSEBUTTONDOWN:
                if button_id == 1 and x > LOOK_THRESHOLD_PIXELS: self.active_fingers[1] = {'action': 'look', 'dx_accum': 0.0}
                elif button_id == 3 and x <= LOOK_THRESHOLD_PIXELS: self.active_fingers[3] = {'action': 'move', 'start_pos':(x,y), 'current_pos':(x,y)}
            elif ev.type == pygame.MOUSEMOTION:
                if ev.buttons[0] and 1 in self.active_fingers: self.active_fingers[1]['dx_accum'] += ev.rel[0]
                if ev.buttons[2] and 3 in self.active_fingers: self.active_fingers[3]['current_pos'] = (x, y)
            elif ev.type == pygame.MOUSEBUTTONUP:
                if button_id in self.active_fingers: del self.active_fingers[button_id]

        def handle_pc_input(self, ev):
            # Handle mouse look
            if ev.type == pygame.MOUSEMOTION:
                base_sens = 0.003
                base_pitch = 0.8
                
                sensitivity = base_sens * persistent.stein_mouse_sens
                pitch_sensitivity = base_pitch * persistent.stein_mouse_sens

                if self.is_aiming:
                    sensitivity *= 0.25
                    pitch_sensitivity *= 0.5

                self.player.rot -= ev.rel[0] * sensitivity
                self.player.planerot -= ev.rel[0] * sensitivity
                
                # Pitch (vertical look)
                self.player.pitch -= ev.rel[1] * pitch_sensitivity
                self.player.pitch = max(-1000.0, min(1000.0, self.player.pitch))

            if ev.type == pygame.KEYDOWN:
                if config.developer:
                    if ev.key == pygame.K_o:
                        self.builder_mode = not self.builder_mode
                        self.player.fly_mode = self.builder_mode
                        if self.builder_mode:
                            self.pickup_msg = "BUILDER MODE ON"
                            self.pickup_msg_timer = 2.0
                        else:
                            self.pickup_msg = "BUILDER MODE OFF"
                            self.pickup_msg_timer = 2.0

                    if ev.key == pygame.K_p:
                        print("--- LEVEL DATA START ---")
                        if isinstance(self.worldMap, dict):
                            print("{")
                            for z in sorted(self.worldMap.keys()):
                                print(f"    {z}: [")
                                for row in self.worldMap[z]:
                                    print(f"        {repr(row)},")
                                print("    ],")
                            print("}")
                        else:
                            print("[")
                            for row in self.worldMap:
                                print(f"    {repr(row)},")
                            print("]")
                        print("--- LEVEL DATA END ---")
                        self.pickup_msg = "LEVEL DATA PRINTED"
                        self.pickup_msg_timer = 2.0

                if ev.key == pygame.K_ESCAPE:
                    pygame.mouse.set_visible(True)
                    pygame.event.set_grab(False)
                    self.mouse_initialized = False
                    return

                if ev.key == pygame.K_1: self.switch_to_slot(SLOT_MELEE)
                if ev.key == pygame.K_2: self.switch_to_slot(SLOT_HANDGUN)
                if ev.key == pygame.K_3: self.switch_to_slot(SLOT_LONG)
                if ev.key == pygame.K_4: self.switch_to_slot(SLOT_SPECIAL)

                if ev.key == pygame.K_f:
                    self.flashlight_on = not self.flashlight_on

                if ev.key == pygame.K_w: self.kb_speed = 1.0
                if ev.key == pygame.K_s: self.kb_speed = -1.0
                if ev.key == pygame.K_a: self.kb_strafe = -1.0
                if ev.key == pygame.K_d: self.kb_strafe = 1.0
                
                # Arrow key controls
                if ev.key == pygame.K_UP: self.kb_speed = 1.0
                if ev.key == pygame.K_DOWN: self.kb_speed = -1.0
                if ev.key == pygame.K_LEFT: self.kb_dir = 1.0
                if ev.key == pygame.K_RIGHT: self.kb_dir = -1.0
                
                if ev.key == pygame.K_SPACE: 
                    if self.player.fly_mode: self.kb_fly_up = True
                    else: self.player.trigger_jump()
                
                if ev.key == pygame.K_LCTRL or ev.key == pygame.K_RCTRL:
                    self.kb_running = True

                if ev.key == pygame.K_n:
                    if self.player.fly_mode: self.kb_fly_down = True

            if ev.type == pygame.MOUSEBUTTONDOWN:
                if self.builder_mode:
                    if ev.button == 1: # Left Click - Place
                        self.handle_builder_action('place')
                    elif ev.button == 3: # Right Click - Remove
                        self.handle_builder_action('remove')
                    elif ev.button == 4: # Wheel Up
                        self.selected_voxel = (self.selected_voxel % 9) + 1
                        self.pickup_msg = f"VOXEL: {self.selected_voxel}"
                        self.pickup_msg_timer = 1.0
                    elif ev.button == 5: # Wheel Down
                        self.selected_voxel = ((self.selected_voxel - 2) % 9) + 1
                        self.pickup_msg = f"VOXEL: {self.selected_voxel}"
                        self.pickup_msg_timer = 1.0
                    
                    return 

                if ev.button == 1: # Left mouse button
                    self.mouse_firing = True
                elif ev.button == 3: # Right mouse button (Aim)
                    self.is_aiming = True
            
            if ev.type == pygame.MOUSEBUTTONUP:
                if ev.button == 1:
                    self.mouse_firing = False
                elif ev.button == 3:
                    self.is_aiming = False

            if ev.type == pygame.KEYUP:
                if ev.key == pygame.K_SPACE: self.kb_fly_up = False
                if ev.key in (pygame.K_w, pygame.K_s, pygame.K_UP, pygame.K_DOWN): self.kb_speed = 0.0
                if ev.key in (pygame.K_a, pygame.K_d): self.kb_strafe = 0.0
                if ev.key in (pygame.K_LEFT, pygame.K_RIGHT): self.kb_dir = 0.0
                if ev.key in (pygame.K_LCTRL, pygame.K_RCTRL): 
                    self.kb_running = False
                
                if ev.key == pygame.K_n:
                    self.kb_fly_down = False

        def poll_gamepad(self):
            self.gp_speed = 0.0; self.gp_strafe = 0.0; self.gp_dir = 0.0
            self.gp_aiming = False; self.gp_firing = False; self.gp_running = False
            DEADZONE = 0.25; TRIGGER_THRESHOLD = 0.6 
            is_switch_held = False

            for joy in self.joysticks:
                try:
                    if not joy.get_init(): continue
                    name = joy.get_name().lower()
                    if "accelerometer" in name or "gyro" in name: continue
                    
                    if joy.get_numaxes() > 4 and joy.get_axis(4) > TRIGGER_THRESHOLD: self.gp_aiming = True
                    if renpy.android:
                        if joy.get_numbuttons() > 9 and joy.get_button(9): self.gp_running = True
                    else:
                        if joy.get_numbuttons() > 4 and joy.get_button(4): self.gp_running = True

                    if joy.get_numaxes() > 0:
                        x = joy.get_axis(0)
                        if abs(x) > DEADZONE: self.gp_strafe += x 
                    if joy.get_numaxes() > 1:
                        y = joy.get_axis(1)
                        if abs(y) > DEADZONE: self.gp_speed -= y 
                    if joy.get_numaxes() > 2:
                        rx = joy.get_axis(2)
                        if abs(rx) > DEADZONE:
                            sens = 2.5 * persistent.stein_gamepad_sens_x
                            if self.is_aiming or self.gp_aiming: sens *= 0.25
                            self.gp_dir -= rx * sens
                    if joy.get_numaxes() > 3:
                        ry = joy.get_axis(3)
                        if abs(ry) > DEADZONE:
                            p_speed = 19.0 * persistent.stein_gamepad_sens_y
                            if self.is_aiming or self.gp_aiming: p_speed *= 0.5
                            self.player.pitch -= ry * p_speed
                            self.player.pitch = max(-1000.0, min(1000.0, self.player.pitch))

                    if joy.get_numaxes() > 5 and joy.get_axis(5) > TRIGGER_THRESHOLD: self.gp_firing = True
                    if joy.get_numbuttons() > 5 and joy.get_button(5): self.gp_firing = True
                    if joy.get_numbuttons() > 0 and joy.get_button(0): self.player.trigger_jump()
                    if joy.get_numbuttons() > 3 and joy.get_button(3): is_switch_held = True

                    btn_flashlight_held = False

                    if renpy.android:
                        if joy.get_numbuttons() > 11 and joy.get_button(11):
                            btn_flashlight_held = True
                    elif joy.get_numhats() > 0:
                        hat_x, hat_y = joy.get_hat(0)
                        if hat_y == 1: 
                            btn_flashlight_held = True
                    
                    if btn_flashlight_held and not self.prev_btn_flashlight:
                        self.flashlight_on = not self.flashlight_on
                    
                    self.prev_btn_flashlight = btn_flashlight_held

                except pygame.error: continue
            
            if is_switch_held and not getattr(self, 'prev_btn_weapon_switch', False):
                self.cycle_weapon()
            
            self.prev_btn_weapon_switch = is_switch_held

        def handle_gamepad_input(self, ev):
            if ev.type == pygame.JOYDEVICEADDED or ev.type == pygame.JOYDEVICEREMOVED:
                pygame.joystick.quit()
                pygame.joystick.init()
                self.joysticks = [pygame.joystick.Joystick(x) for x in range(pygame.joystick.get_count())]
                for joy in self.joysticks: 
                    try: joy.init()
                    except: pass
