#version 330

in vec2 fragTexCoord;
in vec4 fragColor;

uniform sampler2D texture0;
uniform vec4 colDiffuse;

uniform float u_energy;
uniform float u_time;

uniform float u_impactPulse;    // Triggers screen shake & glow spike on block set
uniform float u_clearPulse;     // Triggers row flash on line clear
uniform float u_clearRowY;      // Normalized Y coord (0..1) of cleared row

// Teto / Tetoris Warm Yellow Glow Default
uniform vec3 u_glowColor = vec3(1.0, 0.9, 0.2);

out vec4 finalColor;

const vec2 resolution = vec2(480.0, 960.0);
const float unitSize   = 48.0;

const vec3 BG_BLACK    = vec3(0.04, 0.02, 0.03);
const vec3 GRID_ACCENT = vec3(0.85, 0.15, 0.3);

void main() {
    float smoothEnergy = pow(clamp(u_energy, 0.0, 1.0), 2.0);

    // 0. High-Energy Impact Threshold
    const float ENERGY_THRESHOLD = 0.0;
    // float impactFactor = smoothstep(ENERGY_THRESHOLD, 1.0, u_energy);
    float impactFactor = u_energy;

    // 1. Apparent & Crisp Grid Lines with Audio Wave Modulation
    vec2 pixelPos   = fragTexCoord * resolution;
    vec2 gridUV     = fract(pixelPos / unitSize);
    vec2 distToEdge = min(gridUV, 1.0 - gridUV) * unitSize;
    float minDist   = min(distToEdge.x, distToEdge.y);

    // Sharper, thicker grid lines for strong scannability
    float gridLine  = 1.0 - smoothstep(0.5, 2.5, minDist);

    float wave = sin(fragTexCoord.y * 5.0 - u_time * 5.0) * 0.5 + 0.5;
    wave = pow(wave, 6.0) * (0.2 + smoothEnergy * 0.5);

    // Static base opacity (0.15) ensures grid is always clear & visible
    vec3 bgGrid  = GRID_ACCENT * (0.15 + wave * 0.85) * gridLine;
    vec3 bgFinal = BG_BLACK + bgGrid;

    // 2. Smooth Continuous Harmonic Screen Shake (Beat + Impact combined)
    float totalImpact = max(impactFactor, u_impactPulse * 1.2);

    vec2 smoothShakeDir = vec2(
        sin(u_time * 22.0) * cos(u_time * 11.0),
        cos(u_time * 17.0) * sin(u_time * 13.0)
    );

    float beatShakeIntensity = smoothEnergy * 0.0035;
    float impactDecay = exp(-4.0 * (1.0 - clamp(totalImpact, 0.0, 1.0)));
    float impactShakeIntensity = totalImpact * 0.0075 * impactDecay;

    vec2 totalShake = smoothShakeDir * (beatShakeIntensity + impactShakeIntensity);
    vec2 shakenUV   = fragTexCoord + totalShake;

    // 3. Block Sampling & Edge Glow
    vec4 texel     = texture(texture0, shakenUV);
    vec2 texelSize = 1.0 / resolution;

    vec3 top    = texture(texture0, shakenUV + vec2(0.0, -texelSize.y)).rgb;
    vec3 bottom = texture(texture0, shakenUV + vec2(0.0,  texelSize.y)).rgb;
    vec3 left   = texture(texture0, shakenUV + vec2(-texelSize.x, 0.0)).rgb;
    vec3 right  = texture(texture0, shakenUV + vec2( texelSize.x, 0.0)).rgb;

    float edge = length(abs(top - bottom) + abs(left - right));
    vec3 edgeGlow   = u_glowColor * edge * (0.5 + totalImpact * 1.0);
    vec3 blockFinal = texel.rgb + edgeGlow;

    // 4. Line Clear Horizontal Red & Yellow Flash
    float targetY = 1.0 - u_clearRowY;
    float rowDist = abs(fragTexCoord.y - targetY);
    float lineFlashWidth = 0.03 * u_clearPulse;
    float lineBeam = smoothstep(lineFlashWidth, 0.0, rowDist) * u_clearPulse;

    // Vibrant Teto Crimson & Yellow Core Flash
    vec3 lineClearGlow = vec3(1.0, 0.16, 0.3) * lineBeam * 2.8 + vec3(1.0, 0.9, 0.2) * pow(lineBeam, 2.0) * 2.0;

    // 5. Final Composition
    bool isBackground = (length(texel.rgb) < 0.02);
    vec3 finalRGB     = isBackground ? bgFinal : blockFinal;

    finalRGB += lineClearGlow;

    finalColor = vec4(finalRGB, texel.a) * colDiffuse;
}
