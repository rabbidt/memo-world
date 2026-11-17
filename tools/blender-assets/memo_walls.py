"""Dry-stone wall generator.

Rules (written so they can be ported to the game and run by Ash at build time):
  1. A wall follows a path (any polyline). Everything is placed by distance along it.
  2. Stones are laid in courses. Each course picks its own height; each stone its own width, so no two
     walls match. Widths are rescaled so a course exactly fills the path, and the first stone of every
     other course is a half stone, so joints never line up with the course below (running bond).
  3. Every stone is its own rounded block: a pillow-cornered cuboid, a little lumpy, with one to three
     flat chips knocked off, a slight tilt and its own tint. Gaps between stones show a dark earth core.
  4. A course of wide flat capstones overhangs the top. Ends finish flush with whole stones.
  5. Moss grows on the caps and in the joints, with grass, ferns and flowers along the foot.

Nodes: Wall (textured stones), Core (dark earth, moss, flowers), Greenery (grass and fern cards).
"""
import math
import random

import bmesh
from mathutils import Vector, Matrix, noise

from memo_lib import PI, Asset, lin, box, boulder, stone_mat, TRS
from memo_char import C

UP = Vector((0, 0, 1))
TINTS = ['#efe8d8', '#e2dbcb', '#f6f0e2', '#d8d3c4', '#eadfc9', '#dcdfd2']
MOSS = Vector(lin('#7fb04a'))
DAMP = Vector(lin('#8a9a78'))


def rounded_stone(rng, w, d, h, cuts=3, rad=0.36, lump=0.07, chips=(1, 3)):
    """One hand-laid stone, centred on the origin."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=cuts, use_grid_fill=True)
    off = Vector((rng.uniform(0, 50), rng.uniform(0, 50), rng.uniform(0, 50)))
    lim = 0.5 - rad
    taper = rng.uniform(-0.08, 0.08)
    for v in bm.verts:
        p = v.co
        inner = Vector((max(-lim, min(lim, p.x)), max(-lim, min(lim, p.y)), max(-lim, min(lim, p.z))))
        dv = p - inner
        if dv.length > 1e-6:
            p = inner + dv.normalized() * rad
        q = Vector((p.x * w * (1 + taper * p.z * 2), p.y * d, p.z * h))
        q *= 1 + lump * noise.noise(q * 2.4 + off)
        v.co = q
    for _ in range(rng.randint(*chips)):
        n = Vector((rng.gauss(0, 1), rng.gauss(0, 1), rng.gauss(0, 0.6))).normalized()
        reach = max(v.co.dot(n) for v in bm.verts)
        cut = reach * rng.uniform(0.84, 0.95)
        for v in bm.verts:
            over = v.co.dot(n) - cut
            if over > 0:
                v.co -= n * over * 0.9
    return bm


class Path:
    def __init__(self, pts):
        self.p = [Vector(p) for p in pts]
        self.s = [0.0]
        for a, b in zip(self.p, self.p[1:]):
            self.s.append(self.s[-1] + (b - a).length)
        self.length = self.s[-1]

    def at(self, s):
        """(position, unit tangent, unit left-hand normal) at distance s."""
        s = max(0.0, min(self.length, s))
        i = 0
        while i < len(self.s) - 2 and self.s[i + 1] < s:
            i += 1
        t = (s - self.s[i]) / max(1e-9, self.s[i + 1] - self.s[i])
        pos = self.p[i].lerp(self.p[i + 1], t)
        j0, j1 = max(0, i - 1), min(len(self.p) - 1, i + 2)
        tan = (self.p[i + 1] - self.p[i]).normalized().lerp((self.p[j1] - self.p[j0]).normalized(), 0.5).normalized()
        return pos, tan, UP.cross(tan).normalized()


def arc_path(radius, a0, a1, n=24):
    """Arc centred on the origin, bulging toward -Y (the model's front)."""
    return Path([(radius * math.sin(a0 + (a1 - a0) * i / n), -radius * math.cos(a0 + (a1 - a0) * i / n), 0) for i in range(n + 1)])


def build_wall(a, seed, path, height=0.78, thick=0.44, cuts=3, moss=0.5, dress=True):
    rng = random.Random(seed)
    W = a.raw('Wall')
    W.material = stone_mat()
    W.occlude = True
    core = a.part('Core').put()
    G = a.raw('Greenery')
    L = path.length
    joints = []            # (s, course top z): where moss and ferns may grow

    def lay(s0, w, z, ch, depth, cap=False):
        pos, tan, nrm = path.at(s0 + w / 2)
        gap = 0.012
        sw, sh = max(0.12, w - gap), ch - gap * (0.4 if cap else 0.8)
        bm = rounded_stone(rng, sw, depth, sh, cuts, rad=0.22 if cap else rng.uniform(0.17, 0.27), lump=0.04 if cap else 0.055)
        yaw = math.atan2(tan.y, tan.x)
        M = (Matrix.Translation(pos + UP * (z + ch / 2) + nrm * rng.uniform(-0.02, 0.02))
             @ Matrix.Rotation(yaw + rng.uniform(-0.05, 0.05), 4, 'Z')
             @ Matrix.Rotation(rng.uniform(-0.05, 0.05), 4, 'X') @ Matrix.Rotation(rng.uniform(-0.045, 0.045), 4, 'Y'))
        tint = Vector(lin(rng.choice(TINTS))) * rng.uniform(0.86, 1.06)
        mossy = rng.random() < (moss * (1.3 if cap else 0.45))
        mo = Vector((rng.uniform(0, 30), rng.uniform(0, 30), 0))

        def col(wp, n):
            c = tint
            if wp.z < 0.22:                                   # damp green foot
                c = c.lerp(DAMP * 0.85, (0.22 - wp.z) / 0.22 * 0.55)
            if mossy and n.z > 0.35:
                m = (n.z - 0.35) / 0.65 * (0.55 + 0.6 * noise.noise(wp * 5 + mo))
                c = c.lerp(MOSS, max(0.0, min(0.85, m)))
            return c
        W.mesh(bm, M, col, uv_scale=1.1, uv_off=(rng.random(), rng.random()))

    # courses
    cap_h = 0.12
    z = -0.05
    course = 0
    while z < height - cap_h - 0.12:
        ch = min(rng.uniform(0.2, 0.3), height - cap_h - z)
        widths = [rng.uniform(0.3, 0.62) for _ in range(int(L / 0.3) + 2)]
        if course % 2:
            widths[0] *= 0.5
        acc, row = 0.0, []
        for w in widths:
            if acc + w > L:
                break
            row.append(w)
            acc += w
        k = L / acc
        s = 0.0
        for w in row:
            lay(s, w * k, z, ch * rng.uniform(0.93, 1.03), thick * rng.uniform(0.92, 1.06))
            s += w * k
            joints.append((s, z + ch))
        z += ch
        course += 1
    # capstones
    acc, row = 0.0, []
    while acc < L:
        w = rng.uniform(0.5, 0.85)
        row.append(w)
        acc += w
    k = L / acc
    s = 0.0
    for w in row:
        lay(s, w * k, z - 0.01, cap_h * rng.uniform(0.9, 1.15), thick * 1.2, cap=True)
        s += w * k
    top = z + cap_h

    # dark earth core, seen through the joints
    n = max(2, int(L / 0.35))
    for i in range(n):
        pos, tan, nrm = path.at(L * (i + 0.5) / n)
        core(box(L / n * 1.15, thick * 0.8, top - 0.14), C('#4a4640', rough=1.0),
             mtx=Matrix.Translation(pos + UP * ((top - 0.14) / 2)) @ Matrix.Rotation(math.atan2(tan.y, tan.x), 4, 'Z'))

    if dress:
        dk, lt = Vector(lin('#3f8a3c')), Vector(lin('#bfe070'))
        for i in range(int(L * 5)):                         # grass along both feet
            pos, tan, nrm = path.at(rng.uniform(0, L))
            side = rng.choice((-1, 1))
            base = pos + nrm * side * (thick / 2 + rng.uniform(0.02, 0.2))
            hgt = rng.uniform(0.14, 0.3)
            tv = (tan + nrm * rng.uniform(-0.6, 0.6)).normalized()
            kk = rng.uniform(0.85, 1.1)
            G.card(base + UP * hgt, tv * hgt * 0.9, UP * hgt, 3, [dk * kk, dk * kk, lt * kk, lt * kk], [UP + nrm * side * 0.4] * 4, flip=rng.random() < 0.5)
        fd, fl = Vector(lin('#3f8a45')), Vector(lin('#a8dc78'))
        for sj, zj in rng.sample(joints, min(len(joints), max(2, int(L * 0.8)))):      # ferns sprouting from joints
            if zj > top - 0.2 or zj < 0.2:
                continue
            pos, tan, nrm = path.at(sj)
            side = rng.choice((-1, 1))
            o = nrm * side
            base = pos + o * (thick / 2 - 0.03) + UP * zj
            for j in range(3):
                d = (o * 0.8 + tan * (j - 1) * 0.55 + UP * 0.25).normalized()
                ln = rng.uniform(0.16, 0.26)
                G.card(base + d * ln * 0.5, d.cross(UP).normalized() * ln * 0.3, d * ln * 0.5, 2, [fd, fd, fl, fl], [o + UP * 0.6] * 4)
        for i in range(int(L * moss * 2.2)):                # moss cushions on the caps
            pos, tan, nrm = path.at(rng.uniform(0.1, L - 0.1))
            w = rng.uniform(0.14, 0.3)
            core(boulder(rng, w, w * 0.8, 0.07, 9, 0.2, 1), C(rng.choice(('#7fb24f', '#6fa544', '#93c25c')), rough=1.0),
                 mtx=TRS(pos + nrm * rng.uniform(-0.12, 0.12) + UP * (top - 0.035), (0, 0, rng.uniform(0, 6))), tint=rng.uniform(0.9, 1.1))
        import memo_world as MW
        for i in range(max(2, int(L * 0.9))):
            pos, tan, nrm = path.at(rng.uniform(0, L))
            side = rng.choice((-1, 1))
            MW.flower(core, pos + nrm * side * (thick / 2 + rng.uniform(0.08, 0.25)), rng.choice(('#f7f1e3', '#f2a0a8', '#f2c94c', '#c7a7e8')),
                      rng.uniform(0.2, 0.32), rng)
    return top


def wall_asset(name, seed, path, note, **kw):
    a = Asset(name, note)
    build_wall(a, seed, path, **kw)
    return a


WALLS = [
    ('stone_wall', 201, lambda: arc_path(3.0, -0.7, 0.7), 'Curving dry-stone wall: an 80 degree arc of radius 3 m centred on the origin, 0.8 m tall. Four copies ring a yard.'),
    ('stone_wall_straight', 202, lambda: Path([(-2.0 + 4.0 * i / 8, 0, 0) for i in range(9)]), 'Straight dry-stone wall, 4 m long along X, 0.8 m tall.'),
    ('stone_wall_long', 203, lambda: Path([(-3.5 + 7.0 * i / 28, 0.7 * math.sin(i / 28 * PI * 1.6), 0) for i in range(29)]),
     'Winding dry-stone wall, 7 m long, 0.8 m tall.'),
]


def build_walls():
    for name, seed, mk, note in WALLS:
        yield wall_asset(name, seed, mk(), note)
        yield wall_asset(name + '_lod1', seed, mk(), note + ' Low-detail version for distance.', cuts=1, dress=False)
