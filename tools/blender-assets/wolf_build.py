"""Turn a COPY of Rob's wolf (wolf3.blend, built by ATLAS/wolf/build_wolf3.py) into game-ready Memo GLBs.

blender -b wolf_src/wolf3.blend --python wolf_build.py -- <out_dir>

Nothing is saved back to the .blend. For each growth stage the rig is posed for proportions, the heavy
sheet-matched meshes are decimated, the flat emission colours become lit materials, and the pieces are grouped
into the rigid nodes the game animates: Body, EyeL, EyeR, ArmL, ArmR, Notebook (child of ArmR), Tail,
FootL, FootR.
"""
import json
import os
import sys

import bpy
import bmesh
from mathutils import Vector, Matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import memo_lib as L  # noqa: E402

out = sys.argv[sys.argv.index('--') + 1]
os.makedirs(out, exist_ok=True)

# stage: total height (ear tips), head scale, leg length scale
STAGES = {
    'pup': (0.65, 1.07, 0.86),
    'young': (0.73, 1.04, 0.95),
    'growing_up': (0.82, 1.00, 1.05),
    'grown': (0.90, 0.96, 1.15),
}
# source object -> (node, decimate ratio)
PIECES = {
    'Body': ('Body', 0.022), 'Nose': ('Body', 0.25), 'EarInner.L': ('Body', 1.0), 'EarInner.R': ('Body', 1.0),
    'EyeWhite.L': ('EyeL', 0.3), 'Pupil.L': ('EyeL', 0.3), 'EyeWhite.R': ('EyeR', 0.3), 'Pupil.R': ('EyeR', 0.3),
    'Arm.L': ('ArmL', 0.07), 'Paw.L': ('ArmL', 0.05), 'Cuff.L': ('ArmL', 1.0),
    'Arm.R': ('ArmR', 0.07), 'Paw.R': ('ArmR', 0.05), 'Cuff.R': ('ArmR', 1.0),
    'Leg.L': ('FootL', 0.045), 'Leg.R': ('FootR', 0.05), 'Tail': ('Tail', 0.04),
}
PIVOT_BONE = {'ArmL': 'upper_arm.L', 'ArmR': 'upper_arm.R', 'FootL': 'thigh.L', 'FootR': 'thigh.R', 'Tail': 'tail.0'}

rig = bpy.data.objects['Rig']
scene = bpy.context.scene

# lit versions of the flat sheet colours (emission colour -> base colour)
lit = {}
for m in bpy.data.materials:
    em = next((n for n in m.node_tree.nodes if n.type == 'EMISSION'), None) if m.node_tree else None
    if em is None:
        continue
    col = em.inputs[0].default_value[:3]
    base = m.name.split(' (')[0].split('.')[0]
    if base in ('leg',):
        base = 'fur'
    if base not in lit:
        nm = bpy.data.materials.new('memo_' + base)
        try:
            nm.use_nodes = True
        except Exception:
            pass
        b = next(n for n in nm.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
        if base in ('fur', 'shade'):   # Rob asked for darker fur than the sheet colours
            col = tuple(c * 0.62 for c in col)
        b.inputs['Base Color'].default_value = (*col, 1.0)
        b.inputs['Roughness'].default_value = 0.25 if base == 'ink' else 0.9
        lit[base] = nm
    lit[m.name] = lit[base]


def grab(ob, ratio):
    """Evaluated (posed + decimated) world-space bmesh of a source object, with lit materials."""
    mod = None
    if ratio < 1.0:
        mod = ob.modifiers.new('dec', 'DECIMATE')
        mod.ratio = ratio
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    me.transform(ob.matrix_world)
    if mod:
        ob.modifiers.remove(mod)
    mats = [lit.get(m.name) if m else None for m in me.materials]
    bm = bmesh.new()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)
    return bm, mats


entries = []
for stage, (height, head_s, leg_s) in STAGES.items():
    for pb in rig.pose.bones:
        pb.scale = (1, 1, 1)
    rig.pose.bones['head'].scale = (head_s,) * 3
    for side in 'LR':
        rig.pose.bones['thigh.' + side].scale = (1, leg_s, 1)
        rig.pose.bones['foot.' + side].scale = (1, 1 / leg_s, 1)   # keep the paws their own size
    bpy.context.view_layer.update()

    raw = {}
    for src, (node, ratio) in PIECES.items():
        ob = bpy.data.objects.get(src)
        if ob is None:
            print('MISSING', src)
            continue
        raw.setdefault(node, []).append(grab(ob, ratio))
    lo = min(v.co.z for parts in raw.values() for bm, _ in parts for v in bm.verts)
    hi = max(v.co.z for parts in raw.values() for bm, _ in parts for v in bm.verts)
    s = height / (hi - lo)
    W = Matrix.Scale(s, 4) @ Matrix.Translation((0, 0, -lo))

    a = L.Asset('memo_' + stage, note=f"Memo the wolf, {stage} stage, {height:.2f} m to the ear tips. From Rob's wolf3 model.")
    parts = {}
    for node, items in raw.items():
        if node in PIVOT_BONE:
            pivot = W @ (rig.matrix_world @ rig.pose.bones[PIVOT_BONE[node]].head)
        elif node.startswith('Eye'):
            vs = [v.co for bm, _ in items for v in bm.verts]
            pivot = W @ (sum(vs, Vector()) / len(vs))
        else:
            pivot = Vector((0, 0, 0))
        # eyes, arms and tail ride the Body node so they follow its bob, lean and squash
        p = a.part(node, pivot, parent=None if node in ('Body', 'FootL', 'FootR') else parts['Body'])
        parts[node] = p
        for bm, mats in items:
            bm.transform(Matrix.Translation(-pivot) @ W)
            for f in bm.faces:
                m = mats[f.material_index] if f.material_index < len(mats) else None
                m = m or lit['fur']
                if m not in p.mats:
                    p.mats.append(m)
                f.material_index = p.mats.index(m)
                f.smooth = True
            tmp = bpy.data.meshes.new('tmp')
            bm.to_mesh(tmp)
            bm.free()
            p.bm.from_mesh(tmp)
            bpy.data.meshes.remove(tmp)

    # notebook in his right paw
    hand = W @ (rig.matrix_world @ rig.pose.bones['hand.R'].tail)
    u = height
    nb_c = hand + Vector((-0.012 * u, -0.055 * u, 0.045 * u))
    N = a.part('Notebook', nb_c, parent=parts['ArmR'])
    put = N.put(L.TRS(nb_c, (-0.18, 0.0, 0.25)))
    w, t, h = 0.15 * u, 0.032 * u, 0.2 * u
    put(L.box(w, t, h, 0.004 * u), L.mat('nb_cover', rough=0.7, color='#b5533c'))
    put(L.box(w * 0.9, t * 0.7, h * 0.92, 0.002 * u), L.mat('nb_pages', color='#f6efdc'), loc=(0.01 * u, 0, 0))
    put(L.box(0.012 * u, t * 0.2, h * 0.5), L.mat('nb_ribbon', color='#f2c94c'), loc=(0.02 * u, 0, -h * 0.42))
    put(L.leaf(0.06 * u, 0.034 * u, 0.0, 0.0, 5, 2), L.mat('nb_leaf', color='#f2d58a', double=True),
        loc=(0, -t * 0.56, -0.03 * u), rot=(L.PI / 2, 0, 0), recalc=False)

    L.SHARP = 3.2   # the wolf is a soft sculpt: no sharp edges
    e = L.export_asset(a, out, clear=False)
    entries.append({'name': a.name, **e})
    print(f"BUILT {a.name}: {e['triangles']} tris, {e['bytes'] / 1024:.0f} KB, size {e['size']}")

path = os.path.join(out, 'manifest.json')
old = []
if os.path.exists(path):
    old = [m for m in json.load(open(path))['models'] if m['name'] not in {e['name'] for e in entries}]
json.dump({'units': 'metres', 'up': '+Y', 'front': '+Z', 'origin': 'ground centre', 'models': entries + old},
          open(path, 'w'), indent=1)
