// Boot marker for debugging
try { console.info('[orb] main.js loaded'); } catch(_) {}

// === Three.js Scene Setup ===
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(
  75, window.innerWidth / window.innerHeight, 0.1, 1000
);
camera.position.set(0, 1, 7);
camera.lookAt(0, 0, 0);

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(window.devicePixelRatio);
renderer.setClearColor(0x111111, 1);
document.body.appendChild(renderer.domElement);

// Lighting
scene.add(new THREE.AmbientLight(0xffffff, 0.8));
const dirLight = new THREE.DirectionalLight(0xffffff, 1);
dirLight.position.set(5, 10, 7).normalize();
scene.add(dirLight);

// === Palette (match UI) ===
const UI_BLUE = 0x0064ff;   // like frame borders
const UI_CYAN = 0x00ffff;   // like "+" button & text

// === Shader Orb (blue->cyan pulse) ===
const orbUniforms = {
  time: { value: 0.0 },
  pulse: { value: 0.0 },
  baseColor:  { value: new THREE.Color(UI_BLUE) },
  accentColor:{ value: new THREE.Color(UI_CYAN) }
};

const orb = new THREE.Mesh(
  new THREE.SphereGeometry(0.5, 64, 64),
  new THREE.ShaderMaterial({
    uniforms: orbUniforms,
    vertexShader: `
      varying vec3 vNormal;
      void main() {
        vNormal = normalize(normalMatrix * normal);
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `,
    fragmentShader: `
      uniform float time;
      uniform float pulse;
      uniform vec3 baseColor;
      uniform vec3 accentColor;
      varying vec3 vNormal;

      void main() {
        // subtle moving light across the normal
        float moving = 0.5 + 0.5 * abs(dot(vNormal, normalize(vec3(sin(time*0.7), cos(time*0.9), 1.0))));
        // pulse pushes color towards cyan; otherwise stays closer to deep blue
        float mixAmt = mix(0.25, 1.0, pulse);
        vec3 color = mix(baseColor, accentColor, mixAmt);
        gl_FragColor = vec4(color * moving, 1.0);
      }
    `,
    side: THREE.DoubleSide
  })
);
orb.position.set(0, -1, 0);
scene.add(orb);

// === Glow Shell (cyan/blue additive glow) ===
const shell = new THREE.Mesh(
  new THREE.SphereGeometry(0.55, 64, 64),
  new THREE.ShaderMaterial({
    uniforms: {
      time: { value: 0.0 },
      baseColor:   { value: new THREE.Color(UI_BLUE) },
      accentColor: { value: new THREE.Color(UI_CYAN) }
    },
    transparent: true,
    side: THREE.BackSide,
    blending: THREE.AdditiveBlending,
    vertexShader: `
      varying vec3 vNormal;
      void main() {
        vNormal = normalize(normalMatrix * normal);
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `,
    fragmentShader: `
      uniform float time;
      uniform vec3 baseColor;
      uniform vec3 accentColor;
      varying vec3 vNormal;
      void main() {
        // shimmering rim-ish glow
        float rim = pow(1.0 - max(dot(vNormal, vec3(0.0,0.0,1.0)), 0.0), 1.2);
        float flicker = 0.25 + 0.25 * sin(time * 2.0 + dot(vNormal, vec3(0.0, 1.0, 0.0)) * 10.0);
        float a = clamp(rim + flicker, 0.0, 0.5);
        vec3 c = mix(baseColor, accentColor, 0.6);
        gl_FragColor = vec4(c, a);
      }
    `
  })
);
shell.position.set(0, -1, 0);
scene.add(shell);

// === Floating Glow Sprites (cyan radial) ===
function createGlowTexture() {
  const s = 128;
  const c = document.createElement('canvas');
  c.width = c.height = s;
  const g = c.getContext('2d');
  const r = s / 2;
  const grd = g.createRadialGradient(r, r, 0, r, r, r);
  grd.addColorStop(0.00, 'rgba(255,255,255,0.9)');
  grd.addColorStop(0.40, 'rgba(0,255,255,0.6)');   // cyan mid
  grd.addColorStop(1.00, 'rgba(0,180,255,0.0)');   // blue-cyan fade out
  g.fillStyle = grd;
  g.fillRect(0, 0, s, s);
  const tex = new THREE.Texture(c);
  tex.needsUpdate = true;
  return tex;
}
const glowTexture = createGlowTexture();

for (let i = 0; i < 3; i++) {
  const sprite = new THREE.Sprite(new THREE.SpriteMaterial({
    map: glowTexture,
    color: UI_CYAN,
    transparent: true,
    opacity: 0.25,
    depthWrite: false,
    blending: THREE.AdditiveBlending
  }));
  sprite.scale.set(2.2 + i * 0.3, 2.2 + i * 0.3, 1);
  sprite.position.set(0, -1, 0);
  scene.add(sprite);
}

// === Particle Shell with Animation (light blue) ===
const particleGeo = new THREE.BufferGeometry();
const count = 250;
const positions = [];
const sphericalData = [];

for (let i = 0; i < count; i++) {
  const theta = Math.random() * 2 * Math.PI;
  const phi = Math.acos(2 * Math.random() - 1);
  const baseR = 0.7 + Math.random() * 0.1;
  sphericalData.push({ theta, phi, baseR });

  const x = baseR * Math.sin(phi) * Math.cos(theta);
  const y = baseR * Math.sin(phi) * Math.sin(theta) - 1;
  const z = baseR * Math.cos(phi);
  positions.push(x, y, z);
}

particleGeo.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
particleGeo.userData.spherical = sphericalData;

const particleMat = new THREE.PointsMaterial({
  size: 0.04,
  color: 0x66ccff, // light blue particles
  transparent: true,
  opacity: 0.7,
  depthWrite: false,
  blending: THREE.AdditiveBlending
});

const particleSystem = new THREE.Points(particleGeo, particleMat);
scene.add(particleSystem);

// === Socket Handling ===
const socket = io();
window.socket = socket;
let speaking = false;
socket.on('speak_chunk', () => speaking = true);
socket.on('speak_end', () => speaking = false);

// Connection diagnostics
try {
  socket.on('connect', () => console.info('[orb] socket connected:', socket.id));
  socket.on('disconnect', (r) => console.warn('[orb] socket disconnected:', r));
  socket.io.on('error', (e) => console.error('[orb] io error:', e));
  socket.on('connect_error', (e) => console.error('[orb] connect_error:', e && e.message || e));
  socket.onAny((ev, ...args) => {
    if (ev !== 'video_frame') { // avoid spamming
      console.debug('[orb] event:', ev, args && args[0]);
    }
  });
} catch (_) {}

const logConsole = document.getElementById("log-console");
const logLines = [];
socket.on("INNEMONO_LINE", (data) => {
  if (!data.line) return;
  logLines.push(data.line);
  if (logLines.length > 10) logLines.shift();
  logConsole.innerHTML = logLines.map(line => `<div>${line}</div>`).join("");
  logConsole.scrollTop = logConsole.scrollHeight;
});

// === Map Pin Handler (force-visible cones + pulsing halo) ===
const activePins = [];
socket.on("EMIT_MAP_PIN", ({ lat, lon, label, description }) => {
  if (typeof lat !== 'number' || typeof lon !== 'number') return;
  console.log("📍 Map Pin:", label, lat, lon);
  try {
    if (logConsole) {
      const msg = `📍 ${label || 'Pin'} @ ${lat.toFixed(3)}, ${lon.toFixed(3)}${description? ' — '+description: ''}`;
      const div = document.createElement('div');
      div.textContent = msg;
      logConsole.appendChild(div);
      if (logConsole.children.length > 25) logConsole.removeChild(logConsole.firstChild);
      logConsole.scrollTop = logConsole.scrollHeight;
    }
  } catch (_) {}

  // Push outside the glow/particles so it’s clearly visible
  const radius = 0.70; // was 0.58
  const phi   = (90 - lat) * (Math.PI / 180);
  const theta = (lon + 180) * (Math.PI / 180);

  const x = radius * Math.sin(phi) * Math.cos(theta);
  const y = radius * Math.cos(phi) - 1; // orb center is y = -1
  const z = radius * Math.sin(phi) * Math.sin(theta);

  // Cone: render on top of everything (no depth test), slightly bigger, double-sided
  const pin = new THREE.Mesh(
    new THREE.ConeGeometry(0.10, 0.36, 16),
    new THREE.MeshBasicMaterial({
      color: 0xff0040,
      depthTest: false,
      depthWrite: false,
      transparent: true,
      opacity: 1.0,
      side: THREE.DoubleSide
    })
  );
  pin.position.set(x, y, z);
  pin.lookAt(0, -1, 0);
  pin.renderOrder = 1000;
  scene.add(pin);

  // Glow dot: also on top (pulses in animate)
  const dot = new THREE.Mesh(
    new THREE.SphereGeometry(0.09, 16, 16),
    new THREE.MeshBasicMaterial({
      color: 0xff6666,
      depthTest: false,
      depthWrite: false,
      transparent: true,
      opacity: 0.95
    })
  );
  dot.position.set(x, y, z);
  dot.renderOrder = 1000;
  scene.add(dot);

  activePins.push({ pin, dot, created: performance.now() });
});

// Simple debug helper to verify 3D pins without backend
window.debugOrbPin = function(lat, lon, label, description){
  socket.emit && console.debug('[debugOrbPin] adding local pin');
  socket.listeners && console.debug('[debugOrbPin]');
  socket.emit?.("__noop");
  // Reuse the same logic by emitting a synthetic event to our handler
  const evt = new Event('synthetic');
  // Call handler directly
  try { window.dispatchEvent(evt); } catch (_) {}
  // Duplicate minimal logic inline
  if (typeof lat !== 'number' || typeof lon !== 'number') return false;
  const radius = 0.70;
  const phi   = (90 - lat) * (Math.PI / 180);
  const theta = (lon + 180) * (Math.PI / 180);
  const x = radius * Math.sin(phi) * Math.cos(theta);
  const y = radius * Math.cos(phi) - 1;
  const z = radius * Math.sin(phi) * Math.sin(theta);
  const pin = new THREE.Mesh(
    new THREE.ConeGeometry(0.10, 0.36, 16),
    new THREE.MeshBasicMaterial({ color: 0xff0040, depthTest: false, depthWrite: false, transparent: true, opacity: 1.0, side: THREE.DoubleSide })
  );
  pin.position.set(x, y, z); pin.lookAt(0, -1, 0); pin.renderOrder = 1000; scene.add(pin);
  const dot = new THREE.Mesh(
    new THREE.SphereGeometry(0.09, 16, 16),
    new THREE.MeshBasicMaterial({ color: 0xff6666, depthTest: false, depthWrite: false, transparent: true, opacity: 0.95 })
  );
  dot.position.set(x, y, z); dot.renderOrder = 1000; scene.add(dot);
  activePins.push({ pin, dot, created: performance.now() });
  return true;
};


// === Animate ===
const clock = new THREE.Clock();
function animate() {
  requestAnimationFrame(animate);
  const t = clock.getElapsedTime();

  orbUniforms.time.value = t;
  // speaking drives the blue->cyan mix
  orbUniforms.pulse.value = speaking ? 1.0 : 0.0;
  shell.material.uniforms.time.value = t;

  const posAttr = particleGeo.attributes.position;
  const spherical = particleGeo.userData.spherical;

  for (let i = 0; i < count; i++) {
    const { theta, phi, baseR } = spherical[i];
    const r = baseR + 0.02 * Math.sin(t * 2.0 + i);
    const i3 = i * 3;
    posAttr.array[i3]     = r * Math.sin(phi) * Math.cos(theta);
    posAttr.array[i3 + 1] = r * Math.sin(phi) * Math.sin(theta) - 1;
    posAttr.array[i3 + 2] = r * Math.cos(phi);
  }
  posAttr.needsUpdate = true;

  // Pulse pin dots to draw attention
  if (activePins.length) {
    const pulse = 0.85 + 0.25 * (0.5 + 0.5 * Math.sin(t * 3.2));
    for (let i = 0; i < activePins.length; i++) {
      const ap = activePins[i];
      if (!ap || !ap.dot) continue;
      ap.dot.scale.set(pulse, pulse, pulse);
    }
  }

  renderer.render(scene, camera);
}
animate();

// === Resize ===
window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});
