"""Render a line-up of GLB files:

blender -b --factory-startup --python preview.py -- out.png a.glb b.glb ... [--labels A,B] [--res 2000x800]
        [--turn 25] [--gap 0.3] [--cols N] [--elev 14]
"""
import math
import sys

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index('--') + 1:]
out = argv[0]
files, opts = [], {}
i = 1
while i < len(argv):
    if argv[i].startswith('--'):
        opts[argv[i][2:]] = argv[i + 1]
        i += 2
    else:
        files.append(argv[i])
        i += 1
labels = opts.get('labels', '').split(',') if opts.get('labels') else []
rx, ry = (int(v) for v in opts.get('res', '2000x800').split('x'))
turn = math.radians(float(opts.get('turn', 25)))
gap = float(opts.get('gap', 0.3))
cols = int(opts.get('cols', len(files)))
elev = math.radians(float(opts.get('elev', 14)))

for ob in list(bpy.data.objects):
    bpy.data.objects.remove(ob, do_unlink=True)
scene = bpy.context.scene


def bounds(objs):
    lo = Vector((1e9,) * 3)
    hi = Vector((-1e9,) * 3)
    for ob in objs:
        if ob.type != 'MESH':
            continue
        for corner in ob.bound_box:
            w = ob.matrix_world @ Vector(corner)
            for k in range(3):
                lo[k] = min(lo[k], w[k])
                hi[k] = max(hi[k], w[k])
    return lo, hi


groups = []
for f in files:
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=f)
    new = [o for o in bpy.data.objects if o not in before]
    roots = [o for o in new if o.parent is None]
    for r in roots:
        r.rotation_mode = 'XYZ'
        r.rotation_euler.z += turn
    bpy.context.view_layer.update()
    groups.append((roots, new))

# lay out in rows
x = 0.0
y = 0.0
row_depth = 0.0
glo = Vector((1e9,) * 3)
ghi = Vector((-1e9,) * 3)
for idx, (roots, new) in enumerate(groups):
    if idx and idx % cols == 0:
        x = 0.0
        y += row_depth + gap * 2
        row_depth = 0.0
    lo, hi = bounds(new)
    w = hi.x - lo.x
    for r in roots:
        r.location.x += x - lo.x
        r.location.y += y - lo.y
    bpy.context.view_layer.update()
    lo, hi = bounds(new)
    for k in range(3):
        glo[k] = min(glo[k], lo[k])
        ghi[k] = max(ghi[k], hi[k])
    if idx < len(labels):
        cu = bpy.data.curves.new('lbl', 'FONT')
        cu.body = labels[idx]
        cu.align_x = 'CENTER'
        cu.size = max(0.09, (hi.z - lo.z) * 0.11)
        t = bpy.data.objects.new('lbl', cu)
        scene.collection.objects.link(t)
        t.location = ((lo.x + hi.x) / 2, lo.y - cu.size * 1.2, 0.002)
        m = bpy.data.materials.new('lbl')
        try:
            m.use_nodes = True
        except Exception:
            pass
        lb = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
        lb.inputs['Base Color'].default_value = (0.02, 0.04, 0.02, 1)
        cu.materials.append(m)
    row_depth = max(row_depth, hi.y - lo.y)
    x += w + gap

centre = (glo + ghi) / 2
size = ghi - glo

# ground
bpy.ops.mesh.primitive_plane_add(size=400, location=(centre.x, centre.y, -0.001))
g = bpy.context.object
gm = bpy.data.materials.new('ground')
try:
    gm.use_nodes = True
except Exception:
    pass
b = next(n for n in gm.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
b.inputs['Base Color'].default_value = (0.33, 0.47, 0.20, 1)
b.inputs['Roughness'].default_value = 1.0
g.data.materials.append(gm)

# light
world = bpy.data.worlds.new('w')
scene.world = world
try:
    world.use_nodes = True
except Exception:
    pass
bg = next(n for n in world.node_tree.nodes if n.type == 'BACKGROUND')
bg.inputs[0].default_value = (0.80, 0.90, 1.0, 1)
bg.inputs[1].default_value = 0.55
sun = bpy.data.lights.new('sun', 'SUN')
sun.energy = 2.4
sun.angle = math.radians(12)
sun.color = (1.0, 0.95, 0.86)
so = bpy.data.objects.new('sun', sun)
scene.collection.objects.link(so)
so.rotation_euler = (math.radians(52), 0, math.radians(-38))

# camera
cam = bpy.data.cameras.new('cam')
cam.lens = 70
co = bpy.data.objects.new('cam', cam)
scene.collection.objects.link(co)
scene.camera = co
aspect = rx / ry
hfov = 2 * math.atan(18 / cam.lens)
vfov = 2 * math.atan(math.tan(hfov / 2) / aspect)
dist = max(size.x / 2 * 1.08 / math.tan(hfov / 2), (size.z / 2 * 1.45 + size.y * 0.2) / math.tan(vfov / 2))
target = Vector((centre.x, centre.y, glo.z + size.z * 0.47))
d = Vector((0, -math.cos(elev), math.sin(elev)))
co.location = target + d * dist
co.rotation_euler = (target - co.location).to_track_quat('-Z', 'Y').to_euler()
cam.clip_end = 2000

scene.render.resolution_x = rx
scene.render.resolution_y = ry
scene.render.filepath = out
scene.render.image_settings.file_format = 'PNG'
for eng in ('BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT'):
    try:
        scene.render.engine = eng
        break
    except Exception:
        pass
try:
    scene.eevee.taa_render_samples = 48
except Exception:
    pass
try:
    scene.view_settings.view_transform = 'Standard'
except Exception:
    pass
bpy.ops.render.render(write_still=True)
print('RENDERED', out, scene.render.engine)
