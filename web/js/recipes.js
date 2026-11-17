import * as THREE from 'three';

// Builds a mesh group from a "recipe": the list of simple shapes Memo wrote for something he made.
const GEO = {
  box: new THREE.BoxGeometry(1, 1, 1),
  sphere: new THREE.SphereGeometry(0.5, 24, 16),
  cylinder: new THREE.CylinderGeometry(0.5, 0.5, 1, 24),
  cone: new THREE.ConeGeometry(0.5, 1, 24),
  torus: new THREE.TorusGeometry(0.42, 0.08, 12, 32),
  capsule: new THREE.CapsuleGeometry(0.5, 1, 6, 16).scale(1, 0.5, 1),
  gem: new THREE.OctahedronGeometry(0.5, 0),
  leaf: new THREE.SphereGeometry(0.5, 12, 8),
};

const cache = new Map();
export function material(kind, color) {
  const key = `${kind}:${color}`;
  if (cache.has(key)) return cache.get(key);
  const c = new THREE.Color(color);
  let m;
  switch (kind) {
    case 'glossy': m = new THREE.MeshStandardMaterial({ color: c, roughness: 0.22 }); break;
    case 'metal': m = new THREE.MeshStandardMaterial({ color: c, roughness: 0.32, metalness: 1 }); break;
    case 'glass': m = new THREE.MeshStandardMaterial({ color: c, roughness: 0.05, transparent: true, opacity: 0.45 }); break;
    case 'glow': m = new THREE.MeshStandardMaterial({ color: c, emissive: c, emissiveIntensity: 1.8, roughness: 0.5 }); break;
    case 'wood': m = new THREE.MeshStandardMaterial({ color: c, roughness: 0.78 }); break;
    case 'stone': case 'moss': m = new THREE.MeshStandardMaterial({ color: c, roughness: 1, flatShading: kind === 'stone' }); break;
    default: m = new THREE.MeshStandardMaterial({ color: c, roughness: 0.85 });
  }
  cache.set(key, m);
  return m;
}

export function buildRecipe(recipe) {
  const group = new THREE.Group();
  for (const p of recipe.parts || []) {
    const mesh = new THREE.Mesh(GEO[p.shape] || GEO.box, material(p.material, p.color));
    mesh.scale.set(p.size[0], p.size[1], p.size[2]);
    mesh.position.set(p.position[0], p.position[1], p.position[2]);
    mesh.rotation.set(...p.rotation.map((d) => (d * Math.PI) / 180));
    mesh.castShadow = p.material !== 'glass';
    mesh.receiveShadow = true;
    group.add(mesh);
  }
  // Rest the object on the ground whatever the recipe said.
  const box = new THREE.Box3().setFromObject(group);
  if (Number.isFinite(box.min.y)) for (const c of group.children) c.position.y -= box.min.y;
  group.userData.animation = recipe.animation || 'none';
  return group;
}

export function animateRecipe(group, t) {
  const a = group.userData.animation, ph = group.userData.phase ?? (group.userData.phase = Math.random() * 6);
  const inner = group.userData.inner;
  if (!inner || a === 'none') return;
  if (a === 'bob') inner.position.y = Math.sin(t * 1.4 + ph) * 0.06 + 0.06;
  else if (a === 'spin') inner.rotation.y = t * 0.8 + ph;
  else if (a === 'sway') inner.rotation.z = Math.sin(t * 1.1 + ph) * 0.07;
  else if (a === 'pulse') { const s = 1 + Math.sin(t * 2 + ph) * 0.035; inner.scale.setScalar(s); }
}
