#include "raylib.h"
#include "raymath.h"
#include <math.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

void SendEvent(int event_id, int event_value) {
  int msg_type = 1;
  fwrite(&msg_type, sizeof(int), 1, stdout);
  fwrite(&event_id, sizeof(int), 1, stdout);
  fwrite(&event_value, sizeof(int), 1, stdout);
  fflush(stdout);
}
#include <unistd.h>

#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#endif
#include <stdarg.h>

void CustomLog(int logLevel, const char *text, va_list args) {
  vfprintf(stderr, text, args);
  fprintf(stderr, "\n");
  fflush(stderr);
}

#define MAX_ENEMIES 128
#define MAX_SPRITES 128

typedef struct {
  float x, y, z;
  int state;
  int tex_idx;
  int type;
  float move_speed;
  float timer;
  float hp;
  float move_timer;
  int anim_frame;
} Enemy;

typedef struct {
  float x, y, z;
  int type;
  int state;
} StaticSprite;

typedef struct {
  float x, z;
} SpawnPoint;

Enemy enemies[MAX_ENEMIES];
StaticSprite static_sprites[MAX_SPRITES];
SpawnPoint spawn_points[64];
int num_enemies = 0;
int num_static_sprites = 0;
int num_spawn_points = 0;

unsigned char *ExportImageToBMPMemory(Image image, int *fileSize) {
  int dataSize = image.width * image.height * 4;
  *fileSize = 54 + dataSize;
  unsigned char *bmp = (unsigned char *)malloc(*fileSize);

  // BITMAPFILEHEADER
  bmp[0] = 'B';
  bmp[1] = 'M';
  *(int *)(bmp + 2) = *fileSize;
  *(short *)(bmp + 6) = 0;
  *(short *)(bmp + 8) = 0;
  *(int *)(bmp + 10) = 54;

  // BITMAPINFOHEADER
  *(int *)(bmp + 14) = 40;
  *(int *)(bmp + 18) = image.width;
  *(int *)(bmp + 22) = -image.height;
  *(short *)(bmp + 26) = 1;
  *(short *)(bmp + 28) = 32;
  *(int *)(bmp + 30) = 0;
  *(int *)(bmp + 34) = dataSize;
  *(int *)(bmp + 38) = 0;
  *(int *)(bmp + 42) = 0;
  *(int *)(bmp + 46) = 0;
  *(int *)(bmp + 50) = 0;

  memcpy(bmp + 54, image.data, dataSize);

  return bmp;
}

Texture2D LoadFlippedTexture(const char *path) {
  Image img = LoadImage(path);
  ImageFlipVertical(&img);
  Texture2D tex = LoadTextureFromImage(img);
  UnloadImage(img);
  return tex;
}

typedef struct {
  int w, s, a, d;
  int left, right, up, down;
  int space, shift, ctrl, shoot;
  float mouse_dx, mouse_dy;
  float time_of_day;
  int lighting_quality;
  int shadows_enabled;
} InputPacket;

typedef struct {
  float x;
  float y;
  float z;
  float pitch;
  float yaw;
  float time_of_day;
  int lighting_quality;
  int shadows_enabled;
  float vel_y;
  int is_grounded;
} CameraData;

static CameraData current_cam = {2.0f,  1.0f, 2.0f, 0.0f, 0.0f,
                                 12.0f, 0,    0,    0.0f, 0};

static pthread_mutex_t input_mutex = PTHREAD_MUTEX_INITIALIZER;
static InputPacket current_input = {0};

void *input_listener(void *arg) {
  InputPacket packet;
  while (1) {
    size_t bytes_read = fread(&packet, 1, sizeof(InputPacket), stdin);
    if (bytes_read == sizeof(InputPacket)) {
      pthread_mutex_lock(&input_mutex);
      current_input.w = packet.w;
      current_input.s = packet.s;
      current_input.a = packet.a;
      current_input.d = packet.d;
      current_input.left = packet.left;
      current_input.right = packet.right;
      current_input.up = packet.up;
      current_input.down = packet.down;
      current_input.space = packet.space;
      current_input.shift = packet.shift;
      current_input.ctrl = packet.ctrl;
      current_input.shoot = packet.shoot;
      current_input.mouse_dx += packet.mouse_dx;
      current_input.mouse_dy += packet.mouse_dy;

      current_cam.time_of_day = packet.time_of_day;
      current_cam.lighting_quality = packet.lighting_quality;
      current_cam.shadows_enabled = packet.shadows_enabled;
      pthread_mutex_unlock(&input_mutex);
    } else {
      exit(0);
    }
  }
  return NULL;
}

int map_width = 0;
int map_height = 0;
int map_layers = 0;
int *dynamic_map = NULL;

int main(int argc, char *argv[]) {
#ifdef _WIN32
  _setmode(_fileno(stdout), _O_BINARY);
  _setmode(_fileno(stdin), _O_BINARY);
#endif

  int render_width = 800;
  int render_height = 600;

  int init_header[6];
  size_t header_read = fread(init_header, sizeof(int), 6, stdin);

  int is_arena_mode = 0;
  if (header_read == 6) {
    render_width = init_header[0];
    render_height = init_header[1];
    map_width = init_header[2];
    map_height = init_header[3];
    map_layers = init_header[4];
    is_arena_mode = init_header[5];

    if (map_width > 0 && map_height > 0 && map_layers > 0) {
      int total_tiles = map_width * map_height * map_layers;
      dynamic_map = (int *)malloc(total_tiles * sizeof(int));
      if (dynamic_map != NULL) {
        size_t items_read = 0;
        while (items_read < (size_t)total_tiles) {
          size_t r = fread(dynamic_map + items_read, sizeof(int),
                           total_tiles - items_read, stdin);
          if (r <= 0)
            break;
          items_read += r;
        }
      }
    }

    float start_cam[5];
    fread(start_cam, sizeof(float), 5, stdin);
    current_cam.x = start_cam[0];
    current_cam.y = start_cam[1];
    current_cam.z = start_cam[2];
    current_cam.pitch = start_cam[3];
    current_cam.yaw = start_cam[4];

    fread(&num_enemies, sizeof(int), 1, stdin);
    if (num_enemies > MAX_ENEMIES)
      num_enemies = MAX_ENEMIES;
    fread(&num_static_sprites, sizeof(int), 1, stdin);
    if (num_static_sprites > MAX_SPRITES)
      num_static_sprites = MAX_SPRITES;
    fread(&num_spawn_points, sizeof(int), 1, stdin);

    for (int i = 0; i < num_enemies; i++) {
      fread(&enemies[i].x, sizeof(float), 1, stdin);
      fread(&enemies[i].z, sizeof(float), 1, stdin);
      fread(&enemies[i].type, sizeof(int), 1, stdin);
      fread(&enemies[i].state, sizeof(int), 1, stdin);
      enemies[i].state = 1;
      enemies[i].hp = 100.0f;
      enemies[i].y = 2.0f;
      enemies[i].move_timer = 0.0f;
    }

    for (int i = 0; i < num_static_sprites; i++) {
      fread(&static_sprites[i].x, sizeof(float), 1, stdin);
      fread(&static_sprites[i].z, sizeof(float), 1, stdin);
      fread(&static_sprites[i].type, sizeof(int), 1, stdin);
      static_sprites[i].state = 0;
      static_sprites[i].y = 0.0f;
    }

    if (num_spawn_points > 64)
      num_spawn_points = 64;
    for (int i = 0; i < num_spawn_points; i++) {
      fread(&spawn_points[i].x, sizeof(float), 1, stdin);
      fread(&spawn_points[i].z, sizeof(float), 1, stdin);
    }
  }

  SetTraceLogCallback(CustomLog);
  SetTraceLogLevel(LOG_ALL);

  SetConfigFlags(FLAG_WINDOW_HIDDEN);
  InitWindow(render_width, render_height, "Raylib Server");
  SetTargetFPS(60);

  Texture2D wall_textures[9];
  wall_textures[0] = LoadFlippedTexture("game/pics/walls/eagle.png");
  wall_textures[1] = LoadFlippedTexture("game/pics/walls/redbrick.png");
  wall_textures[2] = LoadFlippedTexture("game/pics/walls/purplestone.png");
  wall_textures[3] = LoadFlippedTexture("game/pics/walls/greystone.png");
  wall_textures[4] = LoadFlippedTexture("game/pics/walls/bluestone.png");
  wall_textures[5] = LoadFlippedTexture("game/pics/walls/mossy.png");
  wall_textures[6] = LoadFlippedTexture("game/pics/walls/wood.png");
  wall_textures[7] = LoadFlippedTexture("game/pics/walls/colorstone.png");
  wall_textures[8] = LoadFlippedTexture("game/pics/walls/cement.png");

  Texture2D floor_tex = LoadFlippedTexture("game/pics/walls/colorstone.png");

  Texture2D sprite_tex[16];
  sprite_tex[0] = LoadTexture("game/pics/items/barrel.png");
  sprite_tex[1] = LoadTexture("game/pics/items/pillar.png");
  sprite_tex[2] = LoadTexture("game/pics/items/greenlight.png");
  sprite_tex[3] = LoadTexture("game/pics/items/pillar_destroyed.png");
  sprite_tex[4] = LoadTexture("game/pics/enemies/guard.png");
  sprite_tex[5] = LoadTexture("game/pics/enemies/guard_d.png");
  sprite_tex[6] = LoadTexture("game/pics/items/bullet.png");
  sprite_tex[7] = LoadTexture("game/pics/items/medkit.png");
  sprite_tex[8] = LoadTexture("game/pics/items/cookie.png");
  sprite_tex[9] = LoadTexture("game/pics/enemies/yuritler.png");
  sprite_tex[10] = LoadTexture("game/pics/enemies/yuritler_d.png");
  sprite_tex[11] = LoadTexture("game/pics/items/coins.png");
  sprite_tex[12] = LoadTexture("game/pics/items/coins.png");
  sprite_tex[13] = LoadTexture("game/pics/items/random_gun_i.png");
  sprite_tex[14] = LoadTexture("game/pics/items/bullet_red.png");
  sprite_tex[15] = LoadTexture("game/pics/items/minigun.png");

  Model guyModel = LoadModel("game/models/monika_walk.glb");

  int guyAnimsCount = 0;
  ModelAnimation *guyAnims =
      LoadModelAnimations("game/models/monika_walk.glb", &guyAnimsCount);

  Mesh cubeMesh = GenMeshCube(2.0f, 2.0f, 2.0f);
  Model cubeModel = LoadModelFromMesh(cubeMesh);

  Mesh floorMesh = GenMeshCube(2.0f, 1.0f, 2.0f);
  Model floorModel = LoadModelFromMesh(floorMesh);

  RenderTexture2D target = LoadRenderTexture(render_width, render_height);
  RenderTexture2D final_target = LoadRenderTexture(render_width, render_height);

  Shader lighting_shader = LoadShader(0, "game/core/lighting.fs");
  int tod_loc = GetShaderLocation(lighting_shader, "time_of_day");
  int lq_loc = GetShaderLocation(lighting_shader, "lighting_quality");
  int sh_loc = GetShaderLocation(lighting_shader, "shadows_enabled");

  Camera3D camera = {0};
  camera.up = (Vector3){0.0f, 1.0f, 0.0f};
  camera.fovy = 60.0f;
  camera.projection = CAMERA_PERSPECTIVE;

  pthread_t thread_id;
  pthread_create(&thread_id, NULL, input_listener, NULL);

  int GetBlock(int mapX, int mapY, int mapZ) {
    if (mapX < 0 || mapX >= map_width || mapZ < 0 || mapZ >= map_height)
      return 1;
    if (mapY < 0 || mapY >= map_layers)
      return 0;
    return dynamic_map[(mapY * map_height * map_width) + (mapZ * map_width) +
                       mapX];
  }

  float arena_timer = 0.0f;
  int current_round = 0;
  float round_timer = 3.0f;
  int active_enemies = 0;

  while (!WindowShouldClose()) {
    pthread_mutex_lock(&input_mutex);
    float mdx = current_input.mouse_dx;
    float mdy = current_input.mouse_dy;
    int k_w = current_input.w | current_input.up;
    int k_s = current_input.s | current_input.down;
    int k_a = current_input.a | current_input.left;
    int k_d = current_input.d | current_input.right;
    int k_space = current_input.space;
    int k_shift = current_input.shift;
    int k_ctrl = current_input.ctrl;
    int k_shoot = current_input.shoot;

    current_input.mouse_dx = 0.0f;
    current_input.mouse_dy = 0.0f;
    pthread_mutex_unlock(&input_mutex);

    float dt = GetFrameTime();
    if (dt > 0.1f)
      dt = 0.1f;

    static float shoot_cooldown = 0.0f;
    if (shoot_cooldown > 0.0f)
      shoot_cooldown -= dt;

    float phys_yawRad = current_cam.yaw * DEG2RAD;
    float phys_pitchRad = current_cam.pitch * DEG2RAD;

    Vector3 forward;
    forward.x = cosf(phys_pitchRad) * cosf(phys_yawRad);
    forward.y = sinf(phys_pitchRad);
    forward.z = cosf(phys_pitchRad) * sinf(phys_yawRad);

    // combat logic
    if (k_shoot && shoot_cooldown <= 0.0f) {
      shoot_cooldown = 0.3f;

      int hit_idx = -1;
      float closest_dist = 20.0f;

      for (int i = 0; i < num_enemies; i++) {
        if (enemies[i].state >= 3)
          continue;

        float ex = enemies[i].x;
        float ey = enemies[i].y;
        float ez = enemies[i].z;

        float vx = ex - current_cam.x;
        float vy = ey - current_cam.y;
        float vz = ez - current_cam.z;

        float t_closest = vx * forward.x + vy * forward.y + vz * forward.z;

        if (t_closest > 0.0f && t_closest < closest_dist) {
          float proj_x = current_cam.x + forward.x * t_closest;
          float proj_z = current_cam.z + forward.z * t_closest;

          float dist_sq =
              (ex - proj_x) * (ex - proj_x) + (ez - proj_z) * (ez - proj_z);
          if (dist_sq < (0.35f * 0.35f)) {
            float hit_y = current_cam.y + forward.y * t_closest;
            if (hit_y >= ey && hit_y <= (ey + 1.5f)) {
              closest_dist = t_closest;
              hit_idx = i;
            }
          }
        }
      }

      if (hit_idx != -1) {
        enemies[hit_idx].hp -= 25.0f;
        if (enemies[hit_idx].hp <= 0.0f) {
          enemies[hit_idx].state = 3; // Dead
        }
      }
    }

    // AI logic
    for (int i = 0; i < num_enemies; i++) {
      if (enemies[i].state >= 4)
        continue;

      float dx = current_cam.x - enemies[i].x;
      float dz = current_cam.z - enemies[i].z;
      float dist = sqrtf(dx * dx + dz * dz);

      if (enemies[i].state == 0) { // idle
        if (dist < 15.0f)
          enemies[i].state = 1;
      } else if (enemies[i].state == 1) { // chase
        if (dist <= 1.5f) {               // attack range
          enemies[i].state = 2;
          enemies[i].timer = 1.0f;
          SendEvent(12, enemies[i].type); // enemy attack
        } else {
          float dir_x = dx / dist;
          float dir_z = dz / dist;
          float ms = 3.0f; // move speed
          float next_x = enemies[i].x + dir_x * ms * dt;
          float next_z = enemies[i].z + dir_z * ms * dt;

          int ex_round = (int)roundf(enemies[i].x / 2.0f);
          int ez_round = (int)roundf(enemies[i].z / 2.0f);
          float e_max_z = -1000.0f;
          for (int l = 0; l < map_layers; l++) {
            if (GetBlock(ex_round, l, ez_round) > 0) {
              float top_z = (l * 2.0f) + 2.0f;
              if (top_z > e_max_z && top_z <= enemies[i].y + 1.5f) {
                e_max_z = top_z;
              }
            }
          }
          if (e_max_z == -1000.0f)
            e_max_z = 1.0f;
          enemies[i].y = e_max_z;

          int el = (int)floorf(enemies[i].y / 2.0f);

          int ex_block = GetBlock((int)roundf(next_x / 2.0f), el,
                                  (int)roundf(enemies[i].z / 2.0f));
          if (ex_block <= 0)
            enemies[i].x = next_x;

          int ez_block = GetBlock((int)roundf(enemies[i].x / 2.0f), el,
                                  (int)roundf(next_z / 2.0f));
          if (ez_block <= 0)
            enemies[i].z = next_z;
        }
      } else if (enemies[i].state == 2) { // attack
        enemies[i].timer -= dt;
        if (enemies[i].timer <= 0.0f)
          enemies[i].state = 1;
      }
    }

    active_enemies = 0;
    for (int i = 0; i < num_enemies; i++) {
      if (enemies[i].state < 3)
        active_enemies++;
    }

    if (is_arena_mode && num_spawn_points > 0) {
      if (active_enemies == 0) {
        round_timer -= dt;
        if (round_timer <= 0.0f) {
          current_round++;
          round_timer = 5.0f;

          int enemies_to_spawn = 2 + (current_round * 2);
          for (int s = 0; s < enemies_to_spawn; s++) {
            if (num_enemies >= MAX_ENEMIES)
              break;
            int sp_idx = rand() % num_spawn_points;
            enemies[num_enemies].x = spawn_points[sp_idx].x;
            enemies[num_enemies].z = spawn_points[sp_idx].z;
            enemies[num_enemies].type = 4;
            enemies[num_enemies].hp = 100.0f;
            if (rand() % 100 < 15 + (current_round * 2)) {
              enemies[num_enemies].type = 9;
              enemies[num_enemies].hp = 150.0f + (current_round * 10);
            }
            enemies[num_enemies].state = 1;
            enemies[num_enemies].y = 2.0f;
            enemies[num_enemies].move_timer = 0.0f;
            num_enemies++;
          }
          active_enemies = enemies_to_spawn;
        }
      }
    }

    int px = (int)roundf(current_cam.x / 2.0f);
    int pz = (int)roundf(current_cam.z / 2.0f);

    float max_z = -1000.0f;
    for (int l = 0; l < map_layers; l++) {
      if (GetBlock(px, l, pz) > 0) {
        float top_z = (l * 2.0f) + 2.0f;
        if (top_z > max_z && top_z <= current_cam.y + 1.5f) {
          max_z = top_z;
        }
      }
    }
    if (max_z == -1000.0f) {
      max_z = 1.0f;
    }

    if (current_cam.is_grounded == 0) {
      current_cam.vel_y -= 35.0f * dt;
      current_cam.y += current_cam.vel_y * dt;

      if (current_cam.y <= max_z) {
        current_cam.y = max_z;
        current_cam.vel_y = 0.0f;
        current_cam.is_grounded = 1;
      }
    } else {
      if (current_cam.y > max_z + 0.1f) {
        current_cam.is_grounded = 0;
      } else {
        current_cam.y = max_z;
        if (k_space) {
          current_cam.vel_y = 15.0f;
          current_cam.is_grounded = 0;
        }
      }
    }

    float speed = 4.0f * dt;
    if (k_shift)
      speed *= 1.5f;

    float target_height = current_cam.y + 1.0f;
    if (k_ctrl && current_cam.is_grounded) {
      target_height -= 0.5f;
      speed *= 0.5f;
    }

    camera.position = (Vector3){current_cam.x, target_height, current_cam.z};

    current_cam.yaw += mdx;
    current_cam.pitch += mdy;

    if (current_cam.pitch > 89.0f)
      current_cam.pitch = 89.0f;
    if (current_cam.pitch < -89.0f)
      current_cam.pitch = -89.0f;

    phys_yawRad = current_cam.yaw * DEG2RAD;
    float fx = cosf(phys_yawRad);
    float fz = sinf(phys_yawRad);
    float rx = cosf(phys_yawRad + PI / 2.0f);
    float rz = sinf(phys_yawRad + PI / 2.0f);

    float dx = 0.0f;
    float dz = 0.0f;

    if (k_w) {
      dx += fx * speed;
      dz += fz * speed;
    }
    if (k_s) {
      dx -= fx * speed;
      dz -= fz * speed;
    }
    if (k_a) {
      dx -= rx * speed;
      dz -= rz * speed;
    }
    if (k_d) {
      dx += rx * speed;
      dz += rz * speed;
    }

    float hitbox = 0.2f;

    // x collision
    if (dx != 0.0f) {
      float targetX = current_cam.x + dx;
      int checkX = (int)roundf((targetX + (dx > 0 ? hitbox : -hitbox)) / 2.0f);
      int pZ = (int)roundf(current_cam.z / 2.0f);
      int pZ1 = (int)roundf((current_cam.z - hitbox) / 2.0f);
      int pZ2 = (int)roundf((current_cam.z + hitbox) / 2.0f);
      int layer = (int)floorf(current_cam.y / 2.0f);

      if (GetBlock(checkX, layer, pZ) == 0 &&
          GetBlock(checkX, layer, pZ1) == 0 &&
          GetBlock(checkX, layer, pZ2) == 0) {
        current_cam.x = targetX;
      }
    }

    // z collision
    if (dz != 0.0f) {
      float targetZ = current_cam.z + dz;
      int checkZ = (int)roundf((targetZ + (dz > 0 ? hitbox : -hitbox)) / 2.0f);
      int pX = (int)roundf(current_cam.x / 2.0f);
      int pX1 = (int)roundf((current_cam.x - hitbox) / 2.0f);
      int pX2 = (int)roundf((current_cam.x + hitbox) / 2.0f);
      int layer = (int)floorf(current_cam.y / 2.0f);

      if (GetBlock(pX, layer, checkZ) == 0 &&
          GetBlock(pX1, layer, checkZ) == 0 &&
          GetBlock(pX2, layer, checkZ) == 0) {
        current_cam.z = targetZ;
      }
    }

    camera.position.x = current_cam.x;
    camera.position.z = current_cam.z;

    forward.x = cosf(phys_pitchRad) * cosf(phys_yawRad);
    forward.y = sinf(phys_pitchRad);
    forward.z = cosf(phys_pitchRad) * sinf(phys_yawRad);

    camera.target =
        (Vector3){camera.position.x + forward.x, camera.position.y + forward.y,
                  camera.position.z + forward.z};

    SetShaderValue(lighting_shader, tod_loc, &current_cam.time_of_day,
                   SHADER_UNIFORM_FLOAT);
    SetShaderValue(lighting_shader, lq_loc, &current_cam.lighting_quality,
                   SHADER_UNIFORM_INT);
    SetShaderValue(lighting_shader, sh_loc, &current_cam.shadows_enabled,
                   SHADER_UNIFORM_INT);

    BeginTextureMode(target);
    ClearBackground(DARKGRAY);
    BeginMode3D(camera);

    if (dynamic_map != NULL) {
      for (int l = 0; l < map_layers; l++) {
        for (int z = 0; z < map_height; z++) {
          for (int x = 0; x < map_width; x++) {
            int tile =
                dynamic_map[(l * map_height * map_width) + (z * map_width) + x];
            if (tile > 0) {
              int tex_idx = tile - 1;
              if (tex_idx < 0)
                tex_idx = 0;
              if (tex_idx > 8)
                tex_idx = 8;

              cubeModel.materials[0].maps[MATERIAL_MAP_DIFFUSE].texture =
                  wall_textures[tex_idx];
              DrawModel(cubeModel,
                        (Vector3){x * 2.0f, l * 2.0f + 1.0f, z * 2.0f}, 1.0f,
                        WHITE);
            }
          }
        }
      }

      floorModel.materials[0].maps[MATERIAL_MAP_DIFFUSE].texture = floor_tex;
      for (int z = 0; z < map_height; z++) {
        for (int x = 0; x < map_width; x++) {
          DrawModel(floorModel, (Vector3){x * 2.0f, -0.5f, z * 2.0f}, 1.0f,
                    WHITE);
        }
      }
    }

    // sprites
    for (int i = 0; i < num_static_sprites; i++) {
      if (static_sprites[i].state >= 0) {
        int type = static_sprites[i].type;
        if (type >= 0 && type < 16) {
          Vector3 pos = {static_sprites[i].x, static_sprites[i].y + 1.0f,
                         static_sprites[i].z};
          DrawBillboard(camera, sprite_tex[type], pos, 2.0f, WHITE);
        }

        if (type == 0 || type == 6 || type == 7 || type == 8 || type == 11 ||
            type == 12 || type >= 13) {
          float dist_sq = (current_cam.x - static_sprites[i].x) *
                              (current_cam.x - static_sprites[i].x) +
                          (current_cam.z - static_sprites[i].z) *
                              (current_cam.z - static_sprites[i].z);
          if (dist_sq < 0.36f) { // 0.6f * 0.6f
            static_sprites[i].state = -1;
            SendEvent(1, static_sprites[i].type); // pickup
          }
        }
      }
    }

    for (int i = 0; i < num_enemies; i++) {
      if (enemies[i].state >= 0) { // render if not completely inactive
        if (enemies[i].type != 5 && enemies[i].type != 1) {

          if (enemies[i].state < 3) {
            enemies[i].move_timer += GetFrameTime();
            if (enemies[i].move_timer > 1.0f / 30.0f) {
              enemies[i].anim_frame++;
              enemies[i].move_timer = 0.0f;
            }
            if (guyAnimsCount > 0) {
              int max_frames = guyAnims[0].frameCount;
              if (enemies[i].anim_frame >= max_frames)
                enemies[i].anim_frame = 0;
              UpdateModelAnimation(guyModel, guyAnims[0],
                                   enemies[i].anim_frame);
            }
          }

          float dx = camera.position.x - enemies[i].x;
          float dz = camera.position.z - enemies[i].z;
          float angle = atan2f(dx, dz) * RAD2DEG;

          Vector3 pos = {enemies[i].x, enemies[i].y, enemies[i].z};

          DrawModelEx(guyModel, pos, (Vector3){0, 1, 0}, angle,
                      (Vector3){0.5f, 0.5f, 0.5f},
                      (enemies[i].state >= 3) ? GRAY : WHITE);

        } else {
          Texture2D tex = sprite_tex[9];
          Texture2D dead_tex = sprite_tex[10];

          if (enemies[i].state >= 3) {
            tex = dead_tex;
          }

          Vector3 pos = {enemies[i].x, enemies[i].y + 1.0f, enemies[i].z};
          DrawBillboard(camera, tex, pos, 2.0f, WHITE);
        }
      }
    }

    EndMode3D();

    if (is_arena_mode) {
      char ui_text[128];
      if (active_enemies == 0 && round_timer > 0.0f) {
        sprintf(ui_text, "ROUND %d STARTING IN: %.1f", current_round + 1,
                round_timer);
        DrawText(ui_text, render_width / 2 - MeasureText(ui_text, 20) / 2, 50,
                 20, YELLOW);
      } else {
        sprintf(ui_text, "ROUND: %d | ENEMIES: %d", current_round,
                active_enemies);
        DrawText(ui_text, render_width - MeasureText(ui_text, 20) - 20, 20, 20,
                 RED);
      }
    }

    EndTextureMode();

    BeginTextureMode(final_target);
    ClearBackground(BLACK);
    BeginShaderMode(lighting_shader);
    DrawTextureRec(target.texture,
                   (Rectangle){0, 0, (float)target.texture.width,
                               -(float)target.texture.height},
                   (Vector2){0, 0}, WHITE);
    EndShaderMode();

    DrawText(
        TextFormat("POS: X:%.1f Y:%.1f Z:%.1f | W:%d S:%d A:%d D:%d | dX:%.1f",
                   current_cam.x, current_cam.y, current_cam.z, k_w, k_s, k_a,
                   k_d, mdx),
        10, 10, 20, YELLOW);

    DrawText(TextFormat("FPS: %i", GetFPS()), render_width - 100,
             render_height - 30, 20, GREEN);
    EndTextureMode();

    Image img = LoadImageFromTexture(final_target.texture);
    ImageFlipVertical(&img);
    ImageFormat(&img, PIXELFORMAT_UNCOMPRESSED_R8G8B8A8);

    int fileSize = 0;
    unsigned char *bmpData = ExportImageToBMPMemory(img, &fileSize);
    UnloadImage(img);

    if (bmpData) {
      int msg_type = 0;
      fwrite(&msg_type, sizeof(int), 1, stdout);
      fwrite(&fileSize, sizeof(int), 1, stdout);
      fwrite(bmpData, 1, fileSize, stdout);
      fflush(stdout);
      free(bmpData);
    }

    BeginDrawing();
    ClearBackground(BLACK);
    DrawTextureRec(final_target.texture,
                   (Rectangle){0, 0, (float)final_target.texture.width,
                               -(float)final_target.texture.height},
                   (Vector2){0, 0}, WHITE);
    EndDrawing();
  }

  for (int i = 0; i < 9; i++) {
    UnloadTexture(wall_textures[i]);
  }
  UnloadTexture(floor_tex);
  for (int i = 0; i < 16; i++) {
    UnloadTexture(sprite_tex[i]);
  }
  UnloadModel(cubeModel);
  UnloadModel(floorModel);
  UnloadShader(lighting_shader);
  UnloadRenderTexture(target);
  UnloadRenderTexture(final_target);
  CloseWindow();
  if (dynamic_map)
    free(dynamic_map);
  return 0;
}
