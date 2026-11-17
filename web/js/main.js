import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { heightAt, buildTerrain, buildGrass, buildFlowers } from './terrain.js';
import { builders, lamps, glows } from './builders.js';
import { animateRecipe } from './recipes.js';
import { Memo } from './memo.js';
import { api, stream, params } from './api.js';
import { initUI } from './ui.js';

const canvas = document.getElementById('scene');
const bubble = document.getElementById('bubble');

// ---------- renderer: WebGPU where the browser has it, WebGL 2 otherwise ----------
const renderer = new THREE.WebGPURenderer({ canvas, antialias: true, forceWebGL: params.get('webgl') === '1' });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;

const scene = new THREE.Scene();
scene.fog = new THREE.Fog('#cfe9f5', 150, 460);
const camera = new THREE.PerspectiveCamera(36, 1, 0.5, 600);
camera.position.set(30, 21, 38);
const controls = new OrbitControls(camera, canvas);
controls.target.set(0, 1.5, 0);
controls.enableDamping = true; controls.dampingFactor = 0.07;
controls.maxPolarAngle = 1.46; controls.minDistance = 4; controls.maxDistance = 110;

// ---------- sky, sun, moon, stars ----------
const skyGeo = new THREE.SphereGeometry(400, 32, 20);
skyGeo.setAttribute('color', new THREE.BufferAttribute(new Float32Array(skyGeo.attributes.position.count * 3), 3));
const sky = new THREE.Mesh(skyGeo, new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.BackSide, fog: false, depthWrite: false, toneMapped: false }));
scene.add(sky);
const hemi = new THREE.HemisphereLight('#dff1ff', '#6f8f5a', 1.0); scene.add(hemi);
const sun = new THREE.DirectionalLight('#fff3d6', 3);
sun.castShadow = true; sun.shadow.mapSize.set(2048, 2048);
Object.assign(sun.shadow.camera, { left: -48, right: 48, top: 48, bottom: -48, near: 1, far: 260 });
sun.shadow.bias = -0.0006; sun.shadow.normalBias = 0.06;
scene.add(sun, sun.target);
const sunDisc = new THREE.Mesh(new THREE.SphereGeometry(9, 20, 12), new THREE.MeshBasicMaterial({ color: '#fff2c9', fog: false, toneMapped: false }));
const moonDisc = new THREE.Mesh(new THREE.SphereGeometry(6, 20, 12), new THREE.MeshBasicMaterial({ color: '#e8eefc', fog: false, toneMapped: false }));
scene.add(sunDisc, moonDisc);

const stars = new THREE.InstancedMesh(new THREE.SphereGeometry(1.1, 5, 4), new THREE.MeshBasicMaterial({ color: '#ffffff', fog: false, transparent: true, toneMapped: false }), 420);
{
  const m = new THREE.Matrix4();
  for (let i = 0; i < 420; i++) {
    const th = Math.random() * 6.283, y = Math.random() * 0.95 + 0.04, r = Math.sqrt(1 - y * y), s = 0.5 + Math.random() * 1.2;
    m.makeScale(s, s, s).setPosition(Math.cos(th) * r * 370, y * 370, Math.sin(th) * r * 370);
    stars.setMatrixAt(i, m);
  }
  scene.add(stars);
}

// ---------- sea ----------
const sea = new THREE.Mesh(new THREE.CircleGeometry(400, 64).rotateX(-Math.PI / 2),
  new THREE.MeshStandardMaterial({ color: '#7fcfc9', roughness: 0.18, metalness: 0.05, transparent: true, opacity: 0.8 }));
sea.receiveShadow = true; scene.add(sea);
const seaFloor = new THREE.Mesh(new THREE.CircleGeometry(400, 32).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ color: '#4fa9b0' }));
seaFloor.position.y = -3; scene.add(seaFloor);

// ---------- clouds and fireflies ----------
const clouds = new THREE.Group(); scene.add(clouds);
const cloudMat = new THREE.MeshStandardMaterial({ color: '#ffffff', roughness: 1, transparent: true, opacity: 0.92, fog: false });
for (let i = 0; i < 9; i++) {
  const c = new THREE.Group(), blob = new THREE.IcosahedronGeometry(1, 2);
  for (let j = 0; j < 5; j++) { const b = new THREE.Mesh(blob, cloudMat); b.position.set((j - 2) * 3.2 + Math.random(), Math.random() * 1.2, Math.random() * 2); b.scale.set(3 + Math.random() * 2.5, 1.6 + Math.random(), 2.4 + Math.random() * 1.5); c.add(b); }
  c.position.set((Math.random() - 0.5) * 240, 36 + Math.random() * 22, (Math.random() - 0.5) * 240);
  c.userData.speed = 0.4 + Math.random() * 0.5; clouds.add(c);
}
const flies = new THREE.InstancedMesh(new THREE.SphereGeometry(0.06, 6, 4), new THREE.MeshBasicMaterial({ color: '#f8ff9a', toneMapped: false }), 46);
const flySeeds = Array.from({ length: 46 }, () => ({ a: Math.random() * 6.28, r: 2 + Math.random() * 7, y: 0.6 + Math.random() * 2, s: 0.3 + Math.random() * 0.6, home: Math.random() < 0.6 ? 'pond' : 'meadow' }));
scene.add(flies);

// ---------- time of day ----------
const forcedHour = params.get('hour') !== null ? Number(params.get('hour')) : null;
const hourNow = () => { if (forcedHour !== null) return forcedHour; const d = new Date(); return d.getHours() + d.getMinutes() / 60 + d.getSeconds() / 3600; };
const K = (h) => new THREE.Color(h), mix = (a, b, t) => a.clone().lerp(b, Math.min(1, Math.max(0, t)));
const SKY = { dayTop: K('#5fa8e6'), dayLow: K('#e9e3d0'), duskTop: K('#6f74b5'), duskLow: K('#ffbf8f'), nightTop: K('#0c1230'), nightLow: K('#27365f') };
let night = 0;
function applyTime() {
  const h = hourNow(), ang = ((h - 6) / 12) * Math.PI, elev = Math.sin(ang);
  const day = THREE.MathUtils.smoothstep(elev, -0.12, 0.3), golden = Math.max(0, 1 - Math.abs(elev - 0.05) / 0.3);
  night = 1 - THREE.MathUtils.smoothstep(elev, -0.2, 0.08);
  const top = mix(mix(SKY.nightTop, SKY.dayTop, day), SKY.duskTop, golden * 0.75);
  const low = mix(mix(SKY.nightLow, SKY.dayLow, day), SKY.duskLow, golden * 0.9);
  const pos = skyGeo.attributes.position, col = skyGeo.attributes.color, c = new THREE.Color();
  for (let i = 0; i < pos.count; i++) { const t = Math.pow(Math.max(0, pos.getY(i) / 400), 0.55); c.copy(low).lerp(top, t); col.setXYZ(i, c.r, c.g, c.b); }
  col.needsUpdate = true;
  scene.fog.color.copy(low);
  const dir = new THREE.Vector3(Math.cos(ang) * 0.9, Math.max(elev, -0.3), 0.45).normalize();
  sunDisc.position.copy(dir).multiplyScalar(360); sunDisc.visible = elev > -0.08;
  sunDisc.material.color.copy(mix(K('#fff6dd'), K('#ffb36b'), golden));
  const moonDir = new THREE.Vector3(-Math.cos(ang) * 0.8, Math.max(-elev, 0.25), -0.5).normalize();
  moonDisc.position.copy(moonDir).multiplyScalar(360); moonDisc.visible = night > 0.3;
  // one shadow-casting light: the sun by day, the moon by night
  const lightDir = night > 0.6 ? moonDir : dir.clone().setY(Math.max(dir.y, 0.12)).normalize();
  sun.position.copy(lightDir).multiplyScalar(120); sun.target.position.set(0, 0, 0);
  sun.color.copy(night > 0.6 ? K('#a9bfff') : mix(K('#ffe9c4'), K('#ffa46a'), golden * 0.9));
  sun.intensity = night > 0.6 ? 0.9 : 0.5 + day * 2.5;
  hemi.color.copy(mix(K('#3a4c85'), K('#ffeedd'), day)); hemi.groundColor.copy(mix(K('#1b2540'), K('#b7c98a'), day));
  hemi.intensity = 0.6 + day * 0.3;
  stars.visible = night > 0.2; stars.material.opacity = night;
  sea.material.color.copy(mix(K('#16365a'), K('#7fcfc9'), day).lerp(K('#c9786a'), golden * 0.25));
  cloudMat.color.copy(mix(K('#39456b'), K('#ffffff'), day).lerp(K('#ffc9a1'), golden * 0.6));
  for (const l of lamps) { l.light.intensity = night * 22 * l.power; l.bulb.material.emissiveIntensity = 0.15 + night * 3; }
  for (const g of glows) g.material.emissiveIntensity = 0.1 + night * 2.4;
  flies.visible = night > 0.4;
  renderer.toneMappingExposure = 0.98 - night * 0.02;
  seaFloor.material.color.copy(mix(K('#0f2440'), K('#4fa9b0'), day));
}

// ---------- the world from the database ----------
const world = { zones: [], objects: new Map(), memo: new Memo(), parcels: [], data: null };
scene.add(world.memo.root);
const pickable = [];

function placeObject(o) {
  const build = builders[o.kind];
  if (!build) return;
  let g;
  if (models[o.kind]) { g = new THREE.Group(); g.add(models[o.kind].clone(true)); if (o.kind === 'notice_board') { g.userData.notes = new THREE.Group(); g.userData.notes.position.set(0, 1.45, 0.1); g.userData.parcels = new THREE.Group(); g.userData.parcels.position.set(0, 0, 1.3); g.add(g.userData.notes, g.userData.parcels); } }
  else g = build(o);
  g.position.set(o.x, heightAt(o.x, o.z), o.z);
  if (!g.userData.noRotate) g.rotation.y = o.rot || 0;
  if (o.kind !== 'creation' && o.kind !== 'pet') g.scale.setScalar(o.scale || 1);
  if (g.userData.followGround) {
    g.rotation.y = 0;
    const done = new Set();
    for (const c of g.children) { const k = `${c.position.x.toFixed(2)},${c.position.z.toFixed(2)}`; c.position.y += heightAt(o.x + c.position.x, o.z + c.position.z) - g.position.y; done.add(k); }
  }
  g.userData.obj = o;
  if (o.kind === 'pet') g.userData.home = new THREE.Vector3(o.x, 0, o.z), g.userData.goal = new THREE.Vector3(o.x, 0, o.z), g.userData.wait = 1;
  scene.add(g); world.objects.set(o.id, g);
  if (o.name || o.kind === 'creation' || o.kind === 'pet') pickable.push(g);
  if (o.kind === 'notice_board') world.board = g;
}
function removeObject(id) {
  const g = world.objects.get(id); if (!g) return;
  scene.remove(g); world.objects.delete(id);
  const i = pickable.indexOf(g); if (i >= 0) pickable.splice(i, 1);
}

export function refreshBoard(wishes, parcels) {
  const b = world.board; if (!b) return;
  b.userData.notes.clear(); b.userData.parcels.clear();
  const open = wishes.filter((w) => w.status === 'open').slice(0, 10);
  const paper = ['#fff8e1', '#ffe0e0', '#e3f2fd', '#e8f5e9', '#fff3c4'];
  open.forEach((w, i) => {
    const n = new THREE.Mesh(new THREE.BoxGeometry(0.32, 0.36, 0.01), new THREE.MeshStandardMaterial({ color: paper[i % 5], roughness: 0.9 }));
    n.position.set(-0.8 + (i % 5) * 0.4, 0.25 - Math.floor(i / 5) * 0.48, 0); n.rotation.z = Math.sin(w.id * 3.1) * 0.14; b.userData.notes.add(n);
    const pin = new THREE.Mesh(new THREE.SphereGeometry(0.03, 8, 6), new THREE.MeshStandardMaterial({ color: '#d1495b', roughness: 0.3 }));
    pin.position.set(n.position.x, n.position.y + 0.13, 0.02); b.userData.notes.add(pin);
  });
  parcels.forEach((p, i) => { const g = builders.parcel(p.kind); g.position.set(-1.2 + (i % 5) * 0.62, 0, Math.floor(i / 5) * 0.6); g.rotation.y = i * 0.7; b.userData.parcels.add(g); });
}

// ---------- picking ----------
const ray = new THREE.Raycaster(), mouse = new THREE.Vector2();
let downAt = null;
canvas.addEventListener('pointerdown', (e) => { downAt = [e.clientX, e.clientY]; });
canvas.addEventListener('pointerup', (e) => {
  if (!downAt || Math.hypot(e.clientX - downAt[0], e.clientY - downAt[1]) > 5) return;
  mouse.set((e.clientX / innerWidth) * 2 - 1, -(e.clientY / innerHeight) * 2 + 1);
  ray.setFromCamera(mouse, camera);
  const hits = ray.intersectObjects([...pickable, world.memo.root], true);
  let hit = hits[0]?.object;
  while (hit && !hit.userData.obj && hit !== world.memo.root) hit = hit.parent;
  ui.select(hit === world.memo.root ? { memo: true } : hit?.userData.obj || null);
});

// ---------- frame loop ----------
let follow = false;
export const setFollow = (v) => { follow = v; };
export const focusOn = (x, z, dist = 16) => {
  const y = heightAt(x, z) + 1;
  const off = camera.position.clone().sub(controls.target).setLength(dist);
  controls.target.set(x, y, z); camera.position.copy(controls.target).add(off);
};
function resize() { renderer.setSize(innerWidth, innerHeight, false); camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix(); }
addEventListener('resize', resize);

const clock = new THREE.Clock(), head = new THREE.Vector3(), m4 = new THREE.Matrix4();
let timeTimer = 0;
function frame() {
  const dt = Math.min(clock.getDelta(), 0.1), t = clock.elapsedTime;
  if ((timeTimer -= dt) <= 0) { applyTime(); timeTimer = forcedHour !== null ? 1e9 : 20; }
  world.memo.update(dt, t);
  for (const g of world.objects.values()) {
    if (g.userData.sway) g.userData.sway.rotation.z = Math.sin(t * 0.9 + g.position.x) * 0.025, g.userData.sway.rotation.x = Math.cos(t * 0.7 + g.position.z) * 0.02;
    if (g.userData.inner) animateRecipe(g, t);
    if (g.userData.water) g.userData.water.position.y = 0.38 + Math.sin(t * 0.8) * 0.015;
    if (g.userData.pet) updatePet(g, dt, t);
  }
  sea.position.y = Math.sin(t * 0.5) * 0.06;
  for (const c of clouds.children) { c.position.x += c.userData.speed * dt; if (c.position.x > 150) c.position.x = -150; }
  if (flies.visible) flySeeds.forEach((f, i) => {
    const z = world.zones.find((zn) => zn.id === f.home) || { x: 0, z: 0 };
    const a = f.a + t * f.s * 0.3;
    m4.makeTranslation(z.x + Math.cos(a) * f.r, heightAt(z.x, z.z) + f.y + Math.sin(t * f.s * 2 + i) * 0.4, z.z + Math.sin(a * 1.3) * f.r);
    flies.setMatrixAt(i, m4);
  }), flies.instanceMatrix.needsUpdate = true;
  if (follow) { const p = world.memo.root.position; controls.target.lerp(head.set(p.x, p.y + 0.6, p.z), 0.06); }
  controls.update();
  // thought bubble follows Memo's head
  head.copy(world.memo.root.position); head.y += 1.25 * world.memo.root.scale.y;
  head.project(camera);
  const visible = head.z < 1 && Math.abs(head.x) < 1.1 && Math.abs(head.y) < 1.1;
  bubble.style.opacity = visible && bubble.dataset.has ? 1 : 0;
  bubble.style.transform = `translate(-50%, -100%) translate(${((head.x + 1) / 2) * innerWidth}px, ${((1 - head.y) / 2) * innerHeight}px)`;
  render();
}

function updatePet(g, dt, t) {
  const u = g.userData, p = g.position;
  const dx = u.goal.x - p.x, dz = u.goal.z - p.z, d = Math.hypot(dx, dz);
  if (d > 0.1) {
    const step = Math.min(d, dt * (d > 6 ? 3 : 1.2));
    p.x += (dx / d) * step; p.z += (dz / d) * step;
    g.rotation.y = Math.atan2(dx, dz);
    u.inner.position.y = Math.abs(Math.sin(t * 10)) * 0.08;
  } else if ((u.wait -= dt) <= 0) {
    const a = Math.random() * 6.28, r = 0.6 + Math.random() * 2.2;
    u.goal.set(u.home.x + Math.cos(a) * r, 0, u.home.z + Math.sin(a) * r); u.wait = 2 + Math.random() * 6;
  } else u.inner.position.y *= 0.8;
  p.y = heightAt(p.x, p.z);
}

// The diorama look: soft contact shadows (ambient occlusion), a gentle depth of field that keeps
// whatever the camera looks at sharp, and a little glow. Each effect is optional: if one cannot
// be built on this machine it is skipped, and ?fx=0 turns them all off.
let render = () => renderer.render(scene, camera);
let focusUniform = null;
async function setupEffects() {
  if (params.get('fx') === '0' || params.get('bloom') === '0') return;
  let pipeline, out, scenePass;
  try {
    const TSL = await import('three/tsl');
    const Pipeline = THREE.RenderPipeline || THREE.PostProcessing;
    pipeline = new Pipeline(renderer);
    scenePass = TSL.pass(scene, camera);
    out = scenePass.getTextureNode('output');
    const tryFx = async (name, fn) => { if (params.get(name) === '0') return; try { out = await fn(TSL); } catch (e) { console.warn(`Effect "${name}" is not available here; skipping it.`, e); } };
    await tryFx('ao', async () => {
      const { ao } = await import('three/addons/tsl/display/GTAONode.js');
      const aoPass = ao(scenePass.getTextureNode('depth'), null, camera);
      aoPass.resolutionScale = 0.5; aoPass.radius.value = 1.1; aoPass.thickness.value = 1.4; aoPass.scale.value = 1.25;
      const shade = aoPass.getTextureNode().r;
      return out.mul(TSL.vec4(TSL.mix(TSL.vec3(0.42, 0.36, 0.44), TSL.vec3(1), shade), 1));
    });
    await tryFx('dof', async () => {
      const { dof } = await import('three/addons/tsl/display/DepthOfFieldNode.js');
      focusUniform = { distance: TSL.uniform(40), range: TSL.uniform(40) };
      return dof(out, scenePass.getViewZNode(), focusUniform.distance, focusUniform.range, 1.2);
    });
    await tryFx('glow', async () => {
      const { bloom } = await import('three/addons/tsl/display/BloomNode.js');
      return out.add(bloom(out, 0.22, 0.6, 1.0));
    });
    pipeline.outputNode = out;
    render = () => {
      if (focusUniform) { const d = camera.position.distanceTo(controls.target); focusUniform.distance.value = d; focusUniform.range.value = Math.max(8, d * 1.15); }
      pipeline.render();
    };
  } catch (e) { console.warn('Effects are not available here; rendering without them.', e); }
}

// Hand-made models (GLB) can replace any procedural mesh: list them in web/assets/models/manifest.json
// as {"models":[{"name":"library_tower","file":"library_tower.glb"}]}. The name is the object's kind,
// or memo_childlike / memo_young / memo_growing_up / memo_grown for Memo himself.
const models = {};
async function loadModels() {
  let manifest;
  try { const r = await fetch('/assets/models/manifest.json'); if (!r.ok) return; manifest = await r.json(); } catch { return; }
  const { GLTFLoader } = await import('three/addons/loaders/GLTFLoader.js');
  const loader = new GLTFLoader();
  await Promise.all((manifest.models || []).map(async (m) => {
    try {
      const gltf = await loader.loadAsync(`/assets/models/${m.file}`);
      gltf.scene.traverse((n) => { if (n.isMesh) { n.castShadow = true; n.receiveShadow = true; } });
      models[m.name] = gltf.scene;
    } catch (e) { console.warn(`Could not load model ${m.file}; using the built-in shape.`, e); }
  }));
}
const stageKey = (stage) => `memo_${String(stage).replace(/ /g, '_')}`;

// ---------- start ----------
let ui;
async function start() {
  let data;
  try { data = await api('world'); } catch (e) { document.getElementById('gate').hidden = false; document.getElementById('gate-msg').textContent = e.message; return; }
  world.data = data; world.zones = data.zones;
  scene.add(buildTerrain(data.zones), buildGrass(data.zones), buildFlowers(data.zones));
  await loadModels();
  for (const o of data.objects) placeObject(o);
  world.memo.models = Object.fromEntries(Object.entries(models).filter(([k]) => k.startsWith('memo_')));
  world.memo.setState(data.memo);
  ui = await initUI({ world, data, focusOn, setFollow, refreshBoard });
  await renderer.init();
  resize(); applyTime();
  await setupEffects();
  document.body.dataset.backend = renderer.backend?.isWebGPUBackend ? 'WebGPU' : 'WebGL 2';
  renderer.setAnimationLoop(frame);
  document.body.classList.add('ready');
  window.memoWorld = { camera, controls, world, focusOn }; // handy in the browser console

  stream((msg) => {
    if (msg.type === 'memo') { world.memo.setState(msg.memo); ui.memo(msg.memo); }
    else if (msg.type === 'object') { removeObject(msg.object.id); placeObject(msg.object); ui.changed('objects'); }
    else if (msg.type === 'object_removed') removeObject(msg.id);
    else if (msg.type === 'object_moved') { const g = world.objects.get(msg.id); if (g?.userData.pet) g.userData.home.set(msg.x, 0, msg.z), g.userData.goal.set(msg.x, 0, msg.z); }
    else ui.changed(msg.type, msg);
  });
}
start();
