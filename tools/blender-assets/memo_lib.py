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


# ---------------------------------------------------------------- sculpted primitives

def hull(points, bevel=0.0, seg=1):
    """Convex hull of points with chamfered edges: chiselled stone forms rather than balls."""
    bm = bmesh.new()
    for p in points:
        bm.verts.new(p)
    bmesh.ops.convex_hull(bm, input=bm.verts[:])
    loose = [v for v in bm.verts if not v.link_faces]
    if loose:
        bmesh.ops.delete(bm, geom=loose, context='VERTS')
    if bevel > 0:
        bmesh.ops.bevel(bm, geom=bm.edges[:], offset=bevel, segments=seg, profile=0.5, affect='EDGES', clamp_overlap=True)
    return bm


def block(rng, w, d, h, jitter=0.16, bevel=0.2, seg=1, extra=2):
    """Irregular hand-cut stone block centred on the origin."""
    pts = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                pts.append((sx * w / 2 * (1 - rng.uniform(0, jitter)), sy * d / 2 * (1 - rng.uniform(0, jitter)),
                            sz * h / 2 * (1 - rng.uniform(0, jitter))))
    for _ in range(extra):
        ax = rng.randrange(3)
        p = [rng.uniform(-0.35, 0.35) * s for s in (w, d, h)]
        p[ax] = rng.choice((-1, 1)) * (w, d, h)[ax] / 2 * rng.uniform(1.0, 1.08)
        pts.append(tuple(p))
    return hull(pts, bevel * min(w, d, h), seg)


def boulder(rng, w, d, h, n=14, bevel=0.07, seg=2, flat_base=True):
    """Faceted boulder: hull of scattered points, base flattened, edges softened."""
    pts = []
    for _ in range(n):
        v = Vector((rng.gauss(0, 1), rng.gauss(0, 1), rng.gauss(0, 1))).normalized()
        r = rng.uniform(0.75, 1.0)
        z = v.z * h / 2 * r
        if flat_base and z < -h * 0.28:
            z = -h * 0.28
        pts.append((v.x * w / 2 * r, v.y * d / 2 * r, z + h * 0.28))
    return hull(pts, bevel * min(w, d, h), seg)


def tile_shape(w, ln, th=0.06, arc=6):
    """Beaver-tail roof tile: square head at +Y, rounded tail at -Y, lying in XY."""
    out = [(-w / 2, ln / 2), (w / 2, ln / 2)]
    ry = w * 0.34
    for i in range(arc + 1):
        a = PI * i / arc
        out.append((w / 2 * math.cos(a), -(ln / 2 - ry) - ry * math.sin(a)))
    bm = bmesh.new()
    top = [bm.verts.new((x, y, th / 2)) for x, y in out]
    bot = [bm.verts.new((x * 0.96, y * 0.98, -th / 2)) for x, y in out]
    bm.faces.new(top)
    bm.faces.new(bot[::-1])
    n = len(out)
    for i in range(n):
        k = (i + 1) % n
        bm.faces.new((top[k], top[i], bot[i], bot[k]))
    return bm


# ---------------------------------------------------------------- foliage texture

def _paint(img, x0, y0, ang, L, W, bright, kind='leaf', tint=(0.93, 1.0, 0.86)):
    """Alpha-composite one leaf / blade / twig into an RGBA float cell image (row 0 = bottom)."""
    import numpy as np
    n = img.shape[0]
    ys, xs = np.mgrid[0:n, 0:n]
    dx = (xs + 0.5) / n - x0
    dy = (ys + 0.5) / n - y0
    u = (dx * math.cos(ang) + dy * math.sin(ang)) / L
    v = -dx * math.sin(ang) + dy * math.cos(ang)
    uc = np.clip(u, 0, 1)
    if kind == 'leaf':
        half = W / 2 * np.sin(PI * uc) ** 0.6 * (1 - 0.25 * uc)
    else:  # blade / twig: wide at the base, tapering
        half = W / 2 * (1 - uc) ** 0.8 * (0.35 + 0.65 * np.minimum(1, uc * 8))
    a = np.clip((half - np.abs(v)) * n + 0.5, 0, 1) * ((u > 0) & (u < 1))
    edge = np.clip(np.abs(v) / np.maximum(half, 1e-6), 0, 1)
    sh = bright * (0.8 + 0.2 * uc) * (1 - 0.22 * edge ** 3)
    sh = sh + 0.07 * np.exp(-(v / (W * 0.07)) ** 2) * (kind == 'leaf')
    for c in range(3):
        img[..., c] = img[..., c] * (1 - a) + np.clip(sh * tint[c], 0, 1) * a
    img[..., 3] = np.maximum(img[..., 3], a)


def foliage_atlas(path, size=1024):
    """2x2 atlas: [leaf cluster A, leaf cluster B / needle bough, grass tuft]. Near-white so vertex colour sets the hue."""
    import numpy as np
    import random as _r
    c = size // 2
    cells = []
    for seed in (1, 2):
        rng = _r.Random(seed)
        img = np.zeros((c, c, 4), np.float32)
        img[..., :3] = (0.8, 0.9, 0.75)
        for ring, (rad, cnt) in enumerate(((0.4, 24), (0.3, 18), (0.2, 12), (0.1, 7))):
            for i in range(cnt):
                a = 2 * PI * (i + rng.uniform(-0.3, 0.3)) / cnt + ring
                r = rad * rng.uniform(0.8, 1.1)
                L = rng.uniform(0.13, 0.19)
                _paint(img, 0.5 + (r - L * 0.5) * math.cos(a), 0.5 + (r - L * 0.5) * math.sin(a), a + rng.uniform(-0.5, 0.5),
                       L, L * rng.uniform(0.5, 0.62), rng.uniform(0.8, 1.0) * (0.84 + 0.05 * ring))
        cells.append(img)
    rng = _r.Random(3)
    img = np.zeros((c, c, 4), np.float32)
    img[..., :3] = (0.8, 0.9, 0.75)
    _paint(img, 0.5, 0.02, PI / 2, 0.95, 0.05, 0.6, 'blade')
    for i in range(15):
        t = 0.06 + 0.86 * i / 15
        ln = 0.42 * (1 - t) ** 0.75 + 0.05
        for s in (1, -1):
            _paint(img, 0.5, t, PI / 2 - s * (1.05 - 0.25 * t) + rng.uniform(-0.08, 0.08), ln * rng.uniform(0.9, 1.05), 0.075,
                   rng.uniform(0.7, 1.0) * (0.75 + 0.25 * t), 'blade')
    cells.append(img)
    rng = _r.Random(4)
    img = np.zeros((c, c, 4), np.float32)
    img[..., :3] = (0.8, 0.9, 0.75)
    for i in range(15):
        _paint(img, 0.5 + rng.uniform(-0.12, 0.12), 0.0, PI / 2 + rng.uniform(-0.6, 0.6), rng.uniform(0.55, 0.97), rng.uniform(0.05, 0.075),
               rng.uniform(0.7, 1.0), 'blade')
    cells.append(img)
    atlas = np.zeros((size, size, 4), np.float32)
    atlas[c:, :c] = cells[0]      # top-left     (cell 0)
    atlas[c:, c:] = cells[1]      # top-right    (cell 1)
    atlas[:c, :c] = cells[2]      # bottom-left  (cell 2: bough)
    atlas[:c, c:] = cells[3]      # bottom-right (cell 3: grass)
    atlas[c:c + 6, 0:6] = (0.9, 1.0, 0.85, 1.0)   # opaque patch for solid foliage cores
    im = bpy.data.images.new('foliage', size, size, alpha=True)
    im.pixels.foreach_set(atlas.ravel())
    im.filepath_raw = path
    im.file_format = 'PNG'
    im.save()
    return im


CELL_UV = {0: (0.0, 0.5), 1: (0.5, 0.5), 2: (0.0, 0.0), 3: (0.5, 0.0)}
SOLID_UV = (0.005, 0.505)
_foliage = {}


def foliage_mat(out_dir):
    if 'm' in _foliage:
        return _foliage['m']
    tex_dir = os.path.join(out_dir, '_tex')
    os.makedirs(tex_dir, exist_ok=True)
    _foliage['dir'] = tex_dir
    im = foliage_atlas(os.path.join(tex_dir, 'foliage.png'))
    m = bpy.data.materials.new('foliage')
    try:
        m.use_nodes = True
    except Exception:
        pass
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    tex = nt.nodes.new('ShaderNodeTexImage')
    tex.image = im
    vc = nt.nodes.new('ShaderNodeVertexColor')
    vc.layer_name = 'Color'
    mix = nt.nodes.new('ShaderNodeMix')
    mix.data_type = 'RGBA'
    mix.blend_type = 'MULTIPLY'
    mix.inputs[0].default_value = 1.0
    nt.links.new(tex.outputs['Color'], mix.inputs[6])
    nt.links.new(vc.outputs['Color'], mix.inputs[7])
    nt.links.new(mix.outputs[2], b.inputs['Base Color'])
    rnd = nt.nodes.new('ShaderNodeMath')
    rnd.operation = 'ROUND'
    nt.links.new(tex.outputs['Alpha'], rnd.inputs[0])
    nt.links.new(rnd.outputs[0], b.inputs['Alpha'])
    b.inputs['Roughness'].default_value = 0.85
    for attr, val in (('blend_method', 'CLIP'), ('surface_render_method', 'DITHERED')):
        try:
            setattr(m, attr, val)
        except Exception:
            pass
    m.use_backface_culling = False
    _foliage['m'] = m
    return m


# ---------------------------------------------------------------- bark texture

def _pnoise(n, cx, cy, seed):
    """Tileable value noise, n x n, with cx by cy cells."""
    import numpy as np
    g = np.random.RandomState(seed).rand(cy, cx).astype(np.float32)
    ys, xs = np.mgrid[0:n, 0:n].astype(np.float32)
    fx, fy = xs / n * cx, ys / n * cy
    x0, y0 = np.floor(fx).astype(int) % cx, np.floor(fy).astype(int) % cy
    x1, y1 = (x0 + 1) % cx, (y0 + 1) % cy
    tx, ty = fx - np.floor(fx), fy - np.floor(fy)
    tx, ty = tx * tx * (3 - 2 * tx), ty * ty * (3 - 2 * ty)
    return (g[y0, x0] * (1 - tx) + g[y0, x1] * tx) * (1 - ty) + (g[y1, x0] * (1 - tx) + g[y1, x1] * tx) * ty


def _fbm(n, cx, cy, seed, octaves=4):
    import numpy as np
    out = np.zeros((n, n), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        out += amp * _pnoise(n, cx * 2 ** o, cy * 2 ** o, seed + o * 17)
        tot += amp
        amp *= 0.5
    return out / tot


def bark_textures(tex_dir, n=512):
    """Tileable bark: plates between vertical furrows, broken by cracks. Returns (albedo, normal) images.

    The albedo is a light warm grey so vertex colour can tint it to any species (and to moss)."""
    import numpy as np
    ys, xs = np.mgrid[0:n, 0:n].astype(np.float32)
    u, v = xs / n, ys / n
    warp = _fbm(n, 2, 3, 1, 3)
    sstripe = u * 7 + 1.5 * (warp - 0.5) + 0.25 * np.sin(2 * PI * v * 2 + 6 * warp)
    plate = np.abs(np.sin(PI * sstripe)) ** 0.55                 # 0 in the furrows, 1 on the plates
    crack = _fbm(n, 5, 14, 7, 3)
    crack = np.clip((crack - 0.56) * 9, 0, 1)                     # short horizontal breaks
    fine = _fbm(n, 24, 6, 11, 3)                                  # fibrous vertical grain
    h = np.clip(plate * (1 - 0.75 * crack) * (0.82 + 0.3 * fine) + 0.1 * (_fbm(n, 6, 6, 21) - 0.5), 0, 1)
    lo, mid, hi = np.array((0.26, 0.22, 0.2)), np.array((0.62, 0.57, 0.52)), np.array((0.93, 0.9, 0.85))
    t = h[..., None]
    alb = np.where(t < 0.5, lo + (mid - lo) * (t / 0.5), mid + (hi - mid) * ((t - 0.5) / 0.5))
    alb = alb * (0.9 + 0.2 * _fbm(n, 3, 3, 31)[..., None])
    alb[..., 1] *= 1 + 0.06 * (_fbm(n, 4, 4, 41) - 0.5)
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5
    k = 5.0
    nrm = np.dstack((-dx * k, -dy * k, np.full_like(h, 1.0 / n * 8)))
    nrm /= np.linalg.norm(nrm, axis=2, keepdims=True)
    out = []
    for name, arr, cs in (('bark', np.clip(alb, 0, 1), 'sRGB'), ('bark_n', nrm * 0.5 + 0.5, 'Non-Color')):
        px = np.dstack((arr.astype(np.float32), np.ones((n, n), np.float32)))
        if cs == 'sRGB':   # pixels are stored scene-linear; write the albedo so it reads as authored sRGB
            px[..., :3] = np.where(px[..., :3] <= 0.04045, px[..., :3] / 12.92, ((px[..., :3] + 0.055) / 1.055) ** 2.4)
        im = bpy.data.images.new(name, n, n, alpha=False)
        im.colorspace_settings.name = cs
        im.pixels.foreach_set(px.ravel())
        im.filepath_raw = os.path.join(tex_dir, name + '.jpg')
        im.file_format = 'JPEG'
        im.save()
        out.append(im)
    return out


def bark_mat():
    if 'bark' in _foliage:
        return _foliage['bark']
    alb, nrm = bark_textures(_foliage['dir'])
    m = bpy.data.materials.new('bark')
    try:
        m.use_nodes = True
    except Exception:
        pass
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    tex = nt.nodes.new('ShaderNodeTexImage')
    tex.image = alb
    vc = nt.nodes.new('ShaderNodeVertexColor')
    vc.layer_name = 'Color'
    mix = nt.nodes.new('ShaderNodeMix')
    mix.data_type = 'RGBA'
    mix.blend_type = 'MULTIPLY'
    mix.inputs[0].default_value = 1.0
    nt.links.new(tex.outputs['Color'], mix.inputs[6])
    nt.links.new(vc.outputs['Color'], mix.inputs[7])
    nt.links.new(mix.outputs[2], b.inputs['Base Color'])
    ntex = nt.nodes.new('ShaderNodeTexImage')
    ntex.image = nrm
    nm = nt.nodes.new('ShaderNodeNormalMap')
    nm.inputs['Strength'].default_value = 0.9
    nt.links.new(ntex.outputs['Color'], nm.inputs['Color'])
    nt.links.new(nm.outputs['Normal'], b.inputs['Normal'])
    b.inputs['Roughness'].default_value = 1.0
    try:
        b.inputs['Specular IOR Level'].default_value = 0.15
    except Exception:
        pass
    _foliage['bark'] = m
    return m


# ---------------------------------------------------------------- stone texture

def _save_tex(name, arr, srgb, tex_dir, n):
    import numpy as np
    px = np.dstack((arr.astype(np.float32), np.ones((n, n), np.float32)))
    if srgb:
        px[..., :3] = np.where(px[..., :3] <= 0.04045, px[..., :3] / 12.92, ((px[..., :3] + 0.055) / 1.055) ** 2.4)
    im = bpy.data.images.new(name, n, n, alpha=False)
    im.colorspace_settings.name = 'sRGB' if srgb else 'Non-Color'
    im.pixels.foreach_set(px.ravel())
    im.filepath_raw = os.path.join(tex_dir, name + '.jpg')
    im.file_format = 'JPEG'
    im.save()
    return im


def _tex_mat(name, alb, nrm, strength, rough=1.0):
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    tex = nt.nodes.new('ShaderNodeTexImage')
    tex.image = alb
    vc = nt.nodes.new('ShaderNodeVertexColor')
    vc.layer_name = 'Color'
    mix = nt.nodes.new('ShaderNodeMix')
    mix.data_type = 'RGBA'
    mix.blend_type = 'MULTIPLY'
    mix.inputs[0].default_value = 1.0
    nt.links.new(tex.outputs['Color'], mix.inputs[6])
    nt.links.new(vc.outputs['Color'], mix.inputs[7])
    nt.links.new(mix.outputs[2], b.inputs['Base Color'])
    ntex = nt.nodes.new('ShaderNodeTexImage')
    ntex.image = nrm
    nm = nt.nodes.new('ShaderNodeNormalMap')
    nm.inputs['Strength'].default_value = strength
    nt.links.new(ntex.outputs['Color'], nm.inputs['Color'])
    nt.links.new(nm.outputs['Normal'], b.inputs['Normal'])
    b.inputs['Roughness'].default_value = rough
    try:
        b.inputs['Specular IOR Level'].default_value = 0.2
    except Exception:
        pass
    return m


def stone_mat():
    """Tileable hand-cut stone: soft mottling, grain speckle, pits and hairline cracks. Light, so vertex colour tints it."""
    if 'stone' in _foliage:
        return _foliage['stone']
    import numpy as np
    n = 512
    m1, m2 = _fbm(n, 3, 3, 51, 4), _fbm(n, 10, 10, 61, 3)
    grain = _pnoise(n, 128, 128, 71)
    pit = np.clip((_pnoise(n, 40, 40, 73) - 0.9) * 12, 0, 1)
    cr = _fbm(n, 4, 4, 81, 4)
    crack = np.clip(1 - np.abs(cr - 0.5) * 70, 0, 1) * np.clip((_fbm(n, 2, 2, 91, 2) - 0.45) * 6, 0, 1)
    height = 0.55 * m1 + 0.3 * m2 + 0.025 * grain - 0.3 * pit - 0.45 * crack
    v = 0.88 + 0.26 * (m1 - 0.5) + 0.12 * (m2 - 0.5) + 0.035 * (grain - 0.5) - 0.16 * pit - 0.28 * crack
    warm = 0.03 * (_fbm(n, 2, 2, 95, 2) - 0.5)
    alb = np.clip(np.dstack((v * (1.0 + warm), v * 0.985, v * (0.95 - warm))), 0, 1)
    dx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) * 0.5
    dy = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) * 0.5
    nrm = np.dstack((-dx * 6, -dy * 6, np.full_like(height, 8.0 / n)))
    nrm /= np.linalg.norm(nrm, axis=2, keepdims=True)
    d = _foliage['dir']
    _foliage['stone'] = _tex_mat('stone', _save_tex('stone', alb, True, d, n), _save_tex('stone_n', nrm * 0.5 + 0.5, False, d, n), 0.6)
    return _foliage['stone']


# ---------------------------------------------------------------- parts / assets

SHARP = math.radians(65)
AO_STRENGTH = 0.75
AO_DIST = 1.1
_AO_DIRS = [Vector(d).normalized() for d in (
    (0, 0, 1), (0.8, 0, 0.6), (-0.8, 0, 0.6), (0, 0.8, 0.6), (0, -0.8, 0.6), (0.6, 0.6, 0.5), (-0.6, 0.6, 0.5),
    (0.6, -0.6, 0.5), (-0.6, -0.6, 0.5), (1, 0, 0.1), (-1, 0, 0.1), (0, 1, 0.1), (0, -1, 0.1))]


def _tint3(t):
    if t is None:
        return (1.0, 1.0, 1.0)
    if isinstance(t, (int, float)):
        return (t, t, t)
    return tuple(t)


def _ao(bvh, pos, n, dist=None):
    """Baked ambient occlusion x a soft darkening toward the ground, for one surface point."""
    dist = dist or AO_DIST
    o = pos + n * 0.03
    occ = 0.0
    cnt = 0
    for d in _AO_DIRS:
        dd = d if d.dot(n) > 0.1 else (-d if (-d).dot(n) > 0.1 else None)
        if dd is None:
            continue
        cnt += 1
        hit = bvh.ray_cast(o, dd, dist)
        if hit[0] is not None:
            occ += 1 - hit[3] / dist
    a = 1 - AO_STRENGTH * occ / max(cnt, 1)
    z = max(0.0, min(1.0, pos.z / 0.5))
    return max(0.45, a) * (0.84 + 0.16 * z * z * (3 - 2 * z))


class Part:
    """A named glTF node: many pieces merged into one mesh with a pivot. Vertex colour carries tint x baked AO."""

    def __init__(self, name, pivot=(0, 0, 0), parent=None):
        self.name = name
        self.parent = parent
        self.pivot = Vector(pivot)
        self.bm = bmesh.new()
        self.mats = []
        self.tints = []

    def add(self, bm, m, loc=(0, 0, 0), rot=(0, 0, 0), scale=1.0, smooth=True, recalc=True, mtx=None, tint=None):
        if isinstance(m, str):
            m = mat(m)
        M = mtx if mtx is not None else TRS(loc, rot, scale)
        M = Matrix.Translation(-self.pivot) @ M
        bm.transform(M)
        if recalc:
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
            # recalc only makes the winding consistent; make sure a closed piece really faces outward
            vol = 0.0
            for f in bm.faces:
                vs = [v.co for v in f.verts]
                for i in range(1, len(vs) - 1):
                    vol += vs[0].dot(vs[i].cross(vs[i + 1]))
            if vol < 0 and all(len(e.link_faces) == 2 for e in bm.edges):
                bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
        elif M.determinant() < 0:
            bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
        if m not in self.mats:
            self.mats.append(m)
        idx = self.mats.index(m)
        for f in bm.faces:
            f.material_index = idx
            f.smooth = smooth
        self.tints.extend([_tint3(tint)] * len(bm.faces))
        tmp = bpy.data.meshes.new('tmp')
        bm.to_mesh(tmp)
        bm.free()
        self.bm.from_mesh(tmp)
        bpy.data.meshes.remove(tmp)
        return self

    def tris(self):
        return sum(len(f.verts) - 2 for f in self.bm.faces)

    def points(self):
        return [v.co + self.pivot for v in self.bm.verts]

    def polys(self):
        self.bm.verts.index_update()
        return [[v.index for v in f.verts] for f in self.bm.faces]

    def finalize(self, parent, bvh=None):
        bm = self.bm
        for e in bm.edges:
            if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > SHARP:
                e.smooth = False
        bm.normal_update()
        ao = {}
        if bvh is not None:
            for v in bm.verts:
                ao[v.index] = _ao(bvh, v.co + self.pivot, v.normal)
        cols = []
        tints = self.tints + [(1.0, 1.0, 1.0)] * (len(bm.faces) - len(self.tints))
        for f, t in zip(bm.faces, tints):
            for lp in f.loops:
                k = ao.get(lp.vert.index, 1.0)
                cols.extend((t[0] * k, t[1] * k, t[2] * k, 1.0))
        me = bpy.data.meshes.new(self.name)
        bm.to_mesh(me)
        bm.free()
        ca = me.color_attributes.new('Color', 'BYTE_COLOR', 'CORNER')
        ca.data.foreach_set('color', cols)
        me.color_attributes.active_color = ca
        for m in self.mats:
            me.materials.append(m)
        ob = bpy.data.objects.new(self.name, me)
        bpy.context.scene.collection.objects.link(ob)
        _attach(self, ob, parent)
        mod = ob.modifiers.new('wn', 'WEIGHTED_NORMAL')
        mod.keep_sharp = True
        return ob

    def put(self, base=None):
        """Return an adder that places pieces in a local frame `base`."""
        base = base if base is not None else Matrix.Identity(4)

        def _put(bm, m, loc=(0, 0, 0), rot=(0, 0, 0), scale=1.0, mtx=None, **kw):
            return self.add(bm, m, mtx=base @ (mtx if mtx is not None else TRS(loc, rot, scale)), **kw)
        _put.base = base
        return _put


def _attach(part, ob, parent):
    if part.parent is not None:
        ob.location = part.pivot - part.parent.pivot
        ob.parent = part.parent.ob
    else:
        ob.location = part.pivot
        ob.parent = parent
    if getattr(part, 'hidden', False):   # optional node (season / snow): the game scales it back to 1
        ob.scale = (0.001, 0.001, 0.001)
    part.ob = ob


class RawPart:
    """Foliage node built vertex by vertex: textured cards with hand-set normals and vertex colours."""

    def __init__(self, name, pivot=(0, 0, 0), parent=None):
        self.name = name
        self.parent = parent
        self.pivot = Vector(pivot)
        self.v, self.n, self.c, self.f, self.uv = [], [], [], [], []
        self.material = None   # defaults to the shared foliage material
        self.occlude = False   # True: solid geometry that takes part in the AO bake

    def face(self, pts, uvs, cols, normals):
        base = len(self.v)
        for p, col, nr in zip(pts, cols, normals):
            self.v.append(Vector(p) - self.pivot)
            self.c.append(tuple(col))
            self.n.append(Vector(nr).normalized())
        self.f.append(tuple(range(base, base + len(pts))))
        self.uv.extend(uvs)

    def card(self, centre, right, up, cell, cols, normals, flip=False):
        """Quad from the atlas cell; `cols` and `normals` are per corner (bl, br, tr, tl)."""
        c = Vector(centre)
        pts = [c - right - up, c + right - up, c + right + up, c - right + up]
        u0, v0 = CELL_UV[cell]
        a, b = 0.012, 0.488
        uvs = [(u0 + a, v0 + a), (u0 + b, v0 + a), (u0 + b, v0 + b), (u0 + a, v0 + b)]
        if flip:
            uvs = [uvs[1], uvs[0], uvs[3], uvs[2]]
        self.face(pts, uvs, cols, normals)

    def tent(self, centre, right, up, cell, cols, normals, bend=0.35, flip=False):
        """Card folded along its centre line into a shallow ridge, so it never reads as a flat sheet edge-on."""
        c = Vector(centre)
        fwd = right.cross(up)
        fwd = fwd.normalized() * right.length * bend if fwd.length > 1e-9 else Vector()
        bl, br, tr, tl = c - right - up, c + right - up, c + right + up, c - right + up
        bm_, tm = c - up + fwd, c + up + fwd
        u0, v0 = CELL_UV[cell]
        a, b, m = 0.012, 0.488, 0.25
        ul, ur = (u0 + b, u0 + a) if flip else (u0 + a, u0 + b)
        nb, nt = (normals[0] + normals[1]) * 0.5 + fwd.normalized() * 0.3, (normals[3] + normals[2]) * 0.5 + fwd.normalized() * 0.3
        cb, ct = (Vector(cols[0]) + Vector(cols[1])) * 0.52, (Vector(cols[3]) + Vector(cols[2])) * 0.52
        self.face([bl, bm_, tm, tl], [(ul, v0 + a), (u0 + m, v0 + a), (u0 + m, v0 + b), (ul, v0 + b)], [cols[0], cb, ct, cols[3]],
                  [normals[0], nb, nt, normals[3]])
        self.face([bm_, br, tr, tm], [(u0 + m, v0 + a), (ur, v0 + a), (ur, v0 + b), (u0 + m, v0 + b)], [cb, cols[1], cols[2], ct],
                  [nb, normals[1], normals[2], nt])

    def solid(self, bm, centre, col, shade_from=None):
        """Opaque dark core mesh (keeps canopies from being see-through)."""
        bm.normal_update()
        for fc in bm.faces:
            pts = [v.co.copy() for v in fc.verts]
            self.face(pts, [SOLID_UV] * len(pts), [col] * len(pts), [(p - Vector(centre)) for p in pts])
        bm.free()

    def tris(self):
        return sum(len(f) - 2 for f in self.f)

    def points(self):
        return [p + self.pivot for p in self.v]

    def polys(self):
        return list(self.f) if self.occlude else []

    def mesh(self, bm, mtx, col_fn, uv_scale=1.0, uv_off=(0.0, 0.0)):
        """Add a solid bmesh (smooth normals, box-projected UVs from its own local shape)."""
        bm.normal_update()
        rot = mtx.to_3x3()
        for fc in bm.faces:
            n = fc.normal
            ax = max(range(3), key=lambda i: abs(n[i]))
            u_ax, v_ax = [(1, 2), (0, 2), (0, 1)][ax]
            pts, uvs, cols, nrms = [], [], [], []
            for v in fc.verts:
                w = mtx @ v.co
                nn = (rot @ v.normal).normalized()
                pts.append(w)
                nrms.append(nn)
                uvs.append((v.co[u_ax] * uv_scale + uv_off[0], v.co[v_ax] * uv_scale + uv_off[1]))
                cols.append(col_fn(w, nn))
            self.face(pts, uvs, cols, nrms)
        bm.free()

    def finalize(self, parent, bvh=None):
        if bvh is not None and self.occlude:
            for i in range(len(self.v)):
                k = _ao(bvh, self.v[i] + self.pivot, self.n[i], 0.6)
                self.c[i] = tuple(c * k for c in self.c[i][:3])
        me = bpy.data.meshes.new(self.name)
        me.from_pydata([tuple(p) for p in self.v], [], self.f)
        uvl = me.uv_layers.new(name='UVMap')
        uvl.data.foreach_set('uv', [x for uv in self.uv for x in uv])
        ca = me.color_attributes.new('Color', 'BYTE_COLOR', 'CORNER')
        cols = []
        for f in self.f:
            for i in f:
                cols.extend((*self.c[i][:3], 1.0))
        ca.data.foreach_set('color', cols)
        me.color_attributes.active_color = ca
        me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
        me.normals_split_custom_set_from_vertices([tuple(n) for n in self.n])
        me.materials.append(self.material or _foliage['m'])
        ob = bpy.data.objects.new(self.name, me)
        bpy.context.scene.collection.objects.link(ob)
        _attach(self, ob, parent)
        return ob


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

    def raw(self, name, pivot=(0, 0, 0), parent=None):
        p = RawPart(name, pivot, parent)
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


def _patch_gltf(path):
    """Force alpha-cutout + double-sided on foliage materials (independent of exporter heuristics).
    Works on both .glb and .gltf files; returns the JSON."""
    import json
    import struct

    def fix(js):
        for m in js.get('materials', []):
            if m.get('name', '').startswith('foliage'):
                m['alphaMode'] = 'MASK'
                m['alphaCutoff'] = 0.4
                m['doubleSided'] = True
        for im in js.get('images', []):
            if 'uri' in im:
                im['uri'] = im['uri'].replace('\\', '/')
        return js
    if path.endswith('.gltf'):
        js = fix(json.load(open(path, encoding='utf-8')))
        json.dump(js, open(path, 'w', encoding='utf-8'), separators=(',', ':'))
        return js
    data = open(path, 'rb').read()
    magic, ver, total = struct.unpack('<III', data[:12])
    jlen, jtype = struct.unpack('<II', data[12:20])
    js = fix(json.loads(data[20:20 + jlen]))
    rest = data[20 + jlen:]
    out = json.dumps(js, separators=(',', ':')).encode()
    out += b' ' * ((4 - len(out) % 4) % 4)
    blob_ = struct.pack('<II', len(out), jtype) + out + rest
    open(path, 'wb').write(struct.pack('<III', magic, ver, 12 + len(blob_)) + blob_)
    return js


def export_asset(asset, out_dir, clear=True, ao=True):
    """Finalize an asset, export <name>.glb, return a manifest entry."""
    from mathutils.bvhtree import BVHTree
    if clear:
        clear_scene()
    asset.parts = [p for p in asset.parts if p.tris() > 0 or any(q.parent is p for q in asset.parts)]
    root = bpy.data.objects.new(asset.name, None)
    bpy.context.scene.collection.objects.link(root)
    tris = sum(p.tris() for p in asset.parts)
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    verts, polys = [], []
    for p in asset.parts:
        pts = p.points()
        base = len(verts)
        for w in pts:
            for i in range(3):
                lo[i] = min(lo[i], w[i])
                hi[i] = max(hi[i], w[i])
        pl = [] if getattr(p, 'hidden', False) else p.polys()
        if pl:
            verts.extend(pts)
            polys.extend([[base + i for i in f] for f in pl])
    bvh = BVHTree.FromPolygons(verts, polys) if (ao and polys) else None
    nodes = {}
    obs = [root]
    for p in asset.parts:
        obs.append(p.finalize(root, bvh))
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
    # textured models are written as .gltf + .bin so they all share one copy of each texture in _tex/
    textured = any(isinstance(p, RawPart) for p in asset.parts)
    fname = asset.name + ('.gltf' if textured else '.glb')
    path = os.path.join(out_dir, fname)
    kw = dict(filepath=path, export_format='GLTF_SEPARATE' if textured else 'GLB', export_keep_originals=textured, use_selection=True, export_apply=True,
              export_yup=True, export_normals=True, export_texcoords=True,
              export_materials='EXPORT', export_animations=False, export_cameras=False,
              export_lights=False, export_vertex_color='ACTIVE', export_all_vertex_colors=False,
              export_active_vertex_color_when_no_material=True)
    props = bpy.ops.export_scene.gltf.get_rna_type().properties.keys()
    bpy.ops.export_scene.gltf(**{k: v for k, v in kw.items() if k in props})
    js = _patch_gltf(path)
    if not clear:
        for ob in obs:
            bpy.data.objects.remove(ob, do_unlink=True)
    return {
        'file': fname,
        'bytes': os.path.getsize(path) + (os.path.getsize(path[:-5] + '.bin') if textured and os.path.exists(path[:-5] + '.bin') else 0),
        'triangles': tris,
        'size': [round(hi.x - lo.x, 3), round(hi.z - lo.z, 3), round(hi.y - lo.y, 3)],
        'nodes': nodes,
        'textured': bool(js.get('images')),
        'optional_nodes': [p.name for p in asset.parts if getattr(p, 'hidden', False)],
        'note': asset.note,
    }
