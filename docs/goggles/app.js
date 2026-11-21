import * as THREE from 'three';
import { detectCapabilities, capsSummary, requestOrientationPermission } from './xr-utils.js';
import { startAR } from './ar-scene.js';
import { startVR } from './vr-game.js';

const landing = document.getElementById('landing');
const hudRoot = document.getElementById('hud-root');
const videoEl = document.getElementById('cam-feed');
const canvas = document.getElementById('gl');
const overlayEl = document.getElementById('overlay');
const capsEl = document.getElementById('caps');
const btnExit = document.getElementById('btn-exit');

let caps = null;
let renderer = null;
let current = null;
let lastT = null;

(async () => {
  caps = await detectCapabilities();
  capsEl.textContent = capsSummary(caps);
})();

function ensureRenderer() {
  if (renderer) return renderer;
  renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setSize(innerWidth, innerHeight);
  renderer.xr.enabled = true;
  window.addEventListener('resize', onResize);
  return renderer;
}

function onResize() {
  if (!renderer || !current) return;
  renderer.setSize(innerWidth, innerHeight);
  current.camera.aspect = innerWidth / innerHeight;
  current.camera.updateProjectionMatrix();
}

async function enterMode(starter) {
  await requestOrientationPermission();
  ensureRenderer();
  landing.hidden = true;
  hudRoot.hidden = false;
  overlayEl.classList.remove('flash-red');

  current = await starter({ renderer, videoEl, overlayEl, caps });
  onResize();
  lastT = null;
  renderer.setAnimationLoop((time, frame) => {
    if (!current) return;
    const t = time / 1000;
    const dt = lastT == null ? 0 : Math.min(t - lastT, 0.1);
    lastT = t;
    current.update(dt, frame);
    renderer.render(current.scene, current.camera);
  });
}

function exitMode() {
  renderer?.setAnimationLoop(null);
  current?.dispose();
  current = null;
  hudRoot.hidden = true;
  landing.hidden = false;
}

document.getElementById('btn-ar').addEventListener('click', () => enterMode(startAR));
document.getElementById('btn-vr').addEventListener('click', () => enterMode(startVR));
btnExit.addEventListener('click', exitMode);
