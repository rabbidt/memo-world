// Dressing: the hand-made models scattered over the island from web/assets/models/layout.json.
// Everything that repeats is drawn instanced, one draw call per mesh of each model.
import * as THREE from 'three';
import { positionLocal, positionWorld, time, sin, cos, vec3, float } from 'three/tsl';
import { heightAt } from './terrain.js';
import { lamps, glows } from './builders.js';

// These exist once, as real objects from the database; the layout only says how they sit.
export const LANDMARKS = new Set(['notice_board', 'burrow', 'workshop_hut', 'library_tower', 'computer', 'pond']);
const SWAY = { tree: 0.05, pine: 0.035, bush: 0.02, grass_tuft: 0.09, flower_cluster: 0.07, flower_cluster_gold: 0.07, flower_cluster_blue: 0.07 };
const NO_SHADOW = new Set(['grass_tuft', 'path_stones']);

export async function loadLayout() {
  try { const r = await fetch('/assets/models/layout.json'); if (!r.ok) return null; return (await r.json()).items || null; } catch { return null; }
}

// A copy of a model's material that leans gently in the wind; higher parts move more.
const swayCache = new Map();
function swaying(mat, amount, pivotY) {
  const key = `${mat.uuid}:${amount}:${pivotY}`;
  if (swayCache.has(key)) return swayCache.get(key);
  const m = new THREE.MeshStandardNodeMaterial();
  for (const k of ['color', 'roughness', 'metalness', 'vertexColors', 'map', 'flatShading', 'emissive', 'emissiveIntensity', 'side']) if (mat[k] !== undefined) { if (m[k]?.copy && mat[k]?.isColor) m[k].copy(mat[k]); else m[k] = mat[k]; }
  const lift = positionLocal.y.sub(pivotY).max(0);
  const phase = positionWorld.x.mul(0.35).add(positionWorld.z.mul(0.27));
  const gust = sin(time.mul(1.3).add(phase)).add(sin(time.mul(2.9).add(phase.mul(2.3))).mul(0.35));
  m.positionNode = positionLocal.add(vec3(gust.mul(lift).mul(amount), float(0), cos(time.mul(1.1).add(phase)).mul(lift).mul(amount * 0.6)));
  swayCache.set(key, m);
  return m;
}

// Window panes and lamp glass in the models warm up at night with everything else.
export function registerGlow(root) {
  const seen = new Set();
  root.traverse((n) => { const m = n.material; if (n.isMesh && m?.emissive && !seen.has(m) && (m.emissive.r + m.emissive.g + m.emissive.b) > 0.05) { seen.add(m); glows.push({ material: m }); } });
}
export function addLamp(group, model, power = 1) {
  const at = model.getObjectByName('Light'); if (!at) return;
  const light = new THREE.PointLight('#ffd28a', 0, 12, 1.6);
  light.position.copy(at.getWorldPosition(new THREE.Vector3()));
  group.add(light);
  lamps.push({ bulb: { material: {} }, light, power });
}

// Models can carry their own seasons: nodes named Canopy_spring, Leaves_autumn, Crops_winter and so on,
// plus Snow. Hidden ones are exported at a tiny scale; the one for today's season is shown at full size.
const SEASON_NODE = /^(Canopy|Leaves|Crops)_(spring|summer|autumn|winter)/;
export function applySeasonNodes(root, S) {
  const groups = new Map();
  root.traverse((n) => {
    const m = SEASON_NODE.exec(n.name);
    if (m) { if (!groups.has(m[1])) groups.set(m[1], {}); groups.get(m[1])[m[2]] = n; }
    else if (/^Snow/.test(n.name)) n.scale.setScalar(S?.snow ? 1 : 0.001);
  });
  for (const set of groups.values()) {
    if (Object.keys(set).length < 2) continue;
    // late autumn and early spring trees are nearer to winter than to their own season
    const want = S ? (S.bare > 0.6 ? 'winter' : S.name) : 'summer';
    const pick = set[want] || set.summer || Object.values(set)[0];
    for (const n of Object.values(set)) n.scale.setScalar(n === pick ? 1 : 0.001);
    root.userData.ownSeasons = true;
  }
}

// What the time of year does to each scattered thing: a tint (multiplied into its own colour) or nothing at all.
const hash = (x, z) => { const v = Math.sin(x * 12.9898 + z * 78.233) * 43758.5453; return v - Math.floor(v); };
function seasonal(name, canopy, it, S, tint) {
  tint.setRGB(1, 1, 1);
  if (!S) return true;
  const r = hash(it.x, it.z);
  if (name === 'tree' && canopy) {
    if (S.bare > 0.55 && r < S.bare * 1.15) return false; // leaves gone
    if (S.autumn > 0.05) { const a = Math.min(1, S.autumn * 1.4), k = hash(it.z, it.x); tint.lerp(k < 0.35 ? AUTUMN[0] : k < 0.7 ? AUTUMN[1] : AUTUMN[2], a); }
    if (S.blossom > 0.05 && r < 0.45) tint.lerp(BLOSSOM, S.blossom * 0.8);
  }
  if (name === 'bush' && S.autumn > 0.05) tint.lerp(AUTUMN[1], S.autumn * 0.6);
  if (name === 'grass_tuft') tint.lerp(STRAW, Math.max(S.autumn * 0.6, S.bare * 0.5));
  if (name.startsWith('flower_cluster') && (S.snow || r > S.flowers * 1.2)) return false;
  if (name === 'mushrooms' && S.name !== 'autumn' && r > 0.3) return false;
  if (S.snow && (canopy || name === 'bush' || name === 'grass_tuft' || name === 'rock' || name === 'path_stones')) tint.lerp(SNOWY, name === 'pine' || name === 'tree' ? 0.55 : 0.8);
  else if (S.frost && (name === 'grass_tuft' || name === 'bush')) tint.lerp(SNOWY, 0.3 * S.frost);
  return true;
}
const AUTUMN = [new THREE.Color(2.6, 1.0, 0.3), new THREE.Color(2.9, 0.7, 0.28), new THREE.Color(2.2, 1.25, 0.3)], BLOSSOM = new THREE.Color(2.1, 1.35, 1.7),
  STRAW = new THREE.Color(1.5, 1.2, 0.6), SNOWY = new THREE.Color(2.6, 2.7, 2.9);

export function buildDressing(items, models, S = null) {
  const root = new THREE.Group(), byName = new Map();
  for (const it of items) { if (LANDMARKS.has(it.name) || !models[it.name]) continue; if (!byName.has(it.name)) byName.set(it.name, []); byName.get(it.name).push(it); }
  const T = new THREE.Matrix4(), M = new THREE.Matrix4(), q = new THREE.Quaternion(), up = new THREE.Vector3(0, 1, 0), s = new THREE.Vector3(), p = new THREE.Vector3();
  for (const [name, list] of byName) {
    const model = models[name];
    model.updateMatrixWorld(true);
    const lightAt = model.getObjectByName('Light')?.getWorldPosition(new THREE.Vector3());
    model.traverse((n) => {
      if (!n.isMesh) return;
      for (let a = n; a; a = a.parent) if (Math.abs(a.scale.x) < 0.01) return; // a part put away for another season
      let canopy = false; for (let a = n; a; a = a.parent) if (a.name.startsWith('Canopy')) canopy = true;
      const pivot = name === 'tree' || name === 'pine' ? (canopy ? -1.5 : 99) : 0; // canopy vertices are measured from the canopy's own pivot
      const mat = SWAY[name] && pivot < 50 ? swaying(n.material, SWAY[name], pivot) : n.material;
      const inst = new THREE.InstancedMesh(n.geometry, mat, list.length), tint = new THREE.Color();
      let i = 0;
      list.forEach((it) => {
        if (!seasonal(name, canopy, it, model.userData.ownSeasons ? null : S, tint)) return;
        const y = it.y ?? heightAt(it.x, it.z) - (name === 'path_stones' ? 0.05 : 0.03);
        T.compose(p.set(it.x, y, it.z), q.setFromAxisAngle(up, it.rotY || 0), s.setScalar(it.scale || 1));
        inst.setMatrixAt(i, M.multiplyMatrices(T, n.matrixWorld)); inst.setColorAt(i, tint); i++;
      });
      inst.count = i;
      inst.castShadow = !NO_SHADOW.has(name); inst.receiveShadow = true;
      inst.frustumCulled = false;
      root.add(inst);
    });
    if (lightAt) for (const it of list) {
      const light = new THREE.PointLight('#ffd28a', 0, 12, 1.6);
      light.position.copy(lightAt).multiplyScalar(it.scale || 1).applyAxisAngle(up, it.rotY || 0).add(p.set(it.x, heightAt(it.x, it.z), it.z));
      root.add(light); lamps.push({ bulb: { material: {} }, light, power: 0.8 });
    }
  }
  return root;
}
