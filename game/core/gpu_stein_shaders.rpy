init -20 python:
    renpy.register_shader("stein.raycaster", variables="""
        uniform float u_volumetric_clouds;
        uniform float u_rain_intensity;
        uniform float u_snow_intensity;
        uniform float u_wetness;
        uniform float u_time_of_day;
        uniform float u_time;
        uniform vec2 u_resolution;
        uniform vec2 u_player_pos;
        uniform vec2 u_player_dir;
        uniform vec2 u_player_plane;
        uniform float u_pitch;
        uniform float u_z_offset;
        uniform float u_vertical_scale;
        uniform sampler2D u_sky_texture;
        uniform sampler2D u_map_texture;
        uniform vec2 u_map_size;
        uniform vec2 u_map_uv_scale; 
        uniform float u_map_layer_norm_height;
        uniform float u_map_layer_base_y;
        uniform float u_map_layer_count;
        uniform vec2 u_map_tex_pixel_size;
        uniform sampler2D u_wall_atlas; 
        uniform sampler2D u_floor_texture;
        uniform float u_num_textures;
        uniform sampler2D u_sprite_atlas; 
        uniform float u_num_sprite_textures;
        uniform vec4 u_sprites[64]; // x, y, texture_id, pitch_offset
        uniform int u_num_active_sprites;
        uniform float u_flash_intensity;
        uniform vec4 u_light_positions[16];
        uniform float u_num_active_lights;
        uniform float u_flashlight_active;
        uniform vec2 u_flashlight_bob;
        uniform float u_soft_shadows;
        uniform float u_enable_shadows;
        uniform float u_max_dist;
        uniform float u_simple_floor;
        uniform vec3 u_ambient_color;
        uniform vec3 u_ambient_near_color;
        varying vec2 v_tex_coord;
        attribute vec2 a_tex_coord;
    """, vertex_200="""
        v_tex_coord = a_tex_coord;
    """, fragment_functions="""
        float hash(vec2 p) {
            p = fract(p * vec2(123.34, 456.21));
            p += dot(p, p + 45.32);
            return fract(p.x * p.y);
        }

        float noise(vec2 p) {
            vec2 i = floor(p);
            vec2 f = fract(p);
            f = f * f * (3.0 - 2.0 * f);
            float a = hash(i);
            float b = hash(i + vec2(1.0, 0.0));
            float c = hash(i + vec2(0.0, 1.0));
            float d = hash(i + vec2(1.0, 1.0));
            return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
        }

        float fbm(vec2 p) {
            float v = 0.0;
            float a = 0.5;
            for (int i = 0; i < 5; i++) {
                v += a * noise(p);
                p *= 2.0;
                a *= 0.5;
            }
            return v;
        }

        float ripple_layer(vec2 uv, float t) {
            vec2 p = uv * 5.0;
            vec2 g = floor(p);
            vec2 f = fract(p) - 0.5;
            
            vec2 rand_offset = (vec2(hash(g), hash(g + 11.5)) - 0.5) * 0.8;
            f -= rand_offset;
            
            float h = hash(g + vec2(3.0, 7.0));
            float t_local = fract(t * 1.2 + h * 10.0);
            
            float d = length(f);
            float r = 0.5 * t_local;
            
            float circle = smoothstep(0.05, 0.0, abs(d - r));
            float fade = 1.0 - t_local;
            
            return circle * fade;
        }

        float rain_layer(vec2 uv, float t) {
            vec2 st = uv;
            st.x *= 20.0; 
            st.y *= 0.5;  
            
            vec2 g = floor(st);
            
            float col_offset = hash(vec2(g.x, 0.0)); 
            float y_move = st.y + t + col_offset * 10.0;
            
            float cell_y = floor(y_move);
            float cell_fract = fract(y_move);
            
            float h = hash(vec2(g.x, cell_y));
            
            if (h < 0.85) return 0.0;
            
            float drop = 1.0 - cell_fract; 
            float beam = smoothstep(0.4, 0.5, fract(st.x)) * smoothstep(0.6, 0.5, fract(st.x));
            
            return drop * beam;
        }

        float intersectPyramid(vec3 ro, vec3 rd, out vec3 outNormal) {
            float tMin = 10000.0;
            bool hit = false;
            
            vec3 N[4]; float D[4];
            N[0] = vec3(1.0, 0.0, 1.0); D[0] = -1.0;
            N[1] = vec3(-1.0, 0.0, 1.0); D[1] = 0.0;
            N[2] = vec3(0.0, 1.0, 1.0); D[2] = -1.0;
            N[3] = vec3(0.0, -1.0, 1.0); D[3] = 0.0;
            
            for(int i=0; i<4; i++) {
                float denom = dot(rd, N[i]);
                if (denom < -0.0001) {
                    float t = -(dot(ro, N[i]) + D[i]) / denom;
                    if (t > 0.0) {
                        vec3 p = ro + rd * t;
                        if (p.z >= 0.0 && p.z <= 0.5) {
                            float h = 0.5 - p.z;
                            if (p.x >= 0.5 - h - 0.01 && p.x <= 0.5 + h + 0.01 &&
                                p.y >= 0.5 - h - 0.01 && p.y <= 0.5 + h + 0.01) {
                                if (t < tMin) {
                                    tMin = t;
                                    outNormal = normalize(N[i]);
                                    hit = true;
                                }
                            }
                        }
                    }
                }
            }
            if (hit) return tMin;
            return -1.0;
        }
    """, fragment_300="""
        const int MAX_STEPS = 128; 
        
        vec2 stein_uv = v_tex_coord;

        // RAY GENERATION (3D)
        // Player Position (Camera Origin). Z=0.5 is eye level + offsets
        vec3 rayPos = vec3(u_player_pos.x, u_player_pos.y, 0.5 + u_z_offset);
        
        // Pitch Angle
        float pitchAngle = atan(u_pitch);
        float cp = cos(pitchAngle);
        float sp = sin(pitchAngle);
        vec3 rightAxis = normalize(vec3(u_player_plane, 0.0));

        // Ray Direction
        float cameraX = 2.0 * stein_uv.x - 1.0; 
        float screenY = (0.5 - stein_uv.y) * 2.0; 
        
        vec3 baseDir = vec3(u_player_dir, 0.0) + vec3(u_player_plane, 0.0) * cameraX + vec3(0.0, 0.0, 1.0) * (screenY / u_vertical_scale);
        
        vec3 rayDir = baseDir * cp + cross(rightAxis, baseDir) * sp + rightAxis * dot(rightAxis, baseDir) * (1.0 - cp);
        rayDir = normalize(rayDir);

        vec3 flashBase = vec3(u_player_dir, 0.0) + vec3(u_player_plane, 0.0) * u_flashlight_bob.x + vec3(0.0, 0.0, 1.0) * u_flashlight_bob.y;
        vec3 flashDir = flashBase * cp + cross(rightAxis, flashBase) * sp + rightAxis * dot(rightAxis, flashBase) * (1.0 - cp);
        flashDir = normalize(flashDir);
        
        // DDA SETUP
        ivec3 mapPos = ivec3(floor(rayPos));
        vec3 deltaDist = abs(1.0 / rayDir);
        ivec3 stepDir;
        vec3 sideDist;
        
        if (rayDir.x < 0.0) { stepDir.x = -1; sideDist.x = (rayPos.x - float(mapPos.x)) * deltaDist.x; }
        else                { stepDir.x = 1;  sideDist.x = (float(mapPos.x) + 1.0 - rayPos.x) * deltaDist.x; }
        
        if (rayDir.y < 0.0) { stepDir.y = -1; sideDist.y = (rayPos.y - float(mapPos.y)) * deltaDist.y; }
        else                { stepDir.y = 1;  sideDist.y = (float(mapPos.y) + 1.0 - rayPos.y) * deltaDist.y; }
        
        if (rayDir.z < 0.0) { stepDir.z = -1; sideDist.z = (rayPos.z - float(mapPos.z)) * deltaDist.z; }
        else                { stepDir.z = 1;  sideDist.z = (float(mapPos.z) + 1.0 - rayPos.z) * deltaDist.z; }

        // DDA LOOP (3D)
        int hit = 0;
        int side = 0; // 0=X, 1=Y, 2=Z
        int wallID = 0;
        float rayDist = 0.0;
        vec3 hitNormal = vec3(0.0);

        for (int i = 0; i < MAX_STEPS; i++) {
            if (sideDist.x < sideDist.y) {
                if (sideDist.x < sideDist.z) {
                    rayDist = sideDist.x;
                    sideDist.x += deltaDist.x;
                    mapPos.x += stepDir.x;
                    side = 0;
                } else {
                    rayDist = sideDist.z;
                    sideDist.z += deltaDist.z;
                    mapPos.z += stepDir.z;
                    side = 2;
                }
            } else {
                if (sideDist.y < sideDist.z) {
                    rayDist = sideDist.y;
                    sideDist.y += deltaDist.y;
                    mapPos.y += stepDir.y;
                    side = 1;
                } else {
                    rayDist = sideDist.z;
                    sideDist.z += deltaDist.z;
                    mapPos.z += stepDir.z;
                    side = 2;
                }
            }
            
            if (rayDist > u_max_dist) { hit = 2; break; } // Too far
            
            // Map Bounds Check
            bool inside = (mapPos.x >= 0 && mapPos.x < int(u_map_size.x) && mapPos.y >= 0 && mapPos.y < int(u_map_size.y));
            
            // Voxel Check
            if (inside) {
                int layer = int(mapPos.z);
                int layer_idx = layer - int(u_map_layer_base_y);
                
                if (layer_idx >= 0 && layer_idx < int(u_map_layer_count)) {
                    float u = (float(mapPos.x) + 0.5) * u_map_tex_pixel_size.x;
                    float v_base = float(layer_idx) * u_map_layer_norm_height;
                    float v_local = (float(mapPos.y) + 0.5) * u_map_tex_pixel_size.y;
                    
                    vec2 mapUV = vec2(u, v_base + v_local);
                    vec4 mapPixel = texture2D(u_map_texture, mapUV);
                    if (mapPixel.r > 0.5) {
                        int id = int(mapPixel.g * 255.0 + 0.5);
                        if (id == 20) {
                            vec3 norm;
                            float t = intersectPyramid(rayPos - vec3(mapPos), rayDir, norm);
                            if (t > 0.0 && t >= rayDist - 0.01) {
                                rayDist = t;
                                wallID = id;
                                hit = 1;
                                hitNormal = norm;
                                break;
                            }
                        } else {
                            wallID = id;
                            hit = 1;
                            break;
                        }
                    }
                }
            }
        }

        vec3 color;
        
        if (hit == 1) {
            vec3 hitPos = rayPos + rayDir * rayDist;
            
            vec2 texUV;
            if (wallID == 20) {
                if (abs(hitNormal.x) > 0.5) {
                    texUV = vec2(fract(hitPos.y), fract(hitPos.z * 2.0));
                } else {
                    texUV = vec2(fract(hitPos.x), fract(hitPos.z * 2.0));
                }
            } else {
                if (side == 0) { // X-Side
                    float wallX = hitPos.y; 
                    if (rayDir.x > 0.0) wallX = 1.0 - wallX;
                    texUV = vec2(fract(wallX), fract(1.0 - hitPos.z));
                } 
                else if (side == 1) { // Y-Side
                    float wallX = hitPos.x;
                    if (rayDir.y < 0.0) wallX = 1.0 - wallX;
                    texUV = vec2(fract(wallX), fract(1.0 - hitPos.z));
                }
                else { // Side 2 (Wall Top/Bottom)
                    texUV = vec2(fract(hitPos.x), fract(hitPos.y));
                }
            }
            
            float texRes = 64.0;
            texUV = (floor(texUV * texRes) + 0.5) / texRes;
            
            float singleTexWidth = 1.0 / u_num_textures;
            float texOffset = float(wallID - 1) * singleTexWidth;
            
            float clampedU = texUV.x * (1.0 - 0.002) + 0.001;
            float finalU = texOffset + (clampedU * singleTexWidth);
            float finalV = texUV.y;
            
            if (finalV < 0.0 || finalV > 1.0) {
                color = vec3(0.0);
            } else {
                color = texture2D(u_wall_atlas, vec2(finalU, finalV), 0.0).rgb;
            }
            
            vec3 finalColor = color;
            
            float fogDist = length(hitPos.xy - u_player_pos);
            
            vec3 ambientLight = u_ambient_color; 
            
            // float personalLight = max(0.0, 1.0 - (fogDist / 4.0)); 
            // ambientLight += u_ambient_near_color * personalLight;
            
            vec3 totalLight = ambientLight;

            if (u_flashlight_active > 0.5) {
                vec3 flashPos = rayPos;

                vec3 lightVec = normalize(hitPos - flashPos);
                
                float dotProd = dot(lightVec, flashDir); 
                float dist3D = distance(hitPos, flashPos);

                if (dotProd > 0.82) { 
                    float spotEffect = smoothstep(0.82, 0.92, dotProd);
                    
                    float att = 1.0 / (1.5 + dist3D * 0.03 + dist3D * dist3D * 0.002);
                    vec3 flashLightColor = vec3(0.95, 0.95, 1.0);
                    
                    totalLight += flashLightColor * att * 2.2 * spotEffect;
                }
            }

            if (u_flash_intensity > 0.01) {
                float distToPlayer = distance(hitPos.xy, u_player_pos);
                float flashAtt = 1.0 / (0.5 + (distToPlayer * distToPlayer) * 0.1);
                vec3 flashColor = vec3(1.0, 0.8, 0.4);
                totalLight += flashColor * u_flash_intensity * flashAtt * 2.0;
            }

            for (int i = 0; i < 16; i++) {
                if (float(i) >= u_num_active_lights) break;
                
                vec4 lightData = u_light_positions[i]; 
                vec2 lightPos = lightData.xy;
                float radius = lightData.z;
                float intensity = lightData.w;
                
                float distToLight = distance(hitPos.xy, lightPos);
                
                if (distToLight < radius) {
                    float visibility = 1.0;
                    
                    if (u_enable_shadows > 0.5) {
                        visibility = 0.0;
                        int samples = 1;
                        float spread = 0.0;
                        
                        if (u_soft_shadows > 0.5) {
                            samples = 9;
                            spread = 0.55;
                        }
                        
                        vec2 dirToLight = normalize(lightPos - hitPos.xy);
                        vec2 perp = vec2(-dirToLight.y, dirToLight.x) * spread;
                        
                        for (int k = 0; k < 9; k++) {
                            if (k >= samples) break;
                            
                            float offScale = 0.0;
                            if (k == 1) offScale = 1.0;
                            if (k == 2) offScale = -1.0;
                            if (k == 3) offScale = 0.5;
                            if (k == 4) offScale = -0.5;
                            if (k == 5) offScale = 0.75;
                            if (k == 6) offScale = -0.75;
                            if (k == 7) offScale = 0.25;
                            if (k == 8) offScale = -0.25;
                            
                            vec2 offset = perp * offScale;
                            
                            vec2 targetPos = lightPos + offset;
                            vec2 rayDir = normalize(targetPos - hitPos.xy);
                            float rayDist = distance(targetPos, hitPos.xy);
                            
                            float stepSize = 0.2;
                            int steps = int(rayDist / stepSize);
                            vec2 checkPos = hitPos.xy + rayDir * 0.1;
                            bool hitWall = false;
                            
                            for(int s=0; s<64; s++) { 
                                if (s >= steps) break;
                                checkPos += rayDir * stepSize;
                                
                                if (abs(floor(checkPos.x) - float(mapPos.x)) < 0.1 && abs(floor(checkPos.y) - float(mapPos.y)) < 0.1) continue;

                                vec2 mapUV = (floor(checkPos) + 0.5) / u_map_size;
                                mapUV *= u_map_uv_scale;
                                vec4 shadowMapPixel = texture2D(u_map_texture, mapUV);
                                if (shadowMapPixel.r > 0.5) {
                                    // Check id to avoid pyramid casting cube shadows
                                    int sID = int(shadowMapPixel.g * 255.0 + 0.5);
                                    if (sID != 20) {
                                        hitWall = true;
                                        break;
                                    }
                                }
                            }
                            
                            if (!hitWall) visibility += 1.0;
                        }
                        
                        visibility /= float(samples);
                    }

                    if (visibility > 0.0) {
                        float att = 1.0 - (distToLight / radius);
                        att = att * att; 
                        
                        vec3 lampColor = vec3(0.2, 1.0, 0.2); 
                        totalLight += lampColor * intensity * att * visibility;
                    }
                }
            }

            float faceShadow = 1.0;
            if (wallID == 20) {
                faceShadow = 0.6 + 0.4 * hitNormal.z;
            } else {
                if (side == 1) faceShadow = 0.7; 
                if (side == 2) faceShadow = 1.0; 
            }
            
            color = finalColor * totalLight * faceShadow;

        } else {
            if (u_volumetric_clouds > 0.5) {
                vec3 skyColorTop;
                vec3 skyColorBottom;
                vec3 cloudColor;
                
                // Day Cycle Colors
                vec3 nightTop = vec3(0.0, 0.0, 0.1);
                vec3 nightBot = vec3(0.05, 0.05, 0.2);
                vec3 nightCloud = vec3(0.1, 0.1, 0.15);

                vec3 dayTop = vec3(0.0, 0.4, 0.8);
                vec3 dayBot = vec3(0.6, 0.8, 1.0);
                vec3 dayCloud = vec3(1.0, 1.0, 1.0);

                vec3 sunsetTop = vec3(0.2, 0.1, 0.4);
                vec3 sunsetBot = vec3(1.0, 0.4, 0.2);
                vec3 sunsetCloud = vec3(1.0, 0.6, 0.5);

                float t = mod(u_time_of_day, 24.0); // Ensure 0-24 range

                
                if (t < 5.0) {
                    skyColorTop = nightTop; skyColorBottom = nightBot; cloudColor = nightCloud;
                } else if (t < 8.0) {
                    float p = (t - 5.0) / 3.0;
                    skyColorTop = mix(nightTop, dayTop, p);
                    skyColorBottom = mix(nightBot, dayBot, p);
                    cloudColor = mix(nightCloud, dayCloud, p);
                } else if (t < 16.0) {
                    skyColorTop = dayTop; skyColorBottom = dayBot; cloudColor = dayCloud;
                } else if (t < 19.0) {
                    float p = (t - 16.0) / 3.0;
                    skyColorTop = mix(dayTop, sunsetTop, p);
                    skyColorBottom = mix(dayBot, sunsetBot, p);
                    cloudColor = mix(dayCloud, sunsetCloud, p);
                } else if (t < 21.0) {
                    float p = (t - 19.0) / 2.0;
                    skyColorTop = mix(sunsetTop, nightTop, p);
                    skyColorBottom = mix(sunsetBot, nightBot, p);
                    cloudColor = mix(sunsetCloud, nightCloud, p);
                } else {
                    skyColorTop = nightTop; skyColorBottom = nightBot; cloudColor = nightCloud;
                }

                float skyGradient = smoothstep(-0.5, 0.5, rayDir.z);
                vec3 skyBase = mix(skyColorBottom, skyColorTop, skyGradient);
                
                color = skyBase;

                if (rayDir.z > 0.01) {
                    vec2 cloudUV = rayDir.xy / rayDir.z;
                    cloudUV += u_time * 0.05;
                    
                    float n = fbm(cloudUV * 0.5);
                    float c = smoothstep(0.4, 0.8, n);
                    c *= smoothstep(0.0, 0.2, rayDir.z);
                    
                    float brightness = 1.0;
                    if (t < 6.0 || t > 20.0) brightness = 0.3;
                    else if (t < 8.0) brightness = mix(0.3, 1.0, (t - 6.0) / 2.0);
                    else if (t > 18.0) brightness = mix(1.0, 0.3, (t - 18.0) / 2.0);
                    
                    color = mix(color, cloudColor * brightness, c);
                }
                
                float starVisibility = 0.0;
                if (t < 6.0) starVisibility = 1.0;
                else if (t < 7.0) starVisibility = 1.0 - (t - 6.0);
                else if (t > 20.0) starVisibility = (t - 20.0) / 1.0;
                if (t > 21.0) starVisibility = 1.0;

                if (starVisibility > 0.01 && rayDir.z > 0.01) {
                    vec2 starUV = rayDir.xy / (1.0 + rayDir.z);
                    
                    float scale = 300.0; 
                    vec2 gridUV = starUV * scale;
                    vec2 gridID = floor(gridUV);
                    vec2 gridLocal = fract(gridUV) - 0.5;
                    
                    float h = hash(gridID);
                    
                    if (h > 0.97) {
                        // Stable random position in cell
                        float r1 = hash(gridID + vec2(12.34, 56.78));
                        float r2 = hash(gridID + vec2(90.12, 34.56));
                        vec2 pos = (vec2(r1, r2) - 0.5) * 0.7;
                        
                        float dist = length(gridLocal - pos);
                        
                        float brightness = smoothstep(0.4, 0.1, dist);
                        
                        float twinkle = 0.7 + 0.3 * sin(u_time * 2.0 + h * 50.0);
                        
                        // Horizon fade
                        float fade = smoothstep(0.01, 0.1, rayDir.z);
                        
                        color += vec3(brightness * twinkle * fade * starVisibility);
                    }
                }
            } else {
                // Skybox
                vec2 skyUV = stein_uv;
                // Apply pitch to skyUV.y
                skyUV.y -= u_pitch; 
                skyUV.y = clamp(skyUV.y, 0.0, 1.0);
                color = texture2D(u_sky_texture, skyUV).rgb;
            }
        }

        // SPRITE RENDERING (Adapted for 3D)
        // We approximate 2D billboard logic using the 3D ray distance
        
        // Calculate Camera Forward Vector (Rotated)
        vec3 forwardUnrot = vec3(u_player_dir, 0.0);
        vec3 forwardRot = forwardUnrot * cp + cross(rightAxis, forwardUnrot) * sp + rightAxis * dot(rightAxis, forwardUnrot) * (1.0 - cp);
        
        float perpWallDist = dot(rayDir * rayDist, forwardRot);
        
        // If we didnt hit a wall (Sky/Void), the depth is infinite
        if (hit != 1) perpWallDist = 10000.0;
        
        float currentDepth = perpWallDist;
        
        // Precalculate pitch shift in pixels for sprites
        // float pitchPixeLCTRL = u_pitch * u_vertical_scale * (u_resolution.y / 2.0);

        float invDet = 1.0 / (u_player_plane.x * u_player_dir.y - u_player_dir.x * u_player_plane.y);

        for (int i = 0; i < 64; i++) {
            if (i >= u_num_active_sprites) break;
            
            vec4 spriteData = u_sprites[i];
            vec2 spritePos = spriteData.xy;
            float texID = spriteData.z;
            float spritePitch = spriteData.w; 

            float spX = spritePos.x - u_player_pos.x;
            float spY = spritePos.y - u_player_pos.y;

            float transformX = invDet * (u_player_dir.y * spX - u_player_dir.x * spY);
            float transformY = invDet * (-u_player_plane.y * spX + u_player_plane.x * spY); 
            
            // Apply Pitch Rotation to Sprite Position
            float camHeight = 0.5 + u_z_offset;
            float spriteZ = -camHeight;
            
            float rotY = transformY * cp + spriteZ * sp;
            float rotZ = -transformY * sp + spriteZ * cp;

            if (rotY <= 0.1) continue;
            // Robust depth check
            if (rotY >= currentDepth) continue; 

            float spriteScreenX = (u_resolution.x / 2.0) * (1.0 + transformX / rotY);
            
            // Scale sprites down
            float spriteScale = 0.55; 
            float spriteHeight = abs(u_resolution.y / rotY) * u_vertical_scale * spriteScale; 
            float spriteWidth = spriteHeight; 

            // Sprite Anchoring Logic (Floor Alignment)
            // Calculate Screen Y of the floor (rotZ)
            float screenY_floor = (rotZ / rotY) * u_vertical_scale;
            float pixelY_floor = (0.5 - screenY_floor / 2.0) * u_resolution.y;
            
            float spritePixeLCTRL = spritePitch * u_vertical_scale * (u_resolution.y / 2.0);
            
            float drawEndY = pixelY_floor - spritePixeLCTRL;
            float drawStartY = drawEndY - spriteHeight;
            
            float drawStartX = spriteScreenX - spriteWidth / 2.0;
            float drawEndX = spriteScreenX + spriteWidth / 2.0;

            float currentPixelX = stein_uv.x * u_resolution.x; 
            float currentPixelY = stein_uv.y * u_resolution.y;

            if (currentPixelX >= drawStartX && currentPixelX <= drawEndX) {
                float texX = (currentPixelX - drawStartX) / spriteWidth;
                
                float texY = (currentPixelY - drawStartY) / spriteHeight;
                // texY = 1.0 - texY;

                if (texY >= 0.0 && texY <= 1.0) {
                    float singleTexW = 1.0 / u_num_sprite_textures;
                    float atlasX = (texID * singleTexW) + (texX * singleTexW);
                    
                    vec4 spriteCol = texture2D(u_sprite_atlas, vec2(atlasX, texY));
                    
                    if (spriteCol.a > 0.5) {
                        
                        float sprDist = length(vec2(spX, spY)); 
                        
                        vec3 sprLight = u_ambient_color;
                        // float sprPersonal = max(0.0, 1.0 - (sprDist / 4.0));
                        // sprLight += u_ambient_near_color * sprPersonal;

                        if (u_flashlight_active > 0.5) {
                            float dotProd = dot(rayDir, flashDir);
                            
                            float dist3D = transformY;
                            
                            if (dotProd > 0.82) {
                                float spotEffect = smoothstep(0.82, 0.92, dotProd);
                                float att = 1.0 / (1.5 + dist3D * 0.03 + dist3D * dist3D * 0.002);
                                vec3 flashLightColor = vec3(0.95, 0.95, 1.0);
                                
                                sprLight += flashLightColor * att * 2.2 * spotEffect;
                            }
                        }

                        if (u_flash_intensity > 0.01) {
                            float flashAtt = 1.0 / (0.5 + (sprDist * sprDist) * 0.1);
                            vec3 flashColor = vec3(1.0, 0.8, 0.4);
                            sprLight += flashColor * u_flash_intensity * flashAtt * 2.0;
                        }

                        for (int j = 0; j < 16; j++) {
                            if (float(j) >= u_num_active_lights) break;
                            
                            vec4 lData = u_light_positions[j];
                            float lDist = distance(spritePos, lData.xy);
                            
                            if (lDist < lData.z) {
                                float visibility = 1.0;
                                
                                if (u_enable_shadows > 0.5) {
                                    visibility = 0.0;
                                    int samples = 1;
                                    float spread = 0.0;
                                    
                                    if (u_soft_shadows > 0.5) {
                                        samples = 9;
                                        spread = 0.55;
                                    }
                                    
                                    vec2 dirToLight = normalize(lData.xy - spritePos);
                                    vec2 perp = vec2(-dirToLight.y, dirToLight.x) * spread;
                                    
                                    for (int k = 0; k < 9; k++) {
                                        if (k >= samples) break;
                                        
                                        float offScale = 0.0;
                                        if (k == 1) offScale = 1.0;
                                        if (k == 2) offScale = -1.0;
                                        if (k == 3) offScale = 0.5;
                                        if (k == 4) offScale = -0.5;
                                        if (k == 5) offScale = 0.75;
                                        if (k == 6) offScale = -0.75;
                                        if (k == 7) offScale = 0.25;
                                        if (k == 8) offScale = -0.25;
                                        
                                        vec2 offset = perp * offScale;
                                        
                                        vec2 targetPos = lData.xy + offset;
                                        vec2 rayDir = normalize(targetPos - spritePos);
                                        float rayDist = distance(targetPos, spritePos);
                                        
                                        float stepSize = 0.2;
                                        int steps = int(rayDist / stepSize);
                                        vec2 checkPos = spritePos + rayDir * 0.1;
                                        bool hitWall = false;
                                        
                                        for(int s=0; s<64; s++) {
                                            if (s >= steps) break;
                                            checkPos += rayDir * stepSize;
                                            
                                            vec2 mapUV = (floor(checkPos) + 0.5) / u_map_size;
                                            mapUV *= u_map_uv_scale;
                                            vec4 smp = texture2D(u_map_texture, mapUV);
                                            if (smp.r > 0.5) {
                                                int sid = int(smp.g * 255.0 + 0.5);
                                                if (sid != 20) {
                                                    hitWall = true;
                                                    break;
                                                }
                                            }
                                        }
                                        
                                        if (!hitWall) visibility += 1.0;
                                    }
                                    
                                    visibility /= float(samples);
                                }

                                if (visibility > 0.0) {
                                    float att = 1.0 - (lDist / lData.z);
                                    att = att * att;
                                    vec3 lampColor = vec3(0.4, 0.9, 0.4);
                                    sprLight += lampColor * lData.w * att * visibility;
                                }
                            }
                        }

                        color = spriteCol.rgb * sprLight;
                        currentDepth = transformY; 
                    }
                }
            }
        }

        if (u_rain_intensity > 0.0) {
            float rainVal = 0.0;
            for (int i=1; i<=4; i++) {
                float dist = float(i) * 2.5; 
                if (dist > currentDepth) break;
                
                vec3 p = rayPos + rayDir * dist;
                
                vec2 uv1 = vec2(p.y, p.z) * vec2(1.0, 2.0); // YZ Plane
                vec2 uv2 = vec2(p.x, p.z) * vec2(1.0, 2.0); // XZ Plane
                
                float t = u_time * 15.0;
                float n1 = rain_layer(uv1, t);
                float n2 = rain_layer(uv2, t);
                
                float blend = abs(rayDir.x);
                float n = mix(n2, n1, blend);
                
                // Distance Fade
                float fade = 1.0 - (dist / 12.0);
                if (fade < 0.0) fade = 0.0;
                
                rainVal += n * fade;
            }
            color = mix(color, vec3(0.7, 0.8, 0.9), rainVal * u_rain_intensity * 0.4);
        }

        if (u_snow_intensity > 0.0) {
            float snowVal = 0.0;
            for (int i=1; i<=4; i++) {
                float dist = float(i) * 2.0; 
                if (dist > currentDepth) break;
                
                vec3 p = rayPos + rayDir * dist;
                
                vec2 uv1 = vec2(p.y, p.z) * 0.8; 
                vec2 uv2 = vec2(p.x, p.z) * 0.8;
                
                float t = u_time * 2.0;
                uv1.y += t;
                uv2.y += t;
                
                uv1.x += sin(u_time + p.z) * 0.2;
                uv2.x += cos(u_time + p.z) * 0.2;
                
                float n1 = noise(uv1);
                float n2 = noise(uv2);
                
                float blend = abs(rayDir.x);
                float n = mix(n2, n1, blend);
                
                float s = smoothstep(0.95, 1.0, n);
                
                float fade = 1.0 - (dist / 10.0);
                if (fade < 0.0) fade = 0.0;
                
                snowVal += s * fade;
            }
            color = mix(color, vec3(1.0), snowVal * u_snow_intensity * 0.8);
        }

        gl_FragColor = vec4(color, 1.0);
    """)

    renpy.register_shader("stein.motion_blur", variables="""
        uniform sampler2D tex0;
        uniform float u_blur_amount;
        varying vec2 v_tex_coord;
    """, fragment_200="""
        vec2 stein_mb_uv = v_tex_coord;
        vec4 mb_color = texture2D(tex0, stein_mb_uv);
        
        if (abs(u_blur_amount) > 0.001) {
            float blur = u_blur_amount * 0.02;
            vec4 sum = vec4(0.0);
            
            // 5-tap optimization
            sum += texture2D(tex0, vec2(stein_mb_uv.x - blur * 2.0, stein_mb_uv.y)) * 0.1;
            sum += texture2D(tex0, vec2(stein_mb_uv.x - blur * 1.0, stein_mb_uv.y)) * 0.25;
            sum += texture2D(tex0, vec2(stein_mb_uv.x, stein_mb_uv.y)) * 0.3;
            sum += texture2D(tex0, vec2(stein_mb_uv.x + blur * 1.0, stein_mb_uv.y)) * 0.25;
            sum += texture2D(tex0, vec2(stein_mb_uv.x + blur * 2.0, stein_mb_uv.y)) * 0.1;
            
            gl_FragColor = sum;
        } else {
            gl_FragColor = mb_color;
        }
    """)

    renpy.register_shader("stein.weapon_fx", variables="""
        varying vec2 v_tex_coord;
        attribute vec2 a_tex_coord;
        uniform float u_flash_progress; 
        uniform float u_flash_angle;
        uniform vec3 u_flash_color;
        uniform float u_heat_distortion;
        uniform float u_enable_smoke;
    """, vertex_200="""
        v_tex_coord = a_tex_coord;
    """, fragment_200="""
        // Center UVs to [-1, 1] range
        vec2 stein_w_uv = (v_tex_coord - 0.5) * 2.0; 
        
        // Internal rotation
        float s = sin(u_flash_angle);
        float c = cos(u_flash_angle);
        vec2 rotated_uv = mat2(c, -s, s, c) * stein_w_uv;
        
        float dist = length(rotated_uv);
        float angle = atan(rotated_uv.y, rotated_uv.x);
        
        // MUZZLE FLASH
        // Flash happens in the first 4% of the duration (1.5s * 0.04 = 0.06s)
        float flash_p = u_flash_progress * 25.0; 
        float flash_intensity = 0.0;
        
        if (flash_p < 1.0) {
            float spikes = abs(sin(angle * 4.0)) * 0.4 + abs(sin(angle * 9.0)) * 0.6;
            float core = exp(-dist * 5.0) * 2.5;
            float rays = exp(-dist * (4.0 + 8.0 * (1.0 - spikes))) * 1.2;
            float mask = smoothstep(1.0, 0.2, dist);
            
            flash_intensity = (core + rays) * (1.0 - flash_p);
            flash_intensity = clamp(flash_intensity * mask, 0.0, 1.0);
        }

        // BARREL SMOKE
        // Simulates smoke emanating from the hot barrel and rising up
        float smoke_alpha = 0.0;
        if (u_enable_smoke > 0.5 && u_flash_progress > 0.02) {
            float smoke_p = (u_flash_progress - 0.02) / 0.98;
            
            // Use unrotated UV so smoke always rises UP relative to screen
            vec2 stream_uv = stein_w_uv;
            
            // Detach from bottom logic (Smoke moves up/away from barrel)
            // We mask out the bottom part, and this mask moves up over time
            // uv.y is negative for up, 0 is center
            float detach_y = -0.1 - (smoke_p * 1.2);
            
            // Mask: Visible if y < detach_y (above the cut-off point)
            // We use smoothstep for a soft bottom edge
            float detach_mask = smoothstep(detach_y + 0.3, detach_y, stream_uv.y);
            
            // Wiggle the stream (turbulence)
            float wiggle = sin(stream_uv.y * 12.0 + u_flash_progress * 15.0) * 0.04;
            stream_uv.x += wiggle;
            
            // Stream shape
            float stream_width = 0.04 + abs(stream_uv.y) * 0.15; 
            float stream_shape = smoothstep(stream_width, 0.0, abs(stream_uv.x));
            
            // Top fade
            float height_mask = smoothstep(-0.95, -0.2, stream_uv.y); 
            
            // Scroll noise up through the stream
            float noise_y = stein_w_uv.y + u_flash_progress * 3.0;
            float noise = sin(stein_w_uv.x * 40.0) * sin(noise_y * 12.0);
            
            // Overall fade out over time
            float fade_out = 1.0 - smoothstep(0.2, 0.9, smoke_p);
            
            smoke_alpha = stream_shape * detach_mask * height_mask * (0.6 + 0.4 * noise) * fade_out * 0.8;
        }

        // HEAT DISTORTION
        float heat_val = 0.0;
        /*
        if (u_heat_distortion > 0.5) {
            float heat_prog = u_flash_progress * 3.0;
            if (heat_prog < 1.0) {
                float wave = sin(rotated_uv.x * 10.0 + heat_prog * 10.0) * 0.1;
                float heat_d = length(rotated_uv + vec2(wave, heat_prog * 0.5));
                float heat_ring = smoothstep(0.05, 0.0, abs(heat_d - 0.4 - heat_prog * 0.3));
                float turb = sin(angle * 20.0 + heat_prog * 20.0);
                heat_val = heat_ring * 0.4 * (1.0 - heat_prog) * (0.5 + 0.5 * turb);
            }
        }
        
        heat_val *= (1.0 - smoke_alpha * 1.5);
        heat_val = max(0.0, heat_val);
        */

        // Combine
        vec3 final_color = u_flash_color * flash_intensity;
        float final_alpha = flash_intensity;
        
        // Add Heat
        final_color += vec3(heat_val);
        final_alpha = max(final_alpha, heat_val);
        
        // Add Smoke
        vec3 smoke_col = vec3(0.95, 0.95, 1.0); // White/Grey smoke
        
        // Mix Smoke
        final_color = mix(final_color, smoke_col, smoke_alpha);
        final_alpha = max(final_alpha, smoke_alpha);
        
        gl_FragColor = vec4(final_color, final_alpha);
    """)

    renpy.register_shader("stein.bloom", variables="""
        uniform sampler2D tex0;
        uniform vec2 u_resolution;
        varying vec2 v_tex_coord;
    """, fragment_200="""
        vec2 stein_bloom_uv = v_tex_coord;
        vec4 source = texture2D(tex0, stein_bloom_uv);
        
        float bloomSpread = 4.0;
        float threshold = 0.8;
        float intensity = 0.5;

        vec4 sum = vec4(0.0);
        vec2 size = vec2(1.0) / u_resolution;

        for (float i = -1.0; i <= 1.0; i++) {
            for (float j = -1.0; j <= 1.0; j++) {
                vec2 offset = vec2(i, j) * bloomSpread * size;
                vec4 col = texture2D(tex0, stein_bloom_uv + offset);
                
                float brightness = dot(col.rgb, vec3(0.2126, 0.7152, 0.0722));
                if (brightness > threshold) {
                    sum += col * brightness; 
                }
            }
        }
        
        sum = sum / 9.0;
        gl_FragColor = source + (sum * intensity);
    """)

    import math
    import pygame
    import time

    if renpy.android:
        simulate_touch = True
    else:
        simulate_touch = False

    config.pygame_events.extend([
        pygame.FINGERMOTION, pygame.FINGERDOWN, pygame.FINGERUP,
        pygame.JOYAXISMOTION, pygame.JOYBUTTONDOWN, pygame.JOYBUTTONUP,
        pygame.JOYHATMOTION, pygame.JOYDEVICEADDED, pygame.JOYDEVICEREMOVED
    ])

    renpy.music.register_channel("gun_sfx", mixer="sfx", loop=False)
    renpy.music.register_channel("shotgun_sfx", mixer="sfx", loop=False)
    renpy.music.register_channel("enemy_sfx", mixer="sfx", loop=False)

    texWidth = 64
    texHeight = 64
    twoPI = math.pi * 2

