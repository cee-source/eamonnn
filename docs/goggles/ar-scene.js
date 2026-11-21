import * as THREE from 'three';
import { VisorHUD, textSprite, updateTextSprite } from './hud.js';
import {
  startEnvironmentCamera, stopStream, OrientationTracker,
  makeOrientationApplier, currentScreenOrientationDeg,
} from './xr-utils.js';

function buildHoloPanel() {
  const group = new THREE.Group();

  const core = new THREE.Mesh(
    new THREE.IcosahedronGeometry(0.1, 1),
    new THREE.MeshBasicMaterial({ color: 0x2de3ff, wireframe: true, transparent: true, opacity: 0.9 }),
  );
  group.add(core);

  const ring = new THREE.Mesh(
    new THREE.RingGeometry(0.16, 0.17, 48),
    new THREE.MeshBasicMaterial({ color: 0xff9a1f, side: THREE.DoubleSide, transparent: true, opacity: 0.8 }),
  );
  ring.rotation.x = Math.PI / 2;
  group.add(ring);

  const label = textSprite('SCANNING...', { color: '#2de3ff', size: 36 });
  label.position.set(0, 0.22, 0);
  label.scale.set(0.3, 0.075, 1);
  group.add(label);

  group._core = core;
  group._ring = ring;
  group._label = label;
  group._t = 0;
  group._lines = [
    'SCANNING...', 'ATMOSPHERE: NOMINAL', 'THREAT LVL: LOW', 'LOCK ACQUIRED',
  ];
  return group;
}

export async function startAR({ renderer, videoEl, overlayEl, caps }) {
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(60, innerWidth / innerHeight, 0.01, 100);
  scene.add(camera);
  const hud = new VisorHUD(camera);

  const panels = [];
  let session = null;
  let hitTestSource = null;
  let reticle = null;
  let orientationTracker = null;
  let applyOrientation = null;
  let camStream = null;
  let frameCount = 0;

  overlayEl.innerHTML = `
    <div class="corner tl">VISOR // AR MODE</div>
    <div class="corner tr" id="ar-mode-label">INITIALISING</div>
    <div class="center-msg" id="ar-msg"></div>
  `;
  const setMsg = (t) => { overlayEl.querySelector('#ar-msg').textContent = t; };

  const usingWebXR = caps.webxrAR;

  if (usingWebXR) {
    try {
      session = await navigator.xr.requestSession('immersive-ar', {
        requiredFeatures: ['hit-test'],
      });
      renderer.xr.setReferenceSpaceType('local');
      await renderer.xr.setSession(session);

      const viewerSpace = await session.requestReferenceSpace('viewer');
      hitTestSource = await session.requestHitTestSource({ space: viewerSpace });

      reticle = new THREE.Mesh(
        new THREE.RingGeometry(0.05, 0.065, 32).rotateX(-Math.PI / 2),
        new THREE.MeshBasicMaterial({ color: 0x2de3ff }),
      );
      reticle.matrixAutoUpdate = false;
      reticle.visible = false;
      scene.add(reticle);

      session.addEventListener('select', () => {
        if (reticle.visible) {
          const panel = buildHoloPanel();
          panel.position.setFromMatrixPosition(reticle.matrix);
          scene.add(panel);
          panels.push(panel);
        }
      });
      session.addEventListener('end', () => { session = null; });

      overlayEl.querySelector('#ar-mode-label').textContent = 'NATIVE WEBXR';
      setMsg('Tap a surface to drop a hologram');
      setTimeout(() => setMsg(''), 4000);
    } catch (e) {
      console.warn('WebXR AR session failed, falling back:', e);
      await startFallback();
    }
  } else {
    await startFallback();
  }

  async function startFallback() {
    try {
      camStream = await startEnvironmentCamera(videoEl);
      videoEl.hidden = false;
    } catch (e) {
      setMsg('Camera access denied / unavailable.\nVisor running without passthrough.');
    }
    orientationTracker = new OrientationTracker();
    orientationTracker.start();
    applyOrientation = makeOrientationApplier(THREE);

    const fixedPanel = buildHoloPanel();
    fixedPanel.position.set(0, 0, -1.6);
    camera.add(fixedPanel);
    panels.push(fixedPanel);

    overlayEl.querySelector('#ar-mode-label').textContent = 'CAMERA FALLBACK';
    hud.setStatus('NO WEBXR — OVERLAY MODE');
  }

  function update(dt, frame) {
    frameCount++;
    let heading = null;

    if (session && frame && hitTestSource && reticle) {
      const refSpace = renderer.xr.getReferenceSpace();
      const results = frame.getHitTestResults(hitTestSource);
      if (results.length) {
        const pose = results[0].getPose(refSpace);
        reticle.visible = true;
        reticle.matrix.fromArray(pose.transform.matrix);
      } else {
        reticle.visible = false;
      }
    } else if (orientationTracker && applyOrientation) {
      const o = orientationTracker.get();
      heading = 360 - o.alpha;
      applyOrientation(camera, o, currentScreenOrientationDeg());
    }

    for (const p of panels) {
      p.rotation.y += dt * 0.8;
      p._core.rotation.x += dt * 0.5;
      p._ring.rotation.z -= dt * 0.6;
      p._t += dt;
      if (frameCount % 30 === 0) {
        const line = p._lines[Math.floor(p._t) % p._lines.length];
        updateTextSprite(p._label, line);
      }
    }

    hud.update(dt, heading);
  }

  function dispose() {
    hud.dispose();
    session?.end().catch(() => {});
    stopStream(camStream);
    orientationTracker?.stop();
    videoEl.hidden = true;
    videoEl.srcObject = null;
    overlayEl.innerHTML = '';
  }

  return { scene, camera, update, dispose };
}
