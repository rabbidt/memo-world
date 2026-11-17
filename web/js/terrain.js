import * as THREE from 'three';
import { positionLocal, positionWorld, time, sin, vec3, mix, uv, attribute, smoothstep, abs, clamp, float } from 'three/tsl';

// The island's shape. One function, used for the ground mesh and for standing things on it.
// Hills and hollows that belong to places (the lookout's hill, the pond's hollow) come from the server
// with the world, so they move when the Keeper moves the place in the layout.
let pathCache = null;
let shaping = [{ x: 22, z: -21, lift: 3.4, radius: 7.5 }, { x: -16, z: -6, lift: -1.15, radius: 4.2 }];
export function setTerrain(list) { if (Array.isArray(list)) shaping = list; }
const smooth = (a, b, v) => { const t = Math.min(1, Math.max(0, (v - a) / (b - a))); return t * t * (3 - 2 * t); };
const gauss = (x, z, c, r) => Math.exp(-((x - c.x) ** 2 + (z - c.z) ** 2) / (r * r));

export function baseHeightAt(x, z) {
  const a = Math.atan2(z, x);
  const r = Math.hypot(x, z) / (1 + 0.07 * Math.sin(3 * a + 1) + 0.045 * Math.sin(5 * a + 2.3) + 0.03 * Math.sin(9 * a));
  const inland = 1 - smooth(22, 36, r);
  let h = 1.35 * inland - 2.2 * smooth(31, 44, r);
  h += (Math.sin(x * 0.21 + 1.3) * Math.cos(z * 0.17) * 0.45 + Math.sin(x * 0.47 + z * 0.39) * 0.16 + Math.sin(z * 0.83 - x * 0.6) * 0.06) * inland;
  h += (Math.sin(x * 0.085 + 0.6) * Math.cos(z * 0.075 - 1.1) * 0.95 + Math.sin(x * 0.05 - z * 0.06 + 2) * 0.5) * inland; // rolling ground
  h = Math.max(h, 0.62 * inland - 2.2 * smooth(31, 44, r)); // no dips below the sea inland
  for (const s of shaping) h += s.lift * gauss(x, z, s, s.radius);
  if (fall) h -= fall.depth * gauss(x, z, fall.pool, 2.7) * smooth(-0.3, 0.3, (x - fall.lip.x) * fall.dx + (z - fall.lip.z) * fall.dz); // a sheer step for the waterfall
  return h;
}

// ---------- the stream ----------
// A stream is a list of places to run through. It is sampled every half metre, given a bed that only
// ever goes downhill, and that bed is cut into the ground, so it makes its own little valley through
// any rise. Where the route passes the waterfall the ground drops in a step and the water falls.
let stream = null, fall = null, bridges = [], season = null;
export function setSeason(s) { season = s; }
export function setStream(route, { width = 1.2, waterfall = null, endLevel = -Infinity, bridgeSpots = [] } = {}) {
  stream = null; fall = null; bridges = bridgeSpots; pathCache = null;
  if (!route || route.length < 2) return;
  if (waterfall) {
    const k = route.findIndex((q) => q.x === waterfall.x && q.z === waterfall.z), prev = route[Math.max(0, k - 1)];
    const len = Math.hypot(waterfall.x - prev.x, waterfall.z - prev.z) || 1, dx = (waterfall.x - prev.x) / len, dz = (waterfall.z - prev.z) / len;
    fall = { pool: waterfall, depth: 2.3, dx, dz, lip: { x: waterfall.x - dx * 1.9, z: waterfall.z - dz * 1.9 } };
  }
  const pts = [], P = (i) => route[Math.min(route.length - 1, Math.max(0, i))];
  let dist = 0;
  for (let i = 0; i < route.length - 1; i++) {
    const a = P(i - 1), b = P(i), c = P(i + 1), d = P(i + 2), len = Math.hypot(c.x - b.x, c.z - b.z), steps = Math.max(2, Math.ceil(len / 0.5));
    for (let j = i ? 1 : 0; j <= steps; j++) {
      const t = j / steps, t2 = t * t, t3 = t2 * t;
      const cr = (p0, p1, p2, p3) => 0.5 * (2 * p1 + (p2 - p0) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (3 * p1 - p0 - 3 * p2 + p3) * t3);
      const wander = Math.sin(t * Math.PI) * Math.sin((dist + t * len) * 0.5) * Math.min(1.1, len * 0.06), nx = -(c.z - b.z) / len, nz = (c.x - b.x) / len;
      pts.push({ x: cr(a.x, b.x, c.x, d.x) + nx * wander, z: cr(a.z, b.z, c.z, d.z) + nz * wander });
    }
    dist += len;
  }
  let level = Infinity, run = 0;
  pts.forEach((q, i) => {
    if (i) run += Math.hypot(q.x - pts[i - 1].x, q.z - pts[i - 1].z);
    q.s = run; q.base = baseHeightAt(q.x, q.z);
    level = Math.min(level, q.base - 0.42);
    q.bed = Math.min(q.base - 0.3, Math.max(level, endLevel - 0.12));
  });
  stream = { pts, width, box: [Math.min(...pts.map((q) => q.x)) - 6, Math.max(...pts.map((q) => q.x)) + 6, Math.min(...pts.map((q) => q.z)) - 6, Math.max(...pts.map((q) => q.z)) + 6] };
}
function nearestOnStream(x, z) {
  if (!stream || x < stream.box[0] || x > stream.box[1] || z < stream.box[2] || z > stream.box[3]) return null;
  let best = null, bd = 49;
  for (const q of stream.pts) { const d = (x - q.x) ** 2 + (z - q.z) ** 2; if (d < bd) { bd = d; best = q; } }
  return best && { q: best, d: Math.sqrt(bd) };
}
// How far a spot is from the water's middle (Infinity when there is no stream nearby).
export const streamDistance = (x, z) => nearestOnStream(x, z)?.d ?? Infinity;

export function heightAt(x, z) {
  const h = baseHeightAt(x, z), n = nearestOnStream(x, z);
  if (!n || n.q.bed >= h) return h;
  const depth = n.q.base - n.q.bed, bank = stream.width * 0.5 + 0.55 + depth * 0.85;
  if (n.d >= bank) return h;
  return h + (n.q.bed - h) * (1 - smooth(stream.width * 0.42, bank, n.d));
}
// Where feet go: the ground, except on a bridge, where it is the deck.
export function walkHeightAt(x, z) {
  for (const b of bridges) { const d = Math.hypot(x - b.x, z - b.z); if (d < 2.6) return Math.max(heightAt(x, z), baseHeightAt(b.x, b.z) + 0.32 + 0.22 * Math.cos((d / 2.6) * Math.PI / 2)); }
  return heightAt(x, z);
}

// The water itself: a ribbon lying in the bed, with a current, foam at the banks and white water on the drops.
export function buildStream() {
  if (!stream) return new THREE.Group();
  const { pts, width } = stream, n = pts.length, pos = new Float32Array(n * 6), uvs = new Float32Array(n * 4), white = new Float32Array(n * 2), idx = [];
  pts.forEach((q, i) => {
    const a = pts[Math.max(0, i - 1)], b = pts[Math.min(n - 1, i + 1)], len = Math.hypot(b.x - a.x, b.z - a.z) || 1, nx = -(b.z - a.z) / len, nz = (b.x - a.x) / len;
    const y = q.bed + 0.17, drop = Math.min(1, Math.max(0, (a.bed - b.bed) / (len * 0.9) - 0.15));
    pos.set([q.x + nx * width * 0.56, y, q.z + nz * width * 0.56, q.x - nx * width * 0.56, y, q.z - nz * width * 0.56], i * 6);
    uvs.set([0, q.s, 1, q.s], i * 4); white.set([drop, drop], i * 2);
    if (i < n - 1) idx.push(i * 2, i * 2 + 2, i * 2 + 1, i * 2 + 1, i * 2 + 2, i * 2 + 3);
  });
  for (let pass = 0; pass < 2; pass++) for (let i = n - 2; i > 0; i--) { const v = Math.max(white[i * 2], white[(i - 1) * 2] * 0.75, white[(i + 1) * 2] * 0.5); white[i * 2] = white[i * 2 + 1] = v; } // foam carries on below a drop
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(pos, 3)); geo.setAttribute('uv', new THREE.BufferAttribute(uvs, 2));
  geo.setAttribute('white', new THREE.BufferAttribute(white, 1)); geo.setIndex(idx); geo.computeVertexNormals();
  const mat = new THREE.MeshStandardNodeMaterial({ roughness: 0.12, metalness: 0.05, transparent: true, side: THREE.DoubleSide });
  const u = uv().x, v = uv().y, rough = attribute('white', 'float');
  const speed = float(1.4).add(rough.mul(3));
  const ripple = sin(v.mul(3.2).sub(time.mul(speed).mul(2.2)).add(sin(u.mul(5).add(v.mul(0.9))).mul(2.2)).add(sin(v.mul(11.3).add(u.mul(3))).mul(0.6)));
  const streaks = smoothstep(0.82, 0.98, ripple).mul(0.55);
  const edge = smoothstep(0.62, 0.95, abs(u.sub(0.5)).mul(2).add(sin(v.mul(5).sub(time.mul(1.5))).mul(0.08)));
  const foam = clamp(streaks.add(edge.mul(0.75)).add(rough.mul(float(0.75).add(ripple.mul(0.25)))), 0, 1);
  const frozen = season?.snow ? 0.35 : 0;
  mat.colorNode = mix(mix(vec3(0.16, 0.5, 0.6), vec3(0.34, 0.7, 0.76), ripple.mul(0.5).add(0.5)), vec3(1, 1, 1), clamp(foam.add(frozen), 0, 1));
  mat.opacityNode = clamp(float(0.78).add(foam.mul(0.3)), 0, 1);
  const mesh = new THREE.Mesh(geo, mat);
  mesh.receiveShadow = true;
  return mesh;
}

const C = (hex) => new THREE.Color(hex);
const SAND = C('#f3e3bd'), SAND_WET = C('#dcc79a'), GRASS = C('#98c964'), GRASS_DARK = C('#6fab52'), MOSS = C('#b9d877'),
  PATH = C('#ead3a4'), ROCK = C('#b9b3a3'), SEABED = C('#69b9b4');

function distToSegment(px, pz, ax, az, bx, bz) {
  const dx = bx - ax, dz = bz - az;
  const t = Math.max(0, Math.min(1, ((px - ax) * dx + (pz - az) * dz) / (dx * dx + dz * dz)));
  return Math.hypot(px - ax - t * dx, pz - az - t * dz);
}

// Winding paths from the notice board out to every place, as points a pace apart.
export function pathSamples(zones) {
  if (pathCache) return pathCache;
  const hub = zones.find((z) => z.id === 'board') || { x: 0, z: 0 }, pts = [];
  zones.forEach((zn, k) => {
    if (zn.id === hub.id) return;
    const dx = zn.x - hub.x, dz = zn.z - hub.z, len = Math.hypot(dx, dz), nx = -dz / len, nz = dx / len, steps = Math.ceil(len / 0.45);
    for (let i = 0; i <= steps; i++) {
      const t = i / steps, sway = Math.sin(t * Math.PI) * (Math.sin(t * 5.5 + k * 1.7) * 1.7 + Math.sin(t * 11 + k) * 0.5);
      pts.push({ x: hub.x + dx * t + nx * sway, z: hub.z + dz * t + nz * sway, t, len });
    }
  });
  return (pathCache = pts);
}

// The time of year on the ground: yellowing in autumn, dull in winter, pale with frost, white under snow.
const STRAW = C('#c2b25f'), DULL = C('#8e9968'), FROST = C('#dfe9e4'), SNOW = C('#f5f8fc');
function seasonGround(col, amount = 1) {
  if (!season) return col;
  col.lerp(STRAW, season.autumn * 0.4 * amount).lerp(DULL, season.bare * (1 - season.autumn) * 0.5 * amount);
  if (season.frost) col.lerp(FROST, 0.5 * season.frost * amount);
  if (season.snow) col.lerp(SNOW, 0.93);
  return col;
}
const BED = C('#a99f88');

export function buildTerrain(zones) {
  const size = 110, seg = 220;
  const geo = new THREE.PlaneGeometry(size, size, seg, seg);
  geo.rotateX(-Math.PI / 2);
  const pos = geo.attributes.position;
  const colors = new Float32Array(pos.count * 3);
  const paths = pathSamples(zones);
  const col = new THREE.Color();
  for (let i = 0; i < pos.count; i++) {
    const x = pos.getX(i), z = pos.getZ(i), h = heightAt(x, z);
    pos.setY(i, h);
    const patch = Math.sin(x * 0.35 + 2) * Math.cos(z * 0.31) * 0.42 + Math.sin(x * 1.3 + z * 0.9) * 0.2 + Math.sin(x * 0.11 - z * 0.08 + 4) * 0.18 + Math.sin(x * 3.1 + 1) * Math.sin(z * 2.7) * 0.08 + 0.5;
    if (h < -0.05) col.copy(SEABED).lerp(SAND_WET, smooth(-1.2, -0.05, h));
    else if (h < 0.75) col.copy(SAND_WET).lerp(SAND, smooth(0, 0.35, h)).lerp(GRASS, smooth(0.55, 0.8, h));
    else {
      col.copy(GRASS_DARK).lerp(GRASS, patch).lerp(MOSS, Math.max(0, patch - 0.7) * 1.6);
      if (h > 3.6) col.lerp(ROCK, smooth(3.6, 4.6, h) * 0.6);
      // worn paths from the notice board out to every place
      let d = 99;
      if (Math.hypot(x, z) < 36) for (let k = 0; k < paths.length; k += 2) { const q = paths[k], dd = Math.abs(x - q.x) + Math.abs(z - q.z); if (dd < d * 1.5) d = Math.min(d, Math.hypot(x - q.x, z - q.z)); }
      for (const zn of zones) d = Math.min(d, Math.max(0, Math.hypot(x - zn.x, z - zn.z) - zn.radius * 0.45) + 0.2);
      const wobble = Math.sin(x * 2.1) * Math.cos(z * 1.7) * 0.25;
      seasonGround(col);
      col.lerp(season?.snow ? SNOW.clone().lerp(PATH, 0.35) : PATH, (1 - smooth(0.55, 1.5, d + wobble)) * 0.85);
      const sd = streamDistance(x, z);
      if (sd < 3) col.lerp(BED, 1 - smooth(0.5, 1.5, sd)); // gravel in the stream bed
    }
    colors.set([col.r, col.g, col.b], i * 3);
  }
  geo.setAttribute('color', new THREE.BufferAttribute(colors, 3));
  geo.computeVertexNormals();
  const mesh = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.95, metalness: 0 }));
  mesh.receiveShadow = true;
  return mesh;
}

// Thousands of grass blades in one draw call.
export function buildGrass(zones) {
  const blade = new THREE.ConeGeometry(0.06, 0.34, 3, 2);
  blade.translate(0, 0.19, 0);
  // Blades are dark at the root so they melt into the ground, and they lean with the wind.
  const mat = new THREE.MeshStandardNodeMaterial({ color: '#ffffff', roughness: 1 });
  const up = positionLocal.y.div(0.36).clamp(0, 1);
  mat.colorNode = mix(vec3(0.62, 0.74, 0.5), vec3(1.08, 1.06, 0.9), up);
  const phase = positionWorld.x.mul(0.4).add(positionWorld.z.mul(0.31));
  const gust = sin(time.mul(1.6).add(phase)).add(sin(time.mul(3.7).add(phase.mul(1.9))).mul(0.3));
  mat.positionNode = positionLocal.add(vec3(gust.mul(up).mul(up).mul(0.09), 0, gust.mul(up).mul(up).mul(0.05)));
  const count = 52000;
  const mesh = new THREE.InstancedMesh(blade, mat, count);
  const m = new THREE.Matrix4(), q = new THREE.Quaternion(), s = new THREE.Vector3(), p = new THREE.Vector3(), e = new THREE.Euler();
  const c = new THREE.Color();
  let n = 0, guard = 0, seed = 7;
  const rand = () => { seed = (seed * 16807) % 2147483647; return seed / 2147483647; };
  const meadow = zones.find((z) => z.id === 'meadow');
  while (n < count && guard++ < count * 6) {
    const inMeadow = meadow && rand() < 0.22;
    const a = rand() * Math.PI * 2, r = inMeadow ? Math.sqrt(rand()) * meadow.radius * 1.3 : Math.sqrt(rand()) * 34;
    const x = (inMeadow ? meadow.x : 0) + Math.cos(a) * r, z = (inMeadow ? meadow.z : 0) + Math.sin(a) * r;
    const h = heightAt(x, z);
    if (h < 0.85 || h > 3.9) continue;
    if (streamDistance(x, z) < 1.5) continue;
    if (season?.snow && rand() < 0.45) continue; // snow flattens much of the grass
    if (!inMeadow && zones.some((zn) => Math.hypot(x - zn.x, z - zn.z) < zn.radius * 0.5)) continue;
    if (pathSamples(zones).some((q, k) => k % 3 === 0 && Math.abs(x - q.x) < 0.9 && Math.abs(z - q.z) < 0.9)) continue;
    p.set(x, h - 0.02, z);
    e.set((rand() - 0.5) * 0.5, rand() * Math.PI, (rand() - 0.5) * 0.5);
    q.setFromEuler(e);
    const k = (inMeadow ? 1.05 : 0.75) + rand() * 0.8;
    s.set(k, k * (0.8 + rand() * 0.8), k);
    m.compose(p, q, s);
    mesh.setMatrixAt(n, m);
    const tone = Math.sin(x * 0.35 + 2) * Math.cos(z * 0.31) * 0.5 + Math.sin(x * 0.11 - z * 0.08 + 4) * 0.25;
    c.setHSL(0.24 + tone * 0.035 + rand() * 0.05, 0.48 + rand() * 0.14, 0.4 + tone * 0.06 + rand() * 0.12);
    mesh.setColorAt(n, seasonGround(c, 1.25));
    n++;
  }
  mesh.count = n;
  mesh.instanceMatrix.needsUpdate = true;
  mesh.receiveShadow = true;
  return mesh;
}

// Wildflowers everywhere, in clumps: two draw calls (stems and heads).
export function buildFlowers(zones) {
  const count = 4200, group = new THREE.Group();
  const heads = new THREE.InstancedMesh(new THREE.SphereGeometry(0.5, 8, 6), new THREE.MeshStandardMaterial({ color: '#ffffff', roughness: 0.8 }), count);
  const stems = new THREE.InstancedMesh(new THREE.CylinderGeometry(0.5, 0.5, 1, 4), new THREE.MeshStandardMaterial({ color: '#7fb565', roughness: 1 }), count);
  const PETALS = ['#f7b7cd', '#fbe08a', '#ffffff', '#cdb4f0', '#f6a98a', '#a9d8ef', '#fdf3c8'];
  const m = new THREE.Matrix4(), q = new THREE.Quaternion(), s = new THREE.Vector3(), p = new THREE.Vector3(), c = new THREE.Color();
  let seed = 99, n = 0, guard = 0;
  const rand = () => { seed = (seed * 16807) % 2147483647; return seed / 2147483647; };
  while (n < count && guard++ < 7000) {
    const a = rand() * Math.PI * 2, r = Math.sqrt(rand()) * 33, cx = Math.cos(a) * r, cz = Math.sin(a) * r;
    const colour = PETALS[Math.floor(rand() * PETALS.length)], clump = 4 + Math.floor(rand() * 9);
    for (let i = 0; i < clump && n < count; i++) {
      const x = cx + (rand() - 0.5) * 2.4, z = cz + (rand() - 0.5) * 2.4, h = heightAt(x, z);
      if (h < 0.9 || h > 4) continue;
      if (streamDistance(x, z) < 1.3 || (season && rand() > season.flowers * (season.snow ? 0 : 1))) continue;
      if (zones.some((zn) => Math.hypot(x - zn.x, z - zn.z) < zn.radius * 0.42)) continue;
      const tall = 0.16 + rand() * 0.22, size = 0.1 + rand() * 0.08;
      m.compose(p.set(x, h + tall / 2, z), q.identity(), s.set(0.025, tall, 0.025)); stems.setMatrixAt(n, m);
      m.compose(p.set(x, h + tall, z), q.identity(), s.set(size, size * 0.6, size)); heads.setMatrixAt(n, m);
      heads.setColorAt(n, c.set(colour).offsetHSL(0, 0, (rand() - 0.5) * 0.06));
      n++;
    }
  }
  heads.count = stems.count = n; heads.castShadow = true;
  group.add(stems, heads);
  return group;
}

// Cobbles: rounded stepping stones set into every path, in one draw call.
export function buildCobbles(zones) {
  const pts = pathSamples(zones), max = pts.length * 3;
  const mesh = new THREE.InstancedMesh(new THREE.SphereGeometry(0.5, 10, 6), new THREE.MeshStandardMaterial({ color: '#ffffff', roughness: 0.95 }), max);
  const m = new THREE.Matrix4(), q = new THREE.Quaternion(), e = new THREE.Euler(), s = new THREE.Vector3(), p = new THREE.Vector3(), c = new THREE.Color();
  let seed = 4242, n = 0;
  const rand = () => { seed = (seed * 16807) % 2147483647; return seed / 2147483647; };
  for (const pt of pts) {
    for (let j = 0; j < 3; j++) {
      if (rand() < 0.22) continue;
      const x = pt.x + (rand() - 0.5) * 1.5, z = pt.z + (rand() - 0.5) * 1.5, h = heightAt(x, z);
      if (h < 0.7) continue;
      const w = 0.3 + rand() * 0.3;
      e.set((rand() - 0.5) * 0.15, rand() * 3.14, (rand() - 0.5) * 0.15);
      m.compose(p.set(x, h + 0.005, z), q.setFromEuler(e), s.set(w, 0.09 + rand() * 0.05, w * (0.7 + rand() * 0.5)));
      mesh.setMatrixAt(n, m);
      mesh.setColorAt(n, c.setHSL(0.08 + rand() * 0.05, 0.16 + rand() * 0.12, 0.66 + rand() * 0.16));
      n++;
    }
  }
  mesh.count = n; mesh.receiveShadow = true; mesh.castShadow = true;
  return mesh;
}
