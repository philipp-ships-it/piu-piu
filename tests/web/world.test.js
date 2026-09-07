/** Deterministische Browser-Unit-Tests mit dem eingebauten Node-Testläufer. */
import test from 'node:test';
import assert from 'node:assert/strict';
import {World, PRESETS, GROUND, drawWorld} from '../../docs/assets/world.js';

test('Vier Profile setzen Tempo, Dichte und Magazin', () => {
  assert.equal(Object.keys(PRESETS).length, 4);
  for (const [name, preset] of Object.entries(PRESETS)) assert.equal(new World(name).ammo, preset.ammo);
  assert.throws(() => new World('kaputt'));
});
test('Doppelsprung erlaubt keinen dritten Sprung', () => {
  const w = new World(); w.action('jump'); assert.equal(w.vy, 1.55);
  w.action('jump'); w.action('jump'); assert.equal(w.jumps, 2); assert.equal(w.vy, 1.35);
});
test('Leeres Magazin blockiert bis genau Tick 90', () => {
  const w = new World(); w.spawn = 100000;
  for (let i = 0; i < 11; i++) w.action('shoot');
  assert.equal(w.bullets.length, 10); assert.equal(w.ammo, 0);
  for (let i = 0; i < 89; i++) w.step();
  assert.equal(w.ammo, 0); w.step(); assert.equal(w.ammo, 10); assert.equal(w.reload, 0);
});
test('30-Sekunden-Fenster füllt das Magazin', () => {
  const w = new World('leicht'); w.spawn = 100000; w.action('shoot');
  for (let i = 0; i < 539; i++) w.step();
  assert.equal(w.ammo, 14); w.step(); assert.equal(w.ammo, 15);
});
test('Checkpoint reproduziert Physik und Zufallsfolge vollständig', () => {
  const w = new World('leicht', 123);
  for (let i = 0; i < 20; i++) { w.action('jump'); w.step(); }
  const copy = World.restore(JSON.parse(JSON.stringify(w.snapshot())));
  for (let i = 0; i < 100; i++) {
    if (i % 9 === 0) { w.action('shoot'); copy.action('shoot'); }
    if (i % 13 === 0) { w.action('jump'); copy.action('jump'); }
    w.step(); copy.step();
    assert.deepEqual(copy.snapshot(), w.snapshot());
  }
});
test('Keine Listen werden zwischen Snapshot und Instanz geteilt', () => {
  const w = new World(); w.action('shoot'); const saved = w.snapshot(); saved.bullets[0].x = 999;
  assert.equal(w.bullets[0].x, 12);
});
test('Tote Runden reagieren weder auf Takte noch Aktionen', () => {
  const w = new World(); w.dead = true; const before = w.snapshot();
  w.step(); w.action('jump'); w.action('shoot'); assert.deepEqual(w.snapshot(), before);
});
test('Schüsse zerstören ein Hindernis und geben 25 Punkte', () => {
  const w = new World(); w.obstacles = [{x: 15, shape: 0, off: 0}]; w.action('shoot'); w.step();
  assert.equal(w.kills, 1); assert.equal(w.score, 25); assert.equal(w.obstacles.length, 0);
});
test('Bodenkollision beendet die Runde, Flieger über dem Boden nicht', () => {
  const a = new World(); a.obstacles = [{x: 9, shape: 0, off: 0}]; a.step(); assert.equal(a.dead, true);
  const b = new World(); b.obstacles = [{x: 9, shape: 5, off: 3}]; b.step(); assert.equal(b.dead, false);
});
test('Ungültige und unvollständige Speicherstände werden verworfen', () => {
  for (const patch of [{ammo: true}, {ammo: 999}, {difficulty:'unknown'}, {y: NaN}, {seed:-1}, {reload:9}, {score:999}, {obstacles:[{x:1, shape:99, off:0}]}, {bullets:[{x:0}]}, {particles:[null]}]) {
    const saved = {...new World().snapshot(), ...patch}; assert.throws(() => World.restore(saved));
  }
  assert.throws(() => World.restore(null)); assert.throws(() => World.restore({}));
});
test('Zeichnen verändert die Runde nicht und bleibt innerhalb der Canvas-API', () => {
  const calls = []; const ctx = {fillRect(){}, fillText(...args){calls.push(args);}};
  const w = new World(); const before = w.snapshot(); drawWorld(ctx, w); drawWorld(ctx, null, 2);
  assert.deepEqual(w.snapshot(), before); assert.ok(calls.length > 100);
  assert.equal(GROUND, 20);
});
