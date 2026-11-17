"""Compose the island from the exported GLBs, write a suggested layout, and render previews.

blender -b --factory-startup --python compose.py -- <models_dir> <out_dir>

layout.json is in game space (+Y up, x/z on the ground, rotY in radians) so the game can place the
same dressing. The ground, hill, sea and path ribbons here are render-only stand-ins for the game's terrain.
"""
import json
import math
import os
import random
import sys

import bpy
import bmesh
from mathutils import Vector, Matrix, noise

argv = sys.argv[sys.argv.index('--') + 1:]
models, out = argv[0], argv[1]
os.makedirs(out, exist_ok=True)
rng = random.Random(7)
scene = bpy.context.scene
for ob in list(bpy.data.objects):
    bpy.data.objects.remove(ob, do_unlink=True)

# game-space layout from the build thread: name -> (x, z, zone radius)
ZONES = {'board': (0, 0, 4.5), 'nook': (-9, 9, 5), 'garden': (11, 9, 6.5), 'workshop': (15, -8, 6),
         'library': (-2, -17, 5.5), 'pond': (-16, -6, 7), 'meadow': (4, 21, 6.5), 'shore': (-24, 17, 6),
         'lookout': (22, -21, 5.5)}
HILL_H = 3.4
LAND_R = 33.0

protos = {}


def proto(name):
    if name not in protos:
        before = set(bpy.data.objects)
        f = os.path.join(models, name + '.gltf')
        bpy.ops.import_scene.gltf(filepath=f if os.path.exists(f) else os.path.join(models, name + '.glb'))
        for o in bpy.data.objects:
            if o not in before and o.name.split('.')[0] in ('Canopy_spring', 'Canopy_autumn', 'Canopy_winter', 'Leaves_spring', 'Leaves_autumn', 'Leaves_winter', 'Snow'):
                o.hide_render = True
        new = [o for o in bpy.data.objects if o not in before]
        root = next(o for o in new if o.parent is None)
        root.location = (0, 0, -500)
        protos[name] = root
    return protos[name]


def dup(ob, parent=None):
    c = ob.copy()
    scene.collection.objects.link(c)
    c.parent = parent
    for ch in ob.children:
        dup(ch, c)
    return c


placed = []


def hill(x, z):
    hx, hz, hr = ZONES['lookout']
    d = math.hypot(x - hx, z - hz) / (hr * 1.5)
    return HILL_H * max(0.0, 1 - d * d) ** 1.5 if d < 1 else 0.0


def place(name, x, z, rot=None, scale=1.0, y=None):
    """Place at game coords (x, z); rot None faces the plaza."""
    if rot is None:
        rot = math.atan2(-x, -z) if (x or z) else 0.0
    o = dup(proto(name))
    o.rotation_mode = 'XYZ'
    o.location = (x, -z, hill(x, z) if y is None else y)
    o.rotation_euler = (0, 0, rot)
    o.scale = (scale,) * 3
    placed.append({'name': name, 'x': round(x, 2), 'z': round(z, 2), 'rotY': round(rot, 3), 'scale': round(scale, 2)})
    return o


def free(x, z, margin=0.0):
    if math.hypot(x, z) > LAND_R - 2.5:
        return False
    for ex, ez, er in ((24, 3, 4.0), (-21.5, 14.5, 3.5), (16, -17, 4.5), (-1, -9.5, 3.0)):
        if math.hypot(x - ex, z - ez) < er + margin:
            return False
    for nm, (zx, zz, zr) in ZONES.items():
        if nm in ('meadow', 'shore'):
            continue
        if math.hypot(x - zx, z - zz) < zr * (0.85 if nm != 'pond' else 1.0) + margin:
            return False
    return True


def near_path(x, z, w=1.6):
    for nm, (zx, zz, _) in ZONES.items():
        if nm == 'board':
            continue
        L = math.hypot(zx, zz)
        t = max(0.0, min(1.0, (x * zx + z * zz) / (L * L)))
        if math.hypot(x - zx * t, z - zz * t) < w:
            return True
    return False


# --- landmarks
place('notice_board', 0, 0, 0.0)
place('burrow', *ZONES['nook'][:2])
place('workshop_hut', *ZONES['workshop'][:2])
place('library_tower', *ZONES['library'][:2])
place('computer', -2 + 3.3, -17 + 1.6, rot=math.atan2(2 - 3.3, 17 - 1.6))
place('pond', *ZONES['pond'][:2])
gx, gz = ZONES['garden'][:2]
for dx in (-1.9, 1.9):
    for dz in (-1.6, 1.6):
        place('garden_plot', gx + dx, gz + dz, rot=0.0)
for i in range(4):   # fence along the back and sides of the garden
    place('fence', gx - 3.6 + 2.4 * i, gz - 4.0, rot=0.0)
for i in range(3):
    place('fence', gx + 4.9, gz - 2.6 + 2.4 * i, rot=math.pi / 2)
    place('fence', gx - 4.9, gz - 2.6 + 2.4 * i, rot=math.pi / 2)
place('well', gx - 6.0, gz - 4.6)
lx, lz = ZONES['lookout'][:2]
place('observatory', lx, lz)
place('waterfall', 16, -17, rot=math.atan2(-6, 4))
place('bridge', -1, -9.5, rot=math.atan2(-2, -17))
place('campfire', 24, 3)
place('beach_hut', -21.5, 14.5)
# plaza ring of low wall with gaps for the paths
for k in range(4):
    place('stone_wall', 0, 0, rot=math.pi / 4 + k * math.pi / 2 + 0.2, scale=1.5)
place('signpost', 2.6, 2.2)
place('bench', -2.9, 2.0, rot=math.atan2(2.9, -2.0))
place('lantern', 3.0, -2.4)
place('lantern', -3.2, -2.6)
place('bench', -16 + 6.6, -6 + 4.6, rot=math.atan2(-6.6, -4.6))
place('stump', 4.5, 20.0)
place('mushrooms', 5.4, 20.6)
place('barrel', 15 + 3.2, -8 + 2.6)
place('crate', 15 + 3.9, -8 + 1.9, rot=0.4)

# --- paths from the plaza to each place
ribbons = []
for nm, (zx, zz, zr) in ZONES.items():
    if nm == 'board':
        continue
    L = math.hypot(zx, zz)
    ang = math.atan2(zx, zz)
    start, end = 5.2, L - zr * (0.62 if nm not in ('pond',) else 0.9)
    n = int((end - start) / 2.5)
    for i in range(n + 1):
        t = (start + (end - start) * (i / max(1, n))) / L
        place('path_stones', zx * t, zz * t, rot=ang + rng.uniform(-0.08, 0.08))
        if i % 3 == 1 and nm not in ('lookout',):
            side = 1 if (i // 3) % 2 else -1
            place('lantern', zx * t + math.cos(ang) * 1.5 * side, zz * t - math.sin(ang) * 1.5 * side, rot=ang + (math.pi / 2) * side)
    ribbons.append((start / L, end / L, zx, zz))

# --- clumps of trees, then loose dressing
count = 0
tries = 0
while count < 26 and tries < 2000:
    tries += 1
    a, r = rng.uniform(0, 2 * math.pi), LAND_R * math.sqrt(rng.uniform(0.05, 0.85))
    x, z = r * math.cos(a), r * math.sin(a)
    if not free(x, z, 2.0) or near_path(x, z, 3.0):
        continue
    count += 1
    for k in range(rng.randint(2, 4)):
        ox, oz = rng.uniform(-3, 3), rng.uniform(-3, 3)
        if free(x + ox, z + oz, 1.0) and not near_path(x + ox, z + oz, 2.2):
            place(rng.choice(('tree', 'tree_tall', 'tree_wide', 'tree_birch', 'tree_blossom', 'pine', 'pine', 'pine_tall')), x + ox, z + oz, rot=rng.uniform(0, 6.28), scale=rng.uniform(0.85, 1.15))
    for k in range(rng.randint(1, 3)):
        ox, oz = rng.uniform(-4, 4), rng.uniform(-4, 4)
        if free(x + ox, z + oz, 0.5) and not near_path(x + ox, z + oz, 1.4):
            place(rng.choice(('bush', 'bush_low', 'bush_berry', 'rock', 'rock_flat')), x + ox, z + oz, rot=rng.uniform(0, 6.28), scale=rng.uniform(0.8, 1.25))

for name, n, margin in (('grass_tuft', 420, -1.0), ('flower_cluster', 60, -0.5), ('flower_cluster_gold', 50, -0.5),
                        ('flower_cluster_blue', 40, -0.5), ('mushrooms', 14, 0.5), ('rock', 8, 0.5), ('rock_tall', 4, 0.5), ('rock_flat', 6, 0.5), ('bush', 10, 0.5), ('bush_low', 10, 0.5), ('bush_berry', 6, 0.5)):
    c = 0
    tries = 0
    while c < n and tries < 20000:
        tries += 1
        a, r = rng.uniform(0, 2 * math.pi), LAND_R * math.sqrt(rng.uniform(0.0, 0.9))
        x, z = r * math.cos(a), r * math.sin(a)
        if not free(x, z, margin) or near_path(x, z, 1.0):
            continue
        if name.startswith('flower') and rng.random() < 0.5:   # meadow gets most of the flowers
            x, z = ZONES['meadow'][0] + rng.uniform(-6, 6), ZONES['meadow'][1] + rng.uniform(-6, 6)
            if math.hypot(x, z) > LAND_R - 2:
                continue
        c += 1
        place(name, x, z, rot=rng.uniform(0, 6.28), scale=rng.uniform(0.9, 1.5) if name != 'grass_tuft' else rng.uniform(1.0, 1.8))

json.dump({'note': 'Suggested dressing in game space. y is ground height at (x, z).', 'items': placed},
          open(os.path.join(out, 'layout.json'), 'w'))

# Ash by the notice board
ash = dup(proto('memo_grown'))
ash.location = (0.9, -6.6, 0)
ash.rotation_euler = (0, 0, 0.75)

# --- render-only terrain
def pmat(name, col, rough=1.0):
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    b = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    b.inputs['Base Color'].default_value = (*col, 1)
    b.inputs['Roughness'].default_value = rough
    return m, b


def add_mesh(name, bm, m):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(m)
    for p in me.polygons:
        p.use_smooth = True
    o = bpy.data.objects.new(name, me)
    scene.collection.objects.link(o)
    return o


bm = bmesh.new()
N, M = 96, 40
rings = []
for j in range(M + 1):
    r = 39.0 * j / M
    ring = []
    for i in range(N):
        a = 2 * math.pi * i / N
        x, y = r * math.cos(a), r * math.sin(a)
        edge = LAND_R + 1.5 * noise.noise(Vector((math.cos(a) * 2, math.sin(a) * 2, 0.5)))
        h = hill(x, -y) + 0.05 * noise.noise(Vector((x * 0.15, y * 0.15, 0)))
        if r > edge:
            h -= min(1.2, (r - edge) * 0.28)
        ring.append(bm.verts.new((x, y, h - 0.02)))
    rings.append(ring)
for j in range(M):
    for i in range(N):
        k = (i + 1) % N
        if j == 0:
            continue
        bm.faces.new((rings[j][i], rings[j][k], rings[j + 1][k], rings[j + 1][i]))
gm, gb = pmat('ground', (0.36, 0.52, 0.2))
nt = gm.node_tree
geo = nt.nodes.new('ShaderNodeNewGeometry')
sep = nt.nodes.new('ShaderNodeSeparateXYZ')
ramp = nt.nodes.new('ShaderNodeValToRGB')
nz = nt.nodes.new('ShaderNodeTexNoise')
nz.inputs['Scale'].default_value = 0.35
mix = nt.nodes.new('ShaderNodeMixRGB')
ramp2 = nt.nodes.new('ShaderNodeValToRGB')
nt.links.new(geo.outputs['Position'], sep.inputs[0])
ramp.color_ramp.elements[0].position = 0.0
ramp.color_ramp.elements[0].color = (0.80, 0.70, 0.42, 1)
ramp.color_ramp.elements[1].position = 1.0
ramp.color_ramp.elements[1].color = (0.36, 0.52, 0.2, 1)
mapr = nt.nodes.new('ShaderNodeMapRange')
mapr.inputs['From Min'].default_value = -0.75
mapr.inputs['From Max'].default_value = -0.25
nt.links.new(sep.outputs['Z'], mapr.inputs['Value'])
nt.links.new(mapr.outputs['Result'], ramp.inputs['Fac'])
ramp2.color_ramp.elements[0].color = (0.30, 0.47, 0.18, 1)
ramp2.color_ramp.elements[1].color = (0.46, 0.60, 0.24, 1)
nt.links.new(nz.outputs[0], ramp2.inputs['Fac'])
nt.links.new(mapr.outputs['Result'], mix.inputs['Fac'])
nt.links.new(ramp.outputs['Color'], mix.inputs['Color1'])
nt.links.new(ramp2.outputs['Color'], mix.inputs['Color2'])
nt.links.new(mix.outputs['Color'], gb.inputs['Base Color'])
add_mesh('ground', bm, gm)

bm = bmesh.new()
bmesh.ops.create_circle(bm, cap_ends=True, segments=64, radius=400)
sm, sb = pmat('sea', (0.16, 0.45, 0.58), 0.15)
sea = add_mesh('sea', bm, sm)
sea.location.z = -0.55

pm, _ = pmat('path', (0.72, 0.62, 0.42))
for t0, t1, zx, zz in ribbons:
    bm = bmesh.new()
    L = math.hypot(zx, zz)
    px, pz = -zz / L, zx / L
    n = 24
    prev = None
    for i in range(n + 1):
        t = t0 + (t1 - t0) * i / n
        x, z = zx * t, zz * t
        w = 0.95 + 0.12 * math.sin(i * 1.3)
        cur = (bm.verts.new((x + px * w, -(z + pz * w), hill(x, z) + 0.012)), bm.verts.new((x - px * w, -(z - pz * w), hill(x, z) + 0.012)))
        if prev:
            bm.faces.new((prev[0], prev[1], cur[1], cur[0]))
        prev = cur
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    add_mesh('path', bm, pm)
bm = bmesh.new()
bmesh.ops.create_circle(bm, cap_ends=True, segments=40, radius=4.4)
pl = add_mesh('plaza', bm, pm)
pl.location.z = 0.012

# --- light and cameras
world = bpy.data.worlds.new('w')
scene.world = world
try:
    world.use_nodes = True
except Exception:
    pass
bg = next(n for n in world.node_tree.nodes if n.type == 'BACKGROUND')
bg.inputs[0].default_value = (0.58, 0.78, 1.0, 1)
bg.inputs[1].default_value = 0.85
sun = bpy.data.lights.new('sun', 'SUN')
sun.energy = 2.3
sun.angle = math.radians(8)
sun.color = (1.0, 0.94, 0.84)
so = bpy.data.objects.new('sun', sun)
scene.collection.objects.link(so)
so.rotation_euler = (math.radians(50), 0, math.radians(-40))

cam = bpy.data.cameras.new('cam')
cam.clip_end = 3000
co = bpy.data.objects.new('cam', cam)
scene.collection.objects.link(co)
scene.camera = co
for eng in ('BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT'):
    try:
        scene.render.engine = eng
        break
    except Exception:
        pass
try:
    scene.eevee.taa_render_samples = 48
    scene.view_settings.view_transform = 'Standard'
except Exception:
    pass
scene.render.image_settings.file_format = 'PNG'

SHOTS = {
    'island': ((18, -92, 62), (0, 2, 0), 62, (2400, 1500)),
    'plaza': ((7, -13, 4.5), (0, 0, 1.3), 32, (2200, 1300)),
    'den': ((-1.5, -3.5, 3.0), (-9, -9, 1.0), 30, (2200, 1300)),
    'library': ((7, 6.5, 4.5), (-2, 17, 2.6), 32, (2200, 1300)),
    'hill': ((6, 10, 6), (19, 19, 2.5), 30, (2200, 1300)),
    'camp_beach': ((14, -8, 5), (24, -3, 0.8), 30, (2200, 1300)),
}
for name, (pos, target, lens, res) in SHOTS.items():
    cam.lens = lens
    co.location = pos
    co.rotation_euler = (Vector(target) - Vector(pos)).to_track_quat('-Z', 'Y').to_euler()
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.filepath = os.path.join(out, name + '.png')
    bpy.ops.render.render(write_still=True)
    print('RENDERED', name)
