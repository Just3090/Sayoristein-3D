# MeshGameLoop uses: MeshScene

# This shit does:
#     Handles user input
#     Manages player/camera position and rotation
#     Performs picking/raycasting by delegating to MeshScene

init -5 python:
    import math
    import time
    import pygame_sdl2 as pygame

    class MeshGameLoop(object):
        """
        Maintains the interactive state of the 3D scene (camera, input, selection).
        """
        def __init__(self, scene, free_fly=True, gameplay=False):
            self.scene = scene

            had_geometry = scene.has_geometry()
            self.player_x = 0.0 if had_geometry else 2.0
            self.player_y = 1.8 if had_geometry else 0.5
            self.player_z = -5.0 if had_geometry else 2.0
            self.player_yaw = 0.0
            self.player_pitch = 0.0

            self.free_fly = free_fly
            self.gameplay = gameplay

            self.move_speed = 3.0
            self.rot_speed = 2.0
            self.vertical_speed = 3.0
            self.pitch_speed = 1.5

            self.input_y = 0.0
            self.input_x = 0.0
            self.input_r = 0.0
            self.input_v = 0.0
            self.input_pitch = 0.0

            self.mouse_dx = 0.0
            self.mouse_dy = 0.0
            self.mouse_initialized = False
            self.rmb_down = False
            self.capture_mouse_always = bool(gameplay)
            self.skip_mouse = False
            self.mouse_sens = 0.003
            self.mouse_pitch_sens = 0.003

            self.pickup_msg = ""
            self.pickup_msg_timer = 0.0

            self.last_pick = -1
            self.last_pick_path = ""
            self.last_pick_t = 0.0

            self._debug_cam_last_motion_log = 0.0

        def add_message(self, text, duration=2.0):
            self.pickup_msg = str(text)
            self.pickup_msg_timer = float(duration)

        def camera_forward(self):
            """
            Calculates the normalized forward direction vector based on the camera's yaw and pitch.
            Must be aligned with the rendering vertex transformations.
            """
            render_yaw = self.player_yaw + (math.pi * 0.5)
            cp = math.cos(self.player_pitch)
            sp = math.sin(self.player_pitch)
            dx = -cp * math.sin(render_yaw)
            dy = sp
            dz = cp * math.cos(render_yaw)
            ln = math.sqrt(dx * dx + dy * dy + dz * dz) or 1.0
            return (dx / ln, dy / ln, dz / ln)

        def perform_pick(self):
            if not self.gameplay:
                return

            origin = (
                float(self.player_x),
                float(self.player_y) + 0.6,
                float(self.player_z),
            )

            direction = self.camera_forward()

            hit = self.scene.raycast_instance(origin, direction)
            if hit is None:
                self.last_pick = -1
                self.last_pick_path = ""
                self.last_pick_t = 0.0
                self.add_message("No instance under crosshair", 1.5)
            else:
                idx, t, path = hit
                self.last_pick = idx
                self.last_pick_path = path
                self.last_pick_t = t
                self.add_message("Selected #{} ({})".format(idx, path), 2.5)

        def release_mouse(self):
            import pygame_sdl2 as pygame
            if self.mouse_initialized:
                pygame.mouse.set_visible(True)
                pygame.event.set_grab(False)
                self.mouse_initialized = False
                self.rmb_down = False
                self.skip_mouse = False
                self.mouse_dx = 0.0
                self.mouse_dy = 0.0
                self.input_y = 0.0
                self.input_x = 0.0
                self.input_r = 0.0
                self.input_v = 0.0
                self.input_pitch = 0.0

        def event(self, ev, x, y, st):
            import pygame_sdl2 as pygame

            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE and self.gameplay:
                self.release_mouse()
                return None

            if TAICHI_DEBUG_CAMERA_INPUT:
                if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
                    btn = getattr(ev, "button", None)
                    print(
                        "[Taichi cam debug] mouse button ev type={} button={} view_xy=({:.0f},{:.0f}) rmb_down={} mouse_init={}".format(
                            ev.type, btn, x, y, self.rmb_down, self.mouse_initialized
                        )
                    )

            if not self.capture_mouse_always:
                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 3:
                    self.rmb_down = True
                    raise renpy.IgnoreEvent()

                if ev.type == pygame.MOUSEBUTTONUP and ev.button == 3:
                    self.rmb_down = False
                    raise renpy.IgnoreEvent()

            if self.gameplay and ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                self.perform_pick()
                raise renpy.IgnoreEvent()

            should_capture = self.capture_mouse_always or self.rmb_down

            if should_capture:
                if not self.mouse_initialized:
                    pygame.mouse.set_visible(False)
                    pygame.event.set_grab(True)
                    pygame.mouse.get_rel()
                    self.mouse_initialized = True
                    self.skip_mouse = True
                    if TAICHI_DEBUG_CAMERA_INPUT:
                        print("[Taichi cam debug] mouse grab ON")
            else:
                if self.mouse_initialized:
                    self.release_mouse()
                    if TAICHI_DEBUG_CAMERA_INPUT:
                        print("[Taichi cam debug] mouse grab OFF")
                return

            if ev.type == pygame.MOUSEMOTION:
                rel = getattr(ev, "rel", (0, 0))
                if getattr(self, "skip_mouse", False):
                    self.skip_mouse = False
                else:
                    self.mouse_dx += rel[0]
                    self.mouse_dy += rel[1]
                if TAICHI_DEBUG_CAMERA_INPUT and should_capture:
                    now = time.time()
                    if now - self._debug_cam_last_motion_log > 0.2:
                        self._debug_cam_last_motion_log = now
                        print(
                            "[Taichi cam debug] motion rel={} accum_dx_dy=({:.2f},{:.2f}) skip_next={}".format(
                                rel, self.mouse_dx, self.mouse_dy, self.skip_mouse
                            )
                        )
                raise renpy.IgnoreEvent()

            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_w or ev.key == pygame.K_UP:
                    self.input_y = -1.0
                elif ev.key == pygame.K_s or ev.key == pygame.K_DOWN:
                    self.input_y = 1.0
                if ev.key == pygame.K_a:
                    self.input_x = 1.0
                elif ev.key == pygame.K_d:
                    self.input_x = -1.0
                if ev.key == pygame.K_LEFT:
                    self.input_r = 1.0
                elif ev.key == pygame.K_RIGHT:
                    self.input_r = -1.0
                if ev.key == pygame.K_SPACE:
                    self.input_v = 1.0
                elif ev.key == pygame.K_LCTRL or ev.key == pygame.K_RCTRL:
                    self.input_v = -1.0
                if ev.key == pygame.K_PAGEUP:
                    self.input_pitch = 1.0
                elif ev.key == pygame.K_PAGEDOWN:
                    self.input_pitch = -1.0
                if self.gameplay and ev.key == pygame.K_e:
                    self.perform_pick()
                raise renpy.IgnoreEvent()

            if ev.type == pygame.KEYUP:
                if ev.key == pygame.K_w or ev.key == pygame.K_UP:
                    self.input_y = 0.0
                elif ev.key == pygame.K_s or ev.key == pygame.K_DOWN:
                    self.input_y = 0.0
                if ev.key == pygame.K_a:
                    self.input_x = 0.0
                elif ev.key == pygame.K_d:
                    self.input_x = 0.0
                if ev.key == pygame.K_LEFT:
                    self.input_r = 0.0
                elif ev.key == pygame.K_RIGHT:
                    self.input_r = 0.0
                if ev.key == pygame.K_SPACE:
                    self.input_v = 0.0
                elif ev.key == pygame.K_LCTRL or ev.key == pygame.K_RCTRL:
                    self.input_v = 0.0
                if ev.key == pygame.K_PAGEUP:
                    self.input_pitch = 0.0
                elif ev.key == pygame.K_PAGEDOWN:
                    self.input_pitch = 0.0
                raise renpy.IgnoreEvent()

        def update(self, dt):
            if self.mouse_initialized:
                self.player_yaw += -(self.mouse_dx * self.mouse_sens)
                self.player_pitch -= (self.mouse_dy * self.mouse_pitch_sens)

            self.mouse_dx = 0.0
            self.mouse_dy = 0.0

            self.player_yaw += self.input_r * self.rot_speed * dt
            move = self.input_y * self.move_speed * dt
            strafe = self.input_x * self.move_speed * dt
            self.player_x += math.cos(self.player_yaw) * move + math.sin(self.player_yaw) * strafe
            self.player_z += math.sin(self.player_yaw) * move - math.cos(self.player_yaw) * strafe

            self.player_y += self.input_v * self.vertical_speed * dt
            self.player_pitch += self.input_pitch * self.pitch_speed * dt
            max_pitch = 1.20
            if self.player_pitch > max_pitch:
                self.player_pitch = max_pitch
            elif self.player_pitch < -max_pitch:
                self.player_pitch = -max_pitch

            if self.pickup_msg_timer > 0.0:
                self.pickup_msg_timer = max(0.0, self.pickup_msg_timer - dt)


screen mesh_play():
    predict False
    modal True

    key "K_ESCAPE" action Return("exit")
    key "s" action None
    key "alt_s" action None
    key "K_f" action None
    key "K_LSHIFT" action None
    key "K_RSHIFT" action None
    key "K_LCTRL" action None
    key "K_RCTRL" action None
    key "mouseup_3" action None

    fixed:
        xfill True
        yfill True

        if SteinContainer.engine is not None:
            add SteinContainer.engine

        text "+" align (0.5, 0.5) size 24 color "#FFF"

        vbox:
            align (0.01, 0.01)
            spacing 2
            text "Play 3D (test)" size 24 color "#FF0"
            text "WASD+Mouse look, LMB/E to select, ESC to exit" size 14 color "#AAA"

            if SteinContainer.engine is not None:
                add DynamicDisplayable(lambda st, at: (Text("cam xyz: {:.2f}, {:.2f}, {:.2f}".format(SteinContainer.engine.loop.player_x, SteinContainer.engine.loop.player_y, SteinContainer.engine.loop.player_z), size=14, color="#9FE"), 0.1) if SteinContainer.engine else (Null(), 0.1))
                add DynamicDisplayable(lambda st, at: (Text("yaw/pitch: {:.3f}, {:.3f}".format(SteinContainer.engine.loop.player_yaw, SteinContainer.engine.loop.player_pitch), size=14, color="#9FE"), 0.1) if SteinContainer.engine else (Null(), 0.1))
                add DynamicDisplayable(lambda st, at: (Text("geo v/t: {} / {}".format(SteinContainer.engine.scene.num_vertices, SteinContainer.engine.scene.num_triangles), size=14, color="#9FE"), 0.1) if SteinContainer.engine else (Null(), 0.1))
                add DynamicDisplayable(lambda st, at: (Text("Selected: #{} ({})".format(SteinContainer.engine.loop.last_pick, SteinContainer.engine.loop.last_pick_path), size=14, color="#FF8") if SteinContainer.engine and SteinContainer.engine.loop.last_pick >= 0 else Text("Selected: (none)", size=14, color="#888"), 0.1) if SteinContainer.engine else (Null(), 0.1))

        if SteinContainer.engine is not None:
            add DynamicDisplayable(lambda st, at: (Text(str(SteinContainer.engine.loop.pickup_msg), size=24, color="#FFF", outlines=[(2, "#000", 0, 0)]) if SteinContainer.engine and SteinContainer.engine.loop.pickup_msg_timer > 0.0 else Null(), 0.1)) align (0.5, 0.85)


label start_mesh_play:
    python:
        store.stein_map_backend = "mesh"
        store.meshMap = load_mesh_map_json("new_mesh_map.json")
        if not store.meshMap or "instances" not in store.meshMap:
            store.meshMap = empty_mesh_map()

        SteinContainer.engine = TaichiEngineDisplayable(
            mesh_map=store.meshMap,
            gameplay=True,
        )

    window hide
    call screen mesh_play
    window show

    python:
        import pygame_sdl2 as pygame
        if getattr(SteinContainer, "engine", None):
            SteinContainer.engine.loop.release_mouse()
            SteinContainer.engine = None
        pygame.mouse.set_visible(True)
        pygame.event.set_grab(False)

    return
