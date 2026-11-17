import * as THREE from 'three';
import { heightAt } from './terrain.js';

// Memo himself: a small round mossy creature with a leaf tail, a sprout on his head and a notebook.
const mat = (color, o = {}) => new THREE.MeshStandardMaterial({ color, roughness: 0.9, ...o });
const SPH = new THREE.SphereGeometry(0.5, 32, 24), BLOB = new THREE.IcosahedronGeometry(0.5, 1);
function part(parent, geo, material, scale, pos, rot) {
  const m = new THREE.Mesh(geo, material);
  m.scale.set(...(Array.isArray(scale) ? scale : [scale, scale, scale]));
  m.position.set(...pos); if (rot) m.rotation.set(...rot);
  m.castShadow = true; parent.add(m); return m;
}

export class Memo {
  constructor() {
    this.root = new THREE.Group();      // world position + facing
    this.body = new THREE.Group();      // squash, bob, lean
    this.root.add(this.body);
    const moss = mat('#86ad5c', { roughness: 1 }), mossDark = mat('#6c9449', { roughness: 1 }), mossLight = mat('#a5c96f', { roughness: 1 });
    const cream = mat('#f3e9cf'), dark = mat('#26221d', { roughness: 0.25 }), white = mat('#ffffff', { roughness: 0.2 });
    const pink = mat('#f2a7a0'), foot = mat('#d99a5b'), leaf = mat('#6fb04f', { roughness: 0.7, side: THREE.DoubleSide }), leafLight = mat('#9ad070', { roughness: 0.7 });

    part(this.body, SPH, moss, [0.86, 0.8, 0.8], [0, 0.46, 0]);
    part(this.body, SPH, cream, [0.6, 0.56, 0.5], [0, 0.4, 0.17]);
    // moss tufts over the back and head
    let s = 3;
    const rnd = () => { s = (s * 16807) % 2147483647; return s / 2147483647; };
    for (let i = 0; i < 22; i++) {
      const th = rnd() * Math.PI * 2, ph = rnd() * 1.15;
      const x = Math.sin(ph) * Math.cos(th) * 0.42, y = Math.cos(ph) * 0.39, z = Math.sin(ph) * Math.sin(th) * 0.39;
      if (z > 0.2 && y < 0.3) continue;
      part(this.body, BLOB, [moss, mossDark, mossLight][i % 3], 0.13 + rnd() * 0.1, [x, 0.46 + y, z], [rnd() * 3, rnd() * 3, 0]);
    }
    // face
    this.eyes = [];
    for (const sx of [-1, 1]) {
      const eye = new THREE.Group(); eye.position.set(sx * 0.155, 0.56, 0.345); this.body.add(eye);
      part(eye, SPH, dark, [0.115, 0.135, 0.07], [0, 0, 0]);
      part(eye, SPH, white, 0.04, [sx * -0.02, 0.035, 0.03]);
      this.eyes.push(eye);
      part(this.body, SPH, pink, [0.1, 0.06, 0.04], [sx * 0.26, 0.45, 0.33]);
    }
    part(this.body, SPH, mat('#c98f6b'), [0.07, 0.05, 0.05], [0, 0.49, 0.4]);
    // sprout
    this.sprout = new THREE.Group(); this.sprout.position.set(0, 0.84, 0.02); this.body.add(this.sprout);
    part(this.sprout, new THREE.CylinderGeometry(0.012, 0.018, 0.16, 6), leaf, 1, [0, 0.06, 0]);
    this.leaves = [
      part(this.sprout, SPH, leafLight, [0.17, 0.03, 0.09], [0.07, 0.15, 0], [0, 0, 0.5]),
      part(this.sprout, SPH, leafLight, [0.17, 0.03, 0.09], [-0.07, 0.15, 0], [0, 0, -0.5]),
      part(this.sprout, SPH, leaf, [0.13, 0.03, 0.07], [0, 0.2, 0.05], [0.6, 1.57, 0]),
      part(this.sprout, SPH, leaf, [0.13, 0.03, 0.07], [0, 0.2, -0.05], [-0.6, 1.57, 0]),
    ];
    // leaf tail
    this.tail = new THREE.Group(); this.tail.position.set(0, 0.34, -0.36); this.body.add(this.tail);
    part(this.tail, SPH, leaf, [0.26, 0.04, 0.5], [0, 0.1, -0.2], [0.55, 0, 0]);
    part(this.tail, new THREE.CylinderGeometry(0.01, 0.014, 0.46, 5), mossDark, 1, [0, 0.115, -0.2], [0.55 + Math.PI / 2, 0, 0]);
    // limbs
    this.feet = [part(this.root, SPH, foot, [0.17, 0.09, 0.24], [-0.15, 0.045, 0.1]), part(this.root, SPH, foot, [0.17, 0.09, 0.24], [0.15, 0.045, 0.1])];
    this.arms = [];
    for (const sx of [-1, 1]) {
      const arm = new THREE.Group(); arm.position.set(sx * 0.38, 0.44, 0.08); this.body.add(arm);
      part(arm, SPH, moss, [0.12, 0.22, 0.12], [0, -0.07, 0.02]);
      this.arms.push(arm);
    }
    // notebook
    this.book = new THREE.Group(); this.arms[1].add(this.book); this.book.position.set(0.04, -0.16, 0.1);
    part(this.book, new THREE.BoxGeometry(1, 1, 1), mat('#8c4f3a'), [0.2, 0.25, 0.05], [0, 0, 0]);
    part(this.book, new THREE.BoxGeometry(1, 1, 1), mat('#f6efdc'), [0.17, 0.22, 0.055], [0.01, 0, 0]);
    part(this.book, new THREE.BoxGeometry(1, 1, 1), mat('#e6c35c', { metalness: 0.6, roughness: 0.4 }), [0.03, 0.26, 0.06], [-0.07, 0, 0]);

    this.target = new THREE.Vector3(); this.state = { activity: 'idle' };
    this.blink = 2; this.placed = false; this.facing = 0;
    this.setMaturity(0);
  }

  // Growing up: bigger, calmer proportions, and more leaves on the sprout. Stops at adult.
  setMaturity(m) {
    this.maturity = m;
    this.root.scale.setScalar(0.72 + 0.33 * m);
    const eye = 1.28 - 0.3 * m;
    for (const e of this.eyes) e.userData.base = eye;
    this.leaves[2].visible = this.leaves[3].visible = m >= 0.5;
    this.sprout.scale.setScalar(0.85 + 0.5 * m);
    this.tail.scale.setScalar(0.8 + 0.4 * m);
  }

  setState(memo) {
    this.state = memo;
    this.target.set(memo.x, 0, memo.z);
    if (!this.placed) { this.root.position.set(memo.x, heightAt(memo.x, memo.z), memo.z); this.placed = true; }
    if (memo.maturity !== undefined && Math.abs(memo.maturity - this.maturity) > 0.01) this.setMaturity(memo.maturity);
  }

  get walking() { return Math.hypot(this.target.x - this.root.position.x, this.target.z - this.root.position.z) > 0.08; }

  update(dt, t) {
    const p = this.root.position, act = this.state.activity;
    const asleep = this.state.asleep || act === 'napping' || act === 'sleeping';
    const dx = this.target.x - p.x, dz = this.target.z - p.z, dist = Math.hypot(dx, dz);
    let bob = 0, lean = 0, squash = 1 + Math.sin(t * 2.2) * 0.02;
    const walking = dist > 0.08;
    if (walking) {
      const step = Math.min(dist, dt * (dist > 30 ? 30 : 2.2));
      p.x += (dx / dist) * step; p.z += (dz / dist) * step;
      this.facing = Math.atan2(dx, dz);
      bob = Math.abs(Math.sin(t * 9)) * 0.09; lean = 0.12;
      this.feet[0].position.z = 0.1 + Math.sin(t * 9) * 0.12; this.feet[1].position.z = 0.1 - Math.sin(t * 9) * 0.12;
      this.feet[0].position.y = 0.045 + Math.max(0, Math.sin(t * 9)) * 0.06; this.feet[1].position.y = 0.045 + Math.max(0, -Math.sin(t * 9)) * 0.06;
    } else {
      for (const f of this.feet) { f.position.z += (0.1 - f.position.z) * 0.2; f.position.y += (0.045 - f.position.y) * 0.2; }
    }
    p.y = heightAt(p.x, p.z);
    let d = this.facing - this.root.rotation.y; d = Math.atan2(Math.sin(d), Math.cos(d));
    this.root.rotation.y += d * Math.min(1, dt * 7);

    let armL = 0, armR = 0, bookFront = 0, tilt = 0;
    if (!walking) {
      if (asleep) { squash = 0.86 + Math.sin(t * 1.1) * 0.035; lean = -0.1; }
      else if (act === 'gathering') { lean = 0.35 + Math.sin(t * 3) * 0.15; armL = -1.0; }
      else if (act === 'writing') { bookFront = 1; armL = -1.1 + Math.sin(t * 14) * 0.12; armR = -0.9; lean = 0.1; }
      else if (act === 'crafting') { bob = Math.abs(Math.sin(t * 5)) * 0.05; armL = -0.9 + Math.sin(t * 10) * 0.5; armR = -0.9 - Math.sin(t * 10) * 0.5; }
      else if (act === 'looking') { tilt = Math.sin(t * 0.9) * 0.16; }
      else if (act === 'computing') { armL = -1.0 + Math.sin(t * 16) * 0.1; armR = -1.0 - Math.sin(t * 16) * 0.1; lean = 0.08; }
      else if (act === 'playing') { bob = Math.abs(Math.sin(t * 6)) * 0.16; tilt = Math.sin(t * 6) * 0.1; }
      else tilt = Math.sin(t * 0.5) * 0.04;
    }
    this.body.position.y += (bob - this.body.position.y) * 0.4;
    this.body.rotation.x += (lean - this.body.rotation.x) * 0.12;
    this.body.rotation.z += (tilt - this.body.rotation.z) * 0.1;
    this.body.scale.set(1 + (1 - squash) * 0.6, squash, 1 + (1 - squash) * 0.6);
    this.arms[0].rotation.x += (armL - this.arms[0].rotation.x) * 0.25;
    this.arms[1].rotation.x += (armR - bookFront * 0.3 - this.arms[1].rotation.x) * 0.25;
    this.tail.rotation.y = Math.sin(t * (walking ? 8 : 1.6)) * (asleep ? 0.03 : 0.22);
    this.sprout.rotation.z = Math.sin(t * 1.9) * 0.08;

    this.blink -= dt;
    if (this.blink < -0.12) this.blink = 2 + Math.random() * 4;
    const closed = asleep || this.blink < 0;
    for (const e of this.eyes) { const b = e.userData.base || 1; e.scale.set(b, closed ? b * 0.12 : b, b); }
  }
}
