import * as THREE from 'three';

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
  h += 3.4 * gauss(x, z, HILL, 7.5);
  h -= 1.15 * gauss(x, z, POND, 4.2);
  return h;
}

const C = (hex) => new THREE.Color(hex);
const SAND = C('#e9d8a6'), SAND_WET = C('#cdb98a'), GRASS = C('#8fbf5f'), GRASS_DARK = C('#5f9a4a'), MOSS = C('#a9cf6b'),
  PATH = C('#d7bd8c'), ROCK = C('#9aa08f'), SEABED = C('#3f8f8c');

function distToSegment(px, pz, ax, az, bx, bz) {
  const dx = bx - ax, dz = bz - az;
  const t = Math.max(0, Math.min(1, ((px - ax) * dx + (pz - az) * dz) / (dx * dx + dz * dz)));
  return Math.hypot(px - ax - t * dx, pz - az - t * dz);
}

export function buildTerrain(zones) {
  const size = 110, seg = 220;
  const geo = new THREE.PlaneGeometry(size, size, seg, seg);
  geo.rotateX(-Math.PI / 2);
  const pos = geo.attributes.position;
  const colors = new Float32Array(pos.count * 3);
  const hub = zones.find((z) => z.id === 'board') || { x: 0, z: 0 };
  const col = new THREE.Color();
  for (let i = 0; i < pos.count; i++) {
    const x = pos.getX(i), z = pos.getZ(i), h = heightAt(x, z);
    pos.setY(i, h);
    const patch = Math.sin(x * 0.35 + 2) * Math.cos(z * 0.31) * 0.5 + Math.sin(x * 1.3 + z * 0.9) * 0.25 + 0.5;
    if (h < -0.05) col.copy(SEABED).lerp(SAND_WET, smooth(-1.2, -0.05, h));
    else if (h < 0.75) col.copy(SAND_WET).lerp(SAND, smooth(0, 0.35, h)).lerp(GRASS, smooth(0.55, 0.8, h));
    else {
      col.copy(GRASS_DARK).lerp(GRASS, patch).lerp(MOSS, Math.max(0, patch - 0.7) * 1.6);
      if (h > 3.6) col.lerp(ROCK, smooth(3.6, 4.6, h) * 0.6);
      // worn paths from the notice board out to every place
      let d = 99;
      for (const zn of zones) if (zn.id !== hub.id) d = Math.min(d, distToSegment(x, z, hub.x, hub.z, zn.x, zn.z));
      for (const zn of zones) d = Math.min(d, Math.max(0, Math.hypot(x - zn.x, z - zn.z) - zn.radius * 0.45) + 0.2);
      const wobble = Math.sin(x * 2.1) * Math.cos(z * 1.7) * 0.25;
      col.lerp(PATH, (1 - smooth(0.45, 1.25, d + wobble)) * 0.8);
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
  const blade = new THREE.ConeGeometry(0.05, 0.38, 3, 1);
  blade.translate(0, 0.19, 0);
  const mat = new THREE.MeshStandardMaterial({ color: '#ffffff', roughness: 1 });
  const count = 9000;
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
    p.set(x, h - 0.02, z);
    e.set((rand() - 0.5) * 0.5, rand() * Math.PI, (rand() - 0.5) * 0.5);
    q.setFromEuler(e);
    const k = (inMeadow ? 1.05 : 0.75) + rand() * 0.8;
    s.set(k, k * (0.8 + rand() * 0.8), k);
    m.compose(p, q, s);
    mesh.setMatrixAt(n, m);
    c.setHSL(0.24 + rand() * 0.08, 0.5 + rand() * 0.15, 0.36 + rand() * 0.16);
    mesh.setColorAt(n, c);
    n++;
  }
  mesh.count = n;
  mesh.instanceMatrix.needsUpdate = true;
  mesh.receiveShadow = true;
  return mesh;
}
