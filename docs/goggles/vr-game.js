import * as THREE from 'three';
import { textSprite, updateTextSprite, ringMesh } from './hud.js';
import { OrientationTracker, makeOrientationApplier, currentScreenOrientationDeg } from './xr-utils.js';

const PLAYER_RADIUS = 1.2;
const SPAWN_DIST = [14, 18];
const START_SPEED = 1.6;
const MAX_SPEED = 5.5;
const RAMP_SECONDS = 90;

let audioCtx = null;
function beep(freq, dur, type = 'sine', gain = 0.15) {
  try {
    audioCtx ??= new (window.AudioContext || window.webkitAudioContext)();
    const osc = audioCtx.createOscillator();
    const amp = audioCtx.createGain();
    osc.type = type;
    osc.frequency.value = freq;
    amp.gain.value = gain;
    osc.connect(amp).connect(audioCtx.destination);
    osc.start();
    amp.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + dur);
    osc.stop(audioCtx.currentTime + dur);
  } catch {}
}

function spawnOrb(scene, elapsed) {
  const theta = Math.random() * Math.PI * 2;
  const phi = Math.acos(THREE.MathUtils.randFloat(-0.3, 0.6));
  const dist = THREE.MathUtils.randFloat(...SPAWN_DIST);
  const pos = new THREE.Vector3(
    dist * Math.sin(phi) * Math.cos(theta),
    dist * Math.cos(phi) - 0.3,
    dist * Math.sin(phi) * Math.sin(theta),
  );

  const bonus = Math.random() < 0.2;
  const color = bonus ? 0xff9a1f : 0x2de3ff;
  const mesh = new THREE.Mesh(
    new THREE.IcosahedronGeometry(bonus ? 0.28 : 0.35, 0),
    new THREE.MeshBasicMaterial({ color, wireframe: false, transparent: true, opacity: 0.9 }),
  );
  mesh.position.copy(pos);
  const wire = new THREE.Mesh(mesh.geometry, new THREE.MeshBasicMaterial({ color: 0xffffff, wireframe: true, transparent: true, opacity: 0.3 }));
  mesh.add(wire);
  scene.add(mesh);

  const speed = THREE.MathUtils.lerp(START_SPEED, MAX_SPEED, Math.min(elapsed / RAMP_SECONDS, 1));
  const velocity = pos.clone().negate().normalize().multiplyScalar(speed * THREE.MathUtils.randFloat(0.85, 1.15));

  return { mesh, velocity, points: bonus ? 25 : 10, alive: true };
}

function spawnHitFlash(scene, position) {
  const ring = ringMesh(0.1, 0.03, 0xffffff, 24);
  ring.position.copy(position);
  ring.lookAt(0, 0, 0);
  scene.add(ring);
  const start = performance.now();
  const tick = () => {
    const t = (performance.now() - start) / 300;
    if (t >= 1) { scene.remove(ring); return; }
    ring.scale.setScalar(1 + t * 2.5);
    ring.material.opacity = 0.9 * (1 - t);
    requestAnimationFrame(tick);
  };
  tick();
}

export async function startVR({ renderer, overlayEl, caps }) {
  const scene = new THREE.Scene();
  scene.fog = new THREE.Fog(0x02060a, 8, 22);
  scene.background = new THREE.Color(0x02060a);

  const camera = new THREE.PerspectiveCamera(65, innerWidth / innerHeight, 0.01, 60);
  scene.add(camera);

  const grid = new THREE.GridHelper(40, 40, 0x2de3ff, 0x113040);
  grid.position.y = -1.6;
  scene.add(grid);

  const starGeo = new THREE.BufferGeometry();
  const starCount = 400;
  const starPos = new Float32Array(starCount * 3);
  for (let i = 0; i < starCount; i++) {
    const r = THREE.MathUtils.randFloat(20, 35);
    const th = Math.random() * Math.PI * 2;
    const ph = Math.acos(THREE.MathUtils.randFloat(-1, 1));
    starPos[i * 3] = r * Math.sin(ph) * Math.cos(th);
    starPos[i * 3 + 1] = r * Math.cos(ph);
    starPos[i * 3 + 2] = r * Math.sin(ph) * Math.sin(th);
  }
  starGeo.setAttribute('position', new THREE.BufferAttribute(starPos, 3));
  scene.add(new THREE.Points(starGeo, new THREE.PointsMaterial({ color: 0x2de3ff, size: 0.05 })));

  const reticle = ringMesh(0.012, 0.003, 0xffffff, 24);
  reticle.position.set(0, 0, -1.2);
  camera.add(reticle);

  const scoreLabel = textSprite('SCORE 0', { color: '#2de3ff', size: 42 });
  scoreLabel.position.set(0.45, 0.35, -1.2);
  scoreLabel.scale.set(0.3, 0.075, 1);
  camera.add(scoreLabel);

  const livesLabel = textSprite('LIVES ***', { color: '#ff9a1f', size: 42 });
  livesLabel.position.set(-0.45, 0.35, -1.2);
  livesLabel.scale.set(0.3, 0.075, 1);
  camera.add(livesLabel);

  const bigLabel = textSprite('', { color: '#2de3ff', size: 48 });
  bigLabel.position.set(0, 0, -1.4);
  bigLabel.scale.set(0.7, 0.175, 1);
  bigLabel.visible = false;
  camera.add(bigLabel);

  let orbs = [];
  let score = 0;
  let lives = 3;
  let elapsed = 0;
  let spawnTimer = 0;
  let gameOver = false;

  const orientationTracker = new OrientationTracker();
  orientationTracker.start();
  const applyOrientation = makeOrientationApplier(THREE);
  let yaw = 0;
  let pitch = 0;
  let dragging = false;
  let dragStart = null;
  let dragMoved = false;

  overlayEl.innerHTML = `
    <div class="corner tl">ORB DEFENDER</div>
    <div class="corner tr">${caps.webxrVR ? 'WEBXR VR' : 'FALLBACK LOOK'}</div>
    <div class="corner bl" id="vr-hint">Drag to look · tap/space to fire</div>
  `;

  function resetGame() {
    orbs.forEach((o) => scene.remove(o.mesh));
    orbs = [];
    score = 0;
    lives = 3;
    elapsed = 0;
    spawnTimer = 0;
    gameOver = false;
    bigLabel.visible = false;
    updateTextSprite(scoreLabel, 'SCORE 0', '#2de3ff');
    updateTextSprite(livesLabel, 'LIVES ***', '#ff9a1f');
  }

  function endGame() {
    gameOver = true;
    bigLabel.visible = true;
    updateTextSprite(bigLabel, `GAME OVER - ${score} PTS`, '#ff3b3b');
    beep(110, 0.6, 'sawtooth', 0.2);
  }

  function fire() {
    if (gameOver) { resetGame(); return; }
    const origin = new THREE.Vector3();
    const dir = new THREE.Vector3();
    camera.getWorldPosition(origin);
    camera.getWorldDirection(dir);
    const raycaster = new THREE.Raycaster(origin, dir, 0.1, 30);
    const hits = raycaster.intersectObjects(orbs.filter((o) => o.alive).map((o) => o.mesh));
    if (hits.length) {
      const hitMesh = hits[0].object;
      const orb = orbs.find((o) => o.mesh === hitMesh);
      if (orb) {
        orb.alive = false;
        scene.remove(orb.mesh);
        spawnHitFlash(scene, hits[0].point);
        score += orb.points;
        updateTextSprite(scoreLabel, `SCORE ${score}`, '#2de3ff');
        beep(880, 0.08, 'square', 0.1);
      }
    } else {
      beep(220, 0.05, 'square', 0.05);
    }
  }

  function onPointerDown(e) {
    dragging = true;
    dragMoved = false;
    dragStart = { x: e.clientX, y: e.clientY, t: performance.now() };
  }
  function onPointerMove(e) {
    if (!dragging || renderer.xr.isPresenting) return;
    const dx = e.movementX ?? 0;
    const dy = e.movementY ?? 0;
    if (Math.abs(e.clientX - dragStart.x) + Math.abs(e.clientY - dragStart.y) > 6) dragMoved = true;
    yaw -= dx * 0.004;
    pitch = THREE.MathUtils.clamp(pitch - dy * 0.004, -1.3, 1.3);
  }
  function onPointerUp() {
    dragging = false;
    if (!dragMoved) fire();
  }
  function onKeyDown(e) {
    if (e.code === 'Space') fire();
  }

  const canvas = renderer.domElement;
  canvas.addEventListener('pointerdown', onPointerDown);
  canvas.addEventListener('pointermove', onPointerMove);
  canvas.addEventListener('pointerup', onPointerUp);
  window.addEventListener('keydown', onKeyDown);

  let xrSession = null;
  if (caps.webxrVR) {
    try {
      xrSession = await navigator.xr.requestSession('immersive-vr', {
        optionalFeatures: ['local-floor'],
      });
      await renderer.xr.setSession(xrSession);
      xrSession.addEventListener('select', fire);
      xrSession.addEventListener('end', () => { xrSession = null; });
    } catch (e) {
      console.warn('WebXR VR session failed, using fallback look:', e);
    }
  }

  function update(dt) {
    if (!renderer.xr.isPresenting) {
      const o = orientationTracker.get();
      if (Math.abs(o.alpha) + Math.abs(o.beta) + Math.abs(o.gamma) > 0.001) {
        applyOrientation(camera, o, currentScreenOrientationDeg());
      } else {
        camera.rotation.set(pitch, yaw, 0, 'YXZ');
      }
      camera.updateMatrixWorld(true);
    }

    if (gameOver) return;
    elapsed += dt;
    spawnTimer -= dt;
    const interval = THREE.MathUtils.lerp(1.6, 0.6, Math.min(elapsed / RAMP_SECONDS, 1));
    if (spawnTimer <= 0 && orbs.length < 18) {
      orbs.push(spawnOrb(scene, elapsed));
      spawnTimer = interval;
    }

    for (const orb of orbs) {
      if (!orb.alive) continue;
      orb.mesh.position.addScaledVector(orb.velocity, dt);
      orb.mesh.rotation.x += dt;
      orb.mesh.rotation.y += dt * 0.7;
      if (orb.mesh.position.length() < PLAYER_RADIUS) {
        orb.alive = false;
        scene.remove(orb.mesh);
        lives -= 1;
        updateTextSprite(livesLabel, `LIVES ${'*'.repeat(Math.max(lives, 0))}`, '#ff9a1f');
        overlayEl.classList.remove('flash-red');
        requestAnimationFrame(() => overlayEl.classList.add('flash-red'));
        beep(140, 0.25, 'sawtooth', 0.2);
        if (lives <= 0) endGame();
      }
    }
    orbs = orbs.filter((o) => o.alive);
  }

  function dispose() {
    canvas.removeEventListener('pointerdown', onPointerDown);
    canvas.removeEventListener('pointermove', onPointerMove);
    canvas.removeEventListener('pointerup', onPointerUp);
    window.removeEventListener('keydown', onKeyDown);
    orientationTracker.stop();
    xrSession?.end().catch(() => {});
    overlayEl.innerHTML = '';
  }

  return { scene, camera, update, dispose };
}
