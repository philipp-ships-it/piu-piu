/** Eigenständige Browser-Simulation. Keine DOM-, Uhr- oder Speicherzugriffe. */
export const PRESETS = Object.freeze({
  leicht: { speed: .75, density: .6, ammo: 15 },
  normal: { speed: 1, density: 1, ammo: 10 },
  schwer: { speed: 1.35, density: 1.35, ammo: 8 },
  irre: { speed: 1.75, density: 1.55, ammo: 6 },
});
export const FPS = 18;
export const GROUND = 20;
const SHAPES = [
  ['  _  ', ' | | ', '_|_|_'], [' __ ', '/  \\', '\\__/'], ['/\\', '/_\\'],
  [' %%% ', '%%%%%', ' \\|/ '], ['piu piu'], ['~o>', ' ^ '],
];

export class World {
  constructor(difficulty = 'normal', seed = 7) {
    if (!Object.hasOwn(PRESETS, difficulty)) throw new Error('Unbekannte Schwierigkeit.');
    this.difficulty = difficulty;
    this.seed = seed >>> 0;
    this.tick = 0; this.distance = 0; this.score = 0; this.kills = 0;
    this.y = 0; this.vy = 0; this.jumps = 0; this.duck = 0;
    this.ammo = PRESETS[difficulty].ammo; this.reload = 0; this.window = 30;
    this.spawn = 28; this.obstacles = []; this.bullets = []; this.particles = [];
    this.dead = false;
  }
  random() {
    this.seed = (Math.imul(1664525, this.seed) + 1013904223) >>> 0;
    return this.seed / 4294967296;
  }
  action(action) {
    if (this.dead) return;
    if (action === 'jump' && this.jumps < 2) {
      this.vy = this.jumps === 0 ? 1.55 : 1.35;
      this.jumps++; this.duck = 0;
    } else if (action === 'duck') {
      if (this.y === 0) this.duck = 8;
      else this.vy -= .9;
    } else if (action === 'shoot' && this.ammo > 0 && this.reload === 0) {
      this.bullets.push({ x: 12, y: GROUND - 1 - Math.round(this.y) });
      this.ammo--;
      if (this.ammo === 0) this.reload = 5;
    }
  }
  burst(obstacle) {
    this.kills++;
    this.obstacles = this.obstacles.filter(other => other !== obstacle);
    for (let i = 0; i < 7; i++) this.particles.push({
      x: obstacle.x + 2, y: GROUND - 2 - obstacle.off,
      vx: this.random() * 1.5 - .75, vy: this.random() - .5, life: 7,
    });
  }
  step() {
    if (this.dead) return;
    this.tick++;
    const preset = PRESETS[this.difficulty];
    const speed = (.95 + 1.75 * (1 - Math.exp(-this.distance / 1400))) * preset.speed;
    this.distance += speed;
    this.vy -= .16; this.y += this.vy;
    if (this.y <= 0) { this.y = 0; this.vy = 0; this.jumps = 0; }
    if (this.duck > 0) this.duck--;
    if (this.reload > 0) {
      this.reload = Math.max(0, this.reload - 1 / FPS);
      if (this.reload < 1e-9) { this.reload = 0; this.ammo = preset.ammo; this.window = 30; }
    } else {
      this.window -= 1 / FPS;
      if (this.window <= 1e-9) { this.window = 30; this.ammo = preset.ammo; }
    }
    for (const obstacle of this.obstacles) obstacle.x -= speed;
    this.obstacles = this.obstacles.filter(o => o.x + SHAPES[o.shape][0].length > 0);
    this.spawn -= speed;
    if (this.spawn <= 0) {
      const shape = Math.floor(this.random() * SHAPES.length);
      this.obstacles.push({x: 57, shape, off: shape === 5 ? 3 : 0});
      this.spawn = (15 + speed * 9) * (.85 + this.random() * .7) / preset.density;
    }
    for (const bullet of [...this.bullets]) {
      const previous = bullet.x; bullet.x += 3.4;
      for (const obstacle of [...this.obstacles]) {
        const rows = SHAPES[obstacle.shape], bottom = GROUND - 1 - obstacle.off;
        const width = Math.max(...rows.map(row => row.length));
        if (previous - obstacle.x - speed <= width && bullet.x >= obstacle.x - 1 &&
            bullet.y <= bottom && bullet.y >= bottom - rows.length + 1) {
          this.burst(obstacle);
          this.bullets = this.bullets.filter(other => other !== bullet);
          break;
        }
      }
    }
    this.bullets = this.bullets.filter(b => b.x < 56);
    for (const p of this.particles) { p.x += p.vx; p.y += p.vy; p.life--; }
    this.particles = this.particles.filter(p => p.life > 0);
    const row = GROUND - 1 - Math.round(this.y);
    for (const obstacle of this.obstacles) {
      const rows = SHAPES[obstacle.shape], bottom = GROUND - 1 - obstacle.off;
      if (obstacle.x <= 10 && obstacle.x + Math.max(...rows.map(r => r.length)) >= 7 &&
          row <= bottom && row >= bottom - rows.length + 1) this.dead = true;
    }
    this.score = Math.floor(this.distance / 3) + this.kills * 25;
  }
  snapshot() { return JSON.parse(JSON.stringify(this)); }
  static restore(data) {
    if (!data || typeof data !== 'object' || !Object.hasOwn(PRESETS, data.difficulty)) throw new Error('Ungültige Browser-Runde.');
    const world = new World(data.difficulty);
    if (Object.keys(data).sort().join() !== Object.keys(world).sort().join()) throw new Error('Unvollständige Browser-Runde.');
    const integers = ['seed', 'tick', 'score', 'kills', 'jumps', 'duck', 'ammo'];
    for (const key of integers) if (!Number.isSafeInteger(data[key]) || data[key] < 0 || data[key] > 2 ** 40) throw new Error('Ungültiger Zähler.');
    for (const key of ['distance', 'y', 'vy', 'reload', 'window', 'spawn']) if (!Number.isFinite(data[key]) || Math.abs(data[key]) > 1e12) throw new Error('Ungültiger Spielwert.');
    if (data.jumps > 2 || data.ammo > PRESETS[data.difficulty].ammo || data.reload < 0 || data.reload > 5 || data.window < 0 || data.window > 30 || data.y < 0 || data.distance < 0 || typeof data.dead !== 'boolean') throw new Error('Spielregeln verletzt.');
    const listFields = {obstacles: ['x', 'shape', 'off'], bullets: ['x', 'y'], particles: ['x', 'y', 'vx', 'vy', 'life']};
    for (const [key, fields] of Object.entries(listFields)) {
      if (!Array.isArray(data[key]) || data[key].length > 1000) throw new Error('Zu viele Spielobjekte.');
      for (const obj of data[key]) {
        if (!obj || Object.keys(obj).sort().join() !== [...fields].sort().join() || fields.some(field => !Number.isFinite(obj[field]) || Math.abs(obj[field]) > 1000)) throw new Error('Ungültiges Spielobjekt.');
        if (key === 'obstacles' && (!Number.isInteger(obj.shape) || obj.shape < 0 || obj.shape >= SHAPES.length || obj.off !== (obj.shape === 5 ? 3 : 0))) throw new Error('Ungültiges Hindernis.');
      }
    }
    if (data.score !== Math.floor(data.distance / 3) + data.kills * 25) throw new Error('Ungültige Punktzahl.');
    return Object.assign(world, JSON.parse(JSON.stringify(data)));
  }
}

/** Zeichenweise Darstellung hält Kaomoji, Kakteen und Landschaft im selben Raster. */
export function drawWorld(context, world, idleTick = 0) {
  const orange = '#ff6b35', pale = '#d9f78b';
  context.fillStyle = '#10120f'; context.fillRect(0, 0, 672, 432);
  context.font = '18px Consolas, "Liberation Mono", monospace';
  context.textBaseline = 'top';
  const put = (x, y, text, color = '#66715a') => {
    context.fillStyle = color;
    Array.from(text).forEach((char, index) => context.fillText(char, (x + index) * 12, y * 18));
  };
  const clock = world ? world.tick : idleTick;
  put(3, 3, ' .        +               .        *     .');
  put(8 - ((clock / 40) % 13), 5, '   .--.');
  put(8 - ((clock / 40) % 13), 6, ' _(    )_');
  put(8 - ((clock / 40) % 13), 7, '(_  __  _)');
  put(39 - ((clock / 75) % 10), 4, '.--.');
  put(38 - ((clock / 75) % 10), 5, '(    )_');
  put(38 - ((clock / 75) % 10), 6, ' `---\'');
  put(25, 9, 'piu piu', '#58624b');
  const distance = world ? world.distance : clock * .3;
  put(0, GROUND, '_'.repeat(56), '#9aa987');
  put(0, GROUND + 1, '^~-_'.repeat(15).slice(Math.floor(distance) % 4, 56 + Math.floor(distance) % 4), '#414b36');
  put(1, GROUND + 3, '+  RENN. SPRING. MACH PIU PIU.  +', '#657156');
  if (!world) {
    put(8, 17, ['(ง•_•)ง', 'ᕦ(•_•)ᕤ'][Math.floor(clock / 5) % 2], orange);
    put(29, 16, '~o>', pale); put(29, 17, Math.floor(clock / 8) % 2 ? ' v ' : ' ^ ', pale);
    put(44, 17, '  _  ', pale); put(44, 18, ' | | ', pale); put(44, 19, '_|_|_', pale);
    return;
  }
  for (const obstacle of world.obstacles) SHAPES[obstacle.shape].forEach((row, index, rows) => put(obstacle.x, GROUND - rows.length - obstacle.off + index, row, pale));
  for (const b of world.bullets) put(b.x, b.y, '-=', orange);
  for (const p of world.particles) put(p.x, p.y, '*', orange);
  const pose = world.dead ? '~(X_X)~' : world.duck ? '(>_<)__' : world.y > .3 ? '\\(•o•)/' : ['(ง•_•)ง', 'ᕦ(•_•)ᕤ'][Math.floor(world.tick / 3) % 2];
  put(6, GROUND - 1 - Math.round(world.y), pose, orange);
  if (world.reload > 0) put(17, 2, `NACHLADEN ${world.reload.toFixed(1)}s`, orange);
}
