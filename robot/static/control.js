const status = document.getElementById('status');
const overlay = document.getElementById('overlay');
const startBtn = document.getElementById('start');
const keyEls = document.querySelectorAll('.key');

const keys = { w: false, a: false, s: false, d: false, ArrowUp: false, ArrowDown: false };

let socket = null;

function connect() {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  socket = new WebSocket(`${proto}://${location.host}/ws`);

  socket.addEventListener('open', () => {
    status.textContent = 'connected';
    status.className = 'connected';
  });

  socket.addEventListener('close', () => {
    status.textContent = 'disconnected — retrying…';
    status.className = 'disconnected';
    setTimeout(connect, 1000);
  });

  socket.addEventListener('error', () => socket.close());
}
connect();

function send(msg) {
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify(msg));
  }
}

function setKey(key, isDown) {
  if (!(key in keys)) return;
  keys[key] = isDown;
  const el = document.querySelector(`.key[data-key="${key}"]`);
  if (el) el.classList.toggle('active', isDown);
}

window.addEventListener('keydown', (e) => {
  if (e.key in keys || e.key.toLowerCase() in keys) {
    setKey(e.key.length === 1 ? e.key.toLowerCase() : e.key, true);
    e.preventDefault();
  }
});

window.addEventListener('keyup', (e) => {
  if (e.key in keys || e.key.toLowerCase() in keys) {
    setKey(e.key.length === 1 ? e.key.toLowerCase() : e.key, false);
    e.preventDefault();
  }
});

// send the held-key state at a steady rate — this also doubles as the
// connection heartbeat the server's safety watchdog relies on.
setInterval(() => {
  send({
    type: 'state',
    w: keys.w, a: keys.a, s: keys.s, d: keys.d,
    arrowUp: keys.ArrowUp, arrowDown: keys.ArrowDown,
  });
}, 50);

// mouse: pointer-locked movement rotates the turret and raises/lowers the boom
startBtn.addEventListener('click', () => {
  document.body.requestPointerLock();
});

document.addEventListener('pointerlockchange', () => {
  overlay.classList.toggle('hidden', document.pointerLockElement === document.body);
});

document.addEventListener('mousemove', (e) => {
  if (document.pointerLockElement !== document.body) return;
  send({ type: 'arm', dx: e.movementX, dy: e.movementY });
});
