"""Build the sheet-based Ash and render orthographic front/side views plus a three-quarter beauty view.

blender -b --factory-startup --python ash_shots.py -- out_dir [stage]
Then ash_compare.py lays the orthographic views over the character sheet.
"""
import math
import os
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import memo_lib as L  # noqa: E402
import memo_ash as MA  # noqa: E402

argv = sys.argv[sys.argv.index('--') + 1:]
out = argv[0]
stage = argv[1] if len(argv) > 1 else 'pup'
os.makedirs(out, exist_ok=True)
L.AO_STRENGTH = 0.3
e = L.export_asset(MA.build_ash('memo_' + stage, stage), out)
print('BUILT', e['triangles'], e['bytes'] // 1024, 'KB', e['size'], list(e['nodes']))

for ob in list(bpy.data.objects):
    bpy.data.objects.remove(ob, do_unlink=True)
bpy.ops.import_scene.gltf(filepath=os.path.join(out, f'memo_{stage}.glb'))
root = next(o for o in bpy.data.objects if o.parent is None)
root.rotation_mode = 'XYZ'
H = MA.STAGES[stage]
scene = bpy.context.scene
world = bpy.data.worlds.new('w')
scene.world = world
try:
    world.use_nodes = True
except Exception:
    pass
bg = next(n for n in world.node_tree.nodes if n.type == 'BACKGROUND')
bg.inputs[0].default_value = (1, 1, 1, 1)
bg.inputs[1].default_value = 1.1
sun = bpy.data.lights.new('sun', 'SUN')
sun.energy = 1.6
sun.angle = math.radians(25)
so = bpy.data.objects.new('sun', sun)
scene.collection.objects.link(so)
so.rotation_euler = (math.radians(55), 0, math.radians(25))
cam = bpy.data.cameras.new('cam')
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
    scene.eevee.taa_render_samples = 64
    scene.view_settings.view_transform = 'Standard'
except Exception:
    pass
scene.render.film_transparent = True
scene.render.image_settings.color_mode = 'RGBA'
scene.render.resolution_x = scene.render.resolution_y = 1000
target = Vector((0, 0, H * 0.5))
cam.type = 'ORTHO'
cam.ortho_scale = H * 1.15
for nm, pos in (('front', (0, -10, 0)), ('side', (10, 0, 0)), ('back', (0, 10, 0))):
    co.location = target + Vector(pos)
    co.rotation_euler = (target - co.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = os.path.join(out, f'ortho_{nm}.png')
    bpy.ops.render.render(write_still=True)
cam.type = 'PERSP'
cam.lens = 85
root.rotation_euler.z = math.radians(32)
co.location = target + Vector((0, -H * 4.2, H * 0.25))
co.rotation_euler = (target - co.location).to_track_quat('-Z', 'Y').to_euler()
scene.render.filepath = os.path.join(out, 'three_quarter.png')
bpy.ops.render.render(write_still=True)
print('SHOTS DONE')
