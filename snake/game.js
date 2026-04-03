// ============================================================
// SNAKE — JavaScript Game Tutorial
// ============================================================
// CONCEPT 1: THE CANVAS
// The <canvas> element is your drawing surface.
// You get a "context" (ctx) from it, then use ctx.fillRect(),
// ctx.drawImage(), etc. to paint every frame.
// ============================================================

const canvas  = document.getElementById('gameCanvas');
const ctx     = canvas.getContext('2d');        // 2D drawing context
const scoreEl = document.getElementById('score');
const msgEl   = document.getElementById('message');

// ============================================================
// CONCEPT 2: CONSTANTS & CONFIGURATION
// Define the rules of your game world up front.
// ============================================================

const GRID       = 20;                   // pixels per grid cell
const COLS       = canvas.width  / GRID; // 20 columns
const ROWS       = canvas.height / GRID; // 20 rows
const TICK_MS    = 120;                  // milliseconds between updates

// ============================================================
// CONCEPT 3: GAME STATE
// Everything that can change is "state".
// Keep it in plain objects/arrays — easy to reset, easy to read.
// ============================================================

let snake;      // array of {x, y} segments, head is [0]
let direction;  // current movement vector {x, y}
let nextDir;    // buffered input so diagonal key presses feel good
let food;       // {x, y} position of the food
let score;
let running;    // is the game loop ticking?
let lastTick;   // timestamp of the last update (for timing)
let animId;     // requestAnimationFrame handle (so we can cancel it)

function initState() {
  snake     = [{ x: 10, y: 10 }, { x: 9, y: 10 }, { x: 8, y: 10 }];
  direction = { x: 1, y: 0 };
  nextDir   = { x: 1, y: 0 };
  food      = randomFood();
  score     = 0;
  running   = false;
  lastTick  = 0;
  updateScore();
}

// ============================================================
// CONCEPT 4: THE GAME LOOP
// requestAnimationFrame calls your function ~60 times/second.
// You decide when to actually *update* logic (every TICK_MS ms).
// Separating "render rate" from "update rate" keeps things smooth.
// ============================================================

function gameLoop(timestamp) {
  animId = requestAnimationFrame(gameLoop); // schedule the next frame

  if (timestamp - lastTick >= TICK_MS) {
    lastTick = timestamp;
    update();      // move the snake, check collisions, etc.
  }

  render();        // draw the current state to the canvas
}

// ============================================================
// CONCEPT 5: UPDATE — the logic step
// Called once per tick. Move things, check rules, change state.
// ============================================================

function update() {
  if (!running) return;

  // Commit buffered direction
  direction = nextDir;

  // Calculate new head position
  const head = {
    x: snake[0].x + direction.x,
    y: snake[0].y + direction.y,
  };

  // --- COLLISION: walls ---
  if (head.x < 0 || head.x >= COLS || head.y < 0 || head.y >= ROWS) {
    endGame();
    return;
  }

  // --- COLLISION: self ---
  if (snake.some(seg => seg.x === head.x && seg.y === head.y)) {
    endGame();
    return;
  }

  // Move: add new head
  snake.unshift(head);

  // --- Did we eat the food? ---
  if (head.x === food.x && head.y === food.y) {
    score += 10;
    updateScore();
    food = randomFood();
    // Don't remove the tail — snake grows!
  } else {
    snake.pop(); // remove tail to keep length constant
  }
}

// ============================================================
// CONCEPT 6: RENDER — the drawing step
// Called every animation frame. Always redraw everything from
// scratch (clear → draw background → draw objects).
// ============================================================

function render() {
  // Clear the canvas
  ctx.fillStyle = '#0f3460';
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  // Draw food
  ctx.fillStyle = '#e94560';
  fillCell(food.x, food.y);

  // Draw snake
  snake.forEach((seg, i) => {
    // Head is slightly brighter than the body
    ctx.fillStyle = i === 0 ? '#4ecca3' : '#1a936f';
    fillCell(seg.x, seg.y);
  });

  // Draw grid lines (subtle)
  ctx.strokeStyle = 'rgba(255,255,255,0.04)';
  ctx.lineWidth = 0.5;
  for (let x = 0; x <= canvas.width; x += GRID) {
    ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, canvas.height); ctx.stroke();
  }
  for (let y = 0; y <= canvas.height; y += GRID) {
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(canvas.width, y); ctx.stroke();
  }
}

// Helper: fill one grid cell with a small gap so cells look distinct
function fillCell(col, row) {
  const gap = 2;
  ctx.fillRect(
    col * GRID + gap,
    row * GRID + gap,
    GRID - gap * 2,
    GRID - gap * 2
  );
}

// ============================================================
// CONCEPT 7: INPUT HANDLING
// Listen for keyboard events. Buffer the direction so the
// player can't reverse into themselves mid-frame.
// ============================================================

const KEY_MAP = {
  ArrowUp:    { x:  0, y: -1 },
  ArrowDown:  { x:  0, y:  1 },
  ArrowLeft:  { x: -1, y:  0 },
  ArrowRight: { x:  1, y:  0 },
};

document.addEventListener('keydown', (e) => {
  const newDir = KEY_MAP[e.key];
  if (!newDir) return;

  e.preventDefault(); // stop page scrolling

  // Prevent 180° reversal (you can't go back into yourself)
  if (newDir.x === -direction.x && newDir.y === -direction.y) return;

  nextDir = newDir;

  // Start the game on the first key press
  if (!running) {
    running  = true;
    lastTick = performance.now();
    msgEl.textContent = '';
  }
});

// ============================================================
// CONCEPT 8: HELPER FUNCTIONS
// Small, focused functions for reusable tasks.
// ============================================================

function randomFood() {
  // Keep trying until the food lands on an empty cell
  let pos;
  do {
    pos = {
      x: Math.floor(Math.random() * COLS),
      y: Math.floor(Math.random() * ROWS),
    };
  } while (snake && snake.some(s => s.x === pos.x && s.y === pos.y));
  return pos;
}

function updateScore() {
  scoreEl.textContent = `Score: ${score}`;
}

function endGame() {
  running = false;
  cancelAnimationFrame(animId);
  msgEl.textContent = `Game over! Score: ${score} — Press any arrow key to play again`;

  // Flash the snake red
  ctx.fillStyle = 'rgba(233, 69, 96, 0.5)';
  snake.forEach(seg => fillCell(seg.x, seg.y));

  // Reset and restart the animation loop (but paused)
  setTimeout(() => {
    initState();
    animId = requestAnimationFrame(gameLoop);
  }, 1000);
}

// ============================================================
// START
// ============================================================

initState();
animId = requestAnimationFrame(gameLoop);
