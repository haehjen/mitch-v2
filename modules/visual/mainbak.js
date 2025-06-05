// main.js

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
const renderer = new THREE.WebGLRenderer({ canvas: document.getElementById('scene'), antialias: true });

renderer.setSize(window.innerWidth, window.innerHeight);
document.body.appendChild(renderer.domElement);

// Lighting
const ambientLight = new THREE.AmbientLight(0x404040);
scene.add(ambientLight);
const directionalLight = new THREE.DirectionalLight(0xffffff, 1);
directionalLight.position.set(5, 5, 5).normalize();
scene.add(directionalLight);

// Orb: Heart core position
const orbGeometry = new THREE.SphereGeometry(0.5, 16, 16);
const orbMaterial = new THREE.MeshBasicMaterial({ color: 0x00ffff, wireframe: true });
const orb = new THREE.Mesh(orbGeometry, orbMaterial);
orb.position.set(0, 5, 0);
scene.add(orb);

// Ring below orb
const ringGeometry = new THREE.RingGeometry(0.6, 0.75, 64);
const ringMaterial = new THREE.MeshBasicMaterial({ color: 0x00ffff, side: THREE.DoubleSide });
const ring = new THREE.Mesh(ringGeometry, ringMaterial);
ring.rotation.x = -Math.PI / 2;
ring.position.set(0, 5, 0);
scene.add(ring);

// Wireframe Mitch with only normal cleanup
const loader = new THREE.OBJLoader();
loader.load('FinalBaseMesh.obj', function (object) {
  object.traverse(function (child) {
    if (child.isMesh) {
      child.material = new THREE.MeshBasicMaterial({ color: 0x00ccff, wireframe: true });
      child.geometry.computeVertexNormals(); // fix only normals, no geometry move
    }
  });

  object.scale.setScalar(0.3);
  object.position.set(0, 0.5, 1);
  scene.add(object);
}, undefined, function (error) {
  console.error('Error loading model:', error);
});

// Animate orb pulse
let clock = new THREE.Clock();
function animate() {
  requestAnimationFrame(animate);
  let t = clock.getElapsedTime();
  orb.scale.setScalar(1 + 0.1 * Math.sin(t * 4));
  renderer.render(scene, camera);
}

// Camera setup
camera.position.set(0, 6, 2.5);
camera.lookAt(0, 6, 0);
animate();

window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});
