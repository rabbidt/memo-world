// A "recipe" is how Memo describes a thing it made: a handful of simple shapes the browser can build.
export const SHAPES = ['box', 'sphere', 'cylinder', 'cone', 'torus', 'capsule', 'gem', 'leaf'];
export const MATERIALS = ['matte', 'glossy', 'metal', 'glass', 'glow', 'wood', 'stone', 'moss'];
export const ANIMATIONS = ['none', 'bob', 'spin', 'sway', 'pulse'];

const vec3 = { type: 'array', items: { type: 'number' }, minItems: 3, maxItems: 3 };

export const RECIPE_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['name', 'story', 'story_english', 'parts', 'animation'],
  properties: {
    name: { type: 'string', description: 'What Memo calls this thing. A few words.' },
    story: { type: 'string', description: 'Two or three sentences in Memo\'s own voice (any style or invented words he likes): why it was made and what it means.' },
    story_english: { type: 'string', description: 'The same story in plain, complete English.' },
    parts: {
      type: 'array',
      description: 'Between 3 and 24 shapes. The object sits on the ground at y = 0 and should fit inside a box about 1.6 wide and 2 tall.',
      items: {
        type: 'object',
        additionalProperties: false,
        required: ['shape', 'size', 'position', 'rotation', 'color', 'material'],
        properties: {
          shape: { type: 'string', enum: SHAPES },
          size: { ...vec3, description: 'Width, height, depth in metres. For a torus: ring diameter, tube thickness, ring diameter.' },
          position: { ...vec3, description: 'Centre of the shape: x, y (up), z in metres.' },
          rotation: { ...vec3, description: 'Rotation in degrees around x, y, z.' },
          color: { type: 'string', description: 'Hex colour like #7aa95c.' },
          material: { type: 'string', enum: MATERIALS },
        },
      },
    },
    animation: { type: 'string', enum: ANIMATIONS, description: 'A gentle motion for the whole object.' },
  },
};

const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, Number.isFinite(Number(v)) ? Number(v) : 0));
const v3 = (a, lo, hi, d) => [0, 1, 2].map((i) => clamp(Array.isArray(a) ? a[i] ?? d : d, lo, hi));

// Never trust model output: clamp everything so a recipe can't break or swamp the world.
// "big" recipes are town buildings: more parts and a larger footprint.
export function sanitizeRecipe(raw, big = false) {
  if (!raw || typeof raw !== 'object' || !Array.isArray(raw.parts)) return null;
  const reach = big ? 2.6 : 1.2, tall = big ? 5.5 : 2.6, maxSize = big ? 5 : 2;
  const parts = raw.parts.slice(0, big ? 40 : 24).filter((p) => p && typeof p === 'object').map((p) => ({
    shape: SHAPES.includes(p.shape) ? p.shape : 'box',
    size: v3(p.size, 0.02, maxSize, 0.3),
    position: [clamp(p.position?.[0], -reach, reach), clamp(p.position?.[1], 0, tall), clamp(p.position?.[2], -reach, reach)],
    rotation: v3(p.rotation, -360, 360, 0),
    color: /^#[0-9a-fA-F]{6}$/.test(p.color || '') ? p.color : '#8fae7a',
    material: MATERIALS.includes(p.material) ? p.material : 'matte',
  }));
  if (parts.length < 1) return null;
  return {
    name: String(raw.name || 'a small thing').slice(0, 60),
    story: String(raw.story || '').slice(0, 600),
    story_english: String(raw.story_english || raw.story || '').slice(0, 600),
    parts,
    animation: ANIMATIONS.includes(raw.animation) ? raw.animation : 'none',
    big,
  };
}
