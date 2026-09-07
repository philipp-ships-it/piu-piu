/** Oberfläche, lokale Speicherung und Bedienung der Browser-Arcade. */
import {World, PRESETS, FPS, drawWorld} from './world.js';

const $ = id => document.getElementById(id);
const canvas = $('world'), context = canvas.getContext('2d');
const overlay = $('game-overlay'), start = $('start-game');
const preference = matchMedia('(prefers-reduced-motion: reduce)');
let motionPaused = preference.matches;
let world = null, running = false, best = 0, selected = 'normal';
let previous = 0, accumulator = 0, idle = 0, confirming = false;
const storageKey = 'piu-piu.arcade.v2';
const cancel = document.createElement('button');
cancel.className = 'button'; cancel.textContent = 'Zurück zur Runde'; cancel.hidden = true;
overlay.append(cancel);

function notify(message) { $('game-notice').textContent = message; }
function save() {
  try {
    localStorage.setItem(storageKey, JSON.stringify({version: 2, best, selected,
      checkpoint: world && !world.dead ? world.snapshot() : null}));
  } catch { $('storage-warning').hidden = false; }
}
function load() {
  try {
    const raw = localStorage.getItem(storageKey);
    if (!raw) return;
    if (raw.length > 200000) throw new Error('Speicherstand zu groß.');
    const data = JSON.parse(raw);
    if (data?.version !== 2 || !Number.isSafeInteger(data.best) || data.best < 0 ||
        !Object.hasOwn(PRESETS, data.selected)) throw new Error('Ungültiges Profil.');
    best = data.best; selected = data.selected;
    if (data.checkpoint !== null) world = World.restore(data.checkpoint);
    if (world?.dead) world = null;
  } catch (error) {
    if (error.name === 'SecurityError') $('storage-warning').hidden = false;
    else notify('Der Browser-Spielstand ist nicht lesbar. Du kannst eine neue Runde starten.');
  }
}
function updateHUD() {
  $('score').textContent = String(world?.score ?? 0).padStart(5, '0');
  $('best').textContent = String(best).padStart(5, '0');
  $('ammo').textContent = world?.reload > 0 ? `${world.reload.toFixed(1)}s` : `${world?.ammo ?? PRESETS[selected].ammo}/${PRESETS[world?.difficulty ?? selected].ammo}`;
  $('difficulty').disabled = Boolean(world && !world.dead);
  $('pause-game').disabled = !world || world.dead || confirming;
  $('pause-game').textContent = running || !world ? 'Pause [P]' : 'Weiter [P]';
}
function showOverlay(title, text, action) {
  overlay.hidden = false;
  $('overlay-title').textContent = title;
  $('overlay-copy').textContent = text;
  start.textContent = action;
  updateHUD();
}
function begin() {
  if (confirming) { world = null; confirming = false; cancel.hidden = true; }
  if (!world || world.dead) world = new World(selected, Date.now());
  overlay.hidden = true; running = true; accumulator = 0; previous = performance.now();
  notify('Runde läuft. Leertaste: springen. Enter: schießen. P: Pause.');
  updateHUD(); save(); canvas.focus({preventScroll: true});
}
function pause() {
  if (!world || world.dead) return;
  running = false; accumulator = 0; save();
  showOverlay('Kurz durchatmen.', 'Deine Runde bleibt hier. Dein nächstes piu auch.', 'Runde fortsetzen →');
}
function newRound() {
  if (world && !world.dead) {
    pause(); confirming = true; cancel.hidden = false;
    showOverlay('Nochmal von vorn?', 'Dein bisheriger Rundenstand wird durch eine neue Runde ersetzt.', 'Ja, neue Runde →');
    start.focus({preventScroll: true});
  } else begin();
}
start.addEventListener('click', begin);
$('hero-play').addEventListener('click', () => { canvas.scrollIntoView({block: 'center', behavior: motionPaused ? 'instant' : 'smooth'}); begin(); });
cancel.addEventListener('click', () => { confirming = false; cancel.hidden = true; begin(); });
$('pause-game').addEventListener('click', () => running ? pause() : begin());
$('new-game').addEventListener('click', newRound);
$('difficulty').addEventListener('change', event => { selected = event.target.value; save(); updateHUD(); });
canvas.addEventListener('keydown', event => {
  if (event.repeat) return;
  const key = event.key.toLowerCase();
  const action = ({' ': 'jump', w: 'jump', arrowup: 'jump', s: 'duck', arrowdown: 'duck', enter: 'shoot'})[key];
  if (key === 'p' || key === 'escape') {
    event.preventDefault(); if (running) pause(); else if (world && !world.dead && !confirming) begin();
  } else if (action && running) { event.preventDefault(); world.action(action); }
});
document.querySelectorAll('[data-action]').forEach(button => button.addEventListener('click', () => {
  if (running) { world.action(button.dataset.action); canvas.focus({preventScroll: true}); }
}));
window.addEventListener('pagehide', () => { if (running) pause(); else save(); });
window.addEventListener('blur', () => { if (running) pause(); });
document.addEventListener('visibilitychange', () => { if (document.hidden && running) pause(); });
function updateMotion() {
  document.body.classList.toggle('paused-motion', motionPaused);
  $('motion-toggle').setAttribute('aria-pressed', String(motionPaused));
  $('motion-toggle').textContent = motionPaused ? 'Animationen fortsetzen' : 'Animationen pausieren';
}
$('motion-toggle').addEventListener('click', () => { motionPaused = !motionPaused; updateMotion(); });
preference.addEventListener('change', event => { motionPaused = event.matches; updateMotion(); });
$('copy-command').addEventListener('click', async () => {
  try { await navigator.clipboard.writeText('python piuu.py'); $('copy-command').textContent = 'KOPIERT ✓'; }
  catch { $('copy-command').textContent = 'BITTE MARKIEREN'; const range = document.createRange(); range.selectNodeContents($('install-command')); const selection = getSelection(); selection.removeAllRanges(); selection.addRange(range); }
});
function frame(now) {
  const dt = Math.min(.22, Math.max(0, (now - previous) / 1000)); previous = now;
  if (running) {
    accumulator += dt;
    while (accumulator >= 1 / FPS && running) {
      world.step(); accumulator -= 1 / FPS;
      if (world.dead) {
        running = false; best = Math.max(best, world.score); save();
        showOverlay('Autsch. Nochmal?', `${world.score} Punkte. ${world.kills} Hindernisse weniger. Da geht noch was.`, 'Noch eine Runde →');
        notify(`Game Over. ${world.score} Punkte. Bestleistung ${best}.`);
      } else if (world.tick % 90 === 0) save();
    }
    updateHUD();
  } else if (!motionPaused && !document.hidden) idle += dt * FPS;
  drawWorld(context, world, Math.floor(idle));
  requestAnimationFrame(frame);
}
load(); $('difficulty').value = selected; updateHUD(); updateMotion();
if (world) showOverlay('Dein piu hat gewartet.', `${world.score} Punkte. Deine gespeicherte Runde ist bereit.`, 'Runde fortsetzen →');
requestAnimationFrame(frame);
