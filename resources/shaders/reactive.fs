#version 330

in vec2 fragTexCoord;
in vec4 fragColor;

uniform sampler2D texture0;
uniform vec4 colDiffuse;

uniform float u_energy;
uniform float u_time;

out vec4 finalColor;

const vec2 resolution = vec2(480.0, 960.0);
const float unitSize = 40.0;

void main() {
    vec4 texel = texture(texture0, fragTexCoord);
    vec2 texelSize = 1.0 / resolution;

    // 1. Edge Detection on Tetris Blocks
    vec3 top    = texture(texture0, fragTexCoord + vec2(0.0, -texelSize.y)).rgb;
    vec3 bottom = texture(texture0, fragTexCoord + vec2(0.0, texelSize.y)).rgb;
    vec3 left   = texture(texture0, fragTexCoord + vec2(-texelSize.x, 0.0)).rgb;
    vec3 right  = texture(texture0, fragTexCoord + vec2(texelSize.x, 0.0)).rgb;

    float edge = length(abs(top - bottom) + abs(left - right));

    // Dynamic Cyan -> Magenta edge glow
    vec3 glowColor = mix(
        vec3(0.0, 0.8, 1.0), 
        vec3(1.0, 0.1, 0.6), 
        sin(u_time * 2.0 + fragTexCoord.y * 3.0) * 0.5 + 0.5
    );
    vec3 edgeGlow = glowColor * edge * (1.5 + u_energy * 6.0);

    // 2. Exact 45px Unit Background Grid
    vec2 pixelPos = fragTexCoord * resolution;
    vec2 gridUV = fract(pixelPos / unitSize);
    float gridLine = step(0.95, gridUV.x) + step(0.95, gridUV.y);
    vec3 bgGrid = vec3(0.04, 0.07, 0.15) * gridLine * (0.3 + u_energy * 1.5);

    // 3. Vertical Audio Wave (Background sweep)
    float wave = sin(fragTexCoord.y * 12.0 - u_time * 5.0) * 0.5 + 0.5;
    wave = pow(wave, 8.0) * u_energy * 0.4;
    vec3 bgWave = vec3(0.5, 0.1, 0.9) * wave;

    // 4. Composition
    bool isBackground = (length(texel.rgb) < 0.02);
    vec3 finalRGB = isBackground ? (bgGrid + bgWave) : (texel.rgb + edgeGlow);

    finalColor = vec4(finalRGB, texel.a) * colDiffuse;
}
