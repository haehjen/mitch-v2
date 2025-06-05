const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(
  75, window.innerWidth / window.innerHeight, 0.1, 1000
);
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

// Orb
const orb = new THREE.Mesh(
  new THREE.SphereGeometry(0.5, 16, 16),
  new THREE.MeshBasicMaterial({ color: 0xd3d3d3, wireframe: true })
);
orb.position.set(0, -4, 0);
scene.add(orb);

// Ring
const stripeCanvas = document.createElement('canvas');
stripeCanvas.width = stripeCanvas.height = 512;
const stripeCtx = stripeCanvas.getContext('2d');
for (let i = 0; i < 512 / 20; i++) {
  stripeCtx.fillStyle = i % 2 === 0 ? '#ffffff' : '#0000ff';
  stripeCtx.fillRect(i * 20, 0, 20, 512);
}
const stripeTex = new THREE.CanvasTexture(stripeCanvas);
const ring = new THREE.Mesh(
  new THREE.RingGeometry(0.6, 0.75, 64),
  new THREE.MeshBasicMaterial({ map: stripeTex, side: THREE.DoubleSide })
);
ring.rotation.x = -Math.PI / 2;
ring.position.set(0, -4, 0);
scene.add(ring);

// === Load Mesh (Echo's head) ===
const loader = new THREE.OBJLoader();
loader.load('FinalBaseMesh.obj', function (object) {
  object.traverse(child => {
    if (child.isMesh) {
      console.log('🧩 Mesh:', child.name || '[unnamed]');
      child.material = new THREE.MeshBasicMaterial({
        color: 0x00ffff,
        wireframe: true,
        side: THREE.DoubleSide
      });

      child.geometry.computeBoundingBox();
      const center = new THREE.Vector3();
      child.geometry.boundingBox.getCenter(center);
      child.geometry.translate(-center.x, -center.y, -center.z);
    }
  });

  object.scale.setScalar(10);
  object.position.set(0, 0, 0);
  scene.add(object);

  camera.position.set(0, 1, 7);
  camera.lookAt(0, 0, 0);
}, undefined, err => {
  console.error('❌ Mesh load failed:', err);
});

// === Socket ring animation ===
let speaking = false;
const socket = io();
socket.on('speak_chunk', () => { speaking = true; });
socket.on('speak_end', () => { speaking = false; });

// === Animate loop ===
const clock = new THREE.Clock();
function animate() {
  requestAnimationFrame(animate);
  const t = clock.getElapsedTime();
  orb.scale.setScalar(1 + 0.1 * Math.sin(t * 4));
  if (speaking) ring.rotation.y += 0.05;
  renderer.render(scene, camera);
}
animate();

// === Resize handler ===
window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});
