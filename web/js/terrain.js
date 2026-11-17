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
const SAND = C('#f3e3bd'), SAND_WET = C('#dcc79a'), GRASS = C('#98c964'), GRASS_DARK = C('#6fab52'), MOSS = C('#b9d877'),
  PATH = C('#ead3a4'), ROCK = C('#b9b3a3'), SEABED = C('#69b9b4');

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
  const blade = new THREE.ConeGeometry(0.06, 0.34, 4, 1);
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
    c.setHSL(0.23 + rand() * 0.08, 0.5 + rand() * 0.14, 0.42 + rand() * 0.16);
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
  const count = 2600, group = new THREE.Group();
  const heads = new THREE.InstancedMesh(new THREE.SphereGeometry(0.5, 8, 6), new THREE.MeshStandardMaterial({ color: '#ffffff', roughness: 0.8 }), count);
  const stems = new THREE.InstancedMesh(new THREE.CylinderGeometry(0.5, 0.5, 1, 4), new THREE.MeshStandardMaterial({ color: '#7fb565', roughness: 1 }), count);
  const PETALS = ['#f7b7cd', '#fbe08a', '#ffffff', '#cdb4f0', '#f6a98a', '#a9d8ef', '#fdf3c8'];
  const m = new THREE.Matrix4(), q = new THREE.Quaternion(), s = new THREE.Vector3(), p = new THREE.Vector3(), c = new THREE.Color();
  let seed = 99, n = 0, guard = 0;
  const rand = () => { seed = (seed * 16807) % 2147483647; return seed / 2147483647; };
  while (n < count && guard++ < 4000) {
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
