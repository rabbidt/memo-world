"""Golden-hour beauty renders of one model: close-up, mid shot and a six-view turntable sheet.

blender -b --factory-startup --python hero.py -- model.glb out_dir [name] [season]
"""
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Vector

argv = sys.argv[sys.argv.index('--') + 1:]
glb, out = argv[0], argv[1]
name = argv[2] if len(argv) > 2 else os.path.splitext(os.path.basename(glb))[0]
season = argv[3] if len(argv) > 3 else 'summer'
os.makedirs(out, exist_ok=True)
scene = bpy.context.scene
for ob in list(bpy.data.objects):
    bpy.data.objects.remove(ob, do_unlink=True)

bpy.ops.import_scene.gltf(filepath=glb)
objs = list(bpy.data.objects)
root = next(o for o in objs if o.parent is None)
root.rotation_mode = 'XYZ'
for o in objs:
    base = o.name.split('.')[0]
    if base.startswith(('Canopy_', 'Leaves_')):
        o.scale = (1, 1, 1) if base.endswith('_' + season) else (0.001,) * 3
    if base == 'Snow':
        o.scale = (1, 1, 1) if season == 'winter' else (0.001,) * 3
bpy.context.view_layer.update()
lo = Vector((1e9,) * 3)
hi = Vector((-1e9,) * 3)
for o in objs:
    if o.type == 'MESH' and min(o.scale) > 0.5:
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            for k in range(3):
                lo[k] = min(lo[k], w[k])
                hi[k] = max(hi[k], w[k])
size = hi - lo
H = size.z
centre = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, 0))

# ground: soft two-tone meadow
bpy.ops.mesh.primitive_plane_add(size=600)
g = bpy.context.object
gm = bpy.data.materials.new('ground')
try:
    gm.use_nodes = True
except Exception:
    pass
nt = gm.node_tree
b = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
nz = nt.nodes.new('ShaderNodeTexNoise')
nz.inputs['Scale'].default_value = 0.6
ramp = nt.nodes.new('ShaderNodeValToRGB')
ramp.color_ramp.elements[0].color = (0.16, 0.30, 0.09, 1)
ramp.color_ramp.elements[1].color = (0.36, 0.50, 0.14, 1)
nt.links.new(nz.outputs[0], ramp.inputs['Fac'])
nt.links.new(ramp.outputs['Color'], b.inputs['Base Color'])
b.inputs['Roughness'].default_value = 1.0
g.data.materials.append(gm)

# meadow dressing (render only): grass-card tufts from the model's own foliage atlas
fol = bpy.data.materials.get('foliage')
if fol:
    import random
    rng = random.Random(5)
    vs, fs, uvs, cols = [], [], [], []
    for i in range(900):
        an, rr = rng.uniform(0, 6.283), 14 * math.sqrt(rng.uniform(0.01, 1))
        if rr < max(size.x, size.y) * 0.22:
            continue
        x, y = centre.x + rr * math.cos(an), centre.y + rr * math.sin(an)
        hgt = rng.uniform(0.18, 0.4)
        ta = rng.uniform(0, 3.1416)
        tx, ty = math.cos(ta) * hgt * 0.9, math.sin(ta) * hgt * 0.9
        b0 = len(vs)
        vs += [(x - tx, y - ty, 0), (x + tx, y + ty, 0), (x + tx, y + ty, hgt * 2), (x - tx, y - ty, hgt * 2)]
        fs.append((b0, b0 + 1, b0 + 2, b0 + 3))
        uvs += [(0.512, 0.012), (0.988, 0.012), (0.988, 0.488), (0.512, 0.488)]
        k = rng.uniform(0.8, 1.1)
        dk, lt = (0.06 * k, 0.24 * k, 0.05 * k, 1), (0.45 * k, 0.72 * k, 0.16 * k, 1)
        cols += [dk, dk, lt, lt]
    me = bpy.data.meshes.new('meadow')
    me.from_pydata(vs, [], fs)
    me.uv_layers.new(name='UVMap').data.foreach_set('uv', [c for uv in uvs for c in uv])
    ca = me.color_attributes.new('Color', 'BYTE_COLOR', 'CORNER')
    ca.data.foreach_set('color', [c for col in cols for c in col])
    me.normals_split_custom_set_from_vertices([(0, 0, 1)] * len(vs))
    me.materials.append(fol)
    scene.collection.objects.link(bpy.data.objects.new('meadow', me))

world = bpy.data.worlds.new('w')
scene.world = world
try:
    world.use_nodes = True
except Exception:
    pass
bg = next(n for n in world.node_tree.nodes if n.type == 'BACKGROUND')
bg.inputs[0].default_value = (0.66, 0.76, 1.0, 1)
bg.inputs[1].default_value = 0.85
sun = bpy.data.lights.new('sun', 'SUN')
sun.energy = 3.8
sun.angle = math.radians(10)
sun.color = (1.0, 0.74, 0.46)
so = bpy.data.objects.new('sun', sun)
scene.collection.objects.link(so)
so.rotation_euler = (math.radians(70), 0, math.radians(42))

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
for attr, val in (('taa_render_samples', 96), ('use_raytracing', False), ('use_shadows', True)):
    try:
        setattr(scene.eevee, attr, val)
    except Exception:
        pass
try:
    scene.view_settings.view_transform = 'Standard'
except Exception:
    pass
scene.render.image_settings.file_format = 'PNG'


def shoot(path, pos, target, lens, res, fstop=None):
    cam.lens = lens
    co.location = pos
    d = Vector(target) - Vector(pos)
    co.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    cam.dof.use_dof = fstop is not None
    if fstop:
        cam.dof.focus_distance = d.length
        cam.dof.aperture_fstop = fstop
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


R = max(size.x, size.y)
long = R > H * 3          # walls and other low, long things get closer cameras
dist = max(H, R) * (1.25 if long else 2.3)
mid_t = centre + Vector((0, 0, H * 0.5))
shoot(os.path.join(out, name + '_mid.png'), mid_t + Vector((dist * 0.35, -dist, (dist * 0.42 if long else H * 0.32))), mid_t, 50, (1800, 1500 if not long else 1200), 2.0 if not long else 4.0)
ct = centre + Vector((0, 0, H * 0.58))
if long:
    shoot(os.path.join(out, name + '_close.png'), ct + Vector((-1.1, -2.3, 0.75)), ct + Vector((0.2, 0, -0.05)), 45, (1800, 1300), 4.0)
    shoot(os.path.join(out, name + '_detail.png'), ct + Vector((0.9, -1.25, 0.45)), ct + Vector((0.1, 0, -0.1)), 50, (1800, 1300), 5.6)
else:
    shoot(os.path.join(out, name + '_close.png'), ct + Vector((-dist * 0.2, -dist * 0.42, -H * 0.12)), ct, 45, (1800, 1500), 2.8)
base_t = centre + Vector((0, 0, H * 0.2))
shoot(os.path.join(out, name + '_base.png'), base_t + Vector((dist * 0.2, -dist * 0.36, H * 0.12)), base_t, 50, (1800, 1500), 5.6)
fk = centre + Vector((0, 0, H * 0.5))
shoot(os.path.join(out, name + '_trunk.png'), fk + Vector((-dist * 0.12, -dist * 0.3, -H * 0.2)), fk, 40, (1800, 1500), 5.6)

tiles = []
for i in range(6):
    root.rotation_euler.z = math.radians(60 * i)
    p = os.path.join(out, f'_tt{i}.png')
    shoot(p, mid_t + Vector((0, -dist * 1.05, (dist * 0.45 if long else H * 0.3))), mid_t, 50, (800, 800), 2.0 if not long else 5.6)
    im = bpy.data.images.load(p)
    arr = np.empty(800 * 800 * 4, np.float32)
    im.pixels.foreach_get(arr)
    tiles.append(arr.reshape(800, 800, 4))
    bpy.data.images.remove(im)
    os.remove(p)
sheet = np.concatenate([np.concatenate(tiles[3:], axis=1), np.concatenate(tiles[:3], axis=1)], axis=0)
im = bpy.data.images.new('sheet', 2400, 1600, alpha=True)
im.pixels.foreach_set(sheet.ravel())
im.filepath_raw = os.path.join(out, name + '_turntable.png')
im.file_format = 'PNG'
im.save()
print('HERO DONE')
