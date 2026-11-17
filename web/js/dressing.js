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

export function buildDressing(items, models) {
  const root = new THREE.Group(), byName = new Map();
  for (const it of items) { if (LANDMARKS.has(it.name) || !models[it.name]) continue; if (!byName.has(it.name)) byName.set(it.name, []); byName.get(it.name).push(it); }
  const T = new THREE.Matrix4(), M = new THREE.Matrix4(), q = new THREE.Quaternion(), up = new THREE.Vector3(0, 1, 0), s = new THREE.Vector3(), p = new THREE.Vector3();
  for (const [name, list] of byName) {
    const model = models[name];
    model.updateMatrixWorld(true);
    const lightAt = model.getObjectByName('Light')?.getWorldPosition(new THREE.Vector3());
    model.traverse((n) => {
      if (!n.isMesh) return;
      let canopy = false; for (let a = n; a; a = a.parent) if (a.name.startsWith('Canopy')) canopy = true;
      const pivot = name === 'tree' || name === 'pine' ? (canopy ? -1.5 : 99) : 0; // canopy vertices are measured from the canopy's own pivot
      const mat = SWAY[name] && pivot < 50 ? swaying(n.material, SWAY[name], pivot) : n.material;
      const inst = new THREE.InstancedMesh(n.geometry, mat, list.length);
      list.forEach((it, i) => {
        const y = it.y ?? heightAt(it.x, it.z) - (name === 'path_stones' ? 0.05 : 0.03);
        T.compose(p.set(it.x, y, it.z), q.setFromAxisAngle(up, it.rotY || 0), s.setScalar(it.scale || 1));
        inst.setMatrixAt(i, M.multiplyMatrices(T, n.matrixWorld));
      });
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
