#version 330

in vec2 fragTexCoord;
in vec4 fragColor;

uniform sampler2D texture0;

uniform float time_of_day;
uniform int lighting_quality;
uniform int shadows_enabled;

out vec4 finalColor;

void main()
{
    vec4 texelColor = texture(texture0, fragTexCoord);
    
    float brightness = 1.0;
    vec3 tint = vec3(1.0, 1.0, 1.0);
    
    if (time_of_day >= 0.0) {
        brightness = sin((time_of_day / 24.0) * 3.14159265);
        
        brightness = max(brightness, 0.2);
        
        if (time_of_day < 6.0 || time_of_day > 18.0) {
            tint = vec3(0.4, 0.5, 0.8);
        } else if (time_of_day < 8.0 || time_of_day > 16.0) {
            tint = vec3(1.0, 0.7, 0.5);
        }
    }
    
    vec3 result = texelColor.rgb * tint * brightness;
    
    if (shadows_enabled != 0) {
        float dist = distance(fragTexCoord, vec2(0.5, 0.5));
        float vignette = smoothstep(0.8, 0.3, dist);
        result *= vignette;
    }
    
    finalColor = vec4(result, texelColor.a);
}
