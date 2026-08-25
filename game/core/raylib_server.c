#include "raylib.h"
#include "raymath.h"
#include "rlgl.h"
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
#define MAX_SPRITES 256
#define MAX_PROJECTILES 128

typedef struct {
  float x, y, z;
  int state;
  int tex_idx;
  int type;
  float move_speed;
  float timer;
  float hp;
  float max_hp;
  float move_timer;
  int anim_frame;
  int burst_count;
  float reload_timer;
  float dodge_timer;
  float attack_range;
  float damage;
} Enemy;

typedef struct {
  float x, y, z;
  int type;
  int state;
} StaticSprite;

typedef struct {
  float x, z;
} SpawnPoint;

typedef struct {
  Vector3 pos;
  Vector3 dir;
  float speed;
  float damage;
  int active;
  int tex_idx; // 6 = yellow bullet, 14 = red bullet
  int from_player; // 1 = player, 0 = enemy
} Projectile;

Enemy enemies[MAX_ENEMIES];
StaticSprite static_sprites[MAX_SPRITES];
SpawnPoint spawn_points[64];
Projectile projectiles[MAX_PROJECTILES];

int num_enemies = 0;
int num_static_sprites = 0;
int num_spawn_points = 0;

int map_width = 0;
int map_height = 0;
int map_layers = 0;
int *dynamic_map = NULL;
int is_arena_mode = 0;

int GetBlock(int mapX, int mapY, int mapZ) {
  if (mapX < 0 || mapX >= map_width || mapZ < 0 || mapZ >= map_height)
    return 1;
  if (mapY < 0 || mapY >= map_layers)
    return 0;
  return dynamic_map[(mapY * map_height * map_width) + (mapZ * map_width) + mapX];
}

int HasLineOfSight(Vector3 from, Vector3 to) {
  Vector3 delta = Vector3Subtract(to, from);
  float dist = Vector3Length(delta);
  if (dist < 0.2f) return 1;
  Vector3 dir = Vector3Scale(delta, 1.0f / dist);
  float step = 0.5f;
  float t = 0.5f;
  while (t < dist - 0.5f) {
    Vector3 p = Vector3Add(from, Vector3Scale(dir, t));
    int bx = (int)roundf(p.x / 2.0f);
    int bz = (int)roundf(p.z / 2.0f);
    int layer = (int)floorf(p.y / 2.0f);
    if (GetBlock(bx, layer, bz) > 0) return 0;
    t += step;
  }
  return 1;
}

void SpawnProjectile(Vector3 pos, Vector3 dir, float speed, float damage, int tex_idx, int from_player) {
  for (int i = 0; i < MAX_PROJECTILES; i++) {
    if (!projectiles[i].active) {
      projectiles[i].pos = pos;
      projectiles[i].dir = Vector3Normalize(dir);
      projectiles[i].speed = speed;
      projectiles[i].damage = damage;
      projectiles[i].tex_idx = tex_idx;
      projectiles[i].from_player = from_player;
      projectiles[i].active = 1;
      return;
    }
  }
}

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
  int active_weapon;
  int bloom_enabled;
  int volumetric_clouds;
  float rain_intensity;
  int soft_shadows;
  int is_aiming;
  int pistol_lvl;
  int shotgun_lvl;
  int minigun_lvl;
  int flashlight_active;
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

typedef struct {
    float cooldown;
    float damage;
    int pellets;
    float spread;
    float recoil_z;
    float recoil_pitch;
} WeaponDef;

WeaponDef weapons[4] = {
    { 0.5f,  25.0f, 1, 0.00f, 0.01f, 5.0f },   // 0: fist
    { 0.38f, 50.0f, 1, 0.00f, 0.05f, 15.0f },  // 1: pistol
    { 1.4f,  35.0f, 5, 0.15f, 0.12f, 30.0f },  // 2: shotgun
    { 0.05f, 40.0f, 1, 0.05f, 0.02f, 5.0f }    // 3: minigun
};

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

      if (!is_arena_mode) {
        current_cam.time_of_day = packet.time_of_day;
      }
      current_cam.lighting_quality = packet.lighting_quality;
      current_cam.shadows_enabled = packet.shadows_enabled;
      current_input.active_weapon = packet.active_weapon;
      current_input.bloom_enabled = packet.bloom_enabled;
      current_input.volumetric_clouds = packet.volumetric_clouds;
      current_input.rain_intensity = packet.rain_intensity;
      current_input.soft_shadows = packet.soft_shadows;
      current_input.is_aiming = packet.is_aiming;
      current_input.pistol_lvl = packet.pistol_lvl;
      current_input.shotgun_lvl = packet.shotgun_lvl;
      current_input.minigun_lvl = packet.minigun_lvl;
      current_input.flashlight_active = packet.flashlight_active;
      pthread_mutex_unlock(&input_mutex);
    } else {
      exit(0);
    }
  }
  return NULL;
}

static int current_round = 0;
static float inter_round_timer = 0.0f;
static int yuritler_count = 0;
static int sniper_count = 0;
static float total_arena_time = 0.0f;
static float weather_timer = 5.0f;
static int weather_active = 0;

void StartNextArenaRound() {
  current_round++;
  inter_round_timer = 0.0f;

  // clean up bodys from previous rounds
  int write_idx = 0;
  for (int i = 0; i < num_enemies; i++) {
    if (enemies[i].state < 3) {
      enemies[write_idx++] = enemies[i];
    }
  }
  num_enemies = write_idx;

  // standard enemies (current_round guards)
  for (int s = 0; s < current_round; s++) {
    if (num_enemies >= MAX_ENEMIES || num_spawn_points == 0) break;
    int sp = rand() % num_spawn_points;
    float jx = ((float)(rand() % 100) / 100.0f - 0.5f) * 0.6f;
    float jz = ((float)(rand() % 100) / 100.0f - 0.5f) * 0.6f;
    enemies[num_enemies].x = spawn_points[sp].x + jx;
    enemies[num_enemies].z = spawn_points[sp].z + jz;
    enemies[num_enemies].type = 4;
    enemies[num_enemies].hp = 100.0f;
    enemies[num_enemies].max_hp = 100.0f;
    enemies[num_enemies].move_speed = 1.5f + ((float)(rand() % 100) / 100.0f - 0.5f) * 0.2f;
    enemies[num_enemies].damage = 10.0f;
    enemies[num_enemies].attack_range = 15.0f;
    enemies[num_enemies].timer = 1.0f;
    enemies[num_enemies].state = 1;
    enemies[num_enemies].y = 2.0f;
    enemies[num_enemies].move_timer = 0.0f;
    enemies[num_enemies].anim_frame = 0;
    enemies[num_enemies].burst_count = 0;
    enemies[num_enemies].reload_timer = 0.0f;
    enemies[num_enemies].dodge_timer = 0.0f;
    num_enemies++;
  }

  // yuritler Boss, every 10 rounds or 15% on even rounds
  int spawn_yuritler = 0;
  if (current_round % 10 == 0) {
    spawn_yuritler = 1;
  } else if (current_round % 2 == 0) {
    if (rand() % 100 < 15) spawn_yuritler = 1;
  }
  if (spawn_yuritler && num_enemies < MAX_ENEMIES && num_spawn_points > 0) {
    yuritler_count++;
    int sp = rand() % num_spawn_points;
    float jx = ((float)(rand() % 100) / 100.0f - 0.5f) * 0.6f;
    float jz = ((float)(rand() % 100) / 100.0f - 0.5f) * 0.6f;
    enemies[num_enemies].x = spawn_points[sp].x + jx;
    enemies[num_enemies].z = spawn_points[sp].z + jz;
    enemies[num_enemies].type = 9;
    enemies[num_enemies].hp = 150.0f + (yuritler_count - 1) * 50.0f;
    enemies[num_enemies].max_hp = enemies[num_enemies].hp;
    enemies[num_enemies].move_speed = 1.8f;
    enemies[num_enemies].damage = 5.0f;
    enemies[num_enemies].attack_range = 20.0f;
    enemies[num_enemies].timer = 1.0f;
    enemies[num_enemies].state = 1;
    enemies[num_enemies].y = 2.0f;
    enemies[num_enemies].move_timer = 0.0f;
    enemies[num_enemies].anim_frame = 0;
    enemies[num_enemies].burst_count = 0;
    enemies[num_enemies].reload_timer = 0.0f;
    enemies[num_enemies].dodge_timer = 0.0f;
    num_enemies++;
  }

  // elite enemies, every 5 rounds
  if (current_round % 5 == 0) {
    int num_elites = current_round / 5;
    for (int e = 0; e < num_elites; e++) {
      if (num_enemies >= MAX_ENEMIES || num_spawn_points == 0) break;
      int sp = rand() % num_spawn_points;
      float jx = ((float)(rand() % 100) / 100.0f - 0.5f) * 0.6f;
      float jz = ((float)(rand() % 100) / 100.0f - 0.5f) * 0.6f;
      enemies[num_enemies].x = spawn_points[sp].x + jx;
      enemies[num_enemies].z = spawn_points[sp].z + jz;
      enemies[num_enemies].type = 2;
      enemies[num_enemies].hp = 100.0f;
      enemies[num_enemies].max_hp = 100.0f;
      enemies[num_enemies].move_speed = 1.5f + ((float)(rand() % 100) / 100.0f - 0.5f) * 0.2f;
      enemies[num_enemies].damage = 4.0f;
      enemies[num_enemies].attack_range = 16.0f;
      enemies[num_enemies].timer = 1.0f;
      enemies[num_enemies].state = 1;
      enemies[num_enemies].y = 2.0f;
      enemies[num_enemies].move_timer = 0.0f;
      enemies[num_enemies].anim_frame = 0;
      enemies[num_enemies].burst_count = 0;
      enemies[num_enemies].reload_timer = 0.0f;
      enemies[num_enemies].dodge_timer = 0.0f;
      num_enemies++;
    }
  }

  // snipers, ddd rounds: 50% chance
  if (current_round % 2 != 0) {
    if (rand() % 100 < 50) {
      sniper_count++;
      for (int sn = 0; sn < sniper_count; sn++) {
        if (num_enemies >= MAX_ENEMIES || num_spawn_points == 0) break;
        int sp = rand() % num_spawn_points;
        float jx = ((float)(rand() % 100) / 100.0f - 0.5f) * 0.6f;
        float jz = ((float)(rand() % 100) / 100.0f - 0.5f) * 0.6f;
        enemies[num_enemies].x = spawn_points[sp].x + jx;
        enemies[num_enemies].z = spawn_points[sp].z + jz;
        enemies[num_enemies].type = 3;
        enemies[num_enemies].hp = 100.0f;
        enemies[num_enemies].max_hp = 100.0f;
        enemies[num_enemies].move_speed = 3.0f;
        enemies[num_enemies].damage = 20.0f;
        enemies[num_enemies].attack_range = 28.0f;
        enemies[num_enemies].timer = 1.8f;
        enemies[num_enemies].state = 1;
        enemies[num_enemies].y = 2.0f;
        enemies[num_enemies].move_timer = 0.0f;
        enemies[num_enemies].anim_frame = 0;
        enemies[num_enemies].burst_count = 0;
        enemies[num_enemies].reload_timer = 0.0f;
        enemies[num_enemies].dodge_timer = 0.0f;
        num_enemies++;
      }
    }
  }
}

int main(int argc, char *argv[]) {
#ifdef _WIN32
  _setmode(_fileno(stdout), _O_BINARY);
  _setmode(_fileno(stdin), _O_BINARY);
#endif

  int render_width = 800;
  int render_height = 600;

  int init_header[6];
  size_t header_read = fread(init_header, sizeof(int), 6, stdin);

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
      enemies[i].max_hp = 100.0f;
      enemies[i].y = 2.0f;
      enemies[i].move_timer = 0.0f;
      enemies[i].anim_frame = 0;
      enemies[i].burst_count = 0;
      enemies[i].reload_timer = 0.0f;
      enemies[i].dodge_timer = 0.0f;
      enemies[i].timer = (float)(rand() % 100) / 100.0f;

      if (enemies[i].type == 1 || enemies[i].type == 9) { // yuritler
        enemies[i].hp = 150.0f;
        enemies[i].max_hp = 150.0f;
        enemies[i].move_speed = 1.8f;
        enemies[i].damage = 5.0f;
        enemies[i].attack_range = 20.0f;
      } else if (enemies[i].type == 2) { // elite enemies
        enemies[i].move_speed = 1.5f;
        enemies[i].damage = 4.0f;
        enemies[i].attack_range = 16.0f;
      } else if (enemies[i].type == 3) { // sniper
        enemies[i].move_speed = 3.0f;
        enemies[i].damage = 20.0f;
        enemies[i].attack_range = 28.0f;
      } else { // standard enemy
        enemies[i].move_speed = 1.5f;
        enemies[i].damage = 10.0f;
        enemies[i].attack_range = 15.0f;
      }
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
  Model weaponModel = LoadModel("game/models/hk_usp.glb");

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
  
  int time_loc = GetShaderLocation(lighting_shader, "u_time");
  int bloom_loc = GetShaderLocation(lighting_shader, "u_bloom");
  int clouds_loc = GetShaderLocation(lighting_shader, "u_clouds");
  int weather_loc = GetShaderLocation(lighting_shader, "u_rain_intensity");
  int yaw_loc = GetShaderLocation(lighting_shader, "u_yaw");
  int pitch_loc = GetShaderLocation(lighting_shader, "u_pitch");
  int aspect_loc = GetShaderLocation(lighting_shader, "u_aspect");
  int cam_pos_loc = GetShaderLocation(lighting_shader, "u_cam_pos");
  int fov_loc = GetShaderLocation(lighting_shader, "u_fovy");
  int flash_loc = GetShaderLocation(lighting_shader, "u_flash_intensity");
  int fl_loc = GetShaderLocation(lighting_shader, "u_flashlight_active");

  Camera3D camera = {0};
  camera.up = (Vector3){0.0f, 1.0f, 0.0f};
  camera.fovy = 60.0f;
  camera.projection = CAMERA_PERSPECTIVE;

  pthread_t thread_id;
  pthread_create(&thread_id, NULL, input_listener, NULL);

  float arena_timer = 0.0f;
  int active_enemies = 0;
  float muzzle_flash_timer = 0.0f;
  float ads_lerp = 0.0f;

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
    int is_aiming = current_input.is_aiming;

    current_input.mouse_dx = 0.0f;
    current_input.mouse_dy = 0.0f;
    pthread_mutex_unlock(&input_mutex);

    float dt = GetFrameTime();
    if (dt > 0.1f)
      dt = 0.1f;

    if (muzzle_flash_timer > 0.0f)
      muzzle_flash_timer -= dt;

    ads_lerp = Lerp(ads_lerp, is_aiming ? 1.0f : 0.0f, 10.0f * dt);
    camera.fovy = Lerp(60.0f, 40.0f, ads_lerp);

    static float shoot_cooldown = 0.0f;
    static float recoil_offset_z = 0.0f;
    static float recoil_pitch = 0.0f;
    
    if (shoot_cooldown > 0.0f)
      shoot_cooldown -= dt;
      
    recoil_offset_z = Lerp(recoil_offset_z, 0.0f, 15.0f * dt);
    recoil_pitch = Lerp(recoil_pitch, 0.0f, 15.0f * dt);

    current_cam.yaw += mdx;
    current_cam.pitch += mdy;

    if (current_cam.pitch > 89.0f)
      current_cam.pitch = 89.0f;
    if (current_cam.pitch < -89.0f)
      current_cam.pitch = -89.0f;

    float phys_yawRad = current_cam.yaw * DEG2RAD;
    float phys_pitchRad = current_cam.pitch * DEG2RAD;

    Vector3 forward;
    forward.x = cosf(phys_pitchRad) * cosf(phys_yawRad);
    forward.y = sinf(phys_pitchRad);
    forward.z = cosf(phys_pitchRad) * sinf(phys_yawRad);

    // combat logic (Player Shooting)
    if (k_shoot && shoot_cooldown <= 0.0f) {
      WeaponDef w = weapons[current_input.active_weapon];
      shoot_cooldown = w.cooldown;

      float base_dmg = w.damage;
      if (current_input.active_weapon == 1) {
        base_dmg *= (1.0f + current_input.pistol_lvl * 0.01f);
      } else if (current_input.active_weapon == 2) {
        base_dmg *= (1.0f + current_input.shotgun_lvl * 0.01f);
      } else if (current_input.active_weapon == 3) {
        base_dmg *= (1.0f + current_input.minigun_lvl * 0.10f);
      }

      float spread_mult = is_aiming ? 0.5f : 1.0f;

      for (int p = 0; p < w.pellets; p++) {
        int hit_idx = -1;
        float closest_dist = 25.0f;
        
        float spread_x = ((float)GetRandomValue(-100, 100) / 100.0f) * w.spread * spread_mult;
        float spread_y = ((float)GetRandomValue(-100, 100) / 100.0f) * w.spread * spread_mult;
        
        Vector3 ray_dir = forward;
        ray_dir.x += spread_x;
        ray_dir.y += spread_y;
        ray_dir.z += spread_x;
        ray_dir = Vector3Normalize(ray_dir);

        for (int i = 0; i < num_enemies; i++) {
          if (enemies[i].state >= 3)
            continue;

          float ex = enemies[i].x;
          float ey = enemies[i].y;
          float ez = enemies[i].z;

          float vx = ex - current_cam.x;
          float vy = ey - current_cam.y;
          float vz = ez - current_cam.z;

          float t_closest = vx * ray_dir.x + vy * ray_dir.y + vz * ray_dir.z;

          if (t_closest > 0.0f && t_closest < closest_dist) {
            float proj_x = current_cam.x + ray_dir.x * t_closest;
            float proj_z = current_cam.z + ray_dir.z * t_closest;

            float dist_sq =
                (ex - proj_x) * (ex - proj_x) + (ez - proj_z) * (ez - proj_z);
            if (dist_sq < (0.35f * 0.35f)) {
              float hit_y = current_cam.y + ray_dir.y * t_closest;
              if (hit_y >= ey && hit_y <= (ey + 1.5f)) {
                closest_dist = t_closest;
                hit_idx = i;
              }
            }
          }
        }

        if (hit_idx != -1) {
          // sniper dodge
          if (enemies[hit_idx].type == 3 && enemies[hit_idx].dodge_timer <= 0.0f) {
            float dodge_dx = -forward.z * 1.5f;
            float dodge_dz = forward.x * 1.5f;
            int check_x = (int)roundf((enemies[hit_idx].x + dodge_dx) / 2.0f);
            int check_z = (int)roundf((enemies[hit_idx].z + dodge_dz) / 2.0f);
            int el = (int)floorf(enemies[hit_idx].y / 2.0f);
            if (GetBlock(check_x, el, check_z) == 0) {
              enemies[hit_idx].x += dodge_dx;
              enemies[hit_idx].z += dodge_dz;
            }
            enemies[hit_idx].dodge_timer = 4.0f;
          } else {
            enemies[hit_idx].hp -= base_dmg;
            SendEvent(10, (int)base_dmg);
            if (enemies[hit_idx].hp <= 0.0f) {
              enemies[hit_idx].state = 3; // Dead
              SendEvent(11, enemies[hit_idx].type);
              
              if (num_static_sprites < MAX_SPRITES) {
                int drop = -1;
                int r = rand() % 100;
                if (enemies[hit_idx].type == 1 || enemies[hit_idx].type == 9) {
                  drop = 12;
                } else if (r < 35) {
                  drop = 11;
                } else if (r < 45) {
                  drop = 7;
                } else if (r < 55) {
                  drop = 13;
                } else if (r < 65) {
                  drop = 15;
                }
                
                if (drop != -1) {
                  static_sprites[num_static_sprites].x = enemies[hit_idx].x;
                  static_sprites[num_static_sprites].y = enemies[hit_idx].y;
                  static_sprites[num_static_sprites].z = enemies[hit_idx].z;
                  static_sprites[num_static_sprites].type = drop;
                  static_sprites[num_static_sprites].state = 0;
                  num_static_sprites++;
                }
              }
            }
          }
        }
      }
      
      if (current_input.active_weapon > 0) {
        muzzle_flash_timer = 0.08f;
      }
      
      SendEvent(20, current_input.active_weapon); // shoot weapon event
      recoil_offset_z = w.recoil_z;
      recoil_pitch = w.recoil_pitch;
    }

    // AI logic
    Vector3 p_pos = {camera.position.x, camera.position.y, camera.position.z};

    for (int i = 0; i < num_enemies; i++) {
      if (enemies[i].state >= 3)
        continue;

      enemies[i].timer -= dt;
      enemies[i].reload_timer -= dt;
      enemies[i].dodge_timer -= dt;

      Vector3 e_pos = {enemies[i].x, enemies[i].y + 1.0f, enemies[i].z};
      float dx = p_pos.x - e_pos.x;
      float dz = p_pos.z - e_pos.z;
      float dist = sqrtf(dx * dx + dz * dz);

      int has_los = HasLineOfSight(e_pos, p_pos);
      int should_move = 1;

      if (enemies[i].type == 1 || enemies[i].type == 9) { // yuritler
        if (dist <= 20.0f && has_los) {
          if (enemies[i].timer <= 0.0f) {
            float base_angle = atan2f(p_pos.z - e_pos.z, p_pos.x - e_pos.x);
            for (int f = 0; f < 4; f++) {
              float angle = base_angle + (f - 1.5f) * 0.12f;
              Vector3 dir = {cosf(angle), (p_pos.y - e_pos.y) / (dist > 0.1f ? dist : 1.0f), sinf(angle)};
              SpawnProjectile(e_pos, dir, 13.0f, 5.0f, 6, 0);
            }
            enemies[i].timer = 1.0f;
          }
          if (dist < 7.0f) should_move = 0;
        }
      } else if (enemies[i].type == 2) { // elite enemy
        if (enemies[i].reload_timer > 0.0f) {
        } else if (dist <= 16.0f && has_los) {
          if (enemies[i].timer <= 0.0f) {
            Vector3 dir = Vector3Normalize(Vector3Subtract(p_pos, e_pos));
            SpawnProjectile(e_pos, dir, 16.0f, 4.0f, 6, 0);
            enemies[i].timer = 0.1f;
            enemies[i].burst_count++;
            if (enemies[i].burst_count >= 10) {
              enemies[i].burst_count = 0;
              enemies[i].reload_timer = 5.0f;
            }
          }
          if (dist < 6.0f) should_move = 0;
        }
      } else if (enemies[i].type == 3) { // sniper
        if (dist <= 28.0f && has_los) {
          if (enemies[i].timer <= 0.0f) {
            Vector3 dir = Vector3Normalize(Vector3Subtract(p_pos, e_pos));
            SpawnProjectile(e_pos, dir, 25.0f, 20.0f, 14, 0);
            enemies[i].timer = 1.8f;
          }
          if (dist < 10.0f) should_move = 0;
        }
      } else { // standard enemy
        if (dist <= 15.0f && has_los) {
          if (enemies[i].timer <= 0.0f) {
            Vector3 dir = Vector3Normalize(Vector3Subtract(p_pos, e_pos));
            SpawnProjectile(e_pos, dir, 14.0f, 10.0f, 6, 0);
            enemies[i].timer = 1.5f;
          }
          if (dist < 5.0f) should_move = 0;
        }
      }

      if (should_move && dist > 0.1f) {
        float dir_x = dx / dist;
        float dir_z = dz / dist;
        float ms = enemies[i].move_speed;
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

        int ex_block = GetBlock((int)roundf(next_x / 2.0f), el, (int)roundf(enemies[i].z / 2.0f));
        if (ex_block <= 0)
          enemies[i].x = next_x;

        int ez_block = GetBlock((int)roundf(enemies[i].x / 2.0f), el, (int)roundf(next_z / 2.0f));
        if (ez_block <= 0)
          enemies[i].z = next_z;
      }
    }

    active_enemies = 0;
    for (int i = 0; i < num_enemies; i++) {
      if (enemies[i].state < 3)
        active_enemies++;
    }

    if (is_arena_mode) {
      total_arena_time += dt;
      current_cam.time_of_day = fmodf(12.0f + total_arena_time * 0.04f, 24.0f);

      weather_timer -= dt * 0.04f;
      if (weather_timer <= 0.0f) {
        if (weather_active) {
          weather_active = 0;
          weather_timer = 5.0f;
        } else {
          if (rand() % 100 < 10) {
            weather_active = 1;
            weather_timer = 6.0f;
          } else {
            weather_timer = 5.0f;
          }
        }
      }
      if (weather_active) {
        current_input.rain_intensity = Lerp(current_input.rain_intensity, 1.0f, 0.5f * dt);
      } else {
        current_input.rain_intensity = Lerp(current_input.rain_intensity, 0.0f, 0.5f * dt);
      }

      if (num_spawn_points > 0) {
        if (active_enemies == 0) {
          if (inter_round_timer > 0.0f) {
            inter_round_timer -= dt;
            if (inter_round_timer <= 0.0f) {
              StartNextArenaRound();
            }
          } else {
            inter_round_timer = 10.0f;
          }
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
    ClearBackground(BLANK);
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

    // projectile update and 3D billboard
    for (int p = 0; p < MAX_PROJECTILES; p++) {
      if (projectiles[p].active) {
        projectiles[p].pos = Vector3Add(projectiles[p].pos,
                                        Vector3Scale(projectiles[p].dir, projectiles[p].speed * dt));
        
        int bx = (int)roundf(projectiles[p].pos.x / 2.0f);
        int bz = (int)roundf(projectiles[p].pos.z / 2.0f);
        int layer = (int)floorf(projectiles[p].pos.y / 2.0f);
        if (GetBlock(bx, layer, bz) > 0) {
          projectiles[p].active = 0;
          continue;
        }

        if (!projectiles[p].from_player) {
          float p_dist_sq = (projectiles[p].pos.x - camera.position.x) * (projectiles[p].pos.x - camera.position.x) +
                            (projectiles[p].pos.y - camera.position.y) * (projectiles[p].pos.y - camera.position.y) +
                            (projectiles[p].pos.z - camera.position.z) * (projectiles[p].pos.z - camera.position.z);
          if (p_dist_sq < 0.4f) {
            projectiles[p].active = 0;
            Vector3 incoming = Vector3Scale(projectiles[p].dir, -1.0f);
            float world_angle_deg = atan2f(incoming.z, incoming.x) * RAD2DEG;
            int angle_encoded = (int)roundf(world_angle_deg);
            SendEvent(12, angle_encoded);
            continue;
          }
        }

        int t_idx = projectiles[p].tex_idx;
        if (t_idx >= 0 && t_idx < 16) {
          DrawBillboard(camera, sprite_tex[t_idx], projectiles[p].pos, 0.5f, WHITE);
        }
      }
    }

    // enemies
    for (int i = 0; i < num_enemies; i++) {
      if (enemies[i].state >= 0) {
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
            UpdateModelAnimation(guyModel, guyAnims[0], enemies[i].anim_frame);
          }
        }

        float edx = camera.position.x - enemies[i].x;
        float edz = camera.position.z - enemies[i].z;
        float angle = atan2f(edx, edz) * RAD2DEG;

        Vector3 pos = {enemies[i].x, enemies[i].y, enemies[i].z};
        
        Color tint = WHITE;
        float model_scale = 0.5f;

        // TODO: remove debug colores
        if (enemies[i].type == 1 || enemies[i].type == 9) { // yuritler
          tint = (Color){255, 200, 50, 255};
          model_scale = 0.65f;
        } else if (enemies[i].type == 2) {
          tint = (Color){200, 40, 40, 255};
        } else if (enemies[i].type == 3) {
          tint = (Color){50, 160, 240, 255};
        }

        if (enemies[i].state >= 3) {
          tint = GRAY;
        }

        DrawModelEx(guyModel, pos, (Vector3){0, 1, 0}, angle,
                    (Vector3){model_scale, model_scale, model_scale}, tint);
      }
    }

    EndMode3D();

    rlDisableDepthTest();
    Camera3D weapon_cam = {0};
    weapon_cam.position = (Vector3){0.0f, 0.0f, 0.0f};
    weapon_cam.target = (Vector3){0.0f, 0.0f, -1.0f};
    weapon_cam.up = (Vector3){0.0f, 1.0f, 0.0f};
    weapon_cam.fovy = camera.fovy;
    weapon_cam.projection = CAMERA_PERSPECTIVE;
    
    BeginMode3D(weapon_cam);
    
    static float sway_x = 0.0f;
    static float sway_y = 0.0f;
    sway_x = Lerp(sway_x, -mdx * 0.5f, 10.0f * GetFrameTime());
    sway_y = Lerp(sway_y, -mdy * 0.5f, 10.0f * GetFrameTime());

    if (sway_x > 20.0f) sway_x = 20.0f;
    if (sway_x < -20.0f) sway_x = -20.0f;
    if (sway_y > 20.0f) sway_y = 20.0f;
    if (sway_y < -20.0f) sway_y = -20.0f;

    static float bob_time = 0.0f;
    float current_speed = (k_w || k_s || k_a || k_d) ? 1.0f : 0.0f;
    
    static float bob_amp = 0.0f;
    bob_amp = Lerp(bob_amp, current_speed, 10.0f * GetFrameTime());
    
    if (bob_amp > 0.01f) {
        bob_time += GetFrameTime() * 12.0f;
    } else {
        bob_time = Lerp(bob_time, 0.0f, 10.0f * GetFrameTime());
    }

    float bob_x = sinf(bob_time / 2.0f) * 0.005f * bob_amp;
    float bob_y = cosf(bob_time) * 0.005f * bob_amp;
    
    Vector3 hip_pos = { 0.05f + bob_x, -0.05f + bob_y, -0.1f + recoil_offset_z };
    Vector3 ads_pos = { 0.0f + bob_x * 0.1f, -0.032f + bob_y * 0.1f, -0.07f + recoil_offset_z };
    Vector3 wp_pos = Vector3Lerp(hip_pos, ads_pos, ads_lerp);
    float wp_scale = 0.3f;
    
    float wp_pitch = 0.0f + recoil_pitch + sway_y * (1.0f - ads_lerp * 0.5f);
    float wp_yaw = 180.0f + sway_x * (1.0f - ads_lerp * 0.5f);
    float wp_roll = sway_x * -0.5f * (1.0f - ads_lerp * 0.5f);
    
    float pitch_rad = wp_pitch * DEG2RAD;
    float yaw_rad = wp_yaw * DEG2RAD;
    float roll_rad = wp_roll * DEG2RAD;
    
    Matrix rotX = MatrixRotateX(pitch_rad);
    Matrix rotY = MatrixRotateY(yaw_rad);
    Matrix rotZ = MatrixRotateZ(roll_rad);
    
    weaponModel.transform = MatrixMultiply(MatrixMultiply(rotX, rotY), rotZ);
    
    DrawModelEx(weaponModel, wp_pos, (Vector3){0,1,0}, 0.0f, (Vector3){wp_scale, wp_scale, wp_scale}, WHITE);
    
    EndMode3D();
    rlEnableDepthTest();

    if (is_arena_mode) {
      char ui_text[128];
      if (active_enemies == 0 && inter_round_timer > 0.0f) {
        sprintf(ui_text, "ROUND %d STARTING IN: %.1f", current_round + 1,
                inter_round_timer);
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
    
    float current_time = (float)GetTime();
    SetShaderValue(lighting_shader, time_loc, &current_time, SHADER_UNIFORM_FLOAT);
    SetShaderValue(lighting_shader, tod_loc, &current_cam.time_of_day, SHADER_UNIFORM_FLOAT);
    SetShaderValue(lighting_shader, sh_loc, &current_cam.shadows_enabled, SHADER_UNIFORM_INT);
    SetShaderValue(lighting_shader, lq_loc, &current_cam.lighting_quality, SHADER_UNIFORM_INT);
    
    SetShaderValue(lighting_shader, bloom_loc, &current_input.bloom_enabled, SHADER_UNIFORM_INT);
    SetShaderValue(lighting_shader, clouds_loc, &current_input.volumetric_clouds, SHADER_UNIFORM_INT);
    SetShaderValue(lighting_shader, weather_loc, &current_input.rain_intensity, SHADER_UNIFORM_FLOAT);
    SetShaderValue(lighting_shader, yaw_loc, &current_cam.yaw, SHADER_UNIFORM_FLOAT);
    SetShaderValue(lighting_shader, pitch_loc, &current_cam.pitch, SHADER_UNIFORM_FLOAT);
    
    float aspect = (float)target.texture.width / (float)target.texture.height;
    SetShaderValue(lighting_shader, aspect_loc, &aspect, SHADER_UNIFORM_FLOAT);
    
    Vector3 cam_pos_val = {current_cam.x, target_height, current_cam.z};
    SetShaderValue(lighting_shader, cam_pos_loc, &cam_pos_val, SHADER_UNIFORM_VEC3);
    
    SetShaderValue(lighting_shader, fov_loc, &camera.fovy, SHADER_UNIFORM_FLOAT);
    float flash_val = (muzzle_flash_timer > 0.0f) ? (muzzle_flash_timer / 0.08f) : 0.0f;
    SetShaderValue(lighting_shader, flash_loc, &flash_val, SHADER_UNIFORM_FLOAT);
    
    float fl_val = current_input.flashlight_active ? 1.0f : 0.0f;
    SetShaderValue(lighting_shader, fl_loc, &fl_val, SHADER_UNIFORM_FLOAT);
    
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
  UnloadModel(weaponModel);
  UnloadShader(lighting_shader);
  UnloadRenderTexture(target);
  UnloadRenderTexture(final_target);
  CloseWindow();
  if (dynamic_map)
    free(dynamic_map);
  return 0;
}
