import * as THREE from 'three';
import { material, buildRecipe } from './recipes.js';
import { heightAt } from './terrain.js';

// One builder per kind of object in the world database. To add a new kind of scenery,
// add a row to the objects table and a builder here.
const G = {
  box: new THREE.BoxGeometry(1, 1, 1),
  sphere: new THREE.SphereGeometry(0.5, 20, 14),
  blob: new THREE.IcosahedronGeometry(0.5, 3),
  rock: new THREE.IcosahedronGeometry(0.5, 2),
  cyl: new THREE.CylinderGeometry(0.5, 0.5, 1, 16),
  cone: new THREE.ConeGeometry(0.5, 1, 16),
  cone6: new THREE.ConeGeometry(0.5, 1, 14),
  dome: new THREE.SphereGeometry(0.5, 24, 12, 0, Math.PI * 2, 0, Math.PI / 2),
  disc: new THREE.CylinderGeometry(0.5, 0.5, 0.04, 32),
};

function add(group, geo, mat, color, size, pos, rot) {
  const m = new THREE.Mesh(G[geo], material(mat, color));
  m.scale.set(...(Array.isArray(size) ? size : [size, size, size]));
  m.position.set(...pos);
  if (rot) m.rotation.set(...rot);
  m.castShadow = true; m.receiveShadow = true;
  group.add(m);
  return m;
}
const hsl = (h, s, l) => `#${new THREE.Color().setHSL(h, s, l).getHexString()}`;
function seeded(seed) { let s = (seed * 9301 + 49297) % 233280; return () => { s = (s * 9301 + 49297) % 233280; return s / 233280; }; }

// Lamps register here so day/night can switch them on.
export const lamps = [];
function lamp(group, pos, color = '#ffd28a', power = 1) {
  const bulb = new THREE.Mesh(G.sphere, new THREE.MeshStandardMaterial({ color, emissive: color, emissiveIntensity: 0, roughness: 0.4 }));
  bulb.scale.setScalar(0.2); bulb.position.set(...pos); group.add(bulb);
  const light = new THREE.PointLight(color, 0, 11, 1.6);
  light.position.set(...pos); group.add(light);
  lamps.push({ bulb, light, power });
  return bulb;
}
export const glows = []; // window-like surfaces that warm up at night
function glowPane(group, geo, size, pos, rot) {
  const m = new THREE.Mesh(G[geo], new THREE.MeshStandardMaterial({ color: '#f3e3b0', emissive: '#ffcf70', emissiveIntensity: 0, roughness: 0.4 }));
  m.scale.set(...size); m.position.set(...pos); if (rot) m.rotation.set(...rot);
  group.add(m); glows.push(m); return m;
}

export const builders = {
  tree(o) {
    const g = new THREE.Group(), r = seeded(o.id), h = o.params.hue ?? 0.5;
    const trunkH = 1.5 + r() * 0.8;
    add(g, 'cyl', 'wood', '#9a7654', [0.32, trunkH, 0.32], [0, trunkH / 2, 0]);
    const blossom = h > 0.82;
    const leaf = blossom ? hsl(0.94, 0.6, 0.82) : hsl(0.24 + h * 0.1, 0.4 + r() * 0.08, 0.52 + h * 0.1);
    const leaf2 = blossom ? hsl(0.96, 0.7, 0.88) : hsl(0.2 + h * 0.1, 0.46, 0.62 + h * 0.06);
    const crown = new THREE.Group(); crown.position.y = trunkH; g.add(crown);
    add(crown, 'blob', 'moss', leaf, [2.1, 1.7, 2.1], [0, 0.6, 0]);
    add(crown, 'blob', 'moss', leaf2, [1.4, 1.2, 1.4], [0.7, 1.0, 0.3], [0.3, 1, 0]);
    add(crown, 'blob', 'moss', leaf, [1.3, 1.1, 1.3], [-0.6, 1.2, -0.4], [1, 0.4, 0]);
    add(crown, 'blob', 'moss', leaf2, [1.1, 0.95, 1.1], [0.1, 1.65, 0.1], [0.5, 2, 0]);
    g.userData.sway = crown;
    return g;
  },
  pine(o) {
    const g = new THREE.Group(), h = o.params.hue ?? 0.5;
    add(g, 'cyl', 'wood', '#8a6a4c', [0.28, 1.1, 0.28], [0, 0.55, 0]);
    const crown = new THREE.Group(); crown.position.y = 0.9; g.add(crown);
    for (let i = 0; i < 4; i++) add(crown, 'cone6', 'moss', hsl(0.38 + h * 0.05, 0.3, 0.38 + i * 0.045 + h * 0.05), [2.0 - i * 0.42, 1.3, 2.0 - i * 0.42], [0, 0.55 + i * 0.75, 0], [0, i * 0.5, 0]);
    g.userData.sway = crown;
    return g;
  },
  rock(o) {
    const g = new THREE.Group(), r = seeded(o.params.seed || o.id);
    add(g, 'rock', 'stone', hsl(0.1, 0.12, 0.7 + r() * 0.1), [1.1 + r() * 0.7, 0.7 + r() * 0.5, 0.9 + r() * 0.6], [0, 0.25, 0], [r(), r() * 3, r()]);
    if (r() > 0.4) add(g, 'rock', 'stone', hsl(0.1, 0.12, 0.76), [0.5, 0.4, 0.5], [0.7, 0.12, 0.3], [r() * 3, r(), 0]);
    if (r() > 0.5) add(g, 'dome', 'moss', '#a9cf7c', [0.7, 0.3, 0.6], [-0.1, 0.52, 0]);
    return g;
  },
  bush(o) {
    const g = new THREE.Group(), r = seeded(o.id), h = o.params.hue ?? 0.5, c = hsl(0.26 + h * 0.08, 0.4, 0.5 + h * 0.08);
    add(g, 'blob', 'moss', c, [1.1, 0.8, 1.0], [0, 0.35, 0]);
    add(g, 'blob', 'moss', c, [0.8, 0.65, 0.8], [0.5, 0.3, 0.2], [1, 1, 0]);
    add(g, 'blob', 'moss', hsl(0.24, 0.46, 0.6), [0.7, 0.55, 0.7], [-0.4, 0.3, -0.25], [0, 2, 1]);
    if (o.params.berries) for (let i = 0; i < 7; i++) add(g, 'sphere', 'glossy', '#d1495b', 0.09, [(r() - 0.5) * 1.1, 0.35 + r() * 0.35, (r() - 0.5) * 0.9]);
    return g;
  },
  flower_patch(o) {
    const g = new THREE.Group(), r = seeded(o.id), n = o.params.count || 6, spread = o.params.spread || 1.4;
    const petals = ['#f4a6c0', '#f7d06b', '#ffffff', '#c9a7eb', '#f28b66', '#9ad1e6'];
    for (let i = 0; i < n; i++) {
      const a = r() * 6.28, d = Math.sqrt(r()) * spread, x = Math.cos(a) * d, z = Math.sin(a) * d, hgt = 0.25 + r() * 0.3;
      add(g, 'cyl', 'moss', '#5c9a4c', [0.03, hgt, 0.03], [x, hgt / 2, z]);
      add(g, 'sphere', 'matte', petals[Math.floor(r() * petals.length)], [0.2, 0.09, 0.2], [x, hgt, z]);
      add(g, 'sphere', 'matte', '#f2c14e', 0.08, [x, hgt + 0.03, z]);
    }
    g.userData.followGround = true;
    return g;
  },
  mushrooms(o) {
    const g = new THREE.Group(), r = seeded(o.id);
    for (let i = 0; i < 4; i++) {
      const x = (r() - 0.5) * 1.2, z = (r() - 0.5) * 1.2, s = 0.5 + r() * 0.8;
      add(g, 'cyl', 'matte', '#f3ead7', [0.12 * s, 0.3 * s, 0.12 * s], [x, 0.15 * s, z]);
      add(g, 'dome', 'glossy', i % 2 ? '#d1495b' : '#e58f4e', [0.42 * s, 0.5 * s, 0.42 * s], [x, 0.28 * s, z]);
    }
    return g;
  },
  lantern() {
    const g = new THREE.Group();
    add(g, 'cyl', 'wood', '#7d6348', [0.12, 1.9, 0.12], [0, 0.95, 0]);
    add(g, 'box', 'wood', '#7d6348', [0.6, 0.08, 0.08], [0.25, 1.85, 0]);
    add(g, 'box', 'metal', '#3c3a36', [0.3, 0.06, 0.3], [0.48, 1.72, 0]);
    add(g, 'cone', 'metal', '#3c3a36', [0.36, 0.16, 0.36], [0.48, 1.8, 0]);
    add(g, 'box', 'glass', '#fff1cc', [0.24, 0.3, 0.24], [0.48, 1.54, 0]);
    lamp(g, [0.48, 1.54, 0]);
    return g;
  },
  signpost() {
    const g = new THREE.Group();
    add(g, 'cyl', 'wood', '#8f7252', [0.12, 1.7, 0.12], [0, 0.85, 0]);
    add(g, 'box', 'wood', '#c9a878', [0.9, 0.22, 0.06], [0.3, 1.45, 0], [0, 0.3, 0.05]);
    add(g, 'box', 'wood', '#b89464', [0.8, 0.22, 0.06], [-0.25, 1.15, 0], [0, -0.5, -0.06]);
    return g;
  },
  notice_board() {
    const g = new THREE.Group();
    add(g, 'cyl', 'wood', '#8f7252', [0.16, 2.3, 0.16], [-1.1, 1.15, 0], [0, 0, 0.04]);
    add(g, 'cyl', 'wood', '#8f7252', [0.16, 2.3, 0.16], [1.1, 1.15, 0], [0, 0, -0.03]);
    add(g, 'box', 'wood', '#b08a5b', [2.3, 1.3, 0.1], [0, 1.45, 0]);
    add(g, 'box', 'wood', '#c9a878', [2.1, 1.1, 0.04], [0, 1.45, 0.06]);
    add(g, 'box', 'wood', '#8c4f3a', [2.9, 0.1, 0.7], [0, 2.38, 0.12], [0.25, 0, 0]);
    add(g, 'dome', 'moss', '#a9cf7c', [1.4, 0.3, 0.5], [-0.4, 2.42, 0.1]);
    g.userData.notes = new THREE.Group(); g.userData.notes.position.set(0, 1.45, 0.1); g.add(g.userData.notes);
    g.userData.parcels = new THREE.Group(); g.userData.parcels.position.set(0, 0, 1.3); g.add(g.userData.parcels);
    return g;
  },
  burrow() {
    const g = new THREE.Group();
    add(g, 'dome', 'moss', '#a5cc78', [5.2, 4.4, 4.8], [0, -0.1, 0]);
    add(g, 'blob', 'moss', '#b4d887', [2.2, 1.2, 2.0], [-1.4, 1.2, -0.5]);
    add(g, 'blob', 'moss', '#93bd6b', [1.8, 1.0, 1.8], [1.3, 1.3, -0.8]);
    add(g, 'cyl', 'wood', '#8c5a3c', [1.3, 0.2, 1.3], [0, 0.72, 2.22], [Math.PI / 2 - 0.25, 0, 0]);
    add(g, 'cyl', 'wood', '#6b4129', [1.5, 0.12, 1.5], [0, 0.72, 2.17], [Math.PI / 2 - 0.25, 0, 0]);
    add(g, 'sphere', 'metal', '#e6c35c', 0.12, [0.38, 0.72, 2.36]);
    glowPane(g, 'cyl', [0.6, 0.1, 0.6], [1.45, 1.05, 1.72], [Math.PI / 2 - 0.4, 0, -0.5]);
    add(g, 'cyl', 'stone', '#9a8f84', [0.4, 1.0, 0.4], [-1.0, 2.2, -0.2]);
    add(g, 'cyl', 'stone', '#7f756b', [0.5, 0.12, 0.5], [-1.0, 2.72, -0.2]);
    for (let i = 0; i < 4; i++) add(g, 'cyl', 'stone', '#b9b3a6', [0.55, 0.08, 0.5], [Math.sin(i) * 0.3, 0.04, 3.0 + i * 0.7]);
    return g;
  },
  garden_plot(o) {
    const g = new THREE.Group(), r = seeded(o.id), crop = o.params.crop;
    add(g, 'box', 'matte', '#7a5a45', [2.6, 0.22, 2.0], [0, 0.11, 0]);
    for (const [x, z, w, d] of [[0, 1.05, 2.8, 0.1], [0, -1.05, 2.8, 0.1], [1.35, 0, 0.1, 2.2], [-1.35, 0, 0.1, 2.2]]) add(g, 'box', 'wood', '#c9a878', [w, 0.34, d], [x, 0.17, z]);
    for (let i = 0; i < 3; i++) for (let j = 0; j < 4; j++) {
      const x = -0.9 + j * 0.6 + (r() - 0.5) * 0.1, z = -0.6 + i * 0.6;
      if (crop === 'flower') { add(g, 'cyl', 'moss', '#5c9a4c', [0.04, 0.4, 0.04], [x, 0.42, z]); add(g, 'sphere', 'matte', ['#f4a6c0', '#f7d06b', '#c9a7eb'][(i + j) % 3], [0.22, 0.12, 0.22], [x, 0.64, z]); }
      else if (crop === 'leafy') add(g, 'blob', 'moss', '#7cc46a', [0.42, 0.3, 0.42], [x, 0.32, z], [r(), r() * 3, 0]);
      else { add(g, 'cyl', 'moss', '#6fb05a', [0.03, 0.22, 0.03], [x, 0.32, z]); add(g, 'sphere', 'moss', '#8fd070', [0.16, 0.05, 0.08], [x + 0.06, 0.43, z], [0, r() * 3, 0.5]); add(g, 'sphere', 'moss', '#8fd070', [0.16, 0.05, 0.08], [x - 0.06, 0.43, z], [0, r() * 3, -0.5]); }
    }
    return g;
  },
  watering_can() {
    const g = new THREE.Group();
    add(g, 'cyl', 'metal', '#7fb7be', [0.4, 0.45, 0.4], [0, 0.23, 0]);
    add(g, 'cyl', 'metal', '#7fb7be', [0.08, 0.5, 0.08], [0.36, 0.34, 0], [0, 0, -0.9]);
    add(g, 'torus' in G ? 'cyl' : 'cyl', 'metal', '#6aa3aa', [0.16, 0.05, 0.16], [0.56, 0.5, 0], [0, 0, -0.9]);
    return g;
  },
  workshop_hut() {
    const g = new THREE.Group();
    add(g, 'box', 'wood', '#b89464', [4.4, 0.16, 3.6], [0, 0.08, 0]);
    for (const [x, z] of [[-2, -1.6], [2, -1.6], [-2, 1.6], [2, 1.6]]) add(g, 'cyl', 'wood', '#8f7252', [0.22, 2.5, 0.22], [x, 1.25, z]);
    add(g, 'box', 'wood', '#a9825a', [4.4, 2.1, 0.14], [0, 1.2, -1.65]);
    add(g, 'box', 'matte', '#d98a6a', [5.2, 0.16, 2.5], [0, 3.05, -1.0], [-0.6, 0, 0]);
    add(g, 'box', 'matte', '#e39a78', [5.2, 0.16, 2.5], [0, 3.05, 1.0], [0.6, 0, 0]);
    add(g, 'box', 'wood', '#8f7252', [5.3, 0.18, 0.18], [0, 3.72, 0]);
    add(g, 'box', 'wood', '#8c6a47', [2.4, 0.14, 0.9], [-0.6, 1.0, -1.0]);
    for (const x of [-1.6, 0.4]) add(g, 'box', 'wood', '#8f7252', [0.14, 0.9, 0.7], [x, 0.5, -1.0]);
    add(g, 'box', 'metal', '#8a8d91', [0.5, 0.1, 0.16], [-1.0, 1.12, -0.9], [0, 0.4, 0]);
    add(g, 'cyl', 'wood', '#d9b98a', [0.1, 0.5, 0.1], [-0.2, 1.12, -0.95], [0, 0, 1.57]);
    add(g, 'sphere', 'glossy', '#e76f51', 0.2, [0.2, 1.17, -1.1]);
    for (let i = 0; i < 4; i++) add(g, 'box', 'metal', ['#8a8d91', '#b08a5b', '#5d6a73', '#c9a878'][i], [0.1, 0.5, 0.06], [-1.4 + i * 0.5, 1.9, -1.55], [0, 0, (i - 1.5) * 0.15]);
    add(g, 'cyl', 'stone', '#8f897d', [0.5, 1.6, 0.5], [1.5, 3.4, -1.0]);
    add(g, 'box', 'wood', '#8c6a47', [0.7, 0.7, 0.7], [1.5, 0.5, 0.9], [0, 0.3, 0]);
    lamp(g, [0, 2.6, -0.3], '#ffc878', 0.9);
    return g;
  },
  log_pile() {
    const g = new THREE.Group();
    for (const [x, y] of [[-0.35, 0.2], [0.1, 0.2], [0.55, 0.2], [-0.12, 0.55], [0.33, 0.55], [0.1, 0.9]]) {
      add(g, 'cyl', 'wood', '#8c6a47', [0.4, 1.6, 0.4], [x, y, 0], [Math.PI / 2, 0, 0]);
      add(g, 'cyl', 'wood', '#e0c9a0', [0.32, 1.62, 0.32], [x, y, 0], [Math.PI / 2, 0, 0]);
    }
    return g;
  },
  library_tower() {
    const g = new THREE.Group();
    add(g, 'cyl', 'stone', '#e6dcc6', [3.4, 3.6, 3.4], [0, 1.8, 0]);
    add(g, 'cyl', 'stone', '#d2c7b0', [3.7, 0.3, 3.7], [0, 0.15, 0]);
    add(g, 'cyl', 'wood', '#8f7252', [3.8, 0.2, 3.8], [0, 3.65, 0]);
    add(g, 'cone', 'matte', '#7fb8a8', [4.4, 2.4, 4.4], [0, 4.9, 0]);
    add(g, 'sphere', 'metal', '#e6c35c', 0.22, [0, 6.15, 0]);
    add(g, 'box', 'wood', '#7a4f33', [0.95, 1.6, 0.16], [0, 0.95, 1.66]);
    add(g, 'cyl', 'wood', '#7a4f33', [0.95, 0.16, 0.95], [0, 1.72, 1.66], [Math.PI / 2, 0, 0]);
    add(g, 'sphere', 'metal', '#e6c35c', 0.1, [0.3, 0.95, 1.78]);
    for (const a of [-0.95, 0.95, 2.4, -2.4]) glowPane(g, 'cyl', [0.6, 0.1, 0.6], [Math.sin(a) * 1.68, 2.45, Math.cos(a) * 1.68], [Math.PI / 2, 0, -a]);
    // a shelf of books that live outside under the eaves
    add(g, 'box', 'wood', '#8c6a47', [1.4, 1.3, 0.4], [2.3, 0.65, 0.9], [0, -0.9, 0]);
    const cols = ['#d1495b', '#edae49', '#00798c', '#8f6bb3', '#66a182', '#e58f4e'];
    for (let row = 0; row < 2; row++) for (let i = 0; i < 6; i++) add(g, 'box', 'matte', cols[(i + row * 2) % 6], [0.14, 0.4, 0.26], [2.3 + (i - 2.5) * 0.115, 0.42 + row * 0.55, 0.9 + (i - 2.5) * 0.145], [0, -0.9, 0]);
    lamp(g, [0.9, 2.2, 1.9], '#ffd28a', 0.8);
    return g;
  },
  bench() {
    const g = new THREE.Group();
    add(g, 'box', 'wood', '#b08a5b', [1.6, 0.1, 0.5], [0, 0.5, 0]);
    add(g, 'box', 'wood', '#b08a5b', [1.6, 0.4, 0.08], [0, 0.85, -0.24], [-0.15, 0, 0]);
    for (const x of [-0.65, 0.65]) add(g, 'box', 'wood', '#8f7252', [0.1, 0.5, 0.45], [x, 0.25, 0]);
    return g;
  },
  computer() {
    const g = new THREE.Group();
    add(g, 'box', 'wood', '#b08a5b', [1.5, 0.1, 0.8], [0, 0.7, 0]);
    for (const [x, z] of [[-0.65, -0.3], [0.65, -0.3], [-0.65, 0.3], [0.65, 0.3]]) add(g, 'cyl', 'wood', '#8f7252', [0.1, 0.7, 0.1], [x, 0.35, z]);
    add(g, 'box', 'matte', '#e8dcc6', [0.75, 0.6, 0.5], [0, 1.1, -0.1]);
    const screen = glowPane(g, 'box', [0.58, 0.42, 0.04], [0, 1.12, 0.16]);
    screen.material = new THREE.MeshStandardMaterial({ color: '#bff3e0', emissive: '#7fe0c0', emissiveIntensity: 0.9, roughness: 0.3 });
    glows.pop(); g.userData.screen = screen;
    add(g, 'box', 'matte', '#d9cdb5', [0.7, 0.05, 0.26], [0, 0.78, 0.25], [0.1, 0, 0]);
    add(g, 'cyl', 'moss', '#5c9a4c', [0.03, 0.3, 0.03], [0.25, 1.55, -0.15]);
    add(g, 'sphere', 'moss', '#8fd070', [0.2, 0.05, 0.1], [0.32, 1.7, -0.15], [0, 0, 0.5]);
    add(g, 'cyl', 'wood', '#8c6a47', [0.5, 0.4, 0.5], [0, 0.2, 0.9]);
    return g;
  },
  pond(o) {
    const g = new THREE.Group(), R = o.params.radius || 4.5, r = seeded(o.id);
    const base = heightAt(o.x, o.z), gy = (dx, dz) => Math.max(0.34, heightAt(o.x + dx, o.z + dz) - base);
    const water = new THREE.Mesh(G.disc, new THREE.MeshStandardMaterial({ color: '#8fd3cc', roughness: 0.1, metalness: 0.05, transparent: true, opacity: 0.85 }));
    water.scale.set(R * 2, 1, R * 2); water.position.y = 0.38; water.receiveShadow = true; g.add(water);
    g.userData.water = water;
    for (let i = 0; i < 16; i++) { const a = (i / 16) * 6.28 + r() * 0.3, d = R * (0.96 + r() * 0.1); add(g, 'rock', 'stone', hsl(0.1, 0.12, 0.68 + r() * 0.12), [0.5 + r() * 0.5, 0.35, 0.5 + r() * 0.4], [Math.cos(a) * d, gy(Math.cos(a) * d, Math.sin(a) * d) + 0.08, Math.sin(a) * d], [r(), r() * 3, 0]); }
    for (let i = 0; i < 7; i++) { const a = r() * 6.28, d = r() * R * 0.75; add(g, 'cyl', 'moss', '#6fb05a', [0.5 + r() * 0.3, 0.03, 0.5 + r() * 0.3], [Math.cos(a) * d, 0.41, Math.sin(a) * d]); if (i % 3 === 0) add(g, 'sphere', 'matte', '#f7c6d9', [0.2, 0.14, 0.2], [Math.cos(a) * d, 0.48, Math.sin(a) * d]); }
    for (let i = 0; i < 18; i++) { const a = 2 + r() * 2.6, d = R * (0.8 + r() * 0.22), hgt = 0.9 + r() * 0.9, y0 = gy(Math.cos(a) * d, Math.sin(a) * d); add(g, 'cyl', 'moss', '#5a8f4a', [0.05, hgt, 0.05], [Math.cos(a) * d, y0 + hgt / 2, Math.sin(a) * d], [(r() - 0.5) * 0.2, 0, (r() - 0.5) * 0.2]); if (i % 2) add(g, 'cyl', 'wood', '#8a6a4c', [0.1, 0.3, 0.1], [Math.cos(a) * d, y0 + hgt, Math.sin(a) * d]); }
    g.userData.noRotate = true;
    return g;
  },
  stump() {
    const g = new THREE.Group();
    add(g, 'cyl', 'wood', '#9a7654', [1.2, 0.6, 1.2], [0, 0.3, 0]);
    add(g, 'cyl', 'wood', '#e0c9a0', [1.05, 0.62, 1.05], [0, 0.3, 0]);
    add(g, 'cyl', 'wood', '#c9a878', [0.6, 0.63, 0.6], [0, 0.3, 0]);
    add(g, 'dome', 'moss', '#a9cf7c', [0.5, 0.25, 0.4], [0.45, 0.1, 0.4]);
    return g;
  },
  driftwood() {
    const g = new THREE.Group();
    add(g, 'cyl', 'wood', '#c8b8a0', [0.25, 2.2, 0.25], [0, 0.18, 0], [Math.PI / 2, 0, 0.1]);
    add(g, 'cyl', 'wood', '#b8a890', [0.14, 0.9, 0.14], [0.3, 0.4, 0.4], [0.8, 0, -0.7]);
    return g;
  },
  shells(o) {
    const g = new THREE.Group(), r = seeded(o.id);
    for (let i = 0; i < 7; i++) add(g, i % 2 ? 'cone' : 'dome', 'glossy', ['#f6e7d8', '#f3c5c5', '#d6e5fa', '#fbe3b5'][i % 4], [0.22, 0.14, 0.2], [(r() - 0.5) * 2.4, 0.05, (r() - 0.5) * 2.4], [r(), r() * 3, r()]);
    g.userData.followGround = true;
    return g;
  },
  build_site() {
    const g = new THREE.Group();
    for (const [x, z] of [[-1.6, -1.6], [1.6, -1.6], [-1.6, 1.6], [1.6, 1.6]]) { add(g, 'cyl', 'wood', '#c9a878', [0.1, 0.8, 0.1], [x, 0.4, z]); add(g, 'sphere', 'matte', '#e76f51', 0.14, [x, 0.84, z]); }
    for (const [x, z, w, d] of [[0, -1.6, 3.2, 0.03], [0, 1.6, 3.2, 0.03], [-1.6, 0, 0.03, 3.2], [1.6, 0, 0.03, 3.2]]) add(g, 'box', 'matte', '#f1e3c4', [w, 0.03, d], [x, 0.7, z]);
    for (let i = 0; i < 4; i++) add(g, 'box', 'wood', '#d9b98a', [1.6, 0.08, 0.3], [0.2, 0.06 + i * 0.09, -0.3 + (i % 2) * 0.12], [0, i * 0.12, 0]);
    add(g, 'cyl', 'wood', '#8f7252', [0.08, 1.1, 0.08], [-0.9, 0.55, 0.9]);
    add(g, 'box', 'wood', '#f1e3c4', [0.7, 0.45, 0.05], [-0.9, 1.1, 0.9], [0, 0.6, 0]);
    return g;
  },
  parcel(kind = 'item') {
    const g = new THREE.Group();
    if (kind === 'pet') { add(g, 'cyl', 'wood', '#c9a878', [0.6, 0.35, 0.6], [0, 0.18, 0]); add(g, 'dome', 'matte', '#e9d8a6', [0.56, 0.3, 0.56], [0, 0.33, 0]); return g; }
    const c = kind === 'special' ? '#c9a7eb' : '#e9c46a';
    add(g, 'box', 'matte', c, [0.5, 0.4, 0.5], [0, 0.2, 0]);
    add(g, 'box', 'matte', '#d1495b', [0.52, 0.42, 0.1], [0, 0.2, 0]);
    add(g, 'box', 'matte', '#d1495b', [0.1, 0.42, 0.52], [0, 0.2, 0]);
    add(g, 'sphere', 'matte', '#d1495b', [0.2, 0.12, 0.12], [0, 0.45, 0]);
    return g;
  },
  creation(o) { return wrap(buildRecipe(o.params)); },
  pet(o) { const g = wrap(buildRecipe(o.params)); g.userData.pet = true; return g; },
};

function wrap(inner) {
  const g = new THREE.Group();
  g.add(inner);
  g.userData.inner = inner; g.userData.animation = inner.userData.animation;
  return g;
}
