// ============================================================
// 3D GAME IN JAVASCRIPT — Three.js Tutorial
// ============================================================
// Three.js works with 3 core objects you always need:
//   SCENE    — the 3D world that holds everything
//   CAMERA   — your viewpoint into that world
//   RENDERER — draws the scene to the canvas each frame
// ============================================================

// ============================================================
// CONCEPT 1: SCENE
// Think of it as an empty stage. You add objects to it.
// ============================================================

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x1a1a2e);  // dark navy
scene.fog = new THREE.Fog(0x1a1a2e, 20, 60);   // fog fades distant objects

// ============================================================
// CONCEPT 2: CAMERA
// PerspectiveCamera mimics how human eyes work — things further
// away look smaller. Parameters: fov, aspect ratio, near, far.
//   fov   — field of view in degrees (75 is natural-feeling)
//   near  — anything closer than this is invisible
//   far   — anything further than this is invisible
// ============================================================

const camera = new THREE.PerspectiveCamera(
  75,                                       // field of view
  window.innerWidth / window.innerHeight,   // aspect ratio
  0.1,                                      // near clipping plane
  100                                       // far clipping plane
);
camera.position.set(0, 8, 12);  // x=0, y=8 (above), z=12 (behind)
camera.lookAt(0, 0, 0);         // aim at the centre of the world

// ============================================================
// CONCEPT 3: RENDERER
// Renders (draws) the scene to a <canvas> in the browser.
// antialias: true smooths jagged edges.
// ============================================================

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.shadowMap.enabled = true;   // enable shadows
document.body.appendChild(renderer.domElement); // add canvas to page

// Handle window resize
window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});

// ============================================================
// CONCEPT 4: LIGHTS
// Without light, everything is black.
// AmbientLight — flat light from everywhere (no shadows)
// DirectionalLight — like the sun, casts shadows
// ============================================================

const ambientLight = new THREE.AmbientLight(0xffffff, 0.4);
scene.add(ambientLight);

const sunLight = new THREE.DirectionalLight(0xffffff, 0.8);
sunLight.position.set(10, 20, 10);
sunLight.castShadow = true;
// Shadow camera controls how large an area casts shadows
sunLight.shadow.camera.left   = -20;
sunLight.shadow.camera.right  =  20;
sunLight.shadow.camera.top    =  20;
sunLight.shadow.camera.bottom = -20;
scene.add(sunLight);

// ============================================================
// CONCEPT 5: GEOMETRY + MATERIAL + MESH
// Every 3D object in Three.js is a Mesh made of two parts:
//   Geometry — the SHAPE (where the vertices/triangles are)
//   Material  — the SURFACE (colour, texture, shininess)
// ============================================================

// --- PLATFORM (a flat box) ---
const platformGeo = new THREE.BoxGeometry(18, 0.5, 18);
const platformMat = new THREE.MeshStandardMaterial({
  color: 0x0f3460,
  roughness: 0.8,
});
const platform = new THREE.Mesh(platformGeo, platformMat);
platform.receiveShadow = true;
platform.position.y = -0.25; // sit it just below y=0
scene.add(platform);

// Draw a subtle grid on the platform
const gridHelper = new THREE.GridHelper(18, 18, 0x4ecca3, 0x4ecca3);
gridHelper.material.opacity = 0.15;
gridHelper.material.transparent = true;
scene.add(gridHelper);

// --- PLAYER BALL ---
// SphereGeometry(radius, widthSegments, heightSegments)
// More segments = rounder sphere (but heavier to render)
const ballGeo = new THREE.SphereGeometry(0.5, 32, 32);
const ballMat = new THREE.MeshStandardMaterial({
  color: 0x4ecca3,
  roughness: 0.3,
  metalness: 0.5,
});
const ball = new THREE.Mesh(ballGeo, ballMat);
ball.castShadow = true;
ball.position.set(0, 0.5, 0); // rest on the platform
scene.add(ball);

// ============================================================
// CONCEPT 6: 3D COORDINATES
// Three.js uses a right-hand coordinate system:
//   X — left / right
//   Y — down / up
//   Z — towards you / away from you
// So to move something "forward" on a flat platform, you
// change Z. To move "right", change X. Y is up/down.
// ============================================================

// ============================================================
// CONCEPT 7: CREATING MULTIPLE OBJECTS (GEM PICKUPS)
// ============================================================

const GEM_COUNT = 8;
const gems = [];

function createGem(x, z) {
  // OctahedronGeometry makes a diamond/gem shape
  const geo = new THREE.OctahedronGeometry(0.35);
  const mat = new THREE.MeshStandardMaterial({
    color: 0xe94560,
    emissive: 0xe94560,     // emissive = glows even without direct light
    emissiveIntensity: 0.3,
    roughness: 0.1,
    metalness: 0.8,
  });
  const gem = new THREE.Mesh(geo, mat);
  gem.castShadow = true;
  gem.position.set(x, 0.8, z);
  scene.add(gem);
  gems.push(gem);
}

// Place gems around the platform
const positions = [
  [-6, -6], [6, -6], [-6, 6], [6, 6],
  [0, -7],  [0,  7], [-7, 0], [7, 0],
];
positions.forEach(([x, z]) => createGem(x, z));

// Point lights near gems make them glow
gems.forEach(gem => {
  const light = new THREE.PointLight(0xe94560, 0.6, 4);
  light.position.copy(gem.position);
  scene.add(light);
});

// ============================================================
// CONCEPT 8: INPUT HANDLING (same idea as 2D)
// ============================================================

const keys = {};
document.addEventListener('keydown', e => {
  keys[e.key] = true;
  // Hide the start message on first keypress
  document.getElementById('message').style.display = 'none';
});
document.addEventListener('keyup',   e => keys[e.key] = false);

// ============================================================
// CONCEPT 9: GAME STATE
// ============================================================

let gemsCollected = 0;
const SPEED        = 0.1;
const FALL_LIMIT   = -5;    // if ball falls below this, game over

const velocity = new THREE.Vector3(); // current movement

// ============================================================
// CONCEPT 10: THE GAME LOOP (same pattern as 2D, different API)
// renderer.render(scene, camera) replaces ctx.fillRect etc.
// ============================================================

const clock = new THREE.Clock(); // Three.js helper for delta time

function gameLoop() {
  requestAnimationFrame(gameLoop);

  const delta = clock.getDelta(); // seconds since last frame

  update(delta);
  render();
}

function update(delta) {
  // --- PLAYER MOVEMENT ---
  // Build a direction vector from keys held
  const dir = new THREE.Vector3();

  if (keys['ArrowUp']    || keys['w'] || keys['W']) dir.z -= 1;
  if (keys['ArrowDown']  || keys['s'] || keys['S']) dir.z += 1;
  if (keys['ArrowLeft']  || keys['a'] || keys['A']) dir.x -= 1;
  if (keys['ArrowRight'] || keys['d'] || keys['D']) dir.x += 1;

  // Normalise so diagonal movement isn't faster
  if (dir.length() > 0) dir.normalize();

  // Apply movement (scaled by speed and delta for frame-rate independence)
  ball.position.x += dir.x * SPEED * 60 * delta;
  ball.position.z += dir.z * SPEED * 60 * delta;

  // Roll the ball visually based on movement
  ball.rotation.x += dir.z * SPEED * 3;
  ball.rotation.z -= dir.x * SPEED * 3;

  // --- GRAVITY (simple version) ---
  // If the ball is over the platform, keep it on top.
  // Otherwise let it fall.
  const onPlatform = (
    Math.abs(ball.position.x) < 9 &&
    Math.abs(ball.position.z) < 9
  );

  if (!onPlatform) {
    velocity.y -= 0.015; // gravity pulls down
  } else {
    velocity.y = 0;
    ball.position.y = 0.5; // snap to platform surface
  }

  ball.position.y += velocity.y;

  // --- FALL OFF = GAME OVER ---
  if (ball.position.y < FALL_LIMIT) {
    ball.position.set(0, 0.5, 0);
    velocity.set(0, 0, 0);
    document.getElementById('message').textContent = 'You fell! Keep going...';
    document.getElementById('message').style.display = 'block';
    setTimeout(() => document.getElementById('message').style.display = 'none', 1500);
  }

  // --- GEM COLLISION DETECTION ---
  // In 3D, collision detection uses distance between positions.
  // If two objects are closer than (r1 + r2), they're overlapping.
  for (let i = gems.length - 1; i >= 0; i--) {
    const gem = gems[i];
    const dist = ball.position.distanceTo(gem.position);
    if (dist < 0.9) { // ball radius (0.5) + gem radius (~0.35) ≈ 0.85
      scene.remove(gem);
      gems.splice(i, 1);
      gemsCollected++;
      document.getElementById('gemCount').textContent = gemsCollected;

      if (gems.length === 0) {
        document.getElementById('message').textContent = '🎉 You collected all gems!';
        document.getElementById('message').style.display = 'block';
      }
    }
  }

  // Spin the gems
  gems.forEach(gem => {
    gem.rotation.y += 0.03;
    gem.position.y = 0.8 + Math.sin(Date.now() * 0.002 + gem.position.x) * 0.15;
  });

  // --- CAMERA FOLLOWS THE BALL ---
  // Move the camera to stay behind/above the ball
  camera.position.x += (ball.position.x - camera.position.x) * 0.05;
  camera.position.z += (ball.position.z + 12 - camera.position.z) * 0.05;
  camera.lookAt(ball.position);
}

function render() {
  renderer.render(scene, camera);
}

// ============================================================
// START
// ============================================================
gameLoop();
