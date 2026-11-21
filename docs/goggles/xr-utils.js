export async function detectCapabilities() {
  const caps = {
    webxrAR: false,
    webxrVR: false,
    camera: 'mediaDevices' in navigator,
    orientation: 'DeviceOrientationEvent' in window,
  };
  if (navigator.xr) {
    try { caps.webxrAR = await navigator.xr.isSessionSupported('immersive-ar'); } catch {}
    try { caps.webxrVR = await navigator.xr.isSessionSupported('immersive-vr'); } catch {}
  }
  return caps;
}

export function capsSummary(caps) {
  const yn = (b) => (b ? 'YES' : 'no');
  return (
    `WebXR AR: ${yn(caps.webxrAR)}  |  WebXR VR: ${yn(caps.webxrVR)}\n` +
    `Camera API: ${yn(caps.camera)}  |  Motion sensors: ${yn(caps.orientation)}\n` +
    (caps.webxrAR || caps.webxrVR
      ? 'Native XR available — full stereo/passthrough will be used.'
      : 'No native WebXR here — using camera/tilt fallback (works, lower fidelity).')
  );
}

export async function requestOrientationPermission() {
  const DOE = window.DeviceOrientationEvent;
  if (DOE && typeof DOE.requestPermission === 'function') {
    try {
      const result = await DOE.requestPermission();
      return result === 'granted';
    } catch {
      return false;
    }
  }
  return 'DeviceOrientationEvent' in window;
}

export async function startEnvironmentCamera(videoEl) {
  const stream = await navigator.mediaDevices.getUserMedia({
    video: { facingMode: 'environment' },
    audio: false,
  });
  videoEl.srcObject = stream;
  await videoEl.play();
  return stream;
}

export function stopStream(stream) {
  stream?.getTracks().forEach((t) => t.stop());
}

/**
 * Standard deviceorientation -> object quaternion mapping (same approach
 * three.js's old DeviceOrientationControls used) so phone tilt drives a
 * believable "look around" in the non-WebXR fallback path.
 */
export function makeOrientationApplier(THREE) {
  const zee = new THREE.Vector3(0, 0, 1);
  const euler = new THREE.Euler();
  const q0 = new THREE.Quaternion();
  const q1 = new THREE.Quaternion(-Math.sqrt(0.5), 0, 0, Math.sqrt(0.5));

  return function applyTo(object3D, { alpha, beta, gamma }, screenOrientDeg = 0) {
    const a = THREE.MathUtils.degToRad(alpha);
    const b = THREE.MathUtils.degToRad(beta);
    const g = THREE.MathUtils.degToRad(gamma);
    const orient = THREE.MathUtils.degToRad(screenOrientDeg);

    euler.set(b, a, -g, 'YXZ');
    object3D.quaternion.setFromEuler(euler);
    object3D.quaternion.multiply(q1);
    object3D.quaternion.multiply(q0.setFromAxisAngle(zee, -orient));
  };
}

export function currentScreenOrientationDeg() {
  const angle = screen.orientation?.angle;
  return typeof angle === 'number' ? angle : window.orientation || 0;
}

/**
 * Tracks device heading/pitch/roll for the non-WebXR "tilt to look" fallback.
 * Returns {alpha, beta, gamma} in degrees via .get(), already permission-gated.
 */
export class OrientationTracker {
  constructor() {
    this._alpha = 0;
    this._beta = 0;
    this._gamma = 0;
    this._handler = (e) => {
      if (e.alpha == null) return;
      this._alpha = e.alpha;
      this._beta = e.beta ?? 0;
      this._gamma = e.gamma ?? 0;
    };
  }

  start() {
    window.addEventListener('deviceorientation', this._handler);
  }

  stop() {
    window.removeEventListener('deviceorientation', this._handler);
  }

  get() {
    return { alpha: this._alpha, beta: this._beta, gamma: this._gamma };
  }
}
