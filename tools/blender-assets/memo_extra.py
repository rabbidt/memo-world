"""Ash's starting features: bridge and stream, beach hut, waterfall, campfire circle and hilltop observatory."""
import math
import random

from mathutils import Vector, Matrix

from memo_lib import (PI, Asset, mat, lin, sphere, box, cyl, lathe, dome, torus, tube, arc, leaf, disc,
                      displace, align_z, TRS, block, boulder, tile_shape)
from memo_char import C, shade
from memo_world import (STONES, TILES_RED, TILES_BLUE, WOODS, TIMBER, PLASTER, GRASS, glow, Rz, ring, stone, stones_ring,
                        stones_line, timber, grain, tiles_gable, tiles_cone, window, door, flower, grass, mushroom,
                        lantern_body, barrel, crate, ivy, dressing, moss, turf_cards, snow_part, SNOW_COL, stones_part, rock_piece)

UP = Vector((0, 0, 1))
WATER = '#7cc4dc'


def water_mat():
    return mat('water', rough=0.08, alpha=0.82, double=True, color=WATER)


def ribbon(rp, pts, widths, across=Vector((1, 0, 0)), white=None):
    """Water strip along pts with UVs (u across, v along the flow) so the game can scroll it."""
    v = 0.0
    prev = None
    for i, p in enumerate(pts):
        p = Vector(p)
        if i:
            v += (p - Vector(pts[i - 1])).length
        w = widths[i] if isinstance(widths, (list, tuple)) else widths
        k = white[i] if white else 0.0
        col = Vector((1, 1, 1)) * (1.0 + 0.0 * k)
        col = Vector((1 - 0.0, 1, 1)) if not k else Vector((1.0 + k, 1.0 + k, 1.0 + k))
        cur = (p - across * w / 2, p + across * w / 2, v, col)
        if prev:
            a0, b0, v0, c0 = prev
            a1, b1, v1, c1 = cur
            n = (b0 - a0).cross(a1 - a0)
            n = n if n.z >= 0 or abs(n.y) > abs(n.z) else -n
            rp.face([a0, b0, b1, a1], [(0, v0), (1, v0), (1, v1), (0, v1)], [c0, c0, c1, c1], [n, n, n, n])
        prev = cur


def fern(rp, base, rng, n=6, size=0.6):
    """Fern rosette from the bough card."""
    dark, light = Vector(lin('#3f8a45')), Vector(lin('#a8dc78'))
    for j in range(n):
        az = 2 * PI * (j + rng.uniform(-0.2, 0.2)) / n
        o = Vector((math.cos(az), math.sin(az), 0))
        d = (o * 0.8 + UP * 0.6).normalized()
        ln = size * rng.uniform(0.8, 1.15)
        tan = Vector((-o.y, o.x, 0))
        rp.card(Vector(base) + d * ln * 0.5, tan * ln * 0.3, d * ln * 0.5, 2, [dark, dark, light, light], [UP + o * 0.4] * 4)


# ------------------------------------------------------------------ bridge and stream

def bridge():
    rng = random.Random(101)
    a = Asset('bridge', 'Humpback stone footbridge, 5.4 m long and 2.2 m wide, walked along Z; the stream passes under along X.')
    stones_part(a)
    P = a.part('Bridge')
    put = P.put()
    deck = lambda y: 0.22 + 0.8 * math.cos(PI * y / 5.6) ** 2
    soffit = lambda y: 0.78 * math.sqrt(max(0.0, 1 - (y / 1.55) ** 2)) - 0.05 if abs(y) < 1.55 else -1
    n = 13
    for i in range(n):
        y = -2.6 + 5.2 * (i + 0.5) / n
        slope = math.atan((deck(y + 0.1) - deck(y - 0.1)) / 0.2)
        # deck slab + cobbles
        put(box(1.7, 0.46, 0.2, 0.02), C('#8f887b'), mtx=TRS((0, y, deck(y) - 0.12), (slope, 0, 0)))
        for k in range(4):
            x = -0.62 + 0.42 * k + rng.uniform(-0.04, 0.04)
            put(block(rng, 0.38, 0.36, 0.1, 0.14, 0.25), C(rng.choice(STONES)), mtx=TRS((x, y + rng.uniform(-0.03, 0.03), deck(y) + 0.0), (slope, 0, rng.uniform(-0.2, 0.2))),
                tint=rng.uniform(0.86, 1.08))
        for s in (1, -1):
            z = max(soffit(y), -0.1) + 0.14
            top = deck(y) + 0.5
            while z < top - 0.05:
                h = min(0.3, top - z)
                stone(put, (s * 0.95, y, z + h / 2 - 0.14), PI / 2, (0.44, 0.34, h * 1.05), rng)
                z += 0.28
            stone(put, (s * 0.95, y, top + 0.02), PI / 2, (0.48, 0.42, 0.14), rng, ['#cbc5b7', '#d6d0c2'])
    for s in (1, -1):    # arch ring of wedge stones
        for i in range(11):
            an = PI * i / 10
            stone(put, (s * 1.08, 1.6 * math.cos(an), 0.8 * math.sin(an) - 0.02), 0, (0.16, 0.34, 0.3), rng, ['#cbc5b7', '#d6d0c2'])
    for i in range(9):   # vault
        an = PI * (i + 0.5) / 9
        put(box(1.9, 0.6, 0.12), C('#7f786c'), mtx=TRS((0, 1.55 * math.cos(an), 0.78 * math.sin(an) - 0.03), (-(an - PI / 2), 0, 0)))
    for s in (1, -1):    # end posts with lanterns
        for e in (1, -1):
            stone(put, (s * 0.98, e * 2.75, 0.45), 0, (0.42, 0.42, 0.9), rng)
            stone(put, (s * 0.98, e * 2.75, 0.96), 0, (0.5, 0.5, 0.14), rng, ['#cbc5b7'])
    timber(put, (0.98, -2.75, 1.0), (0.98, -2.75, 1.9), 0.1)
    timber(put, (0.98, -2.75, 1.84), (0.66, -2.75, 1.84), 0.06, pegs=False)
    lantern_body(put, (0.7, -2.75, 1.8), 1.1)
    a.anchor('Light', (0.7, -2.75, 1.5))
    for s in (1, -1):
        moss(put, (s * 0.95, rng.uniform(-1, 1), deck(0.5) + 0.57), 0.34, 0.26, rng)
        for e in (1, -1):
            grass(put, (s * 1.3, e * 2.6, 0), 8, 0.36, rng)
            flower(put, (s * 1.35, e * 2.2, 0), rng.choice(('#f7f1e3', '#f2a0a8')), 0.3, rng)
    ivy(put, Matrix.Translation((-1.13, 0, 0)) @ Rz(-PI / 2) @ Matrix.Translation((0, 0, 0)), [(-1.9 + 0.25 * k, 0.5 + 0.12 * k) for k in range(6)], rng)
    return a


def stream():
    rng = random.Random(102)
    a = Asset('stream', 'Stream piece 8 m long (along X), about 1.7 m wide, with stony banks. Tile end to end; Water has flow UVs.')
    stones_part(a)
    W = a.raw('Water')
    W.material = water_mat()
    cy = lambda x: 0.35 * math.sin(x * 0.75)
    pts = [(x, cy(x), 0.03) for x in [-4 + 8 * i / 16 for i in range(17)]]
    ribbon(W, pts, [1.5 + 0.2 * math.sin(i) for i in range(17)], Vector((0, 1, 0)))
    P = a.part('Banks')
    put = P.put()
    put(box(8.0, 2.0, 0.1), C('#5c8f8a'), loc=(0, 0, -0.06))
    for s in (1, -1):
        x = -4.0
        while x < 4.0:
            w = rng.uniform(0.3, 0.6)
            y = cy(x) + s * (0.85 + rng.uniform(-0.05, 0.15))
            put(boulder(rng, w, w * 0.8, w * 0.55, 10, 0.1, 1), C(rng.choice(STONES)), mtx=TRS((x, y, -0.04), (0, 0, rng.uniform(0, 6))), tint=rng.uniform(0.88, 1.06))
            x += w * 0.85
        for k in range(5):
            x = rng.uniform(-3.8, 3.8)
            grass(put, (x, cy(x) + s * 1.25, 0), 7, 0.34, rng)
    for k in range(5):
        x = rng.uniform(-3.5, 3.5)
        put(boulder(rng, 0.3, 0.26, 0.2, 9, 0.12, 1), C(STONES[1]), loc=(x, cy(x) + rng.uniform(-0.4, 0.4), -0.03))
    F = a.raw('Ferns')
    for k in range(4):
        x = rng.uniform(-3.5, 3.5)
        fern(F, (x, cy(x) + rng.choice((-1.2, 1.2)), 0), rng)
    return a


# ------------------------------------------------------------------ beach hut

def beach_hut():
    rng = random.Random(111)
    a = Asset('beach_hut', 'Striped beach hut on stilts with a porch, 3.4 x 3.6 m footprint, 3.8 m tall. Door faces front.')
    stones_part(a)
    Sn = snow_part(a)
    P = a.part('Hut')
    put = P.put()
    W, D, fz, Hw, rise = 2.6, 2.3, 0.55, 2.0, 0.95
    bleached = ['#b89b74', '#a88a66', '#c9ad85', '#9f8463']
    # stilts and platform
    for sx in (-1.45, 0, 1.45):
        for sy in (-1.9, -0.6, 1.1):
            timber(put, (sx, sy, -0.2), (sx, sy, fz), 0.16, WOODS[1], pegs=False)
    for i in range(12):
        y = -2.05 + 3.35 * (i + 0.5) / 12
        put(box(3.3, 0.26, 0.07, 0.015), C(bleached[i % 4]), loc=(rng.uniform(-0.03, 0.03), y, fz + 0.03), rot=(0, 0, rng.uniform(-0.01, 0.01)), tint=rng.uniform(0.9, 1.08))
    # striped plank walls
    cy = 0.05
    stripes = ['#8fc4d6', '#f6efdc']

    def wall(x0, y0, x1, y1, skip=None):
        d = Vector((x1 - x0, y1 - y0, 0))
        n = int(round(d.length / 0.2))
        rot = math.atan2(d.y, d.x)
        for i in range(n):
            t = (i + 0.5) / n
            if skip and skip(t):
                continue
            p = Vector((x0, y0, 0)) + d * t
            colr = stripes[i % 2]
            put(box(d.length / n * 0.96, 0.07, Hw, 0.012), C(colr, rough=0.8), mtx=TRS((p.x, p.y, fz + 0.06 + Hw / 2), (0, 0, rot)), tint=rng.uniform(0.9, 1.06))
    hx, hy = W / 2, D / 2
    wall(-hx, cy - hy, hx, cy - hy, lambda t: 0.36 < t < 0.64)
    wall(-hx, cy + hy, hx, cy + hy)
    wall(-hx, cy - hy, -hx, cy + hy)
    wall(hx, cy - hy, hx, cy + hy)
    for sx in (-hx, hx):
        for sy in (cy - hy, cy + hy):
            timber(put, (sx, sy, fz + 0.06), (sx, sy, fz + 0.06 + Hw), 0.12, '#f6efdc', pegs=False)
    # gables (planks cut to the roof line) and roof
    for sy in (cy - hy, cy + hy):
        for i in range(13):
            x = -hx + W * (i + 0.5) / 13
            hh = rise * (1 - abs(x) / hx)
            if hh > 0.05:
                put(box(W / 13 * 0.96, 0.07, hh, 0.01), C(stripes[i % 2], rough=0.8), loc=(x, sy, fz + 0.06 + Hw + hh / 2), tint=rng.uniform(0.9, 1.06))
    tiles_gable(put, W, D, fz + 0.06 + Hw, rise, 0.3, rng, bleached, tw=0.34)
    # door, porthole, porch rail and steps
    Dr = P.put(Matrix.Translation((0, cy - hy, fz + 0.06)))
    door(Dr, 0.7, 1.35, '#e98d78', None, rng)
    Wn = P.put(Rz(PI / 2) @ Matrix.Translation((0, -hx - 0.02, fz + 1.3)))
    Wn(torus(0.26, 0.05, 16, 6), C('#f6efdc'), rot=(PI / 2, 0, 0))
    Wn(cyl(0.24, 0.24, 0.05, 16), glow(), loc=(0, 0.02, 0), rot=(PI / 2, 0, 0))
    for sx in (-1.55, 1.55):
        for sy in (-1.95, -1.25):
            timber(put, (sx, sy, fz), (sx, sy, fz + 0.9), 0.09, '#f6efdc', pegs=False)
        put(tube([(sx, -1.95, fz + 0.82), (sx, -1.6, fz + 0.7), (sx, -1.25, fz + 0.82)], 0.022, 5), C('#cbb98f'))
    put(tube([(-1.55, -1.95, fz + 0.82), (-1.0, -1.95, fz + 0.68), (-0.5, -1.95, fz + 0.82)], 0.022, 5), C('#cbb98f'))
    timber(put, (-0.5, -1.95, fz), (-0.5, -1.95, fz + 0.9), 0.09, '#f6efdc', pegs=False)
    for k in range(2):
        put(box(0.9, 0.3, 0.07, 0.015), C(bleached[k]), loc=(0.55, -2.25 - 0.32 * k, fz - 0.16 - 0.2 * k))
    # life ring, surfboard, bunting, lantern, driftwood, shells
    Lr = P.put(Matrix.Translation((0.82, cy - hy - 0.06, fz + 1.35)))
    for k in range(8):
        seg = torus(0.2, 0.055, 4, 6)
        Lr(tube(arc((0, 0, 0), 0.2, 2 * PI * k / 8, 2 * PI * (k + 1) / 8, 3, 'xz'), 0.055, 6, False), C('#d6604d' if k % 2 else '#f7f5ef'))
        seg.free()
    sb = sphere(1.0, 14, 8)
    put(sb, C('#f2c94c', rough=0.4), mtx=TRS((-1.55, cy + 0.2, fz + 1.05), (0.0, 0.22, 0)) @ Matrix.Diagonal((0.05, 0.26, 1.0, 1)))
    put(box(0.012, 0.05, 1.7), C('#f7f5ef'), mtx=TRS((-1.6, cy + 0.2, fz + 1.05), (0.0, 0.22, 0)))
    flags = ['#e98d78', '#f2c94c', '#8fc4d6', '#f7f5ef', '#9cc77a']
    for i in range(9):
        t = (i + 0.5) / 9
        x = -1.5 + 3.0 * t
        z = fz + 2.25 - 0.28 * math.sin(PI * t)
        put(leaf(0.24, 0.2, 0, 0, 3, 2), C(flags[i % 5], double=True), mtx=TRS((x, cy - hy - 0.34, z), (-PI / 2, 0, 0)), recalc=False)
    put(tube([(-1.5 + 3.0 * t / 8, cy - hy - 0.34, fz + 2.25 - 0.28 * math.sin(PI * t / 8)) for t in range(9)], 0.008, 4), C('#cbb98f'))
    put(cyl(0.012, 0.012, 0.25, 5), C('#4d535a'), loc=(-0.85, cy - hy - 0.2, fz + 1.95))
    lantern_body(put, (-0.85, cy - hy - 0.2, fz + 1.95), 1.0)
    a.anchor('Light', (-0.85, cy - hy - 0.2, fz + 1.7))
    put(tube([(1.9, -1.2, 0.08), (2.3, -0.4, 0.12), (2.5, 0.5, 0.07)], [0.1, 0.085, 0.05], 7), C('#c9bfae'))
    for k in range(6):
        put(lathe([(0, 0), (0.06, 0.01), (0.045, 0.035), (0, 0.045)], 7), C(rng.choice(('#f6d9cf', '#fff4e6', '#f2c1b0'))), loc=(rng.uniform(-2, 2.4), rng.uniform(-2.9, -2.3), 0))
    crate(put, (1.15, -1.5, fz + 0.06), 0.42, 0.3)
    return a


# ------------------------------------------------------------------ waterfall

def waterfall():
    rng = random.Random(121)
    a = Asset('waterfall', 'Rocky cascade 4.3 m tall and 6 m wide falling into a pool at the front. Water and Foam are separate nodes with flow UVs.')
    stones_part(a)
    P = a.part('Rocks')
    put = P.put()
    cols = ['#e2dbcb', '#efe8d8', '#d5cfc0', '#dcdfd2']
    for layer in range(6):
        z = 0.7 * layer
        yb = 0.4 + 0.42 * layer
        cnt = 6 - (layer // 2)
        for i in range(cnt):
            x = -2.6 + 5.2 * (i + 0.5) / cnt + rng.uniform(-0.25, 0.25)
            if abs(x) < 0.75 and layer >= 3:
                zz, sz = z - 0.55, 0.8    # the notch the water runs through
            else:
                zz, sz = z, rng.uniform(1.1, 1.6)
            rock_piece(put, boulder(rng, sz * rng.uniform(1.0, 1.35), sz * rng.uniform(0.9, 1.2), sz * rng.uniform(0.8, 1.1), 20, 0.06, 2),
                       TRS((x, yb + rng.uniform(-0.2, 0.25), zz - 0.2), (rng.uniform(-0.15, 0.15), rng.uniform(-0.15, 0.15), rng.uniform(0, 6))), rng,
                       cols[(i + layer) % 4])
    for i in range(7):   # pool rim
        an = PI + PI * (i + 0.5) / 7
        s = rng.uniform(0.5, 0.9)
        rock_piece(put, boulder(rng, s, s * 0.8, s * 0.5, 14, 0.08, 2), TRS((2.1 * math.cos(an), -0.9 + 1.9 * math.sin(an), -0.05), (0, 0, rng.uniform(0, 6))), rng)
    put(lathe([(2.0, 0.0), (1.6, -0.25), (0, -0.4)], 20), C('#5c8f8a'), loc=(0, -1.0, 0), scale=(1.0, 0.85, 1))
    W = a.raw('Water')
    W.material = water_mat()
    path = [(0, 3.2, 3.48), (0, 2.6, 3.46), (0, 2.25, 3.4), (0, 2.1, 3.0), (0, 2.05, 2.3), (0, 2.0, 1.9), (0, 1.6, 1.86), (0, 1.25, 1.8),
            (0, 1.1, 1.3), (0, 1.05, 0.6), (0, 1.0, 0.06)]
    wd = [0.9, 0.95, 1.0, 1.05, 1.1, 1.15, 1.25, 1.3, 1.35, 1.4, 1.5]
    ribbon(W, path, wd, Vector((1, 0, 0)), white=[0, 0, 0.1, 0.25, 0.3, 0.3, 0.1, 0.15, 0.3, 0.35, 0.4])
    pool = disc(1.95, 24, 0.06, 2.0)
    for fc in pool.faces:
        pts = [Vector((v.co.x, v.co.y * 0.85 - 1.0, 0.05)) for v in fc.verts]
        W.face(pts, [(p.x * 0.25 + 0.5, p.y * 0.25) for p in pts], [(1, 1, 1)] * len(pts), [UP] * len(pts))
    pool.free()
    Fm = a.raw('Foam')
    Fm.material = mat('foam', rough=0.6, alpha=0.9, double=True, color='#f4fbff')
    for i in range(9):
        an = rng.uniform(0, 2 * PI)
        r = rng.uniform(0.1, 0.75)
        c = Vector((r * math.cos(an), 0.75 - abs(r * math.sin(an)) * 0.9, 0.075))
        s = rng.uniform(0.18, 0.34)
        d = disc(s, 9, 0.2, i)
        for fc in d.faces:
            pts = [v.co + c for v in fc.verts]
            Fm.face(pts, [(0.5, 0.5)] * len(pts), [(1, 1, 1)] * len(pts), [UP] * len(pts))
        d.free()
    for (x, y, z) in ((0.0, 1.85, 1.92), (-0.3, 2.05, 3.42)):
        d = disc(0.3, 8, 0.2, x)
        for fc in d.faces:
            pts = [v.co + Vector((x, y, z)) for v in fc.verts]
            Fm.face(pts, [(0.5, 0.5)] * len(pts), [(1, 1, 1)] * len(pts), [UP] * len(pts))
        d.free()
    # greenery on the ledges
    G = a.raw('Greenery')
    for i in range(10):
        x = rng.choice((-1, 1)) * rng.uniform(1.0, 2.6)
        layer = rng.randrange(1, 6)
        base = Vector((x, 0.2 + 0.42 * layer, 0.7 * layer + 0.35))
        fern(G, base, rng, 6, 0.7)
    for i in range(8):
        x = rng.choice((-1, 1)) * rng.uniform(1.2, 2.7)
        layer = rng.randrange(2, 6)
        moss(put, (x, 0.5 + 0.42 * layer, 0.7 * layer + 0.42), 0.7, 0.5, rng)
    for i in range(8):
        an = PI + PI * rng.random()
        grass(put, (2.6 * math.cos(an), -0.9 + 2.4 * math.sin(an), 0), 8, 0.36, rng)
    return a


# ------------------------------------------------------------------ campfire

def campfire():
    rng = random.Random(131)
    a = Asset('campfire', 'Campfire circle 5 m across: stone fire pit, stacked logs, four log seats. Flame is its own node; Light marks the fire.')
    stones_part(a)
    P = a.part('Camp')
    put = P.put()
    put(disc(0.62, 14, 0.1, 1.0), C('#4a4541', rough=1.0), loc=(0, 0, 0.02), recalc=False)
    stones_ring(put, 0.72, 0.0, 1, 0.26, rng, sw=0.4, depth=0.32)
    for k in range(6):
        an = 2 * PI * k / 6
        o = Vector((math.cos(an), math.sin(an), 0))
        lg = tube([o * 0.42 + UP * 0.05, o * 0.05 + UP * 0.52], [0.075, 0.06], 7)
        displace(lg, 0.008, 9, k)
        put(lg, C(WOODS[k % 3], rough=0.95), tint=rng.uniform(0.75, 1.0))
    for k in range(7):
        an = rng.uniform(0, 2 * PI)
        put(block(rng, 0.09, 0.08, 0.06, 0.2, 0.2), C('#ff9a4a', emit=1.0), loc=(0.3 * math.cos(an), 0.3 * math.sin(an), 0.06))
    Fl = a.part('Flame', (0, 0, 0.3))
    for r, h, colr, off in ((0.24, 0.85, '#ff8a3a', (0, 0, 0)), (0.16, 0.62, '#ffc04a', (0.03, -0.02, 0.02)), (0.09, 0.4, '#fff0a8', (-0.01, 0.02, 0.04))):
        fl = lathe([(0, 0), (r * 0.8, h * 0.12), (r, h * 0.3), (r * 0.6, h * 0.62), (r * 0.2, h * 0.88), (0, h)], 9)
        for v in fl.verts:
            t = v.co.z / h
            v.co.x += 0.06 * math.sin(t * 5 + r * 30) * t
            v.co.y += 0.05 * math.cos(t * 4 + r * 20) * t
        Fl.add(fl, C(colr, rough=0.6, emit=1.0), loc=Vector((0, 0, 0.28)) + Vector(off))
    a.anchor('Light', (0, 0, 0.7))
    for k in range(4):   # log seats
        an = 2 * PI * k / 4 + 0.5
        c = Vector((2.0 * math.cos(an), 2.0 * math.sin(an), 0.24))
        tv = Vector((-math.sin(an), math.cos(an), 0))
        ln = rng.uniform(1.3, 1.7)
        lg = tube([c - tv * ln / 2, c - tv * ln / 6 + UP * 0.02, c + tv * ln / 6, c + tv * ln / 2], [0.25, 0.24, 0.25, 0.23], 10)
        displace(lg, 0.02, 4, k)
        put(lg, C(WOODS[1], rough=0.95), tint=rng.uniform(0.9, 1.05))
        for e in (-1, 1):
            put(cyl(0.2, 0.2, 0.02, 10), C('#d9b98a'), mtx=Matrix.Translation(c + tv * e * (ln / 2 + 0.002)) @ align_z(tv * e))
            put(torus(0.11, 0.007, 10, 4), C('#b98f5f'), mtx=Matrix.Translation(c + tv * e * (ln / 2 + 0.022)) @ align_z(tv * e))
        moss(put, c + UP * 0.22 + tv * 0.3, 0.3, 0.2, rng)
    # woodpile, kettle on a flat stone, mug
    for k in range(5):
        put(tube([(2.6, -2.2 + 0.2 * (k % 3) + 0.1 * (k // 3), 0.09 + 0.17 * (k // 3)), (3.3, -2.2 + 0.2 * (k % 3) + 0.1 * (k // 3), 0.09 + 0.17 * (k // 3))], 0.09, 7),
            C(WOODS[k % 3], rough=0.95), tint=rng.uniform(0.85, 1.05))
    stone(put, (1.05, -0.2, 0.05), 0.4, (0.5, 0.42, 0.14), rng)
    put(lathe([(0, 0), (0.11, 0), (0.13, 0.1), (0.09, 0.19), (0.04, 0.21), (0, 0.21)], 10), C('#4d535a', rough=0.4), loc=(1.05, -0.2, 0.12))
    put(tube(arc((1.05, -0.2, 0.3), 0.1, 0, PI, 6, 'xz'), 0.01, 4, False), C('#4d535a', rough=0.4))
    put(tube([(1.16, -0.2, 0.22), (1.26, -0.2, 0.3)], [0.02, 0.012], 5), C('#4d535a', rough=0.4))
    dressing(put, rng, 2.7, 12, 7)
    return a


# ------------------------------------------------------------------ observatory

def observatory():
    rng = random.Random(141)
    a = Asset('observatory', 'Hilltop observatory, 5 m across and 6.6 m tall: stone base, timber-framed drum, turning copper Dome node with a telescope.')
    stones_part(a)
    Sn = snow_part(a)
    P = a.part('Observatory')
    put = P.put()
    wood = C(TIMBER, rough=0.9)
    R = 2.1
    put(cyl(R - 0.02, R - 0.02, 1.55, 28), C('#8f887b'))
    stones_ring(put, R, 0.0, 4, 0.38, rng, sw=0.48, gap=(0.0, 0.33))
    put(cyl(R - 0.08, R - 0.08, 1.9, 28), C(PLASTER, rough=0.95), loc=(0, 0, 1.5))
    put(cyl(R + 0.06, R + 0.06, 0.16, 28), wood, loc=(0, 0, 1.48))
    put(cyl(R + 0.14, R + 0.14, 0.2, 28), wood, loc=(0, 0, 3.32))
    for i in range(12):
        az = 2 * PI * (i + 0.5) / 12
        timber(P.put(ring(R - 0.06, az)), (0, 0, 1.6), (0, 0, 3.36), 0.15)
        if i % 3 == 0:
            az2 = 2 * PI * (i + 1.5) / 12
            timber(put, (R * math.sin(az), -R * math.cos(az), 1.7), (R * math.sin(az2), -R * math.cos(az2), 2.7), 0.11)
    # walkway cornice of stone
    stones_ring(put, R + 0.12, 3.5, 1, 0.24, rng, sw=0.5, depth=0.5, mats=['#cbc5b7', '#d6d0c2', '#bdb6a7'])
    door(P.put(ring(R, 0.0)), 0.95, 1.4, '#6f9aa0', True, rng)
    put(box(1.6, 0.5, 0.14, 0.04), C(STONES[0]), loc=(0, -R - 0.35, 0.07))
    put(box(2.0, 0.5, 0.08, 0.03), C(STONES[1]), loc=(0, -R - 0.7, 0.04))
    for az in (1.2, -1.2, 2.5, -2.5):
        window(P.put(ring(R - 0.07, az, 2.45)), 0.5, 0.62, True, '#7fa0a8', az > 0, rng)
    window(P.put(ring(R - 0.07, 0.0, 2.75)), 0.5, 0.4, True)
    # dome: copper plates between ribs, a slit and a brass telescope
    Dm = a.part('Dome', (0, 0, 3.74))
    dz = 3.74
    Rd, Hd = 2.0, 1.95
    copper = ['#7fb5a5', '#74a898', '#8cc0b0', '#6fa08f']
    segs = 14
    for i in range(segs):
        a0 = 2 * PI * i / segs + PI / 2 + PI / segs
        if i == 0:
            continue   # the open slit, facing front
        for j in range(5):
            e0, e1 = PI / 2 * j / 5, PI / 2 * (j + 1) / 5 * 0.985
            pl = lathe([(Rd * math.cos(e0), Hd * math.sin(e0)), (Rd * math.cos(e1), Hd * math.sin(e1))], 1) if False else None
            a1 = a0 + 2 * PI / segs * 0.94
            pts = []
            import bmesh as _bm
            bmx = _bm.new()
            vs = []
            for (ee, aa) in ((e0, a0), (e0, a1), (e1, a1), (e1, a0)):
                vs.append(bmx.verts.new((Rd * math.cos(ee) * math.cos(aa), Rd * math.cos(ee) * math.sin(aa), Hd * math.sin(ee))))
            bmx.faces.new(vs)
            _bm.ops.solidify(bmx, geom=bmx.faces[:], thickness=0.05)
            Dm.add(bmx, C(copper[(i + j) % 4], rough=0.55), loc=(0, 0, dz), tint=rng.uniform(0.88, 1.08))
    for i in range(segs + 1):
        aa = 2 * PI * i / segs + PI / 2 + PI / segs
        rib = [(Rd * 1.01 * math.cos(e) * math.cos(aa), Rd * 1.01 * math.cos(e) * math.sin(aa), dz + Hd * 1.01 * math.sin(e)) for e in [PI / 2 * k / 8 for k in range(9)]]
        Dm.add(tube(rib, 0.045, 6), C('#4f7f73', rough=0.5))
    Dm.add(torus(Rd + 0.03, 0.09, 28, 6), C('#4f7f73', rough=0.5), loc=(0, 0, dz))
    Dm.add(dome(Rd * 0.96, Hd * 0.96, 20, 6), C('#2f3a40'), loc=(0, 0, dz))
    Dm.add(sphere(0.12, 10, 6), C('#c9a24a', rough=0.35), loc=(0, 0, dz + Hd + 0.08))
    cap = lathe([(Rd * math.cos(t) + 0.1, Hd * math.sin(t) + 0.08) for t in [0.75 + (PI / 2 - 0.75) * k / 5 for k in range(5)]] + [(0, Hd + 0.14)], 20)
    displace(cap, 0.03, 2.0, 1)
    Sn.add(cap, C(SNOW_COL, rough=0.9), loc=(0, 0, dz))
    brass = C('#c9a24a', rough=0.35)
    T = Dm.put(TRS((0, -0.4, dz + 0.7), (-0.75, 0, 0)))
    T(cyl(0.2, 0.17, 1.9, 12), brass, loc=(0, 0, 0), rot=(PI / 2, 0, 0))
    T(cyl(0.24, 0.24, 0.14, 12), C('#8a6f2f', rough=0.4), loc=(0, -1.8, 0), rot=(PI / 2, 0, 0))
    T(cyl(0.12, 0.1, 0.5, 10), brass, loc=(0, 0.45, 0), rot=(PI / 2, 0, 0))
    # weather vane, lantern, ivy, greenery
    Lp = P.put(ring(R, -0.5, 2.0))
    timber(Lp, (0, 0, 0), (0, -0.45, 0), 0.06, '#4d535a', pegs=False)
    lantern_body(Lp, (0, -0.4, -0.03), 1.2)
    a.anchor('Light', tuple(ring(R, -0.5, 1.65) @ Vector((0, -0.4, 0))))
    ivy(put, ring(R, 1.85), [(0.1 * k % 0.5 - 0.2, 0.3 + 0.3 * k) for k in range(10)], rng)
    barrel(put, (1.5, -R - 0.35, 0), 0.8)
    dressing(put, rng, R + 0.45, 12, 8)
    return a


def build_extra():
    for f in (bridge, beach_hut, waterfall, campfire, observatory):
        yield f()
