init -10 python:
    class DamageIndicator(object):
        def __init__(self, angle, duration=2.0):
            self.angle = angle
            self.duration = duration
            self.max_duration = duration

    class Player(object):
        def __init__(self, wm, x, y, dirx, diry, planex, planey):
            self.wm = wm
            self.x = x; self.y = y
            self.dirx = float(dirx); self.diry = float(diry)
            self.planex = float(planex); self.planey = float(planey)
            self.health = 100
            self.pitch = 0.0
            self.current_weapon_name = "fist"
            self.rot = math.atan2(diry, dirx)
            self.planerot = math.atan2(planey, planex)
            self.dir = 0; self.speed = 0; self.strafe_speed = 0
            self.moveSpeed = 2.5; self.rotSpeed = 90 * math.pi / 180
            self.mapWidth = wm.mapWidth; self.mapHeight = wm.mapHeight
            self.z = 0.0; self.velocity_z = 0.0
            self.GRAVITY = 35.0; self.JUMP_FORCE = 8.5; self.CROUCH_DEPTH = -0.4
            self.is_grounded = True; self.is_crouching = False
            self.crouch_timer = 0.0; self.crouch_duration = 0.06
            self.fly_mode = False

        def get_ground_height_at(self, x, y, check_z=None):
            if check_z is None: check_z = self.z
            
            map_address, _ = self.wm.flat_map_buffer.buffer_info()
            
            return stein_core.get_map_height(
                x, y, check_z,
                map_address,
                self.wm.mapWidth, self.wm.mapHeight,
                self.wm.num_layers, self.wm.min_layer
            )

        def trigger_jump(self):
            if self.is_grounded and not self.is_crouching:
                self.is_crouching = True; self.crouch_timer = self.crouch_duration

        def update_physics(self, dt):
            if self.fly_mode:
                self.is_grounded = False
                self.velocity_z = 0.0
                
                fly_speed = 5.0
                if self.wm.kb_running: fly_speed = 10.0
                
                if self.wm.kb_fly_up:
                    self.z += fly_speed * dt
                if self.wm.kb_fly_down:
                    self.z -= fly_speed * dt
                return

            floor_h = self.get_ground_height_at(self.x, self.y)
            
            if self.is_crouching:
                self.crouch_timer -= dt
                progress = 1.0 - (self.crouch_timer / self.crouch_duration)
                target_z = floor_h + (self.CROUCH_DEPTH * math.sin(progress * math.pi))
                self.z = target_z 
                
                if self.crouch_timer <= 0:
                    self.is_crouching = False; self.is_grounded = False; self.velocity_z = self.JUMP_FORCE
                    self.z = max(self.z, floor_h)
            
            p_data = self.wm.player_data
            p_data.x = self.x
            p_data.y = self.y
            p_data.z = self.z
            p_data.vel_z = self.velocity_z
            p_data.rot = self.rot
            p_data.is_grounded = 1 if self.is_grounded else 0
            p_data.is_crouching = 1 if self.is_crouching else 0

        def resolve_wall_collision(self, radius):
            if self.fly_mode: return

            # Right
            if self.wm.isBlocking(math.floor(self.x + radius), math.floor(self.y), self.z):
                self.x = math.floor(self.x + radius) - radius - 0.001
            # Left
            elif self.wm.isBlocking(math.floor(self.x - radius), math.floor(self.y), self.z):
                self.x = math.floor(self.x - radius) + 1.0 + radius + 0.001
            
            # Down
            if self.wm.isBlocking(math.floor(self.x), math.floor(self.y + radius), self.z):
                self.y = math.floor(self.y + radius) - radius - 0.001
            # Up
            elif self.wm.isBlocking(math.floor(self.x), math.floor(self.y - radius), self.z):
                self.y = math.floor(self.y - radius) + 1.0 + radius + 0.001

        def move(self, dt):
            self.update_physics(dt)

            if self.fly_mode:
                moveStep = self.speed * self.moveSpeed * dt
                strafeStep = self.strafe_speed * self.moveSpeed * dt
                self.rot += self.dir * self.rotSpeed * dt
                self.rot %= twoPI
                
                vx = math.cos(self.rot) * moveStep + math.sin(self.rot) * strafeStep
                vy = math.sin(self.rot) * moveStep - math.cos(self.rot) * strafeStep
                
                self.x += vx
                self.y += vy
            else:
                # Use the new C implementation
                map_address, _ = self.wm.flat_map_buffer.buffer_info()
                
                SteinWrapper.update_player_complete(
                    self.wm.player_ptr,
                    dt,
                    float(self.speed),        # input_speed
                    float(self.strafe_speed), # input_strafe
                    float(self.dir),          # input_turn
                    float(self.moveSpeed),
                    float(self.rotSpeed),
                    map_address,
                    self.wm.mapWidth, self.wm.mapHeight,
                    self.wm.num_layers, self.wm.min_layer
                )
                
                p_data = self.wm.player_data
                self.x = p_data.x
                self.y = p_data.y
                self.z = p_data.z
                self.velocity_z = p_data.vel_z
                self.rot = p_data.rot
                self.is_grounded = (p_data.is_grounded == 1)
                
                if self.z < -25.0:
                    self.z = 10.0; self.velocity_z = 0.0

            self.dirx = math.cos(self.rot)
            self.diry = math.sin(self.rot)
            
            self.planex = math.cos(self.rot - 1.5708) * 0.66 
            self.planey = math.sin(self.rot - 1.5708) * 0.66

    class Projectile(object):
        def __init__(self, wm, x, y, dir_x, dir_y, texture_index, damage, fired_by_player=False, is_invisible=False, pitch=0.0):
            self.wm = wm
            self.x = x
            self.y = y
            self.dir_x = dir_x
            self.dir_y = dir_y
            self.texture_index = texture_index
            self.damage = damage
            self.fired_by_player = fired_by_player
            self.is_invisible = is_invisible
            self.pitch = pitch
            
            if self.fired_by_player:
                self.speed = 100.0 
                self.z = self.wm.player.z + 0.5
                self.dir_z = (pitch / float(self.wm.height))
            else:
                self.speed = 12.0
                ground_h = self.wm.player.get_ground_height_at(x, y, check_z=self.wm.player.z)
                self.z = ground_h + 0.5
                
                p_x = self.wm.player.x
                p_y = self.wm.player.y
                p_z = self.wm.player.z + 0.3
                
                dist_2d = math.sqrt((p_x - x)**2 + (p_y - y)**2)
                if dist_2d > 0:
                    self.dir_z = (p_z - self.z) / dist_2d
                else:
                    self.dir_z = 0.0

        def update(self, dt):
            distance_to_travel = self.speed * dt
            
            step_size = 0.4
            dist_traveled = 0.0

            while dist_traveled < distance_to_travel:
                step = min(step_size, distance_to_travel - dist_traveled)
                
                self.x += self.dir_x * step
                self.y += self.dir_y * step
                self.z += self.dir_z * step
                dist_traveled += step

                if self.wm.isBlocking(math.floor(self.x), math.floor(self.y), self.z): 
                    return False
                
                ground_h = self.wm.player.get_ground_height_at(self.x, self.y, check_z=self.z)
                if self.z < ground_h:
                    return False

                if not self.fired_by_player:
                    player = self.wm.player
                    if math.sqrt((player.x - self.x)**2 + (player.y - self.y)**2) < 0.5:
                        if self.z >= player.z and self.z <= player.z + 0.9:
                            if not self.wm.builder_mode:
                                player.health -= self.damage
                                self.wm.add_damage_indicator(-self.dir_x, -self.dir_y)
                                self.wm.damage_flash_timer = 0.2
                                self.wm.time_since_last_damage = 0.0
                                renpy.sound.play("sounds/ow.ogg", channel="audio")
                            return False
                else:
                    for enemy in list(self.wm.enemies):
                        if math.sqrt((enemy.x - self.x)**2 + (enemy.y - self.y)**2) < 0.5:
                            e_ground = self.wm.player.get_ground_height_at(enemy.x, enemy.y, check_z=enemy.y) # Enemy doesnt have Z, assume ground
                            e_ground = self.wm.player.get_ground_height_at(enemy.x, enemy.y, check_z=self.z) 
                            
                            if self.z >= e_ground and self.z <= e_ground + 0.9:
                                if hasattr(self, 'pitch'):
                                    pass

                                taken = True
                                if hasattr(enemy, 'take_damage'): 
                                    taken = enemy.take_damage(self.damage)
                                else:
                                    enemy.health -= self.damage
                                
                                if taken:
                                    self.wm.hit_marker_timer = 0.15
                                    renpy.sound.play("sounds/ow.ogg", channel="audio")
                                    if enemy.health <= 0:
                                        if self.wm.is_arena_mode: persistent.stein_kills += 1
                                        if enemy in self.wm.enemies: self.wm.enemies.remove(enemy)
                                        self.wm.sprite_positions.append((enemy.x, enemy.y, enemy.destroyed_texture_index))
                                        
                                        if self.wm.is_arena_mode:
                                            drop_prob = 1.0 if enemy.coin_index == 12 else 0.35
                                            if renpy.random.random() < drop_prob:
                                                self.wm.sprite_positions.append((enemy.x, enemy.y, enemy.coin_index)) # Coins

                                        # Weapon drops removed as per request (by Fran)
                                        # if not renpy.store.stein_has_shotgun:
                                        #     if renpy.random.random() < (0.25 if enemy.coin_index == 12 else 0.10):
                                        #         self.wm.sprite_positions.append((enemy.x, enemy.y, 13)) # Shotgun
                                        
                                        # if not renpy.store.stein_has_minigun:
                                        #     if renpy.random.random() < 0.10:
                                        #         self.wm.sprite_positions.append((enemy.x, enemy.y, 15)) # Minigun

                                    return False
            return True

    class BaseEnemy(object):
        def __init__(self, wm, x, y, health=100):
            self.wm = wm
            self.x = x; self.y = y; self.health = health
            self.state = 'idle'
            self.last_known_x = None; self.last_known_y = None
            self.texture_index = 0; self.destroyed_texture_index = 0
            self.moveSpeed = 1.5; self.rotSpeed = 75 * math.pi / 180
            self.attack_range = 8.0; self.sight_range = 15.0
            if self.wm.is_arena_mode: self.attack_range = 24.0; self.sight_range = 30.0
            self.attack_cooldown = 1.5; self.damage = 10; self.coin_index = 11
            self.attack_timer = 1.0
            self.mapWidth = wm.mapWidth; self.mapHeight = wm.mapHeight

        def update(self, dt, player):
            self.attack_timer = max(0, self.attack_timer - dt)
            player_x, player_y = player.x, player.y
            dist_to_player = math.sqrt((player_x - self.x)**2 + (player_y - self.y)**2)
            has_los = self.has_line_of_sight(player_x, player_y)

            if has_los: self.last_known_x = player_x; self.last_known_y = player_y

            if self.state == 'idle':
                if dist_to_player < self.sight_range and has_los: self.state = 'chasing'
            elif self.state == 'chasing':
                target_x, target_y = player_x, player_y
                if not has_los:
                    if self.last_known_x is not None:
                        target_x, target_y = self.last_known_x, self.last_known_y
                        if math.sqrt((target_x - self.x)**2 + (target_y - self.y)**2) < 1.0:
                            self.state = 'idle'; self.last_known_x = None; return
                    else: self.state = 'idle'; return
                
                should_move = True
                if has_los:
                    if dist_to_player < self.attack_range:
                        if dist_to_player < self.attack_range * 0.5: should_move = False
                        if self.attack_timer == 0: self.attack(player)
                    else: should_move = True
                if should_move: self.move(dt, target_x, target_y)

        def attack(self, player): self.attack_timer = self.attack_cooldown

        def check_wall_collision(self, x, y, radius=0.3):
            if self.wm.isBlocking(x, y): return True
            if self.wm.isBlocking(x + radius, y): return True
            if self.wm.isBlocking(x - radius, y): return True
            if self.wm.isBlocking(x, y + radius): return True
            if self.wm.isBlocking(x, y - radius): return True
            return False

        def move(self, dt, target_x, target_y):
            dx = target_x - self.x; dy = target_y - self.y
            angle = math.atan2(dy, dx)
            look_dist = 1.2; radius = 0.35
            ahead_x = self.x + math.cos(angle) * look_dist
            ahead_y = self.y + math.sin(angle) * look_dist
            
            if self.check_wall_collision(ahead_x, ahead_y, radius):
                offsets = [-0.785, 0.785, -1.57, 1.57]
                found_path = False
                for off in offsets:
                    test_angle = angle + off
                    tx = self.x + math.cos(test_angle) * look_dist
                    ty = self.y + math.sin(test_angle) * look_dist
                    if not self.check_wall_collision(tx, ty, radius):
                        angle = test_angle; found_path = True; break
                if not found_path: angle += 2.0

            moveStep = self.moveSpeed * dt
            vx = math.cos(angle) * moveStep; vy = math.sin(angle) * moveStep
            if not self.check_wall_collision(self.x + vx, self.y, radius): self.x += vx
            if not self.check_wall_collision(self.x, self.y + vy, radius): self.y += vy

        def has_line_of_sight(self, target_x, target_y):
            map_address, _ = self.wm.flat_map_buffer.buffer_info()
            
            
            check_z = self.wm.player.z + 0.5
            
            return stein_core.check_line_of_sight(
                self.x, self.y, check_z,
                target_x, target_y,
                map_address,
                self.wm.mapWidth, self.wm.mapHeight, 
                self.wm.num_layers, self.wm.min_layer
            )

    class Guard(BaseEnemy):
        def __init__(self, wm, x, y, texture_index, destroyed_texture_index, health=100):
            super(Guard, self).__init__(wm, x, y, health)
            self.texture_index = texture_index; self.destroyed_texture_index = destroyed_texture_index
            self.moveSpeed = 1.5; self.damage = 10; self.bullet_texture_index = 6

        def attack(self, player):
            super(Guard, self).attack(player)
            
            dir_x = player.x - self.x
            dir_y = player.y - self.y
            dist = math.sqrt(dir_x**2 + dir_y**2)
            
            if dist > 0:
                dir_x /= dist
                dir_y /= dist
            
            self.wm.spawn_projectile(
                self.x, self.y, self.wm.player.z + 0.5, 
                dir_x, dir_y, 0.0,
                12.0, 
                self.bullet_texture_index, 
                self.damage, 
                False
            )
            
            renpy.sound.play("sounds/e-gunshot.ogg", channel="audio")

    class Yuritler(Guard):
        def __init__(self, wm, x, y, health=150):
            super(Yuritler, self).__init__(wm, x, y, 9, 10, health)
            self.damage = 5; self.moveSpeed = 1.8; self.attack_cooldown = 1.0; self.coin_index = 12
        
        def attack(self, player):
            self.attack_timer = self.attack_cooldown
            dir_x = player.x - self.x
            dir_y = player.y - self.y
            dist = math.sqrt(dir_x**2 + dir_y**2)
            
            if dist > 0:
                base_angle = math.atan2(dir_y, dir_x)
                for i in range(4):
                    offset = (i / 3.0 - 0.5) * 0.2
                    p_dirx = math.cos(base_angle + offset)
                    p_diry = math.sin(base_angle + offset)
                    
                    self.wm.spawn_projectile(
                        self.x, self.y, self.wm.player.z + 0.5,
                        p_dirx, p_diry, 0.0,
                        12.0,
                        self.bullet_texture_index, 
                        self.damage, 
                        False
                    )
            
            renpy.sound.play("sounds/e-gunshot.ogg", channel="audio")

    class EliteGuard(Guard):
        def __init__(self, wm, x, y, health=100):
            super(EliteGuard, self).__init__(wm, x, y, 4, 5, health)
            self.damage = 3; self.attack_cooldown = 0.1
            self.burst_limit = 10; self.shots_fired_in_burst = 0
            self.is_reloading = False; self.reload_time = 5.0; self.reload_timer = 0.0

        def update(self, dt, player):
            if self.is_reloading:
                self.reload_timer -= dt
                if self.reload_timer <= 0: self.is_reloading = False; self.shots_fired_in_burst = 0; self.attack_timer = 0.5
            super(EliteGuard, self).update(dt, player)

        def attack(self, player):
            if self.is_reloading: return
            self.attack_timer = self.attack_cooldown
            dir_x = player.x - self.x; dir_y = player.y - self.y
            dist = math.sqrt(dir_x**2 + dir_y**2)
            if dist > 0: dir_x /= dist; dir_y /= dist
            
            self.wm.spawn_projectile(self.x, self.y, self.wm.player.z + 0.5, dir_x, dir_y, 0.0, 12.0, self.bullet_texture_index, self.damage, False)
            
            renpy.sound.play("sounds/e-gunshot.ogg", channel="audio")
            self.shots_fired_in_burst += 1
            if self.shots_fired_in_burst >= self.burst_limit: self.is_reloading = True; self.reload_timer = self.reload_time

    class Sniper(Guard):
        def __init__(self, wm, x, y, health=100):
            super(Sniper, self).__init__(wm, x, y, 4, 5, health)
            self.damage = 20; self.attack_cooldown = 1.5; self.moveSpeed = 3.0; self.bullet_texture_index = 14
            self.dodge_cooldown = 4.0; self.dodge_timer = 0.0

        def update(self, dt, player):
            self.dodge_timer = max(0, self.dodge_timer - dt)
            super(Sniper, self).update(dt, player)

        def take_damage(self, amount):
            if self.dodge_timer <= 0:
                self.dodge_timer = self.dodge_cooldown
                player = self.wm.player
                dx = player.x - self.x; dy = player.y - self.y
                dist = math.sqrt(dx*dx + dy*dy)
                if dist > 0:
                    ndx = dx / dist; ndy = dy / dist
                    strafe_x = -ndy; strafe_y = ndx
                    dodge_distance = 1.5
                    tx = self.x + strafe_x * dodge_distance; ty = self.y + strafe_y * dodge_distance
                    if not self.check_wall_collision(tx, ty, 0.35): self.x = tx; self.y = ty
                    else:
                        tx = self.x - strafe_x * dodge_distance; ty = self.y - strafe_y * dodge_distance
                        if not self.check_wall_collision(tx, ty, 0.35): self.x = tx; self.y = ty
                return False
            self.health -= amount
            return True

    class Weapon(object):
        def __init__(self, name, category, 
            normal_frameCount=5, normal_fps=15, normal_flash_frame=0, normal_name=None,
            ads_enter_frameCount=0, ads_enter_fps=20, ads_enter_name=None,
            ads_fire_frameCount=0, ads_fire_fps=15, ads_fire_flash_frame=0, ads_fire_name=None,
            run_enter_frameCount=0, run_enter_fps=15, run_enter_flash_frame=0, run_enter_name=None,
            zoom_factor=11, damage=25, projectile_type=None, cooldown=0.5, 
            ads_idle=None, ads_fire=None, loop_frames=None, 
            flash_offset=(0,0), flash_ads_offset=(0,0), flash_size=1.0, flash_color=(1.0, 0.9, 0.7),
            frameCount=None, ads_name=None, ads_frameCount=None 
            ):
            
            self.name = name
            self.category = category
            
            if frameCount is not None: normal_frameCount = frameCount
            if ads_frameCount is not None: ads_fire_frameCount = ads_frameCount
            if ads_name is not None: ads_fire_name = ads_name

            self.damage = damage; self.projectile_type = projectile_type; self.cooldown = cooldown
            self.loop_frames = loop_frames
            
            self.flash_config = {
                'offset_normal': flash_offset,
                'offset_ads': flash_ads_offset,
                'size': flash_size,
                'color': flash_color,
                'frame_normal': normal_flash_frame,
                'frame_ads': ads_fire_flash_frame,
                'frame_run': run_enter_flash_frame
            }
            
            self.playing = False
            self.frame_index = 0
            self.oldst = None
            self.last_fired = 0.0
            self.current_flash_rot = 0.0
            
            # --- Animation Data ---
            self.anims = {
                'normal': [],
                'ads_enter': [],
                'ads_fire': [],
                'run_enter': []
            }
            
            self.fps = {
                'normal': normal_fps,
                'ads_enter': ads_enter_fps,
                'ads_fire': ads_fire_fps,
                'run_enter': run_enter_fps
            }
            
            # Load Normal
            base_normal = normal_name if normal_name else name
            for i in range(normal_frameCount): 
                self.anims['normal'].append(Transform("pics/weapons/%s%s.webp" % (base_normal, i+1), xysize=(1280, 720)))
                
            # Load ADS Enter
            if ads_enter_frameCount > 0:
                base_enter = ads_enter_name if ads_enter_name else (name + "_ads_enter")
                for i in range(ads_enter_frameCount):
                    self.anims['ads_enter'].append(Transform("pics/weapons/%s%s.webp" % (base_enter, i+1), xysize=(1280, 720)))

            # Load ADS Fire
            if ads_fire_frameCount > 0:
                base_ads_fire = ads_fire_name if ads_fire_name else (name + "_ads")
                for i in range(ads_fire_frameCount):
                    self.anims['ads_fire'].append(Transform("pics/weapons/%s%s.webp" % (base_ads_fire, i+1), xysize=(1280, 720)))
            
            # Load Run Enter
            if run_enter_frameCount > 0:
                base_run = run_enter_name if run_enter_name else (name + "_run")
                for i in range(run_enter_frameCount):
                    self.anims['run_enter'].append(Transform("pics/weapons/%s%s.webp" % (base_run, i+1), xysize=(1280, 720)))
            
            self.ads_idle_img = Transform(ads_idle, xysize=(1280, 720)) if ads_idle else None
            self.ads_fire_static = Transform(ads_fire, xysize=(1280, 720)) if ads_fire else None
            
            # State: 'hip', 'entering_ads', 'ads'
            self.aim_state = 'hip'
            self.anim_state = 'idle' # 'idle', 'playing'
            
            self.flash_base = Transform(Image("pics/items/sight.webp"), size=(512, 512))

        def play(self):
            if self.anim_state != 'playing':
                self.anim_state = 'playing'
                self.frame_index = 0
                self.oldst = None
                self.current_flash_rot = renpy.random.random() * math.pi * 2.0

        def render_to(self, r, width, height, st, at, is_ads=False, is_firing=False, movement_state=None):
            if self.oldst is None: self.oldst = st
            dt = st - self.oldst
            
            is_running = movement_state.get('is_running', False) if movement_state else False

            if is_firing:
                is_running = False
            
            if is_ads:
                if self.aim_state in ('entering_run', 'running', 'exiting_run'):
                    self.aim_state = 'hip'

                if self.aim_state == 'hip':
                    if self.anims['ads_enter']:
                        self.aim_state = 'entering_ads'
                        self.frame_index = 0
                        self.anim_state = 'idle'
                        self.oldst = st
                    else:
                        self.aim_state = 'ads'
            elif is_running and self.anims.get('run_enter'):
                if self.aim_state in ('hip', 'exiting_run'):
                    if self.aim_state == 'hip' and self.anim_state == 'playing':
                        pass
                    else:
                        self.aim_state = 'entering_run'
                        self.frame_index = 0
                        self.anim_state = 'idle'
                        self.oldst = st
                elif self.aim_state in ('ads', 'entering_ads'):
                    self.aim_state = 'hip'
            else:
                if is_firing and self.aim_state in ('running', 'entering_run', 'exiting_run'):
                    self.aim_state = 'hip'
                elif self.aim_state in ('running', 'entering_run'):
                    self.aim_state = 'exiting_run'
                    self.frame_index = 0
                    self.oldst = st

                if self.aim_state != 'hip' and self.aim_state != 'exiting_run':
                    self.aim_state = 'hip'

            current_img = None
            frame_duration = 0.1
            active_anim_list = []
            
            # Determine which animation list to use and frame duration
            if self.aim_state == 'entering_ads':
                active_anim_list = self.anims['ads_enter']
                frame_duration = 1.0 / self.fps['ads_enter']
                
                if dt >= frame_duration:
                    self.oldst = st
                    self.frame_index += 1
                    if self.frame_index >= len(active_anim_list):
                        self.aim_state = 'ads'
                        self.frame_index = 0
            
            if self.aim_state == 'entering_run':
                active_anim_list = self.anims['run_enter']
                frame_duration = 1.0 / self.fps['run_enter']
                
                if dt >= frame_duration:
                    self.oldst = st
                    self.frame_index += 1
                    if self.frame_index >= len(active_anim_list):
                        self.aim_state = 'running'
                        self.frame_index = len(active_anim_list) - 1
            
            if self.aim_state == 'exiting_run':
                active_anim_list = self.anims['run_enter']
                frame_duration = 1.0 / self.fps['run_enter']
                
                if dt >= frame_duration:
                    self.oldst = st
                    self.frame_index += 1
                    if self.frame_index >= len(active_anim_list):
                        self.aim_state = 'hip'
                        self.frame_index = 0
            
            if self.aim_state == 'hip':
                if self.anim_state == 'playing':
                    active_anim_list = self.anims['normal']
                    frame_duration = 1.0 / self.fps['normal']
                    
                    if dt >= frame_duration:
                        self.oldst = st
                        if self.loop_frames and is_firing:
                            if self.frame_index == self.loop_frames[-1]: self.frame_index = self.loop_frames[0]
                            else: self.frame_index += 1
                        else:
                            self.frame_index += 1
                        
                        if self.frame_index >= len(active_anim_list):
                            self.frame_index = 0
                            self.anim_state = 'idle'
                    
                    if active_anim_list:
                        safe_idx = min(self.frame_index, len(active_anim_list)-1)
                        current_img = active_anim_list[safe_idx]
                else:
                    if self.anims['normal']:
                        current_img = self.anims['normal'][0]
            
            elif self.aim_state == 'ads':
                if self.anim_state == 'playing':
                    active_anim_list = self.anims['ads_fire']
                    if active_anim_list:
                        frame_duration = 1.0 / self.fps['ads_fire']
                        if dt >= frame_duration:
                            self.oldst = st
                            self.frame_index += 1
                            if self.frame_index >= len(active_anim_list):
                                self.frame_index = 0
                                self.anim_state = 'idle'
                        
                        safe_idx = min(self.frame_index, len(active_anim_list)-1)
                        current_img = active_anim_list[safe_idx]
                    else:
                        current_img = self.ads_fire_static if (self.ads_fire_static and is_firing) else self.ads_idle_img
                else:
                    current_img = self.ads_idle_img
            
            elif self.aim_state == 'entering_ads':
                if active_anim_list:
                    safe_idx = min(self.frame_index, len(active_anim_list)-1)
                    current_img = active_anim_list[safe_idx]

            elif self.aim_state == 'entering_run':
                if active_anim_list:
                    safe_idx = min(self.frame_index, len(active_anim_list)-1)
                    current_img = active_anim_list[safe_idx]

            elif self.aim_state == 'exiting_run':
                run_list = self.anims['run_enter']
                if run_list:
                    rev_idx = len(run_list) - 1 - self.frame_index
                    safe_idx = max(0, min(rev_idx, len(run_list)-1))
                    current_img = run_list[safe_idx]
            
            elif self.aim_state == 'running':
                if self.anims['run_enter']:
                    current_img = self.anims['run_enter'][-1]

            # Render Weapon
            if current_img:
                eileen = renpy.render(current_img, 1280, 720, st, at)
                ew, eh = eileen.get_size()
                
                # Bobbing & Breathing Logic
                offset_x = 0; offset_y = 0
                is_moving = movement_state and movement_state.get('is_moving', False)
                
                if is_moving and self.aim_state in ('hip', 'entering_run', 'running', 'exiting_run'):
                    bob_speed = 15.0 if movement_state.get('is_running', False) else 10.0
                    bob_amp_x = 50.0 if movement_state.get('is_running', False) else 20.0
                    offset_x = math.sin(st * bob_speed) * bob_amp_x
                    offset_y = abs(math.cos(st * bob_speed)) * (bob_amp_x / 2.0)
                
                elif self.aim_state == 'ads':
                    # ADS Breathing
                    breath_speed = 1.5
                    breath_amp_x = 1.5
                    breath_amp_y = 2.5
                    offset_x = math.sin(st * breath_speed) * breath_amp_x
                    # Ensure y offset is always positive (moves down) to avoid revealing bottom cut
                    offset_y = (math.sin(st * breath_speed * 1.1) + 1.0) * 0.5 * breath_amp_y
                    
                elif self.aim_state == 'hip' and not is_moving:
                    # Idle Breathing
                    breath_speed = 2.0
                    breath_amp_x = 4.0
                    breath_amp_y = 6.0
                    offset_x = math.sin(st * breath_speed) * breath_amp_x
                    # Ensure y offset is always positive
                    offset_y = (math.sin(st * breath_speed * 0.95) + 1.0) * 0.5 * breath_amp_y
                
                if self.projectile_type and self.anim_state == 'playing':
                    should_flash = False
                    flash_config_key = 'normal'
                    
                    if self.aim_state == 'hip':
                        if self.frame_index == self.flash_config['frame_normal']:
                            should_flash = True
                            flash_config_key = 'normal'
                    elif self.aim_state == 'ads':
                        if self.frame_index == self.flash_config['frame_ads']:
                            should_flash = True
                            flash_config_key = 'ads'
                    
                    import time
                    time_diff = time.time() - self.last_fired
                    flash_dur = 1.0
                    
                    if should_flash or (time_diff < flash_dur): 
                        base_x = self.flash_config['offset_ads'][0] if (self.aim_state == 'ads') else self.flash_config['offset_normal'][0]
                        base_y = self.flash_config['offset_ads'][1] if (self.aim_state == 'ads') else self.flash_config['offset_normal'][1]
                        
                        fx = base_x + offset_x
                        fy = base_y + offset_y
                        
                        progress = time_diff / flash_dur
                        
                        f_t = Transform(
                            child=self.flash_base,
                            shader="stein.weapon_fx",
                            u_flash_progress=progress,
                            u_flash_color=self.flash_config['color'],
                            u_flash_angle=self.current_flash_rot,
                            u_heat_distortion=1.0 if getattr(persistent, "stein_heat_distortion", True) else 0.0,
                            u_enable_smoke=1.0 if getattr(persistent, "stein_lighting_quality", 0) == 0 else 0.0,
                            zoom=self.flash_config['size'],
                            additive=1.0
                        )
                        f_r = renpy.render(f_t, width, height, st, at)
                        fw, fh = f_r.get_size()
                        r.blit(f_r, (width/2 + fx - fw/2, height + fy - fh/2))

                r.blit(eileen, (width/2 - ew/2 + offset_x, height - eh + offset_y))

