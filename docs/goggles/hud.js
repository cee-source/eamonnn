import * as THREE from 'three';

function textSprite(text, { color = '#2de3ff', size = 64, weight = '600' } = {}) {
  const canvas = document.createElement('canvas');
  canvas.width = 512;
  canvas.height = 128;
  const ctx = canvas.getContext('2d');
  ctx.font = `${weight} ${size}px 'Share Tech Mono', monospace`;
  ctx.fillStyle = color;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.shadowColor = color;
  ctx.shadowBlur = 20;
  ctx.fillText(text, canvas.width / 2, canvas.height / 2);

  const tex = new THREE.CanvasTexture(canvas);
  tex.minFilter = THREE.LinearFilter;
  const mat = new THREE.SpriteMaterial({ map: tex, transparent: true, depthTest: false });
  const sprite = new THREE.Sprite(mat);
  sprite.scale.set(0.5, 0.125, 1);
  sprite._canvas = canvas;
  sprite._ctx = ctx;
  sprite._tex = tex;
  return sprite;
}

function updateTextSprite(sprite, text, color = '#2de3ff') {
  const { _ctx: ctx, _canvas: canvas } = sprite;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = color;
  ctx.shadowColor = color;
  ctx.fillText(text, canvas.width / 2, canvas.height / 2);
  sprite._tex.needsUpdate = true;
}

function ringMesh(radius, thickness, color, segments = 64, arcFraction = 1) {
  const geo = new THREE.RingGeometry(radius - thickness, radius, segments, 1, 0, Math.PI * 2 * arcFraction);
  const mat = new THREE.MeshBasicMaterial({
    color, side: THREE.DoubleSide, transparent: true, opacity: 0.85, depthTest: false,
  });
  return new THREE.Mesh(geo, mat);
}

/**
 * Visor HUD: a bundle of camera-attached objects (corner readouts, a
 * rotating "arc reactor" gauge, a compass ring, a center reticle) that
 * always render fixed-in-view, same trick real HMD HUDs use since a 2D
 * DOM overlay doesn't show inside an immersive WebXR session.
 */
export class VisorHUD {
  constructor(camera) {
    this.camera = camera;
    this.group = new THREE.Group();
    this.group.position.set(0, 0, -1.2);
    camera.add(this.group);

    this.reactor = new THREE.Group();
    this.reactor.position.set(0, -0.32, 0);
    const outer = ringMesh(0.09, 0.012, 0x2de3ff);
    const inner = ringMesh(0.065, 0.02, 0xff9a1f, 48, 0.75);
    this.reactor.add(outer, inner);
    this._reactorOuter = outer;
    this._reactorInner = inner;
    this.group.add(this.reactor);

    this.compass = ringMesh(0.5, 0.004, 0x2de3ff, 64);
    this.compass.position.set(0, 0.42, 0);
    this.compass.rotation.x = -0.1;
    this.group.add(this.compass);

    this.headingLabel = textSprite('N 000', { color: '#2de3ff', size: 40 });
    this.headingLabel.position.set(0, 0.42, 0);
    this.headingLabel.scale.set(0.2, 0.05, 1);
    this.group.add(this.headingLabel);

    this.clockLabel = textSprite('00:00:00', { color: '#2de3ff', size: 40 });
    this.clockLabel.position.set(0.32, 0.28, 0);
    this.clockLabel.scale.set(0.22, 0.055, 1);
    this.group.add(this.clockLabel);

    this.statusLabel = textSprite('VISOR ONLINE', { color: '#ff9a1f', size: 36 });
    this.statusLabel.position.set(-0.32, 0.28, 0);
    this.statusLabel.scale.set(0.24, 0.06, 1);
    this.group.add(this.statusLabel);

    this.reticle = ringMesh(0.015, 0.003, 0x2de3ff, 32);
    this.reticle.position.set(0, 0, -0.05);
    this.group.add(this.reticle);

    this._lastClock = '';
    this._t = 0;
  }

  setStatus(text) {
    updateTextSprite(this.statusLabel, text, '#ff9a1f');
  }

  update(dt, heading = null) {
    this._t += dt;
    this._reactorOuter.rotation.z += dt * 0.6;
    this._reactorInner.rotation.z -= dt * 1.1;
    const pulse = 0.9 + Math.sin(this._t * 3) * 0.1;
    this.reactor.scale.setScalar(pulse);

    if (heading != null) {
      this.compass.rotation.z = THREE.MathUtils.degToRad(heading);
      updateTextSprite(this.headingLabel, `N ${Math.round(heading).toString().padStart(3, '0')}`);
    }

    const now = new Date().toLocaleTimeString('en-GB');
    if (now !== this._lastClock) {
      this._lastClock = now;
      updateTextSprite(this.clockLabel, now);
    }
  }

  dispose() {
    this.camera.remove(this.group);
  }
}

export { textSprite, updateTextSprite, ringMesh };
