import * as THREE from 'three';
import { positionLocal, positionWorld, time, sin, vec3, mix } from 'three/tsl';

// The island's shape. One function, used for the ground mesh and for standing things on it.
const HILL = { x: 22, z: -21 }, POND = { x: -16, z: -6 };
const smooth = (a, b, v) => { const t = Math.min(1, Math.max(0, (v - a) / (b - a))); return t * t * (3 - 2 * t); };
const gauss = (x, z, c, r) => Math.exp(-((x - c.x) ** 2 + (z - c.z) ** 2) / (r * r));

export function heightAt(x, z) {
  const a = Math.atan2(z, x);
  const r = Math.hypot(x, z) / (1 + 0.07 * Math.sin(3 * a + 1) + 0.045 * Math.sin(5 * a + 2.3) + 0.03 * Math.sin(9 * a));
  const inland = 1 - smooth(22, 36, r);
  let h = 1.35 * inland - 2.2 * smooth(31, 44, r);
  h += (Math.sin(x * 0.21 + 1.3) * Math.cos(z * 0.17) * 0.45 + Math.sin(x * 0.47 + z * 0.39) * 0.16 + Math.sin(z * 0.83 - x * 0.6) * 0.06) * inland;
  h += (Math.sin(x * 0.085 + 0.6) * Math.cos(z * 0.075 - 1.1) * 0.95 + Math.sin(x * 0.05 - z * 0.06 + 2) * 0.5) * inland; // rolling ground
  h += 3.4 * gauss(x, z, HILL, 7.5);
  h -= 1.15 * gauss(x, z, POND, 4.2);
  return h;
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
let pathCache = null;
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
      col.lerp(PATH, (1 - smooth(0.55, 1.5, d + wobble)) * 0.85);
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
    mesh.setColorAt(n, c);
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
