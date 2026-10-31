/**
 * dashboard/beams.js
 * -------------------
 * Official WebGL2 Beams engine from @react-bits/Beams-TS-TW (React Bits).
 * Glossy ribbons that ripple in the dark and catch the light following the cursor.
 * 100% local, dependency-free WebGL2 shader implementation.
 */

(function (global) {
  const QUAD_VERTEX = `#version 300 es
in vec2 aPosition;
void main() {
  gl_Position = vec4(aPosition, 0.0, 1.0);
}`;

  const FIELD = `#version 300 es
precision highp float;
uniform vec2 uView;
uniform vec2 uScale;
uniform vec2 uTurn;
uniform float uTime;
uniform float uWidth;
uniform float uWave;
uniform float uDepth;
uniform float uRough;
uniform float uSeed;
uniform float uTwist;
uniform vec3 uLight;
uniform float uFill;
uniform float uCamera;
uniform vec4 uPointer;
out vec4 outColor;

const float PI = 3.141592653589793;

vec4 permute(vec4 x) {
  return mod(((x * 34.0) + 1.0) * x, 289.0);
}

vec4 taylorInvSqrt(vec4 r) {
  return 1.79284291400159 - 0.85373472095314 * r;
}

vec3 fade(vec3 t) {
  return t * t * t * (t * (t * 6.0 - 15.0) + 10.0);
}

float cnoise(vec3 P) {
  vec3 Pi0 = floor(P);
  vec3 Pi1 = Pi0 + vec3(1.0);
  Pi0 = mod(Pi0, 289.0);
  Pi1 = mod(Pi1, 289.0);
  vec3 Pf0 = fract(P);
  vec3 Pf1 = Pf0 - vec3(1.0);
  vec4 ix = vec4(Pi0.x, Pi1.x, Pi0.x, Pi1.x);
  vec4 iy = vec4(Pi0.yy, Pi1.yy);
  vec4 iz0 = Pi0.zzzz;
  vec4 iz1 = Pi1.zzzz;
  vec4 ixy = permute(permute(ix) + iy);
  vec4 ixy0 = permute(ixy + iz0);
  vec4 ixy1 = permute(ixy + iz1);
  vec4 gx0 = ixy0 / 7.0;
  vec4 gy0 = fract(floor(gx0) / 7.0) - 0.5;
  gx0 = fract(gx0);
  vec4 gz0 = vec4(0.5) - abs(gx0) - abs(gy0);
  vec4 sz0 = step(gz0, vec4(0.0));
  gx0 -= sz0 * (step(0.0, gx0) - 0.5);
  gy0 -= sz0 * (step(0.0, gy0) - 0.5);
  vec4 gx1 = ixy1 / 7.0;
  vec4 gy1 = fract(floor(gx1) / 7.0) - 0.5;
  gx1 = fract(gx1);
  vec4 gz1 = vec4(0.5) - abs(gx1) - abs(gy1);
  vec4 sz1 = step(gz1, vec4(0.0));
  gx1 -= sz1 * (step(0.0, gx1) - 0.5);
  gy1 -= sz1 * (step(0.0, gy1) - 0.5);
  vec3 g000 = vec3(gx0.x, gy0.x, gz0.x);
  vec3 g100 = vec3(gx0.y, gy0.y, gz0.y);
  vec3 g010 = vec3(gx0.z, gy0.z, gz0.z);
  vec3 g110 = vec3(gx0.w, gy0.w, gz0.w);
  vec3 g001 = vec3(gx1.x, gy1.x, gz1.x);
  vec3 g101 = vec3(gx1.y, gy1.y, gz1.y);
  vec3 g011 = vec3(gx1.z, gy1.z, gz1.z);
  vec3 g111 = vec3(gx1.w, gy1.w, gz1.w);
  vec4 norm0 = taylorInvSqrt(vec4(dot(g000, g000), dot(g010, g010), dot(g100, g100), dot(g110, g110)));
  g000 *= norm0.x;
  g010 *= norm0.y;
  g100 *= norm0.z;
  g110 *= norm0.w;
  vec4 norm1 = taylorInvSqrt(vec4(dot(g001, g001), dot(g011, g011), dot(g101, g101), dot(g111, g111)));
  g001 *= norm1.x;
  g011 *= norm1.y;
  g101 *= norm1.z;
  g111 *= norm1.w;
  float n000 = dot(g000, Pf0);
  float n100 = dot(g100, vec3(Pf1.x, Pf0.yz));
  float n010 = dot(g010, vec3(Pf0.x, Pf1.y, Pf0.z));
  float n110 = dot(g110, vec3(Pf1.xy, Pf0.z));
  float n001 = dot(g001, vec3(Pf0.xy, Pf1.z));
  float n101 = dot(g101, vec3(Pf1.x, Pf0.y, Pf1.z));
  float n011 = dot(g011, vec3(Pf0.x, Pf1.yz));
  float n111 = dot(g111, Pf1);
  vec3 fade_xyz = fade(Pf0);
  vec4 n_z = mix(vec4(n000, n100, n010, n110), vec4(n001, n101, n011, n111), fade_xyz.z);
  vec2 n_yz = mix(n_z.xy, n_z.zw, fade_xyz.y);
  float n_xyz = mix(n_yz.x, n_yz.y, fade_xyz.x);
  return 2.2 * n_xyz;
}

float laneHash(float lane, float seed) {
  return fract(sin(lane * 91.3458 + seed * 17.17) * 47453.5453);
}

float lobe(float nh, float nl, float nv, float vh, float roughness) {
  float a = roughness * roughness;
  float a2 = a * a;
  float d = nh * nh * (a2 - 1.0) + 1.0;
  float distribution = a2 / (PI * d * d);
  float gv = nl * sqrt(nv * nv * (1.0 - a2) + a2);
  float gl = nv * sqrt(nl * nl * (1.0 - a2) + a2);
  float visibility = 0.5 / max(gv + gl, 0.0001);
  float fresnel = 0.028 + 0.972 * pow(1.0 - vh, 5.0);
  return distribution * visibility * fresnel * nl;
}

vec2 glint(float lane, vec2 local, float wave, float depth, float time, float twist, float rough, vec3 light, float fill, float camera, float seed) {
  float along = local.y / wave - laneHash(lane, seed) * 60.0;
  float stepVal = 0.01;
  float slope = (cnoise(vec3(0.0, along + stepVal, time)) - cnoise(vec3(0.0, along - stepVal, time))) / (2.0 * stepVal);
  slope *= 0.2 * depth;
  float spin = laneHash(lane + 0.37, seed);
  float tilt = ((spin - 0.5) * 0.5 + sin(time * 2.1 + spin * 6.2831) * 0.06) * twist;
  vec3 normal = normalize(vec3(tilt, -slope, 1.0));
  vec3 view = normalize(vec3(-local, camera));
  float nv = max(dot(normal, view), 0.0001);
  vec3 l = normalize(light);
  vec3 halfway = normalize(l + view);
  float core = lobe(max(dot(normal, halfway), 0.0), max(dot(normal, l), 0.0), nv, max(dot(view, halfway), 0.0), rough);
  vec3 fillL = normalize(vec3(0.0, -light.y * 1.25, light.z));
  vec3 fillHalf = normalize(fillL + view);
  core += fill * lobe(max(dot(normal, fillHalf), 0.0), max(dot(normal, fillL), 0.0), nv, max(dot(view, fillHalf), 0.0), rough);
  return vec2(core, core);
}

void main() {
  vec2 css = gl_FragCoord.xy * uScale;
  vec2 centered = css - uView * 0.5;
  vec2 local = mat2(uTurn.x, -uTurn.y, uTurn.y, uTurn.x) * centered;

  float across = local.x / uWidth + 0.5;
  float lane = floor(across);
  float u = across - lane;

  vec2 value = glint(lane, local, uWave, uDepth, uTime, uTwist, uRough, uLight, uFill, uCamera, uSeed);

  float pixel = max(uScale.x, uScale.y);
  float seam = min(u, 1.0 - u) * uWidth;
  if (seam < pixel * 1.5) {
    float other = u < 0.5 ? lane - 1.0 : lane + 1.0;
    float blend = 0.5 * (1.0 - smoothstep(0.0, pixel * 1.5, seam));
    value = mix(value, glint(other, local, uWave, uDepth, uTime, uTwist, uRough, uLight, uFill, uCamera, uSeed), blend);
  }

  vec2 toPointer = css - uPointer.xy;
  float near = exp(-dot(toPointer, toPointer) / (2.0 * uPointer.w * uPointer.w)) * uPointer.z;
  value *= 1.0 + near * 0.8;
  float hot = max(value.y - 0.18, 0.0);
  outColor = vec4(value.x, value.y, min(hot, 6.0), 1.0);
}`;

  const COMPOSITE = `#version 300 es
precision highp float;
uniform sampler2D uField;
uniform vec2 uResolution;
uniform vec3 uColor;
uniform vec3 uInk;
uniform float uGain;
uniform float uGlow;
uniform float uPresence;
uniform float uGrain;
uniform float uFade;
uniform float uOpacity;
uniform float uLightMode;
out vec4 outColor;

float random(vec2 st) {
  return fract(sin(dot(st, vec2(12.9898, 78.233))) * 43758.5453123);
}

float grainNoise(vec2 st) {
  vec2 i = floor(st);
  vec2 f = fract(st);
  float a = random(i);
  float b = random(i + vec2(1.0, 0.0));
  float c = random(i + vec2(0.0, 1.0));
  float d = random(i + vec2(1.0, 1.0));
  vec2 u = f * f * (3.0 - 2.0 * f);
  return mix(a, b, u.x) + (c - a) * u.y * (1.0 - u.x) + (d - b) * u.x * u.y;
}

vec3 acesFilmic(vec3 color) {
  const mat3 inputMatrix = mat3(
    vec3(0.59719, 0.07600, 0.02840),
    vec3(0.35458, 0.90834, 0.13383),
    vec3(0.04823, 0.01566, 0.83777)
  );
  const mat3 outputMatrix = mat3(
    vec3(1.60475, -0.10208, -0.00327),
    vec3(-0.53108, 1.10813, -0.07276),
    vec3(-0.07367, -0.00605, 1.07602)
  );
  color = inputMatrix * (color / 0.6);
  vec3 a = color * (color + 0.0245786) - 0.000090537;
  vec3 b = color * (0.983729 * color + 0.4329510) + 0.238081;
  color = outputMatrix * (a / b);
  return clamp(color, 0.0, 1.0);
}

vec3 toSrgb(vec3 color) {
  return mix(color * 12.92, 1.055 * pow(color, vec3(1.0 / 2.4)) - 0.055, step(vec3(0.0031308), color));
}

float feather(float x, float edge) {
  float t = clamp(x / max(edge, 0.0001), 0.0, 1.0);
  return t * t * t * (t * (t * 6.0 - 15.0) + 10.0);
}

void main() {
  vec2 uv = gl_FragCoord.xy / uResolution;
  float radiance = textureLod(uField, uv, 0.0).r;
  float bloom = 0.0;
  bloom += textureLod(uField, uv, 2.0).b * 0.3;
  bloom += textureLod(uField, uv, 3.0).b * 0.3;
  bloom += textureLod(uField, uv, 4.0).b * 0.22;
  bloom += textureLod(uField, uv, 5.0).b * 0.18;

  float hot = textureLod(uField, uv, 0.0).g;
  vec3 light = uColor * (radiance + bloom * uGlow) * uGain;
  light += mix(uColor, vec3(1.0), 0.7) * hot * hot * 0.12 * uGain;
  light *= uPresence;
  vec3 color = toSrgb(acesFilmic(light));
  color -= grainNoise(gl_FragCoord.xy) / 15.0 * uGrain;
  color = max(color, 0.0);

  float edge = uFade * 0.5;
  float mask = feather(uv.x, edge) * feather(1.0 - uv.x, edge) * feather(uv.y, edge) * feather(1.0 - uv.y, edge);
  mask *= uOpacity;
  float dither = (random(gl_FragCoord.yx + 31.7) - 0.5) / 255.0;

  color = clamp(color + dither, 0.0, 1.0) * mask;
  outColor = vec4(color, max(color.r, max(color.g, color.b)));
}`;

  const INTRO_SECONDS = 1.6;
  const MAX_FIELD_PIXELS = 1600000;
  const clamp = (v, min, max) => Math.min(max, Math.max(min, v));

  const compileShader = (gl, type, source) => {
    const s = gl.createShader(type);
    if (!s) return null;
    gl.shaderSource(s, source);
    gl.compileShader(s);
    if (gl.getShaderParameter(s, gl.COMPILE_STATUS)) return s;
    console.warn("Shader compile error:", gl.getShaderInfoLog(s));
    gl.deleteShader(s);
    return null;
  };

  const linkProgram = (gl, fragmentSource) => {
    const v = compileShader(gl, gl.VERTEX_SHADER, QUAD_VERTEX);
    const f = compileShader(gl, gl.FRAGMENT_SHADER, fragmentSource);
    const p = gl.createProgram();
    if (!v || !f || !p) return null;
    gl.attachShader(p, v);
    gl.attachShader(p, f);
    gl.bindAttribLocation(p, 0, 'aPosition');
    gl.linkProgram(p);
    gl.deleteShader(v);
    gl.deleteShader(f);
    if (!gl.getProgramParameter(p, gl.LINK_STATUS)) {
      console.warn("Program link error:", gl.getProgramInfoLog(p));
      gl.deleteProgram(p);
      return null;
    }
    const uniforms = {};
    const count = gl.getProgramParameter(p, gl.ACTIVE_UNIFORMS);
    for (let i = 0; i < count; i++) {
      const info = gl.getActiveUniform(p, i);
      if (info) uniforms[info.name] = gl.getUniformLocation(p, info.name);
    }
    return { program: p, uniforms };
  };

  function initBeams(canvasId, userOptions) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return null;

    const gl = canvas.getContext('webgl2', {
      alpha: true,
      premultipliedAlpha: true,
      antialias: false,
      depth: false,
      stencil: false,
      powerPreference: 'high-performance'
    });

    if (!gl) {
      console.warn("WebGL2 not supported, Beams fallback active.");
      return null;
    }

    const opts = Object.assign({
      color: '#ffffff',
      beamWidth: 170,
      rotation: 30,
      speed: 0.85,
      waveLength: 220,
      depth: 1.25,
      sharpness: 0.65,
      twist: 0.15,
      fillLight: 0.45,
      glow: 0.85,
      brightness: 2.0,
      variation: 0,
      grain: 0.18,
      quality: 0.85,
      mouseInteraction: true,
      mouseStrength: 1.0,
      intro: true,
      fade: 0.05,
      opacity: 0.85
    }, userOptions || {});

    const floatTargets = !!gl.getExtension('EXT_color_buffer_float');
    const fieldProgram = linkProgram(gl, FIELD);
    const compositeProgram = linkProgram(gl, COMPOSITE);
    if (!fieldProgram || !compositeProgram) return null;

    const buffer = gl.createBuffer();
    const vao = gl.createVertexArray();
    gl.bindVertexArray(vao);
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
    gl.enableVertexAttribArray(0);
    gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);

    let texture = null;
    const framebuffer = gl.createFramebuffer();
    const target = { width: 0, height: 0 };
    const sizeTarget = (w, h) => {
      if (target.width === w && target.height === h) return;
      target.width = w;
      target.height = h;
      if (texture) gl.deleteTexture(texture);
      texture = gl.createTexture();
      gl.bindTexture(gl.TEXTURE_2D, texture);
      const levels = Math.floor(Math.log2(Math.max(w, h))) + 1;
      gl.texStorage2D(gl.TEXTURE_2D, levels, floatTargets ? gl.RGBA16F : gl.RGBA8, w, h);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
      gl.bindFramebuffer(gl.FRAMEBUFFER, framebuffer);
      gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, texture, 0);
    };

    const probe = document.createElement('canvas').getContext('2d', { willReadFrequently: true });
    const toLinear = (hex) => {
      if (!probe) return [0.5, 0.55, 0.97];
      probe.clearRect(0, 0, 1, 1);
      probe.fillStyle = hex;
      probe.fillRect(0, 0, 1, 1);
      const d = probe.getImageData(0, 0, 1, 1).data;
      return [Math.pow(d[0] / 255, 2.2), Math.pow(d[1] / 255, 2.2), Math.pow(d[2] / 255, 2.2)];
    };

    const view = { width: 1, height: 1, fieldWidth: 1, fieldHeight: 1 };
    const pointer = { x: 0, y: 0, inside: false };
    const state = { clock: 0, intro: 0, reach: 0, x: 0, y: 0, lightY: 0 };
    let raf = 0;
    let last = 0;

    const render = () => {
      const presence = state.intro * state.intro * state.intro * (state.intro * (state.intro * 6 - 15) + 10);
      gl.bindVertexArray(vao);
      sizeTarget(view.fieldWidth, view.fieldHeight);

      const angle = (opts.rotation * Math.PI) / 180;
      const sweep = (1 - presence) * -9;
      const reach = state.reach * opts.mouseStrength;
      const f = fieldProgram.uniforms;
      gl.bindFramebuffer(gl.FRAMEBUFFER, framebuffer);
      gl.viewport(0, 0, target.width, target.height);
      gl.useProgram(fieldProgram.program);
      gl.uniform2f(f.uView, view.width, view.height);
      gl.uniform2f(f.uScale, view.width / target.width, view.height / target.height);
      gl.uniform2f(f.uTurn, Math.cos(angle), Math.sin(angle));
      gl.uniform1f(f.uTime, (state.clock * 0.12) % 289);
      gl.uniform1f(f.uWidth, opts.beamWidth);
      gl.uniform1f(f.uWave, opts.waveLength);
      gl.uniform1f(f.uDepth, opts.depth);
      gl.uniform1f(f.uRough, 0.55 - opts.sharpness * 0.5);
      gl.uniform1f(f.uSeed, opts.variation);
      gl.uniform1f(f.uTwist, opts.twist);
      gl.uniform1f(f.uFill, opts.fillLight);
      gl.uniform3f(f.uLight, 0, 3 + sweep + state.lightY * reach, 10);
      gl.uniform1f(f.uCamera, view.height * 1.866);
      gl.uniform4f(f.uPointer, state.x, view.height - state.y, reach, Math.max(view.height, view.width) * 0.28);
      gl.drawArrays(gl.TRIANGLES, 0, 3);
      gl.bindTexture(gl.TEXTURE_2D, texture);
      gl.generateMipmap(gl.TEXTURE_2D);

      const c = compositeProgram.uniforms;
      const tint = toLinear(opts.color);
      const tone = 0.2126 * tint[0] + 0.7152 * tint[1] + 0.0722 * tint[2];
      const shadeDepth = Math.min(1, 0.18 / Math.max(tone, 0.001));
      const ink = tint.map(v => Math.pow(Math.min(1, v * shadeDepth), 1 / 2.2));
      gl.bindFramebuffer(gl.FRAMEBUFFER, null);
      gl.viewport(0, 0, canvas.width, canvas.height);
      gl.useProgram(compositeProgram.program);
      gl.uniform2f(c.uResolution, canvas.width, canvas.height);
      gl.uniform3fv(c.uColor, tint);
      gl.uniform3fv(c.uInk, ink);
      gl.uniform1f(c.uGain, opts.brightness);
      gl.uniform1f(c.uGlow, opts.glow);
      gl.uniform1f(c.uPresence, presence);
      gl.uniform1f(c.uGrain, opts.grain * 1.75);
      gl.uniform1f(c.uFade, opts.fade);
      gl.uniform1f(c.uOpacity, opts.opacity);
      gl.uniform1f(c.uLightMode, 0);
      gl.activeTexture(gl.TEXTURE0);
      gl.bindTexture(gl.TEXTURE_2D, texture);
      gl.uniform1i(c.uField, 0);
      gl.drawArrays(gl.TRIANGLES, 0, 3);
    };

    const frame = (now) => {
      raf = 0;
      if (document.hidden) return;
      const dt = last ? Math.min(0.05, (now - last) / 1000) : 1 / 60;
      last = now;
      state.clock += dt * opts.speed;
      if (state.intro < 1) state.intro = Math.min(1, state.intro + dt / INTRO_SECONDS);

      const engaged = opts.mouseInteraction && pointer.inside;
      if (engaged && state.reach < 0.01) {
        state.x = pointer.x;
        state.y = pointer.y;
      }
      const follow = 1 - Math.exp(-dt * 7);
      state.x += (pointer.x - state.x) * follow;
      state.y += (pointer.y - state.y) * follow;
      state.reach += ((engaged ? 1 : 0) - state.reach) * (1 - Math.exp(-dt * (engaged ? 3.2 : 1.8)));
      const turn = (opts.rotation * Math.PI) / 180;
      const offsetX = state.x - view.width / 2;
      const offsetY = view.height / 2 - state.y;
      const along = -Math.sin(turn) * offsetX + Math.cos(turn) * offsetY;
      state.lightY = clamp((along / (view.height * 0.5)) * 3, -4, 4);
      render();

      raf = requestAnimationFrame(frame);
    };

    const resize = () => {
      const w = window.innerWidth;
      const h = window.innerHeight;
      const ratio = Math.min(window.devicePixelRatio || 1, 2);
      view.width = w;
      view.height = h;
      canvas.width = Math.max(1, Math.round(w * ratio));
      canvas.height = Math.max(1, Math.round(h * ratio));
      let fieldScale = opts.quality * ratio;
      if (w * h * fieldScale * fieldScale > MAX_FIELD_PIXELS) {
        fieldScale = Math.sqrt(MAX_FIELD_PIXELS / (w * h));
      }
      view.fieldWidth = Math.max(1, Math.round(w * fieldScale));
      view.fieldHeight = Math.max(1, Math.round(h * fieldScale));
      render();
    };

    window.addEventListener('resize', resize);
    window.addEventListener('pointermove', (e) => {
      pointer.x = e.clientX;
      pointer.y = e.clientY;
      pointer.inside = true;
    }, { passive: true });
    document.documentElement.addEventListener('pointerleave', () => {
      pointer.inside = false;
    });

    resize();
    raf = requestAnimationFrame(frame);

    return {
      destroy: () => {
        cancelAnimationFrame(raf);
        window.removeEventListener('resize', resize);
      }
    };
  }

  global.initReactBitsBeams = initBeams;
})(window);

