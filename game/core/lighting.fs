#version 330

in vec2 fragTexCoord;
in vec4 fragColor;

uniform sampler2D texture0;
uniform float time_of_day;
uniform int lighting_quality;
uniform int shadows_enabled;

uniform float u_time;
uniform int u_bloom;
uniform int u_clouds;
uniform float u_rain_intensity;
uniform float u_yaw;
uniform float u_pitch;
uniform float u_aspect;
uniform vec3 u_cam_pos;
uniform float u_fovy;
uniform float u_flash_intensity;
uniform float u_flashlight_active;

out vec4 finalColor;

float hash(vec2 p)
{
    p = fract(p * vec2(123.34, 456.21));
    p += dot(p, p + 45.32);
    return fract(p.x * p.y);
}

float noise(vec2 p)
{
    vec2 i = floor(p);
    vec2 f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    float a = hash(i);
    float b = hash(i + vec2(1.0, 0.0));
    float c = hash(i + vec2(0.0, 1.0));
    float d = hash(i + vec2(1.0, 1.0));
    return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
}

float fbm(vec2 p)
{
    float v = 0.0;
    float a = 0.5;
    for (int i = 0; i < 5; i++)
    {
        v += a * noise(p);
        p *= 2.0;
        a *= 0.5;
    }
    return v;
}

float rain_layer(vec2 uv, float t)
{
    vec2 st = uv;
    st.x *= 20.0;
    st.y *= 0.5;

    vec2 g = floor(st);
    float col_offset = hash(vec2(g.x, 0.0));
    float y_move = st.y - t + col_offset * 10.0;

    float cell_y = floor(y_move);
    float cell_fract = fract(y_move);

    float h = hash(vec2(g.x, cell_y));
    if (h < 0.85)
        return 0.0;

    float drop = 1.0 - cell_fract;
    float beam = smoothstep(0.4, 0.5, fract(st.x)) * smoothstep(0.6, 0.5, fract(st.x));

    return drop * beam;
}

void main()
{
    vec4 texelColor = texture(texture0, fragTexCoord);
    vec3 result = texelColor.rgb;

    float t = mod(time_of_day, 24.0);

    if (texelColor.a == 0.0)
    {
        vec2 ndc = fragTexCoord * 2.0 - 1.0;

        float yawRad = u_yaw * (3.141592653589793 / 180.0);
        float pitchRad = u_pitch * (3.141592653589793 / 180.0);

        vec3 forward = vec3(cos(yawRad) * cos(pitchRad), sin(pitchRad), sin(yawRad) * cos(pitchRad));
        vec3 worldUp = vec3(0.0, 1.0, 0.0);

        vec3 right;
        if (abs(forward.y) > 0.999)
        {
            right = normalize(cross(forward, vec3(0.0, 0.0, 1.0)));
        }
        else
        {
            right = normalize(cross(forward, worldUp));
        }
        vec3 up = cross(right, forward);

        float curFov = u_fovy > 10.0 ? u_fovy : 60.0;
        float fovRad = curFov * (3.141592653589793 / 180.0);
        float focalLength = 1.0 / tan(fovRad / 2.0);

        vec3 rayDir = normalize(forward * focalLength + right * (ndc.x * u_aspect) + up * ndc.y);

        vec3 skyColorTop;
        vec3 skyColorBottom;
        vec3 cloudColor;

        vec3 nightTop = vec3(0.01, 0.01, 0.05);
        vec3 nightBot = vec3(0.04, 0.05, 0.12);
        vec3 nightCloud = vec3(0.1, 0.1, 0.15);

        vec3 dayTop = vec3(0.1, 0.45, 0.9);
        vec3 dayBot = vec3(0.65, 0.82, 0.98);
        vec3 dayCloud = vec3(1.0, 1.0, 1.0);

        vec3 sunsetTop = vec3(0.2, 0.1, 0.35);
        vec3 sunsetBot = vec3(0.95, 0.45, 0.2);
        vec3 sunsetCloud = vec3(1.0, 0.65, 0.5);

        if (t < 5.0)
        {
            skyColorTop = nightTop;
            skyColorBottom = nightBot;
            cloudColor = nightCloud;
        }
        else if (t < 8.0)
        {
            float p = (t - 5.0) / 3.0;
            skyColorTop = mix(nightTop, dayTop, p);
            skyColorBottom = mix(nightBot, dayBot, p);
            cloudColor = mix(nightCloud, dayCloud, p);
        }
        else if (t < 16.0)
        {
            skyColorTop = dayTop;
            skyColorBottom = dayBot;
            cloudColor = dayCloud;
        }
        else if (t < 19.0)
        {
            float p = (t - 16.0) / 3.0;
            skyColorTop = mix(dayTop, sunsetTop, p);
            skyColorBottom = mix(dayBot, sunsetBot, p);
            cloudColor = mix(dayCloud, sunsetCloud, p);
        }
        else if (t < 21.0)
        {
            float p = (t - 19.0) / 2.0;
            skyColorTop = mix(sunsetTop, nightTop, p);
            skyColorBottom = mix(sunsetBot, nightBot, p);
            cloudColor = mix(sunsetCloud, nightCloud, p);
        }
        else
        {
            skyColorTop = nightTop;
            skyColorBottom = nightBot;
            cloudColor = nightCloud;
        }

        float skyGradient = smoothstep(-0.1, 0.6, rayDir.y);
        result = mix(skyColorBottom, skyColorTop, skyGradient);

        float horizonHaze = exp(-abs(rayDir.y) * 7.0);
        vec3 hazeColor = mix(vec3(0.9, 0.35, 0.1), vec3(0.95, 0.6, 0.25), smoothstep(16.0, 18.0, t));
        float hazeIntensity =
            (smoothstep(4.5, 6.5, t) * smoothstep(8.5, 6.5, t) + smoothstep(16.5, 18.5, t) * smoothstep(20.5, 18.5, t));
        result = mix(result, hazeColor, horizonHaze * hazeIntensity * 0.65);

        float sunAngle = ((t - 6.0) / 24.0) * 6.28318530718;
        vec3 sunDir = normalize(vec3(cos(sunAngle), sin(sunAngle), 0.25 * cos(sunAngle)));
        vec3 moonDir = -sunDir;

        if (sunDir.y > -0.15)
        {
            float sunDot = max(dot(rayDir, sunDir), 0.0);
            float sunDisc = smoothstep(0.9985, 0.9995, sunDot);
            float sunGlow = pow(sunDot, 12.0) * 0.5 + pow(sunDot, 48.0) * 0.5;
            vec3 sunColor = mix(vec3(1.0, 0.45, 0.15), vec3(1.0, 1.0, 0.9), smoothstep(0.0, 0.25, sunDir.y));
            result += (sunColor * sunDisc * 1.5 + sunColor * sunGlow * 0.45) * smoothstep(-0.1, 0.1, sunDir.y);
        }

        float nightFactor = smoothstep(6.0, 4.0, t) + smoothstep(18.0, 20.0, t);
        nightFactor = clamp(nightFactor, 0.0, 1.0);

        if (nightFactor > 0.01)
        {
            if (moonDir.y > -0.15)
            {
                float moonDot = max(dot(rayDir, moonDir), 0.0);
                float moonDisc = smoothstep(0.9988, 0.9995, moonDot);
                float moonGlow = pow(moonDot, 24.0) * 0.3;
                vec3 moonColor = vec3(0.85, 0.92, 1.0);
                result += (moonColor * moonDisc * 1.1 + moonColor * moonGlow * 0.35) * nightFactor *
                          smoothstep(-0.1, 0.1, moonDir.y);
            }

            if (rayDir.y > 0.02)
            {
                vec2 starPos = floor(rayDir.xz / (rayDir.y + 0.4) * 250.0);
                float starHash = hash(starPos);
                if (starHash > 0.982)
                {
                    float twinkle = sin(u_time * 2.5 + starHash * 200.0) * 0.35 + 0.65;
                    float starBright =
                        pow((starHash - 0.982) / 0.018, 2.0) * twinkle * smoothstep(0.02, 0.25, rayDir.y);
                    result += vec3(0.85, 0.92, 1.0) * starBright * nightFactor * 0.9;
                }
            }
        }

        if (u_clouds != 0)
        {
            if (rayDir.y > 0.01)
            {
                float cloudHeight = 60.0;
                float dist = (cloudHeight - u_cam_pos.y) / rayDir.y;
                vec2 worldCloud = u_cam_pos.xz + rayDir.xz * dist;
                vec2 cloudUV = worldCloud * 0.008 + vec2(u_time * 0.012, u_time * 0.006);

                float cloudVal = fbm(cloudUV);

                float skyFade = smoothstep(0.01, 0.18, rayDir.y); // Fade near horizon
                float cloudAlpha = smoothstep(0.32, 0.68, cloudVal) * skyFade * 0.85;
                result = mix(result, cloudColor, cloudAlpha);
            }
        }
    }
    else
    {
        float sunAngle = ((t - 6.0) / 24.0) * 6.28318530718;
        float sunElev = sin(sunAngle);

        float dayFactor = clamp(sunElev * 1.5 + 0.3, 0.0, 1.0);
        float brightness = mix(0.22, 1.0, dayFactor);

        float sunsetFactor = smoothstep(-0.25, 0.15, sunElev) * smoothstep(0.65, 0.15, sunElev);

        vec3 nightTint = vec3(0.45, 0.55, 0.85);
        vec3 dayTint = vec3(1.0, 1.0, 1.0);
        vec3 sunsetTint = vec3(1.05, 0.75, 0.55);

        vec3 tint = mix(nightTint, dayTint, dayFactor);
        tint = mix(tint, sunsetTint, sunsetFactor * 0.8);

        result = result * tint * brightness;

        if (u_flash_intensity > 0.0)
        {
            result += texelColor.rgb * vec3(1.4, 1.1, 0.7) * u_flash_intensity * 0.75;
        }

        if (u_flashlight_active > 0.0)
        {
            float flash_dist = distance(fragTexCoord, vec2(0.5, 0.5));
            float spot = smoothstep(0.48, 0.05, flash_dist);
            result += texelColor.rgb * vec3(1.2, 1.15, 1.0) * spot * 1.5 * u_flashlight_active;
        }
    }

    if (u_rain_intensity > 0.0)
    {
        float rain_t = u_time * 3.0;
        float n1 = rain_layer(fragTexCoord * 2.0, rain_t);
        float n2 = rain_layer(fragTexCoord * 1.5 + vec2(0.3, 0.5), rain_t * 1.2);
        float rainVal = n1 + n2;

        result = mix(result, vec3(0.7, 0.8, 0.9), rainVal * u_rain_intensity * 0.4);
    }

    if (shadows_enabled != 0)
    {
        float dist = distance(fragTexCoord, vec2(0.5, 0.5));
        float vignette = smoothstep(0.8, 0.3, dist);
        result *= vignette;
    }

    if (u_bloom != 0)
    {
        vec2 offset = vec2(0.005, 0.005);
        vec3 sum = texture(texture0, fragTexCoord + vec2(offset.x, 0.0)).rgb +
                   texture(texture0, fragTexCoord - vec2(offset.x, 0.0)).rgb +
                   texture(texture0, fragTexCoord + vec2(0.0, offset.y)).rgb +
                   texture(texture0, fragTexCoord - vec2(0.0, offset.y)).rgb;
        sum *= 0.25;

        float lum = dot(sum, vec3(0.299, 0.587, 0.114));
        if (lum > 0.7)
        {
            result += sum * 0.5;
        }
    }

    finalColor = vec4(result, 1.0);
}
