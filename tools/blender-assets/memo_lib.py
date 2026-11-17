"""Shared helpers for building Memo's island assets procedurally in Blender.

Everything is built in Blender space (Z up, front = -Y, 1 unit = 1 metre) and
exported to glTF space (Y up, front = +Z).
"""
import math
import os

import bpy
import bmesh
from mathutils import Vector, Matrix, Euler, noise

PI = math.pi

PALETTE = {
    'grass': '#7fb24f', 'moss': '#76a846', 'moss_dark': '#4f7f35', 'moss_light': '#a3cc6a',
    'wood': '#8a5a35', 'wood_dark': '#5e3b22', 'wood_light': '#b98652',
    'stone': '#9c9b93', 'stone_dark': '#74756f', 'stone_light': '#bdbbb0',
    'roof_red': '#b5533c', 'roof_red_dark': '#8f3f2e', 'roof_teal': '#3f7f7a', 'roof_teal_dark': '#2f615d',
    'cream': '#efe6cc', 'plaster': '#e9dcc0', 'soil': '#5a3d2b', 'sand': '#e0cf9a',
    'metal': '#8d949c', 'metal_dark': '#4d535a', 'brass': '#c9a24a',
    'leaf': '#5fae4a', 'leaf_dark': '#3f8a3c', 'pine': '#3f8f72', 'pine_dark': '#2f7360',
    'pink': '#f2a0a8', 'red': '#d0463b', 'yellow': '#f2c94c', 'white': '#f7f5ef',
    'black': '#15151a', 'orange': '#e08a3c', 'paper': '#f4ecd6', 'purple': '#9a7bd0',
    'blue': '#5b8fd6', 'tan': '#c79a6b', 'book_red': '#8f3d2f', 'book_blue': '#3d5f8f',
    'book_green': '#4c7a4a', 'plastic': '#d9d2c0', 'reed': '#7c5a2e',
}


def lin(h):
    h = h.lstrip('#')
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255.0
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return out


_mats = {}


def mat(name, rough=0.85, metal=0.0, emit=0.0, alpha=1.0, double=False, color=None, vcol=False):
    """Cached Principled material. `name` is a palette key unless `color` is given."""
    key = name
    if key in _mats:
        return _mats[key]
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    nt = m.node_tree
    b = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if b is None:
        b = nt.nodes.new('ShaderNodeBsdfPrincipled')
        out = next((n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL'), None) or nt.nodes.new('ShaderNodeOutputMaterial')
        nt.links.new(b.outputs[0], out.inputs[0])
    rgb = lin(color or PALETTE[name])
    b.inputs['Base Color'].default_value = (*rgb, 1.0)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    if emit:
        b.inputs['Emission Color'].default_value = (*rgb, 1.0)
        b.inputs['Emission Strength'].default_value = emit
    if alpha < 1.0:
        b.inputs['Alpha'].default_value = alpha
        for attr, val in (('blend_method', 'BLEND'), ('surface_render_method', 'BLENDED')):
            try:
                setattr(m, attr, val)
            except Exception:
                pass
    if vcol:
        n = nt.nodes.new('ShaderNodeVertexColor')
        n.layer_name = 'Color'
        nt.links.new(n.outputs['Color'], b.inputs['Base Color'])
    m.use_backface_culling = not double
    _mats[key] = m
    return m


# ---------------------------------------------------------------- primitives

def sphere(r=1.0, seg=20, rings=12):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=r)
    return bm


def ico(r=1.0, sub=2):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=r)
    return bm


def box(sx, sy, sz, bevel=0.0, seg=1):
    """Box centred on the origin, optionally chamfered."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= sx
        v.co.y *= sy
        v.co.z *= sz
    if bevel > 0:
        bevel = min(bevel, min(sx, sy, sz) * 0.45)
        bmesh.ops.bevel(bm, geom=bm.edges[:], offset=bevel, segments=seg, profile=0.5, affect='EDGES')
    return bm


def cyl(r1, r2, h, seg=16):
    """Cylinder / cone with its base on z=0."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg,
                          radius1=r1, radius2=max(r2, 1e-4), depth=h)
    for v in bm.verts:
        v.co.z += h / 2
    return bm


def lathe(profile, seg=20):
    """Revolve (r, z) points around Z. Points with r == 0 become poles."""
    bm = bmesh.new()
    rings = []
    for r, z in profile:
        if r <= 1e-6:
            rings.append([bm.verts.new((0, 0, z))])
        else:
            rings.append([bm.verts.new((r * math.cos(2 * PI * j / seg), r * math.sin(2 * PI * j / seg), z))
                          for j in range(seg)])
    for a, b in zip(rings, rings[1:]):
        for j in range(seg):
            k = (j + 1) % seg
            if len(a) == 1 and len(b) == 1:
                continue
            if len(a) == 1:
                bm.faces.new((a[0], b[k], b[j]))
            elif len(b) == 1:
                bm.faces.new((a[j], a[k], b[0]))
            else:
                bm.faces.new((a[j], a[k], b[k], b[j]))
    return bm


def dome(R, H, seg=24, rings=8):
    prof = [(R * math.cos(t), H * math.sin(t)) for t in [PI / 2 * i / rings for i in range(rings)]] + [(0, H)]
    return lathe(prof, seg)


def torus(R, r, seg=24, rseg=8):
    bm = bmesh.new()
    rings = []
    for i in range(seg):
        a = 2 * PI * i / seg
        ring = []
        for j in range(rseg):
            b = 2 * PI * j / rseg
            rr = R + r * math.cos(b)
            ring.append(bm.verts.new((rr * math.cos(a), rr * math.sin(a), r * math.sin(b))))
        rings.append(ring)
    for i in range(seg):
        a, b = rings[i], rings[(i + 1) % seg]
        for j in range(rseg):
            k = (j + 1) % rseg
            bm.faces.new((a[j], b[j], b[k], a[k]))
    return bm


def tube(pts, r, seg=8, cap=True):
    """Sweep a circle along a polyline. `r` may be a list of per-point radii."""
    pts = [Vector(p) for p in pts]
    n = len(pts)
    rs = list(r) if isinstance(r, (list, tuple)) else [r] * n
    bm = bmesh.new()
    rings = []
    prev = None
    for i, p in enumerate(pts):
        if i == 0:
            t = pts[1] - p
        elif i == n - 1:
            t = p - pts[i - 1]
        else:
            t = pts[i + 1] - pts[i - 1]
        t.normalize()
        if prev is None:
            a = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
            N = (a - t * a.dot(t)).normalized()
        else:
            N = (prev - t * prev.dot(t)).normalized()
        B = t.cross(N)
        prev = N
        rings.append([bm.verts.new(p + (N * math.cos(2 * PI * j / seg) + B * math.sin(2 * PI * j / seg)) * rs[i])
                      for j in range(seg)])
    for a, b in zip(rings, rings[1:]):
        for j in range(seg):
            k = (j + 1) % seg
            bm.faces.new((a[j], a[k], b[k], b[j]))
    if cap:
        bm.faces.new(rings[0])
        bm.faces.new(rings[-1])
    return bm


def arc(c, r, a0, a1, n, plane='xz'):
    """Points on an arc, angles in radians, in the given plane."""
    c = Vector(c)
    out = []
    for i in range(n + 1):
        a = a0 + (a1 - a0) * i / n
        u, v = r * math.cos(a), r * math.sin(a)
        if plane == 'xz':
            out.append(c + Vector((u, 0, v)))
        elif plane == 'yz':
            out.append(c + Vector((0, u, v)))
        else:
            out.append(c + Vector((u, v, 0)))
    return out


def leaf(L, W, bend=0.2, fold=0.15, nu=8, nv=4):
    """Leaf lying in XY, growing along +Y from the origin, normal +Z."""
    bm = bmesh.new()
    rows = []
    for i in range(nu + 1):
        t = i / nu
        w = W * 0.5 * (max(0.0, math.sin(PI * t)) ** 0.75) * (1 - 0.3 * t)
        row = []
        for j in range(nv + 1):
            s = j / nv * 2 - 1
            row.append(bm.verts.new((s * w, t * L, bend * L * t * t + fold * abs(s) * w)))
        rows.append(row)
    for a, b in zip(rows, rows[1:]):
        for j in range(nv):
            bm.faces.new((a[j], a[j + 1], b[j + 1], b[j]))
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-6)
    return bm


def disc(r, seg=24, wobble=0.0, seed=0.0, notch=0.0):
    """Flat disc on z=0 facing +Z. `notch` removes a wedge (lily pads)."""
    bm = bmesh.new()
    c = bm.verts.new((0, 0, 0))
    a0, a1 = notch / 2, 2 * PI - notch / 2
    n = seg
    ring = []
    for i in range(n + 1 if notch else n):
        a = a0 + (a1 - a0) * i / n if notch else 2 * PI * i / n
        rr = r * (1 + wobble * noise.noise(Vector((math.cos(a) * 1.3, math.sin(a) * 1.3, seed))))
        ring.append(bm.verts.new((rr * math.cos(a), rr * math.sin(a), 0)))
    cnt = len(ring)
    for i in range(cnt if not notch else cnt - 1):
        bm.faces.new((c, ring[i], ring[(i + 1) % cnt]))
    return bm


def prism(w, d, h):
    """Triangular gable prism: base w wide on z=0, apex at z=h, extruded d along Y (centred)."""
    bm = bmesh.new()
    f = [bm.verts.new((x, -d / 2, z)) for x, z in ((-w / 2, 0), (w / 2, 0), (0, h))]
    b = [bm.verts.new((x, d / 2, z)) for x, z in ((-w / 2, 0), (w / 2, 0), (0, h))]
    bm.faces.new(f)
    bm.faces.new(b[::-1])
    for i in range(3):
        k = (i + 1) % 3
        bm.faces.new((f[i], b[i], b[k], f[k]))
    return bm


def displace(bm, strength, freq=1.0, seed=0.0):
    bm.normal_update()
    off = Vector((seed * 13.1, seed * 7.7, seed * 3.3))
    for v in bm.verts:
        v.co += v.normal * noise.noise(v.co * freq + off) * strength
    return bm


def blob(r, sub=2, strength=0.2, freq=1.2, seed=0.0, squash=(1, 1, 1)):
    bm = ico(r, sub)
    displace(bm, r * strength, freq / max(r, 1e-4), seed)
    for v in bm.verts:
        v.co.x *= squash[0]
        v.co.y *= squash[1]
        v.co.z *= squash[2]
    return bm


def align_z(direction):
    """Rotation matrix taking +Z to `direction`."""
    return Vector((0, 0, 1)).rotation_difference(Vector(direction).normalized()).to_matrix().to_4x4()


def TRS(loc=(0, 0, 0), rot=(0, 0, 0), scale=1.0):
    s = (scale, scale, scale) if isinstance(scale, (int, float)) else scale
    return Matrix.Translation(Vector(loc)) @ Euler(rot).to_matrix().to_4x4() @ Matrix.Diagonal((*s, 1.0))


# ---------------------------------------------------------------- parts / assets

SHARP = math.radians(65)


class Part:
    """A named glTF node: many pieces merged into one mesh with a pivot."""

    def __init__(self, name, pivot=(0, 0, 0), parent=None):
        self.name = name
        self.parent = parent
        self.pivot = Vector(pivot)
        self.bm = bmesh.new()
        self.mats = []

    def add(self, bm, m, loc=(0, 0, 0), rot=(0, 0, 0), scale=1.0, smooth=True, recalc=True, mtx=None):
        if isinstance(m, str):
            m = mat(m)
        M = mtx if mtx is not None else TRS(loc, rot, scale)
        M = Matrix.Translation(-self.pivot) @ M
        bm.transform(M)
        if recalc:
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        elif M.determinant() < 0:
            bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
        if m not in self.mats:
            self.mats.append(m)
        idx = self.mats.index(m)
        for f in bm.faces:
            f.material_index = idx
            f.smooth = smooth
        tmp = bpy.data.meshes.new('tmp')
        bm.to_mesh(tmp)
        bm.free()
        self.bm.from_mesh(tmp)
        bpy.data.meshes.remove(tmp)
        return self

    def tris(self):
        return sum(len(f.verts) - 2 for f in self.bm.faces)

    def finalize(self, parent):
        bm = self.bm
        for e in bm.edges:
            if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > SHARP:
                e.smooth = False
        me = bpy.data.meshes.new(self.name)
        bm.to_mesh(me)
        bm.free()
        for m in self.mats:
            me.materials.append(m)
        ob = bpy.data.objects.new(self.name, me)
        bpy.context.scene.collection.objects.link(ob)
        if self.parent is not None:
            ob.location = self.pivot - self.parent.pivot
            ob.parent = self.parent.ob
        else:
            ob.location = self.pivot
            ob.parent = parent
        mod = ob.modifiers.new('wn', 'WEIGHTED_NORMAL')
        mod.keep_sharp = True
        self.ob = ob
        return ob

    def put(self, base=None):
        """Return an adder that places pieces in a local frame `base`."""
        base = base if base is not None else Matrix.Identity(4)

        def _put(bm, m, loc=(0, 0, 0), rot=(0, 0, 0), scale=1.0, mtx=None, **kw):
            return self.add(bm, m, mtx=base @ (mtx if mtx is not None else TRS(loc, rot, scale)), **kw)
        return _put


class Asset:
    def __init__(self, name, note=''):
        self.name = name
        self.note = note
        self.parts = []
        self.anchors = {}

    def part(self, name, pivot=(0, 0, 0), parent=None):
        p = Part(name, pivot, parent)
        self.parts.append(p)
        return p

    def anchor(self, name, loc):
        self.anchors[name] = tuple(loc)


def clear_scene():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for me in list(bpy.data.meshes):
        if me.users == 0:
            bpy.data.meshes.remove(me)


def export_asset(asset, out_dir, clear=True):
    """Finalize an asset, export <name>.glb, return a manifest entry."""
    if clear:
        clear_scene()
    root = bpy.data.objects.new(asset.name, None)
    bpy.context.scene.collection.objects.link(root)
    tris = sum(p.tris() for p in asset.parts)
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    for p in asset.parts:
        for v in p.bm.verts:
            w = v.co + p.pivot
            for i in range(3):
                lo[i] = min(lo[i], w[i])
                hi[i] = max(hi[i], w[i])
    nodes = {}
    obs = [root]
    for p in asset.parts:
        obs.append(p.finalize(root))
        # glTF space: x, y(up), z = x, z, -y
        nodes[p.name] = {'pivot': [round(p.pivot.x, 4), round(p.pivot.z, 4), round(-p.pivot.y, 4)],
                         'parent': p.parent.name if p.parent else None}
    for name, loc in asset.anchors.items():
        e = bpy.data.objects.new(name, None)
        bpy.context.scene.collection.objects.link(e)
        e.location = loc
        e.parent = root
        obs.append(e)
        nodes[name] = {'pivot': [round(loc[0], 4), round(loc[2], 4), round(-loc[1], 4)], 'parent': None, 'empty': True}
    bpy.context.view_layer.update()
    for ob in bpy.data.objects:
        ob.select_set(ob in obs)
    bpy.context.view_layer.objects.active = root
    path = os.path.join(out_dir, asset.name + '.glb')
    kw = dict(filepath=path, export_format='GLB', use_selection=True, export_apply=True,
              export_yup=True, export_normals=True, export_texcoords=False,
              export_materials='EXPORT', export_animations=False, export_cameras=False,
              export_lights=False, export_vertex_color='MATERIAL')
    props = bpy.ops.export_scene.gltf.get_rna_type().properties.keys()
    bpy.ops.export_scene.gltf(**{k: v for k, v in kw.items() if k in props})
    if not clear:
        for ob in obs:
            bpy.data.objects.remove(ob, do_unlink=True)
    return {
        'file': asset.name + '.glb',
        'bytes': os.path.getsize(path),
        'triangles': tris,
        'size': [round(hi.x - lo.x, 3), round(hi.z - lo.z, 3), round(hi.y - lo.y, 3)],
        'nodes': nodes,
        'note': asset.note,
    }
