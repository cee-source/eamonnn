// === SCENE ===
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x87CEEB);
scene.fog = new THREE.Fog(0x87CEEB, 20, 80);

// === CAMERA ===
const camera = new THREE.PerspectiveCamera(75, innerWidth/innerHeight, 0.1, 200);
camera.position.set(0, 1.7, 50);

// === RENDERER ===
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(innerWidth, innerHeight);
renderer.shadowMap.enabled = true;
document.body.appendChild(renderer.domElement);
window.addEventListener('resize', () => {
  camera.aspect = innerWidth/innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
});

// === LIGHTS ===
const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
scene.add(ambientLight);
const sunLight = new THREE.DirectionalLight(0xffffaa, 1.0);
sunLight.castShadow = true;
scene.add(sunLight);
const moonLight = new THREE.DirectionalLight(0x3344aa, 0.4);
moonLight.visible = false;
scene.add(moonLight);

// === GROUND ===
const ground = new THREE.Mesh(
  new THREE.PlaneGeometry(300, 300),
  new THREE.MeshLambertMaterial({ color: 0x4a7c3f })
);
ground.rotation.x = -Math.PI/2;
ground.receiveShadow = true;
scene.add(ground);

// === BLOCK TYPES ===
const BLOCKS = {
  cobble: { color: 0x888888, name: 'Cobblestone' },
  planks: { color: 0xC4A35A, name: 'Planks'      },
  dirt:   { color: 0x8B6914, name: 'Dirt'         },
  sand:   { color: 0xF4D03F, name: 'Sand'         },
  stone:  { color: 0x777777, name: 'Stone'        },
  wood:   { color: 0x5C3317, name: 'Wood'         },
  leaf:   { color: 0x228B22, name: 'Leaves'       },
  lava:   { color: 0xFF4500, name: 'Lava'         },
  glass:  { color: 0x88ccff, name: 'Glass'        },
};

function colorHex(type) {
  if (!type || !BLOCKS[type]) return '#333';
  return '#' + BLOCKS[type].color.toString(16).padStart(6, '0');
}

// === INVENTORY ===
// slots 0-8 = hotbar, 9-35 = main inventory
const inventory = Array(36).fill(null).map(() => ({ type: null, count: 0 }));
let selectedSlot = 0;
let inventoryOpen = false;

function addToInventory(type) {
  for (let i = 0; i < 36; i++) {
    if (inventory[i].type === type && inventory[i].count < 64) {
      inventory[i].count++;
      renderHotbar();
      if (inventoryOpen) renderInvScreen();
      return true;
    }
  }
  for (let i = 0; i < 36; i++) {
    if (!inventory[i].type) {
      inventory[i] = { type, count: 1 };
      renderHotbar();
      if (inventoryOpen) renderInvScreen();
      return true;
    }
  }
  return false;
}

function consumeSelected() {
  const slot = inventory[selectedSlot];
  if (!slot.type || slot.count <= 0) return null;
  const type = slot.type;
  slot.count--;
  if (slot.count === 0) slot.type = null;
  renderHotbar();
  if (inventoryOpen) renderInvScreen();
  return type;
}

// Starting blocks
['cobble','cobble','cobble','cobble','cobble',
 'planks','planks','planks','dirt','dirt','sand']
  .forEach(t => addToInventory(t));

// === HOTBAR UI ===
function renderHotbar() {
  const el = document.getElementById('hotbar');
  el.innerHTML = '';
  for (let i = 0; i < 9; i++) {
    const slot = inventory[i];
    const div = document.createElement('div');
    div.className = 'hslot' + (i === selectedSlot ? ' selected' : '');
    if (slot.type) {
      const icon = document.createElement('div');
      icon.className = 'slot-icon';
      icon.style.background = colorHex(slot.type);
      div.appendChild(icon);
      const cnt = document.createElement('div');
      cnt.className = 'slot-count';
      cnt.textContent = slot.count;
      div.appendChild(cnt);
    }
    el.appendChild(div);
  }
}

// === INVENTORY SCREEN UI ===
function renderInvScreen() {
  const main   = document.getElementById('inv-main');
  const hotbar = document.getElementById('inv-hotbar');
  main.innerHTML = '';
  hotbar.innerHTML = '';
  for (let i = 9; i < 36; i++) renderInvSlot(main,   i);
  for (let i = 0; i <  9; i++) renderInvSlot(hotbar, i);
}

function renderInvSlot(parent, index) {
  const slot = inventory[index];
  const div  = document.createElement('div');
  div.className = 'islot' + (index === selectedSlot ? ' selected' : '');
  if (slot.type) {
    const icon = document.createElement('div');
    icon.className = 'slot-icon';
    icon.style.background = colorHex(slot.type);
    div.appendChild(icon);
    const cnt = document.createElement('div');
    cnt.className = 'slot-count';
    cnt.textContent = slot.count;
    div.appendChild(cnt);
  }
  div.addEventListener('click', () => {
    if (index < 9) {
      selectedSlot = index;
    } else {
      const tmp = { ...inventory[selectedSlot] };
      inventory[selectedSlot] = { ...inventory[index] };
      inventory[index] = tmp;
    }
    renderHotbar();
    renderInvScreen();
  });
  parent.appendChild(div);
}

function toggleInventory() {
  inventoryOpen = !inventoryOpen;
  const screen = document.getElementById('inv-screen');
  if (inventoryOpen) {
    screen.classList.add('open');
    document.exitPointerLock();
    renderInvScreen();
  } else {
    screen.classList.remove('open');
    renderer.domElement.requestPointerLock();
  }
}

renderHotbar();

// === PLACED BLOCKS ===
const placedBlocks = [];

function placeBlock(x, y, z, type) {
  const isLava = type === 'lava';
  const mat = new THREE.MeshLambertMaterial({
    color:       BLOCKS[type] ? BLOCKS[type].color : 0x888888,
    emissive:    isLava ? 0xff2200 : 0x000000,
    transparent: type === 'glass',
    opacity:     type === 'glass' ? 0.5 : 1.0,
  });
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(1, 1, 1), mat);
  mesh.position.set(Math.round(x), Math.round(y), Math.round(z));
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  mesh.userData.type = type;
  mesh.userData.hp   = isLava ? Infinity : 3;
  scene.add(mesh);
  placedBlocks.push(mesh);
  return mesh;
}

// === WORLD GENERATION ===
function makeTree(x, z) {
  const h = 4 + Math.floor(Math.random() * 3);
  for (let y = 0; y < h; y++) placeBlock(x, y + 0.5, z, 'wood');
  for (let lx = -2; lx <= 2; lx++)
    for (let lz = -2; lz <= 2; lz++)
      for (let ly = 0; ly <= 2; ly++) {
        if (Math.abs(lx) === 2 && Math.abs(lz) === 2) continue;
        if (Math.random() > 0.25) placeBlock(x+lx, h+ly+0.5, z+lz, 'leaf');
      }
}

function makeLavaPool(cx, cz) {
  for (let lx = -2; lx <= 2; lx++)
    for (let lz = -2; lz <= 2; lz++)
      if (Math.random() > 0.2) placeBlock(cx+lx, -0.5, cz+lz, 'lava');
  const glow = new THREE.PointLight(0xff4400, 3, 10);
  glow.position.set(cx, 1, cz);
  scene.add(glow);
}

function makeHouse(cx, cz) {
  const w = 7, d = 7, wallH = 4;
  for (let bx = 0; bx < w; bx++)
    for (let by = 0; by < wallH; by++)
      for (let bz = 0; bz < d; bz++) {
        if (!(bx===0||bx===w-1||bz===0||bz===d-1)) continue;
        if (bz===0 && bx===3 && by<3) continue;
        if (by===2 && (bx===1||bx===w-2) && (bz===0||bz===d-1)) {
          placeBlock(cx+bx-3, by+0.5, cz+bz-3, 'glass'); continue;
        }
        placeBlock(cx+bx-3, by+0.5, cz+bz-3, 'cobble');
      }
  for (let bx = -1; bx <= w; bx++)
    for (let bz = -1; bz <= d; bz++)
      placeBlock(cx+bx-3, wallH+0.5, cz+bz-3, 'planks');
}

function makeFountain(cx, cz) {
  for (let fx = -2; fx <= 2; fx++)
    for (let fz = -2; fz <= 2; fz++) {
      if (Math.abs(fx)===2 || Math.abs(fz)===2) {
        placeBlock(cx+fx, 0.5, cz+fz, 'stone');
      } else {
        const w = placeBlock(cx+fx, 0.3, cz+fz, 'glass');
        w.material.color.set(0x0077cc);
      }
    }
  placeBlock(cx, 1.5, cz, 'stone');
}

function makeVillageWall() {
  const R = 22;
  for (let i = -R; i <= R; i++) {
    if (Math.abs(i) < 3) continue;
    for (let h = 0; h < 3; h++) {
      placeBlock(i,  h+0.5, -R, 'cobble');
      placeBlock(i,  h+0.5,  R, 'cobble');
      placeBlock(-R, h+0.5,  i, 'cobble');
      placeBlock( R, h+0.5,  i, 'cobble');
    }
  }
}

function generateWorld() {
  for (let i = 0; i < 40; i++) {
    const x = (Math.random()-0.5)*200, z = (Math.random()-0.5)*200;
    if (Math.abs(x)>28 || Math.abs(z)>28) makeTree(x, z);
  }
  for (let i = 0; i < 6; i++) {
    const x = (Math.random()-0.5)*180, z = (Math.random()-0.5)*180;
    if (Math.abs(x)>35 || Math.abs(z)>35) makeLavaPool(x, z);
  }
  makeFountain(0, 0);
  makeVillageWall();
  [[-12,-10],[12,-10],[-12,10],[12,10],[-12,0],[12,0],[0,-14],[0,14]]
    .forEach(([hx,hz]) => makeHouse(hx, hz));
}
generateWorld();

// === VILLAGERS ===
const villagers = [];
function makeVillager(x, z) {
  const g = new THREE.Group();
  const body = new THREE.Mesh(new THREE.BoxGeometry(0.6,1.0,0.4), new THREE.MeshLambertMaterial({color:0x5c3317}));
  body.position.y = 0.5; g.add(body);
  const head = new THREE.Mesh(new THREE.BoxGeometry(0.55,0.55,0.55), new THREE.MeshLambertMaterial({color:0xffdbac}));
  head.position.y = 1.28; g.add(head);
  const nose = new THREE.Mesh(new THREE.BoxGeometry(0.12,0.22,0.22), new THREE.MeshLambertMaterial({color:0xffdbac}));
  nose.position.set(0, 1.22, 0.38); g.add(nose);
  [-0.14, 0.14].forEach(ex => {
    const eye = new THREE.Mesh(new THREE.BoxGeometry(0.1,0.1,0.05), new THREE.MeshBasicMaterial({color:0x111111}));
    eye.position.set(ex, 1.32, 0.28); g.add(eye);
  });
  g.position.set(x, 0, z);
  scene.add(g);
  villagers.push({ mesh:g, hp:20, wanderTimer:0, wx:0, wz:0 });
}
[[-5,-5],[5,-5],[-5,5],[5,5],[0,-9],[0,9],[-9,0],[9,0]]
  .forEach(([x,z]) => makeVillager(x, z));

// === MONSTERS ===
const monsters = [];
function makeMonster(x, z) {
  const g = new THREE.Group();
  const torso = new THREE.Mesh(new THREE.BoxGeometry(0.6,0.8,0.35), new THREE.MeshLambertMaterial({color:0x2d7a2d}));
  torso.position.y = 0.5; g.add(torso);
  const head = new THREE.Mesh(new THREE.BoxGeometry(0.55,0.55,0.55), new THREE.MeshLambertMaterial({color:0x3a8f3a}));
  head.position.y = 1.18; g.add(head);
  [-0.55, 0.55].forEach(side => {
    const arm = new THREE.Mesh(new THREE.BoxGeometry(0.22,0.65,0.22), new THREE.MeshLambertMaterial({color:0x2d7a2d}));
    arm.position.set(side, 0.75, 0.28); arm.rotation.x = -Math.PI/2.5; g.add(arm);
  });
  [-0.12, 0.12].forEach(ex => {
    const eye = new THREE.Mesh(new THREE.BoxGeometry(0.1,0.1,0.05), new THREE.MeshBasicMaterial({color:0xff0000}));
    eye.position.set(ex, 1.22, 0.28); g.add(eye);
  });
  g.position.set(x, 0, z);
  scene.add(g);
  monsters.push({ mesh:g, hp:10, speed:0.025+Math.random()*0.02, attackTimer:0 });
}

// === PLAYER ===
const player = { hp:20, maxHp:20, invincible:0, onGround:false };
const keys   = {};
let yaw = Math.PI, pitch = 0, locked = false;

// === POINTER LOCK ===
document.getElementById('overlay').addEventListener('click', () => {
  if (!inventoryOpen) renderer.domElement.requestPointerLock();
});
document.addEventListener('pointerlockchange', () => {
  locked = document.pointerLockElement === renderer.domElement;
  if (!locked && !inventoryOpen)
    document.getElementById('overlay').style.display = 'flex';
  else
    document.getElementById('overlay').style.display = 'none';
});
document.addEventListener('mousemove', e => {
  if (!locked) return;
  yaw  -= e.movementX * 0.0022;
  pitch = Math.max(-1.2, Math.min(1.2, pitch - e.movementY * 0.0022));
});
document.addEventListener('keydown', e => {
  keys[e.code] = true;
  if (e.code === 'KeyE') { toggleInventory(); return; }
  for (let i = 0; i < 9; i++)
    if (e.code === 'Digit'+(i+1)) { selectedSlot = i; renderHotbar(); }
});
document.addEventListener('keyup', e => keys[e.code] = false);

// === RAYCASTING ===
const ray = new THREE.Raycaster();
function rayHitBlock() {
  ray.setFromCamera({ x:0, y:0 }, camera);
  const hits = ray.intersectObjects(placedBlocks);
  return hits.length > 0 && hits[0].distance < 5 ? hits[0] : null;
}
function rayHitMonster() {
  ray.setFromCamera({ x:0, y:0 }, camera);
  const hits = ray.intersectObjects(monsters.map(m => m.mesh), true);
  if (hits.length > 0 && hits[0].distance < 4) {
    const obj = hits[0].object;
    return monsters.find(m => m.mesh === obj || m.mesh === obj.parent);
  }
  return null;
}

// LEFT CLICK = break block / punch monster
renderer.domElement.addEventListener('click', () => {
  if (!locked) return;
  const monster = rayHitMonster();
  if (monster) {
    monster.hp -= 5;
    const kb = monster.mesh.position.clone().sub(camera.position).normalize();
    monster.mesh.position.x += kb.x * 1.5;
    monster.mesh.position.z += kb.z * 1.5;
    if (monster.hp <= 0) {
      scene.remove(monster.mesh);
      monsters.splice(monsters.indexOf(monster), 1);
    }
    return;
  }
  const hit = rayHitBlock();
  if (hit) {
    const block = hit.object;
    if (block.userData.type !== 'lava') {
      block.userData.hp--;
      block.material.emissive.set(0xff0000);
      setTimeout(() => { if (block.material) block.material.emissive.set(0x000000); }, 100);
      if (block.userData.hp <= 0) {
        addToInventory(block.userData.type);
        scene.remove(block);
        placedBlocks.splice(placedBlocks.indexOf(block), 1);
      }
    }
  }
});

// RIGHT CLICK = place block
renderer.domElement.addEventListener('contextmenu', e => {
  e.preventDefault();
  if (!locked) return;
  const hit = rayHitBlock();
  if (!hit) return;
  const type = consumeSelected();
  if (!type) return;
  const pos = hit.object.position.clone().add(hit.face.normal);
  if (pos.distanceTo(camera.position) > 1.2) {
    placeBlock(pos.x, pos.y, pos.z, type);
  } else {
    addToInventory(type); // refund if too close to player
  }
});

// === DAY / NIGHT ===
let time = 0.3, night = false, wasNight = false, nightsSurvived = 0;
const DAY_LENGTH = 1800;
const SKY_DAY    = new THREE.Color(0x87CEEB);
const SKY_SUNSET = new THREE.Color(0xff6b35);
const SKY_NIGHT  = new THREE.Color(0x05080f);

function updateDayNight() {
  time += 1/DAY_LENGTH; if (time >= 1) time = 0;
  let sky;
  if      (time < 0.22) sky = SKY_NIGHT.clone().lerp(SKY_SUNSET, time/0.22);
  else if (time < 0.30) sky = SKY_SUNSET.clone().lerp(SKY_DAY,   (time-0.22)/0.08);
  else if (time < 0.70) sky = SKY_DAY.clone();
  else if (time < 0.78) sky = SKY_DAY.clone().lerp(SKY_SUNSET,   (time-0.70)/0.08);
  else                  sky = SKY_SUNSET.clone().lerp(SKY_NIGHT,  (time-0.78)/0.22);
  scene.background = sky;
  scene.fog.color.copy(sky);
  const isDay = time > 0.25 && time < 0.75;
  night = !isDay;
  const sunAngle = (time - 0.25) * Math.PI * 2;
  sunLight.position.set(Math.cos(sunAngle)*60, Math.sin(sunAngle)*60, 20);
  sunLight.intensity = Math.max(0, Math.sin(time*Math.PI*2 - Math.PI*0.5));
  ambientLight.intensity = isDay ? 0.55 : 0.08;
  moonLight.visible = night;
  moonLight.position.set(-Math.cos(sunAngle)*60, -Math.sin(sunAngle)*60, -20);
  if (!night && wasNight) nightsSurvived++;
  wasNight = night;
}

// === MONSTER SPAWNING ===
let spawnTimer = 0;
function spawnMonsters() {
  if (!night) return;
  if (++spawnTimer > 180) {
    spawnTimer = 0;
    const angle = Math.random()*Math.PI*2, dist = 35+Math.random()*20;
    makeMonster(Math.cos(angle)*dist, Math.sin(angle)*dist);
  }
}

// === MONSTER AI ===
function updateMonsters() {
  for (let i = monsters.length-1; i >= 0; i--) {
    const m = monsters[i];
    let nearest = camera.position.clone();
    let nearestDist = m.mesh.position.distanceTo(camera.position);
    villagers.forEach(v => {
      const d = m.mesh.position.distanceTo(v.mesh.position);
      if (d < nearestDist) { nearestDist = d; nearest = v.mesh.position.clone(); }
    });
    const dir = nearest.clone().sub(m.mesh.position); dir.y = 0;
    if (dir.length() > 0.1) {
      dir.normalize();
      m.mesh.position.x += dir.x * m.speed;
      m.mesh.position.z += dir.z * m.speed;
      m.mesh.lookAt(nearest.x, m.mesh.position.y, nearest.z);
    }
    m.mesh.position.y = Math.max(0, Math.abs(Math.sin(Date.now()*0.008+i))*0.08);
    if (m.mesh.position.distanceTo(camera.position) < 1.3) {
      m.attackTimer++;
      if (m.attackTimer > 60 && player.invincible <= 0) {
        m.attackTimer = 0; player.hp -= 2; player.invincible = 50;
        if (player.hp <= 0) {
          document.exitPointerLock();
          document.getElementById('overlay').innerHTML =
            '<h1 style="color:#e94560">YOU DIED</h1><p>Refresh to try again</p>';
          document.getElementById('overlay').style.display = 'flex';
        }
      }
    }
    villagers.forEach((v, vi) => {
      if (m.mesh.position.distanceTo(v.mesh.position) < 1.2) {
        m.attackTimer++;
        if (m.attackTimer > 80) {
          m.attackTimer = 0; v.hp -= 2;
          if (v.hp <= 0) {
            scene.remove(v.mesh); villagers.splice(vi, 1);
            if (villagers.length === 0) {
              document.exitPointerLock();
              document.getElementById('overlay').innerHTML =
                '<h1 style="color:#e94560">VILLAGE FELL</h1><p>All villagers died.</p>';
              document.getElementById('overlay').style.display = 'flex';
            }
          }
        }
      }
    });
    if (!night) {
      m.hp -= 0.05;
      m.mesh.children.forEach(c => { if (c.material) c.material.emissive = new THREE.Color(0xff2200); });
      if (m.hp <= 0) { scene.remove(m.mesh); monsters.splice(i, 1); }
    }
  }
}

// === VILLAGER AI ===
function updateVillagers() {
  villagers.forEach(v => {
    v.wanderTimer--;
    if (v.wanderTimer <= 0) {
      v.wanderTimer = 80 + Math.random()*120;
      if (night) {
        const a = Math.atan2(-v.mesh.position.z, -v.mesh.position.x);
        v.wx = Math.cos(a)*0.05; v.wz = Math.sin(a)*0.05;
      } else {
        const a = Math.random()*Math.PI*2;
        v.wx = Math.cos(a)*0.02; v.wz = Math.sin(a)*0.02;
      }
    }
    if (Math.abs(v.mesh.position.x) < 20 && Math.abs(v.mesh.position.z) < 20) {
      v.mesh.position.x += v.wx; v.mesh.position.z += v.wz;
    } else { v.wx *= -1; v.wz *= -1; }
    v.mesh.rotation.y = Math.atan2(v.wx, v.wz);
    v.mesh.position.y = Math.abs(Math.sin(Date.now()*0.004))*0.04;
  });
}

// === HUD ===
function updateHUD() {
  let html = '';
  for (let i = 0; i < player.maxHp/2; i++) html += i < player.hp/2 ? '❤️' : '🖤';
  document.getElementById('hearts').innerHTML = html;
  const phase = night ? '🌙 NIGHT — Defend!' : '☀️ DAY';
  document.getElementById('status').textContent =
    `${phase}  |  Villagers: ${villagers.length}  |  Monsters: ${monsters.length}  |  Nights: ${nightsSurvived}`;
}

// === PLAYER MOVEMENT ===
const vel = new THREE.Vector3();
function updatePlayer() {
  if (player.invincible > 0) player.invincible--;
  vel.y -= 0.01;
  const forward = new THREE.Vector3(-Math.sin(yaw), 0, -Math.cos(yaw));
  const right   = new THREE.Vector3( Math.cos(yaw), 0, -Math.sin(yaw));
  const move    = new THREE.Vector3();
  if (keys['KeyW']    || keys['ArrowUp'])    move.add(forward);
  if (keys['KeyS']    || keys['ArrowDown'])  move.sub(forward);
  if (keys['KeyA']    || keys['ArrowLeft'])  move.sub(right);
  if (keys['KeyD']    || keys['ArrowRight']) move.add(right);
  if (move.length() > 0) move.normalize();
  if (keys['Space'] && player.onGround) { vel.y = 0.18; player.onGround = false; }
  camera.position.x += move.x * 0.09 + vel.x;
  camera.position.z += move.z * 0.09 + vel.z;
  camera.position.y += vel.y;
  if (camera.position.y < 1.7) { camera.position.y = 1.7; player.onGround = true; vel.y = 0; }
  placedBlocks.forEach(b => {
    if (b.userData.type === 'lava' && b.position.distanceTo(camera.position) < 1.8)
      player.hp = Math.max(0, player.hp - 0.05);
  });
  camera.rotation.order = 'YXZ';
  camera.rotation.y = yaw;
  camera.rotation.x = pitch;
}

// === MAIN LOOP ===
let frame = 0;
function loop() {
  requestAnimationFrame(loop);
  frame++;
  if (!inventoryOpen) {
    updateDayNight();
    updatePlayer();
    spawnMonsters();
    if (frame % 2 === 0) updateMonsters();
    if (frame % 3 === 0) updateVillagers();
  }
  if (frame % 20 === 0) updateHUD();
  renderer.render(scene, camera);
}
loop();
