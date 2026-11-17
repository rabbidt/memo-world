"""Trees, pines and shrubs with layered leaf-card canopies.

Foliage is many small alpha-cut cards from a painted atlas, scattered over irregular cluster volumes on real
branches, with puffy hand-set normals and vertex-colour gradients (dark inside and below, light on top).
A dark solid core inside each cluster stops the canopy being see-through. Every model also has a _lod1.
"""
import math
import random

from mathutils import Vector

from mathutils import Matrix

from memo_lib import bark_mat, PI, Asset, lin, ico, cyl, lathe, tube, torus, sphere, displace, TRS, align_z
from memo_char import C

UP = Vector((0, 0, 1))


def rgb(h):
    return Vector(lin(h))


PAL = {
    'oak': ('#2e6f4a', '#6fbd43', '#e9f58a'),
    'elm': ('#3a7d46', '#72c063', '#d2f08c'),
    'olive': ('#476b35', '#8aac48', '#d6e274'),
    'birch': ('#5f9636', '#a9d653', '#eef58a'),
    'blossom': ('#e07aa8', '#ffb8d0', '#fff0f4'),
    'pine': ('#1f5c4c', '#3f9a74', '#a4e2b8'),
    'pine_blue': ('#235f5f', '#4aa096', '#b4e8d6'),
    'spring': ('#5a9a3c', '#9ed35a', '#e6f79a'),
    'autumn': ('#a5471f', '#e58a2e', '#f7cf5a'),
    'autumn_red': ('#8f2f24', '#d4532f', '#f08a3a'),
    'autumn_gold': ('#a8741f', '#e8b53a', '#fbe77a'),
    'wintry': ('#6b4a2a', '#9a6f3a', '#c79a5a'),
    'bush': ('#3b7338', '#72b84e', '#c6ea7a'),
    'bush_dark': ('#2f6238', '#559c4e', '#a4d470'),
}


def _unit(rng):
    while True:
        v = Vector((rng.gauss(0, 1), rng.gauss(0, 1), rng.gauss(0, 1)))
        if v.length > 1e-3:
            return v.normalized()


def _mix(a, b, t):
    t = max(0.0, min(1.0, t))
    return a * (1 - t) + b * t


def canopy(rp, rng, clusters, pal, n_per=70, size=0.8, lod=1.0, cells=(0, 1), pal2=None, mix=0.0, core=True, dens=1.0):
    """Scatter leaf cards over ellipsoid clusters [(centre, radii)]."""
    dark, mid, light = (rgb(h) for h in PAL[pal])
    alt = [rgb(h) for h in PAL[pal2]] if pal2 else None
    zmin = min(c.z - r.z for c, r in clusters)
    zmax = max(c.z + r.z for c, r in clusters)
    centre = sum((c for c, _ in clusters), Vector()) / len(clusters)
    for ci, (c, rad) in enumerate(clusters):
        if core:
            cm = ico(1.0, 1)
            displace(cm, 0.18, 1.7, ci * 3.7)
            for v in cm.verts:
                v.co = Vector((v.co.x * rad.x * 0.5, v.co.y * rad.y * 0.5, v.co.z * rad.z * 0.46)) + c
            rp.solid(cm, c, rgb(PAL['oak'][0]) * 0.3 if pal == 'blossom' else dark * 0.38)
        area = (rad.x * rad.y + rad.y * rad.z + rad.x * rad.z) / 3
        n = max(3, int(n_per * area * lod * dens))
        for i in range(n):
            d = _unit(rng)
            if d.z < -0.8:
                d.z = -d.z * 0.4
                d.normalize()
            k = rng.uniform(0.74, 1.08)
            p = c + Vector((d.x * rad.x, d.y * rad.y, d.z * rad.z)) * k
            ns = Vector((d.x / rad.x, d.y / rad.y, d.z / rad.z)).normalized()
            f = (ns + _unit(rng) * 0.42 + UP * 0.15).normalized()
            t = f.cross(UP)
            t = t.normalized() if t.length > 1e-3 else Vector((1, 0, 0))
            b = f.cross(t)
            roll = rng.uniform(0, 2 * PI)
            s = size * rng.uniform(0.7, 1.25) / math.sqrt(lod) * 0.5
            right = (t * math.cos(roll) + b * math.sin(roll)) * s
            up = (-t * math.sin(roll) + b * math.cos(roll)) * s
            h = (p.z - zmin) / max(1e-3, zmax - zmin)
            dk, md, lt = (dark, mid, light) if not (alt and rng.random() < mix) else alt
            lit = max(0.0, min(1.0, 0.5 * h + 0.5 * (0.5 + 0.5 * ns.z)))   # high and up-facing = sun-lit
            col = _mix(dk, md, lit * 1.7)
            col = _mix(col, lt, (lit - 0.5) * 2.2)
            col = col * (0.6 + 0.4 * (k - 0.74) / 0.34) * rng.uniform(0.9, 1.1)
            col = Vector((col.x * rng.uniform(0.93, 1.07), col.y, col.z * rng.uniform(0.9, 1.1)))
            corners = [p - right - up, p + right - up, p + right + up, p - right + up]
            zc = [q.z for q in corners]
            zl, zh = min(zc), max(zc)
            cols = [col * (0.82 + 0.18 * ((q.z - zl) / max(1e-4, zh - zl))) for q in corners]
            norms = []
            for q in corners:
                e = q - c
                norms.append(Vector((e.x / rad.x, e.y / rad.y, e.z / rad.z)).normalized() * 0.7
                             + (q - centre).normalized() * 0.18 + UP * 0.22)
            rp.tent(p, right, up, rng.choice(cells), cols, norms, bend=rng.uniform(0.25, 0.45), flip=rng.random() < 0.5)


SEASONS = ('spring', 'summer', 'autumn', 'winter')


def season_canopies(a, node, pivot, seed, clusters, kw, seasons, summer):
    """One foliage node per season (<node>_spring ... _winter). All but summer are exported hidden."""
    cfg = {'spring': ('spring', 'blossom', 0.12, 0.9), 'summer': (*summer, 1.0),
           'autumn': ('autumn', 'autumn_red', 0.4, 0.85), 'winter': ('wintry', None, 0.0, 0.1)}
    cfg.update(seasons)
    for s in SEASONS:
        pal, pal2, mix, dens = cfg[s]
        rp = a.raw(node + '_' + s, pivot)
        rp.hidden = s != 'summer'
        canopy(rp, random.Random(seed * 7 + 1), clusters, pal, pal2=pal2, mix=mix, dens=dens, core=s != 'winter', **kw)





TEXEL = 0.85          # metres of bark covered by one repeat of the texture
NORTH = Vector((-0.85, -0.5, 0)).normalized()
MOSS = Vector(lin('#86b84a')) * 1.25


class Bark:
    """Where bark geometry goes: a textured RawPart plus the species tint."""

    def __init__(self, rp, tint='#a58a74'):
        self.rp = rp
        self.tint = rgb(tint)


def bark_tube(bk, rng, pts, radii, seg=14, shape=None, v0=0.0, moss=0.0, shade0=1.0):
    """Tapered tube with cylindrical UVs, radial normals and painted vertex colour
    (dark at the ground and in the forks, moss on the north side low down)."""
    pts = [Vector(p) for p in pts]
    n = len(pts)
    rings = []
    prev = None
    v = v0
    reps = max(1, round(2 * PI * (sum(radii) / n) / TEXEL))
    for i, p in enumerate(pts):
        tg = (pts[1] - p) if i == 0 else ((p - pts[i - 1]) if i == n - 1 else (pts[i + 1] - pts[i - 1]))
        tg.normalize()
        if prev is None:
            a = Vector((1, 0, 0)) if abs(tg.x) < 0.9 else Vector((0, 1, 0))
            N = (a - tg * a.dot(tg)).normalized()
        else:
            N = (prev - tg * prev.dot(tg)).normalized()
        B = tg.cross(N)
        prev = N
        if i:
            v += (p - pts[i - 1]).length / TEXEL
        ring = []
        for j in range(seg + 1):
            ang = 2 * PI * (j % seg) / seg
            d = N * math.cos(ang) + B * math.sin(ang)
            rr = radii[i] * (1 + (shape(i / (n - 1), ang) if shape else 0.0))
            pos = p + d * rr
            k = (0.55 + 0.45 * min(1.0, max(0.0, pos.z) / 0.6)) * (shade0 if i == 0 else 1.0)
            col = bk.tint * k * rng.uniform(0.94, 1.06)
            if moss > 0:
                m = max(0.0, d.dot(NORTH)) ** 0.7 * max(0.0, 1 - pos.z / 2.4) * moss
                m *= 0.55 + 0.9 * abs(math.sin(ang * 3.3 + pos.z * 4.1))
                col = _mix(col, MOSS, min(0.85, m))
            ring.append((pos, d, (j / seg * reps, v), col))
        rings.append(ring)
    for a, b in zip(rings, rings[1:]):
        for j in range(seg):
            q = (a[j], a[j + 1], b[j + 1], b[j])
            bk.rp.face([x[0] for x in q], [x[2] for x in q], [x[3] for x in q], [x[1] for x in q])
    return v


def trunk(put, rng, top, r, bark, lean=(0, 0), roots=5, tint=1.0):
    """Curved, tapered, fluted trunk with root flare and knots. Returns the centre-line function at(t)."""
    sx, sy = rng.uniform(0, 6), rng.uniform(0, 6)

    def at(t):
        return Vector((lean[0] * t ** 1.4 + 0.1 * r * 4 * math.sin(t * 4.2 + sx) * t,
                       lean[1] * t ** 1.4 + 0.1 * r * 4 * math.sin(t * 3.6 + sy) * t, top * t))
    n = 14
    pts = [at(i / n) - Vector((0, 0, 0.1 if i == 0 else 0)) for i in range(n + 1)]
    rad = [r * (0.6 + 0.4 * (1 - i / n)) * (1 + 1.0 * math.exp(-(i / n) * 13)) for i in range(n + 1)]
    knots = [(rng.uniform(0.25, 0.85), rng.uniform(0, 2 * PI)) for _ in range(3)]

    def shape(tt, ang):
        ridge = math.sin(7 * ang + 2.5 * math.sin(tt * 5 + sx)) * 0.5 + math.sin(13 * ang + tt * 9) * 0.25
        s = 0.085 * ridge * (1 + 1.6 * math.exp(-tt * 9))
        for kt, ka in knots:
            da = math.atan2(math.sin(ang - ka), math.cos(ang - ka))
            s += 0.22 * math.exp(-((tt - kt) * top / (r * 0.9)) ** 2 - (da / 0.45) ** 2)
        return s + 0.05 * math.sin(tt * 11 + ang * 2 + sy)
    bark_tube(bark, rng, pts, rad, 18, shape, moss=1.0)
    for k in range(roots):
        an = 2 * PI * (k + rng.uniform(-0.25, 0.25)) / roots
        ln = r * rng.uniform(2.6, 3.9)
        o = Vector((math.cos(an), math.sin(an), 0))
        side = Vector((-o.y, o.x, 0)) * rng.uniform(-0.4, 0.4) * r
        bark_tube(bark, rng, [o * r * 0.55 + Vector((0, 0, r * 1.9)), o * (r * 0.95 + ln * 0.3) + side * 0.5 + Vector((0, 0, r * 0.75)),
                              o * (r + ln * 0.7) + side + Vector((0, 0, r * 0.22)), o * (r + ln) + side * 1.3 + Vector((0, 0, -0.06))],
                  [r * 0.52, r * 0.4, r * 0.24, r * 0.08], 9, lambda tt, ang: 0.08 * math.sin(5 * ang + k), moss=0.7)
    return at


def branch(put, rng, start, az, elev, length, r, bark, tint=1.0):
    o = Vector((math.cos(az), math.sin(az), 0))
    pts = []
    n = 6
    for i in range(n + 1):
        t = i / n
        e = elev + 0.35 * t
        pts.append(start + o * length * t * math.cos(elev) + UP * length * math.sin(e) * t
                   + Vector((rng.uniform(-0.05, 0.05), rng.uniform(-0.05, 0.05), 0)) * length * t)
    pts[0] = start - (pts[1] - start) * 0.25        # start inside the parent limb
    rad = [r * (1 - 0.8 * i / n) * (1.3 if i <= 1 else 1.0) for i in range(n + 1)]
    bark_tube(bark, rng, pts, rad, 10, lambda tt, ang: 0.07 * math.sin(5 * ang + az), shade0=0.6)
    return pts


def make_tree(name, seed, h=5.2, r=0.26, spread=2.1, cs=1.1, pal='oak', bark='#a58a74', n_br=5, lean=(0.2, 0.1),
              leaders=2, lod=1.0, note='', birch=False, pal2=None, mix=0.0, size=0.8, n_per=70, crown=0.56, seasons=None, forks=2, satellites=4, dress=True):
    rng = random.Random(seed)
    a = Asset(name, note)
    T = a.raw('Trunk')
    T.material = bark_mat()
    put = a.part('Base').put()
    bk = Bark(T, bark)
    top = h * crown
    at = trunk(put, rng, top, r, bk, lean)
    if birch:
        for i in range(7):
            p = at(rng.uniform(0.08, 0.95))
            put(cyl(r * 0.78, r * 0.74, rng.uniform(0.03, 0.07), 10), C('#3a3a38'), loc=p + Vector((0, 0, 0)), rot=(rng.uniform(-0.1, 0.1), 0, rng.uniform(0, 6)))
    clusters = []
    for k in range(n_br):
        t = 0.5 + 0.48 * (k + rng.uniform(0, 0.6)) / n_br
        az = 2 * PI * (k * 0.618 + rng.uniform(-0.08, 0.08))
        ln = spread * rng.uniform(0.7, 1.05) * (0.75 + 0.25 * (1 - t))
        pts = branch(put, rng, at(t), az, rng.uniform(0.35, 0.75), ln, r * 0.5 * (1.2 - t * 0.5), bk)
        s = cs * rng.uniform(0.8, 1.15)
        clusters.append((pts[-1] + UP * s * 0.25, Vector((s * rng.uniform(0.9, 1.2), s * rng.uniform(0.9, 1.2), s * rng.uniform(0.62, 0.8)))))
        for fk in range(forks):   # each limb forks into twigs that carry their own leaf clusters
            az2 = az + (1 if fk % 2 else -1) * rng.uniform(0.7, 1.25)
            p2 = branch(put, rng, pts[2 if fk < 2 else 3], az2, rng.uniform(0.45, 0.95), ln * rng.uniform(0.45, 0.65), r * 0.2, bk)
            s2 = cs * rng.uniform(0.5, 0.78)
            clusters.append((p2[-1] + UP * s2 * 0.2, Vector((s2 * rng.uniform(1.0, 1.3), s2 * rng.uniform(1.0, 1.3), s2 * 0.8))))
    for k in range(leaders):
        az = 2 * PI * (k / max(1, leaders) + rng.uniform(0, 0.3))
        pts = branch(put, rng, at(1.0), az, 1.05, (h * 0.86 - top) * rng.uniform(0.85, 1.0), r * 0.52, bk)
        s = cs * rng.uniform(0.9, 1.2)
        clusters.append((pts[-1] + UP * s * 0.15, Vector((s * 1.1, s * 1.1, s * 0.78))))
    clusters.append((at(1.0) + UP * (h * 0.14), Vector((cs * 1.05, cs * 1.05, cs * 0.7))))
    for k in range(satellites):   # small tufts breaking the outline
        c, rad = clusters[rng.randrange(len(clusters) - 1)]
        d = _unit(rng)
        d.z = -abs(d.z) * 0.5
        s3 = cs * rng.uniform(0.28, 0.42)
        clusters.append((c + Vector((d.x * rad.x, d.y * rad.y, d.z * rad.z)) * 1.05, Vector((s3 * 1.2, s3 * 1.2, s3 * 0.85))))
    if dress:
        import memo_world as MW
        for k in range(9):
            an, rr = rng.uniform(0, 2 * PI), rng.uniform(0.5, 1.5)
            MW.grass(put, (rr * math.cos(an), rr * math.sin(an), 0), 8, rng.uniform(0.22, 0.4), rng)
        for k in range(6):
            an, rr = rng.uniform(0, 2 * PI), rng.uniform(0.7, 1.6)
            MW.flower(put, (rr * math.cos(an), rr * math.sin(an), 0), rng.choice(('#f7f1e3', '#f2c94c', '#f2a0a8', '#c7a7e8')), rng.uniform(0.2, 0.32), rng)
        for k in range(3):
            an, rr = rng.uniform(0, 2 * PI), rng.uniform(0.9, 1.5)
            w = rng.uniform(0.25, 0.5)
            put(MW.boulder(rng, w, w * 0.8, w * 0.6, 12, 0.08, 2), C(rng.choice(MW.STONES), rough=0.95),
                mtx=TRS((rr * math.cos(an), rr * math.sin(an), -0.03), (0, 0, rng.uniform(0, 6))), tint=rng.uniform(0.88, 1.05))
        for k in range(4):
            an = rng.uniform(0, 2 * PI)
            MW.moss(put, (r * 1.5 * math.cos(an), r * 1.5 * math.sin(an), r * 0.9), r * 1.6, r * 1.2, rng)
        MW.mushroom(put, (r * 2.4, -r * 1.5, 0), 1.3, rng=rng)
        MW.mushroom(put, (r * 2.9, -r * 1.2, 0), 0.9, '#d9903f', False, rng)
        U = a.raw('Undergrowth')
        dk, lt = rgb('#3f8a3c'), rgb('#bfe070')
        for k in range(26):
            an, rr = rng.uniform(0, 2 * PI), rng.uniform(0.35, 1.9)
            base = Vector((rr * math.cos(an), rr * math.sin(an), 0))
            hgt = rng.uniform(0.22, 0.42)
            tv = Vector((math.cos(an * 3.1 + k), math.sin(an * 3.1 + k), 0))
            kk = rng.uniform(0.85, 1.1)
            U.card(base + UP * hgt, tv * hgt * 0.9, UP * hgt, 3, [dk * kk, dk * kk, lt * kk, lt * kk], [UP + tv.cross(UP) * 0.3] * 4, flip=rng.random() < 0.5)
    season_canopies(a, 'Canopy', (0, 0, top), seed, clusters, dict(n_per=n_per, size=size, lod=lod), seasons or {}, (pal, pal2, mix))
    return a


def make_pine(name, seed, h=6.0, R=1.9, tiers=11, pal='pine', lod=1.0, note=''):
    rng = random.Random(seed)
    a = Asset(name, note)
    T = a.raw('Trunk')
    T.material = bark_mat()
    put = a.part('Base').put()
    bk = Bark(T, '#a87a60')
    lean = (rng.uniform(-0.15, 0.15), rng.uniform(-0.15, 0.15))
    at0 = trunk(put, rng, h * 0.8, 0.2, bk, lean, roots=4)
    at = lambda t: at0(min(1.0, t * 0.97 / 0.8)) + Vector((0, 0, max(0.0, t * h * 0.97 - h * 0.8)))
    dark, mid, light = (rgb(x) for x in PAL[pal])
    z0 = h * 0.2
    for season in ('summer', 'winter'):
        _pine_canopy(a, random.Random(seed + 5), season, at, h, R, tiers, pal, lod, z0, seed)
    return a


def _pine_canopy(a, rng, season, at, h, R, tiers, pal, lod, z0, seed):
    dark, mid, light = (rgb(x) for x in PAL[pal])
    snow = season == 'winter'
    white = Vector((1.0, 1.0, 1.0))
    Cn = a.raw('Canopy_' + season, (0, 0, h * 0.2))
    Cn.hidden = snow
    core = lathe([(0, z0), (R * 0.34, z0 + 0.1), (R * 0.17, z0 + (h - z0) * 0.5), (0, h * 0.93)], 9)
    displace(core, 0.08, 1.5, seed)
    for v in core.verts:
        p = at(max(0, min(1, v.co.z / (h * 0.97))))
        v.co.x += p.x
        v.co.y += p.y
    Cn.solid(core, Vector((0, 0, h * 0.5)), dark * 0.4)
    tiers = max(4, int(round(tiers * (0.7 + 0.3 * lod))))
    for k in range(tiers):
        t = k / (tiers - 1)
        z = h * (0.2 + 0.7 * t)
        axis = at(z / (h * 0.97))
        rad = R * (1 - t) ** 0.9 + 0.3
        nb = max(5, int(round((14 - 7 * t) * (0.5 + 0.5 * lod))))
        for layer, (droop, lf, zoff) in enumerate(((0.38 - 0.1 * t, 1.0, 0.0), (0.95, 0.72, 0.12))):
            cnt = nb if layer == 0 else max(3, nb * 2 // 3)
            for j in range(cnt):
                az = 2 * PI * (j + 0.5 * (k % 2) + 0.25 * layer + rng.uniform(-0.18, 0.18)) / cnt
                o = Vector((math.cos(az), math.sin(az), 0))
                tan = Vector((-math.sin(az), math.cos(az), 0))
                dr = droop + rng.uniform(-0.1, 0.1)
                d = (o * math.cos(dr) - UP * math.sin(dr)).normalized()
                ln = rad * lf * rng.uniform(0.88, 1.15)
                base = axis + UP * zoff + o * 0.08
                col = _mix(_mix(dark, mid, 0.35 + 0.65 * t), light, 0.25 + 0.3 * t) * rng.uniform(0.88, 1.1) * (1.0 if layer == 0 else 0.8)
                up = d * ln * 0.5
                right = tan * ln * 0.6 * (1.0 if lod >= 1 else 1.3)
                n_in = (o * 0.35 + UP * 0.95)
                n_out = (o * 0.75 + UP * 0.6 - d.cross(tan) * 0.0)
                Cn.card(base + up, right, up, 2,
                        [col * 0.62, col * 0.62] + [(_mix(col * 1.12, white, 0.8) if snow and layer == 0 else col * 1.12)] * 2,
                        [n_in - tan * 0.3, n_in + tan * 0.3, n_out + tan * 0.35, n_out - tan * 0.35], flip=rng.random() < 0.5)
    tip = at(1.0)
    for j in range(3):
        az = PI * j / 3
        tan = Vector((math.cos(az), math.sin(az), 0))
        Cn.card(tip + UP * 0.1, tan * 0.34, UP * 0.5, 2, [mid * 0.8, mid * 0.8, white if snow else light, white if snow else light], [tan.cross(UP) + UP] * 4)


def make_bush(name, seed, w=1.5, h=1.0, pal='bush', lod=1.0, flowers=None, berries=None, note='', count=5):
    rng = random.Random(seed)
    a = Asset(name, note)
    put = a.part('Stems').put()
    bk = C('#5a4130', rough=0.95)
    clusters = []
    for k in range(count):
        az = 2 * PI * (k * 0.618 + rng.uniform(-0.05, 0.05))
        d = (w * 0.3) * rng.uniform(0.3, 1.0) if k else 0.0
        s = rng.uniform(0.3, 0.44) * (1.25 if k == 0 else 1.0) * (h / 1.0)
        tipp = Vector((d * math.cos(az), d * math.sin(az), h * rng.uniform(0.45, 0.7) * (1.15 if k == 0 else 0.85)))
        put(tube([Vector((d * 0.2 * math.cos(az), d * 0.2 * math.sin(az), -0.03)), tipp * 0.55 + Vector((0, 0, 0.05)), tipp],
                 [0.045, 0.035, 0.02], 5), bk)
        clusters.append((tipp, Vector((s * rng.uniform(1.0, 1.3), s * rng.uniform(1.0, 1.3), s * rng.uniform(0.75, 0.95)))))
    season_canopies(a, 'Leaves', (0, 0, 0), seed, clusters, dict(n_per=150, size=0.42, lod=lod), {}, (pal, None, 0.0))
    for i in range(int((14 if flowers or berries else 0) * (0.5 + 0.5 * lod))):
        c, rad = rng.choice(clusters)
        d = _unit(rng)
        d.z = abs(d.z) * 0.8 + 0.1
        d.normalize()
        p = c + Vector((d.x * rad.x, d.y * rad.y, d.z * rad.z)) * 1.02
        if berries:
            put(sphere(0.035, 6, 4), C(berries, rough=0.35), loc=p)
        else:
            colr = rng.choice(flowers)
            for j in range(5):
                an = 2 * PI * j / 5
                tv = d.cross(UP).normalized() if abs(d.z) < 0.99 else Vector((1, 0, 0))
                bv = d.cross(tv)
                put(sphere(1.0, 5, 3), C(colr), loc=p + (tv * math.cos(an) + bv * math.sin(an)) * 0.04, scale=(0.03, 0.03, 0.022))
            put(sphere(0.02, 5, 3), C('#f2c94c'), loc=p + d * 0.012)
    return a


TREES = [
    (make_tree, 'tree', dict(seed=11, h=5.6, r=0.3, cs=0.95, n_br=6, n_per=120, size=0.62, lean=(0.35, 0.15), note='Broad oak with a layered leaf-card canopy, about 5.5 m tall.')),
    (make_tree, 'tree_tall', dict(seed=12, h=7.0, r=0.24, spread=1.25, cs=0.95, pal='elm', n_br=7, lean=(0.1, -0.15), leaders=2, seasons={'autumn': ('autumn_gold', 'autumn', 0.3, 0.85)},
                                 crown=0.62, note='Tall narrow elm, about 7 m.')),
    (make_tree, 'tree_wide', dict(seed=13, h=4.8, r=0.32, spread=3.0, cs=1.25, pal='olive', n_br=6, lean=(0.7, 0.3), leaders=1,
                                 crown=0.48, note='Old spreading tree with a leaning trunk, about 5 m tall and 8 m across.')),
    (make_tree, 'tree_blossom', dict(seed=14, h=4.2, r=0.2, spread=1.8, cs=0.95, pal='elm', bark='#a8857c', seasons={'spring': ('blossom', 'oak', 0.18, 1.0), 'autumn': ('autumn_red', 'autumn', 0.3, 0.85)},
                                    n_br=5, lean=(-0.3, 0.2), size=0.62, n_per=95, note='Blossom tree: pink in spring, green in summer, red in autumn. About 4.3 m.')),
    (make_tree, 'tree_birch', dict(seed=15, h=6.0, r=0.15, spread=1.5, cs=0.8, pal='birch', bark='#ffffff', n_br=6, lean=(0.25, 0.1),
                                  birch=True, size=0.6, n_per=85, seasons={'autumn': ('autumn_gold', None, 0.0, 0.8)}, crown=0.6, note='Slender birch with a pale banded trunk, about 6 m.')),
    (make_pine, 'pine', dict(seed=21, note='Layered spruce built from drooping bough cards, about 6 m.')),
    (make_pine, 'pine_tall', dict(seed=22, h=8.2, R=1.7, tiers=15, pal='pine_blue', note='Tall slim blue-green fir, about 8 m.')),
    (make_bush, 'bush', dict(seed=31, flowers=('#f2a0a8', '#f7f1e3'), note='Leafy flowering shrub, about 1.6 m across.')),
    (make_bush, 'bush_low', dict(seed=32, w=2.2, h=0.7, count=7, pal='bush_dark', note='Low spreading shrub, about 2.2 m across.')),
    (make_bush, 'bush_berry', dict(seed=33, w=1.3, h=1.2, pal='bush_dark', berries='#c8452f', note='Upright berry bush, about 1.3 m tall.')),
]


def build_trees():
    for fn, name, kw in TREES:
        yield fn(name, **kw)
        kw2 = dict(kw, lod=0.38, note=kw.get('note', '') + ' Low-detail version for distance.')
        yield fn(name + '_lod1', **kw2)
