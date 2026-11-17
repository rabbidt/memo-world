"""Memo's island: locations and props in a cozy miniature-diorama style.

Rounded stone, chunky roof tiles, timber frames, warm plaster, tufty grass and flowers. All original geometry.
Blender space: Z up, front = -Y. Exported as +Y up, front = +Z, origin at ground centre.
"""
import math
import random

from mathutils import Vector, Matrix

import bmesh

from memo_lib import (PI, Asset, lin, sphere, ico, box, cyl, lathe, dome, torus, tube, arc, leaf, disc, prism,
                      displace, blob, align_z, TRS, block, boulder, tile_shape)
from memo_char import C, shade

STONES = ['#b9b2a4', '#a59e90', '#cbc5b7', '#aeb0a0']
TILES_RED = ['#c8674b', '#b9573f', '#d67a58', '#c26f4a']
TILES_BLUE = ['#6f8fa3', '#5f7f95', '#83a1b3', '#7895a0']
TILES_SAGE = ['#7fa58a', '#6c937a', '#93b79b', '#86a67f']
WOODS = ['#8a5d3b', '#7a5236', '#96683f']
TIMBER = '#6b4630'
PLASTER = '#f3e7cf'
GRASS = ['#7fb24f', '#6fa544', '#93c25c']
LEAVES = ['#5c9c48', '#6fae52', '#86bf5e', '#4d8a44']
GLOW = '#ffd98a'
SOIL = '#6a4a35'


def glow():
    return C(GLOW, rough=0.4, emit=1.0)


def Rz(a):
    return Matrix.Rotation(a, 4, 'Z')


def ring(R, az, z=0.0):
    """Local frame on a cylinder wall: origin on the surface, -Y pointing outward."""
    return Rz(az) @ Matrix.Translation((0, -R, z))


# ------------------------------------------------------------------ building blocks



def stones_ring(put, R, z0, rows, rh, rng, sw=0.42, depth=0.34, gap=None, a0=0.0, a1=2 * PI, mats=STONES):
    for row in range(rows):
        n = max(3, int((a1 - a0) * R / sw))
        for i in range(n):
            az = a0 + (a1 - a0) * (i + 0.5 * (row % 2)) / n
            if gap and abs((az - gap[0] + PI) % (2 * PI) - PI) < gap[1]:
                continue
            w = (a1 - a0) * R / n
            stone(put, (R * math.sin(az), -R * math.cos(az), z0 + rh * (row + 0.5)), az,
                  (w * rng.uniform(0.95, 1.12), depth * rng.uniform(0.9, 1.1), rh * rng.uniform(1.0, 1.15)), rng, mats)


def stones_line(put, p0, p1, z0, rows, rh, rng, sw=0.42, depth=0.34, mats=STONES):
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    rot = math.atan2(d.y, d.x)
    for row in range(rows):
        n = max(1, int(d.length / sw))
        for i in range(n + (row % 2)):
            t = (i + 0.5 - 0.5 * (row % 2)) / n
            t = min(max(t, 0.02), 0.98)
            p = p0 + d * t
            stone(put, (p.x, p.y, z0 + rh * (row + 0.5)), rot,
                  (d.length / n * rng.uniform(0.95, 1.12), depth * rng.uniform(0.9, 1.1), rh * rng.uniform(1.0, 1.15)), rng, mats)










def window(put, w=0.5, h=0.7, arched=True, shutters=None, flowerbox=False, rng=None):
    wood = C(TIMBER, rough=0.9)
    put(box(w + 0.16, 0.14, h + 0.16, 0.03), wood)
    put(box(w, 0.17, h), glow())
    if arched:
        put(cyl(w / 2 + 0.08, w / 2 + 0.08, 0.14, 16), wood, loc=(0, 0.07, h / 2), rot=(PI / 2, 0, 0))
        put(cyl(w / 2, w / 2, 0.17, 16), glow(), loc=(0, 0.085, h / 2), rot=(PI / 2, 0, 0))
    put(box(0.05, 0.2, h + (w / 2 if arched else 0)), wood, loc=(0, 0, (w / 4 if arched else 0)))
    put(box(w, 0.2, 0.05), wood, loc=(0, 0, 0.05))
    put(box(w + 0.3, 0.26, 0.08, 0.02), wood, loc=(0, -0.06, -h / 2 - 0.1))
    if shutters:
        for s in (1, -1):
            put(box(w * 0.5, 0.06, h + 0.06, 0.015), C(shutters), loc=(s * (w * 0.78 + 0.08), -0.03, 0))
            put(box(w * 0.4, 0.07, 0.04), C(shade(shutters, 0.8)), loc=(s * (w * 0.78 + 0.08), -0.04, h * 0.25))
            put(box(w * 0.4, 0.07, 0.04), C(shade(shutters, 0.8)), loc=(s * (w * 0.78 + 0.08), -0.04, -h * 0.25))
    if flowerbox and rng:
        put(box(w + 0.24, 0.22, 0.16, 0.03), C('#7a5236'), loc=(0, -0.2, -h / 2 - 0.2))
        cols = ['#f2a0a8', '#f7f1e3', '#f2c94c', '#e98d78']
        for i in range(5):
            x = (i - 2) * (w + 0.1) / 5
            put(blob(0.07, 1, 0.2, 2, i), C(LEAVES[i % 3]), loc=(x, -0.2, -h / 2 - 0.1))
            put(sphere(0.045, 6, 4), C(rng.choice(cols)), loc=(x + 0.02, -0.24, -h / 2 - 0.03))


def door(put, w=0.9, h=1.5, col='#7fa0a8', arch_stones=None, rng=None):
    """Arched plank door; origin at ground level on the wall surface."""
    wood = C(TIMBER, rough=0.9)
    put(box(w + 0.2, 0.16, h, 0.03), wood, loc=(0, 0, h / 2))
    put(cyl(w / 2 + 0.1, w / 2 + 0.1, 0.16, 20), wood, loc=(0, 0.08, h), rot=(PI / 2, 0, 0))
    n = 5
    for i in range(n):
        x = -w / 2 + w * (i + 0.5) / n
        hh = h + math.sqrt(max(0.0, (w / 2) ** 2 - x * x)) * 0.98
        put(box(w / n * 0.94, 0.2, hh - 0.04, 0.015), C(shade(col, 1.0 - 0.06 * (i % 2)), rough=0.85), loc=(x, -0.01, hh / 2))
        if rng:
            grain(put, x, hh / 2, w / n * 0.8, hh * 0.8, -0.112, rng, col, True, 2)
    for zz in (h * 0.3, h * 0.85):
        put(box(w * 0.92, 0.23, 0.07, 0.01), C('#4d535a', rough=0.5), loc=(0, -0.01, zz))
    put(sphere(0.055, 8, 6), C('#c9a24a', rough=0.35), loc=(w * 0.3, -0.14, h * 0.55))
    if arch_stones and rng:
        r = w / 2 + 0.24
        for i in range(9):
            a = PI * i / 8
            stone(put, (r * math.cos(a), -0.02, h + r * math.sin(a)), 0, (0.3, 0.3, 0.3), rng)
        for s in (1, -1):
            for k in range(int(h / 0.3)):
                stone(put, (s * r, -0.02, 0.15 + k * 0.3), 0, (0.3, 0.3, 0.32), rng)


def flower(put, loc, col, h=0.3, rng=None, centre='#f2c94c'):
    loc = Vector(loc)
    lean = Vector((rng.uniform(-0.05, 0.05), rng.uniform(-0.05, 0.05), 0)) if rng else Vector()
    tip = loc + Vector((0, 0, h)) + lean
    put(tube([loc, (loc + tip) / 2 + lean * 0.3, tip], 0.012, 4), C('#5c9c48'))
    for i in range(5):
        a = 2 * PI * i / 5
        put(sphere(1.0, 5, 3), C(col), loc=tip + Vector((0.04 * math.cos(a), 0.04 * math.sin(a), 0.0)), rot=(0, 0, a),
            scale=(0.036, 0.026, 0.012))
    put(sphere(1.0, 5, 3), C(centre), loc=tip + Vector((0, 0, 0.008)), scale=(0.022, 0.022, 0.016))
    put(leaf(h * 0.55, h * 0.2, 0.3, 0.2, 4, 2), C('#6fae52', double=True),
        mtx=TRS(loc, (0, 0, rng.uniform(0, 6.28) if rng else 0)) @ TRS(rot=(0.9, 0, 0)), recalc=False)


def grass(put, loc, n=9, h=0.3, rng=None, spread=0.08):
    for i in range(n):
        a = rng.uniform(0, 2 * PI)
        r = rng.uniform(0, spread)
        hh = h * rng.uniform(0.6, 1.1)
        put(leaf(hh, hh * 0.2, bend=rng.uniform(0.05, 0.35), fold=0.35, nu=4, nv=2), C(rng.choice(GRASS), rough=0.8, double=True),
            mtx=TRS(Vector(loc) + Vector((r * math.cos(a), r * math.sin(a), 0)), (0, 0, a)) @ TRS(rot=(1.25, 0, 0)), recalc=False)


def mushroom(put, loc, s=1.0, col='#d9614f', spots=True, rng=None):
    loc = Vector(loc)
    put(lathe([(0, 0), (0.05 * s, 0), (0.04 * s, 0.1 * s), (0.035 * s, 0.17 * s), (0, 0.17 * s)], 8), C('#f3ead8'), loc=loc)
    prof = [(0, 0.15 * s), (0.11 * s, 0.14 * s)] + [(0.12 * s * math.cos(t), (0.15 + 0.09 * math.sin(t)) * s) for t in (0.2, 0.6, 1.0, 1.35)] + [(0, 0.245 * s)]
    put(lathe(prof, 10), C(col, rough=0.6), loc=loc)
    if spots:
        for i in range(4):
            a = 2 * PI * i / 4 + 0.4
            put(sphere(1.0, 5, 3), C('#fff6ea'), loc=loc + Vector((0.07 * s * math.cos(a), 0.07 * s * math.sin(a), 0.215 * s)),
                scale=(0.02 * s, 0.02 * s, 0.008 * s))


def lantern_body(put, loc, s=1.0):
    """Hanging lantern, origin at its top ring."""
    loc = Vector(loc)
    iron = C('#4d535a', rough=0.5)
    put(torus(0.03 * s, 0.008 * s, 10, 5), iron, loc=loc, rot=(PI / 2, 0, 0))
    put(cyl(0.11 * s, 0.03 * s, 0.09 * s, 8), iron, loc=loc - Vector((0, 0, 0.12 * s)))
    put(box(0.15 * s, 0.15 * s, 0.2 * s, 0.03 * s), glow(), loc=loc - Vector((0, 0, 0.22 * s)))
    for sx in (1, -1):
        for sy in (1, -1):
            put(box(0.02 * s, 0.02 * s, 0.22 * s), iron, loc=loc + Vector((sx * 0.075 * s, sy * 0.075 * s, -0.22 * s)))
    put(box(0.19 * s, 0.19 * s, 0.035 * s, 0.01 * s), iron, loc=loc - Vector((0, 0, 0.335 * s)))


def book(put, loc, rotz, size=(0.2, 0.28, 0.05), col='#8f3d2f'):
    w, d, h = size
    put(box(w, d, h, 0.006), C(col, rough=0.7), mtx=TRS(loc, (0, 0, rotz)))
    put(box(w * 0.94, d * 0.96, h * 0.7), C('#f6efdc'), mtx=TRS(loc, (0, 0, rotz)) @ Matrix.Translation((w * 0.04, 0, 0)))


def barrel(put, loc, s=1.0):
    loc = Vector(loc)
    put(lathe([(0, 0), (0.26, 0), (0.32, 0.22), (0.335, 0.4), (0.32, 0.58), (0.26, 0.8), (0.22, 0.8), (0.22, 0.76), (0, 0.76)], 14),
        C(WOODS[0]), loc=loc, scale=s)
    for z in (0.16, 0.64):
        put(torus(0.305, 0.022, 14, 5), C('#4d535a', rough=0.5), loc=loc + Vector((0, 0, z * s)), scale=s)


def crate(put, loc, s=0.6, rotz=0.0):
    M = TRS(loc, (0, 0, rotz))
    put(box(s * 0.94, s * 0.94, s * 0.94, 0.01), C(WOODS[2]), mtx=M @ Matrix.Translation((0, 0, s / 2)))
    t = s * 0.1
    dark = C(WOODS[1])
    for sx in (1, -1):
        for sy in (1, -1):
            put(box(t, t, s, 0.008), dark, mtx=M @ Matrix.Translation((sx * (s - t) / 2, sy * (s - t) / 2, s / 2)))
        for zz in (t / 2, s - t / 2):
            put(box(t, s, t, 0.008), dark, mtx=M @ Matrix.Translation((sx * (s - t) / 2, 0, zz)))
            put(box(s, t, t, 0.008), dark, mtx=M @ Matrix.Translation((0, sx * (s - t) / 2, zz)))


def ivy(put, base, pts, rng):
    for p in pts:
        for k in range(3):
            put(leaf(0.16, 0.13, -0.2, 0.2, 4, 2), C(rng.choice(LEAVES[:3]), double=True),
                mtx=base @ TRS((p[0] + rng.uniform(-0.08, 0.08), -0.03, p[1] + rng.uniform(-0.08, 0.08)),
                               (PI / 2 + rng.uniform(-0.3, 0.3), 0, rng.uniform(-PI, PI))), recalc=False)


def dressing(put, rng, R, n_grass=6, n_flowers=4, cols=('#f2a0a8', '#f7f1e3', '#f2c94c')):
    """Tufts and flowers around the foot of something of radius R."""
    for i in range(n_grass):
        a = rng.uniform(0, 2 * PI)
        r = R * rng.uniform(0.95, 1.12)
        grass(put, (r * math.cos(a), r * math.sin(a), 0), 7, rng.uniform(0.22, 0.38), rng)
    for i in range(n_flowers):
        a = rng.uniform(0, 2 * PI)
        r = R * rng.uniform(0.98, 1.15)
        flower(put, (r * math.cos(a), r * math.sin(a), 0), rng.choice(cols), rng.uniform(0.22, 0.34), rng)


# ------------------------------------------------------------------ locations

def library_tower():
    rng = random.Random(11)
    a = Asset('library_tower', 'Round stone-and-timber library tower, 3.7 m across at the roof line, 6.2 m tall. Door faces front.')
    stones_part(a)
    snow_part(a)
    P = a.part('Tower')
    put = P.put()
    wood = C(TIMBER, rough=0.9)
    put(cyl(1.5, 1.5, 1.15, 28), C('#8f887b'))
    stones_ring(put, 1.52, 0.0, 3, 0.37, rng, sw=0.46, gap=(0.0, 0.42))
    put(cyl(1.46, 1.46, 2.4, 28), C(PLASTER, rough=0.95), loc=(0, 0, 1.1))
    put(cyl(1.56, 1.56, 0.16, 28), wood, loc=(0, 0, 1.08))
    put(cyl(1.62, 1.62, 0.18, 28), wood, loc=(0, 0, 3.32))
    put(cyl(1.6, 1.64, 0.62, 28), C(PLASTER, rough=0.95), loc=(0, 0, 3.48))
    put(cyl(1.7, 1.7, 0.14, 28), wood, loc=(0, 0, 4.04))
    for i in range(10):
        az = 2 * PI * (i + 0.5) / 10
        M = ring(1.47, az)
        timber(P.put(M), (0, 0, 1.2), (0, 0, 3.36), 0.15)
        if i % 2 == 0:
            az2 = 2 * PI * (i + 1.5) / 10
            p0 = Vector((1.5 * math.sin(az), -1.5 * math.cos(az), 1.3))
            p1 = Vector((1.5 * math.sin(az2), -1.5 * math.cos(az2), 2.2))
            timber(put, p0, p1, 0.11)
        timber(P.put(ring(1.63, az)), (0, 0, 3.48), (0, 0, 4.08), 0.12)
    tiles_cone(put, 2.12, 4.1, 1.95, 7, rng, TILES_RED, flare=1.22)
    put(sphere(0.12, 10, 8), C('#c9a24a', rough=0.35), loc=(0, 0, 6.1))
    put(cyl(0.05, 0.03, 0.14, 8), C('#c9a24a', rough=0.35), loc=(0, 0, 5.95))
    # door + stone arch, steps
    door(P.put(ring(1.5, 0.0)), 0.9, 1.35, '#6f9aa0', True, rng)
    put(box(1.5, 0.5, 0.14, 0.04), C(STONES[0]), loc=(0, -1.85, 0.07))
    put(box(1.9, 0.5, 0.08, 0.03), C(STONES[1]), loc=(0, -2.2, 0.04))
    # windows
    for az, z in ((1.25, 2.2), (-1.25, 2.2), (2.6, 2.2), (-2.6, 2.2)):
        window(P.put(ring(1.47, az, z)), 0.5, 0.62, True, '#7fa0a8', True, rng)
    window(P.put(ring(1.47, 0.0, 2.55)), 0.55, 0.5, True, None, False, rng)
    for az in (0.9, -0.9, PI):
        window(P.put(ring(1.63, az, 3.76)), 0.34, 0.26, False)
    # hanging book sign + lantern by the door
    S = P.put(ring(1.5, 0.62, 1.95))
    timber(S, (0, 0, 0), (0, -0.6, 0), 0.07)
    S(box(0.42, 0.05, 0.34, 0.02), C(WOODS[2]), loc=(0, -0.38, -0.24))
    S(box(0.14, 0.07, 0.2, 0.01), C('#f6efdc'), loc=(-0.075, -0.38, -0.24), rot=(0, 0.12, 0))
    S(box(0.14, 0.07, 0.2, 0.01), C('#f6efdc'), loc=(0.075, -0.38, -0.24), rot=(0, -0.12, 0))
    Lp = P.put(ring(1.5, -0.62, 1.95))
    timber(Lp, (0, 0, 0), (0, -0.45, 0), 0.06, '#4d535a')
    lantern_body(Lp, (0, -0.4, -0.03), 1.2)
    a.anchor('Light', tuple(ring(1.5, -0.62, 1.6) @ Vector((0, -0.4, 0))))
    # ivy, books, barrel, greenery
    ivy(put, ring(1.5, 1.95), [(0.1 * k % 0.5 - 0.2, 0.3 + 0.28 * k) for k in range(10)], rng)
    ivy(put, ring(1.5, 2.2), [(0, 0.3 + 0.3 * k) for k in range(6)], rng)
    for k, colr in enumerate(('#8f3d2f', '#3d5f8f', '#4c7a4a', '#c9a24a')):
        book(put, (1.05 + 0.02 * k, -1.75, 0.035 + 0.062 * k), 0.3 * k - 0.4, (0.3, 0.4, 0.06), colr)
    barrel(put, (-1.25, -1.6, 0), 0.8)
    dressing(put, rng, 1.95, 10, 7)
    return a


def workshop_hut():
    rng = random.Random(23)
    a = Asset('workshop_hut', 'Open-fronted timber workshop, 4.4 x 3.6 m, 3.8 m tall, with bench, tools, anvil and lantern.')
    stones_part(a)
    snow_part(a)
    P = a.part('Hut')
    put = P.put()
    W, D, Hp, rise = 4.4, 3.6, 2.2, 1.35
    hx, hy = W / 2 - 0.2, D / 2 - 0.2
    # cobbled floor
    put(box(W - 0.1, D - 0.1, 0.1, 0.03), C('#a59e90'), loc=(0, 0, 0.03))
    for i in range(26):
        x, y = rng.uniform(-hx, hx), rng.uniform(-hy, hy)
        stone(put, (x, y, 0.07), rng.uniform(0, 3), (rng.uniform(0.4, 0.6), rng.uniform(0.35, 0.5), 0.1), rng)
    # low stone walls: back and sides
    stones_line(put, (-hx, hy, 0), (hx, hy, 0), 0.05, 3, 0.3, rng)
    for s in (1, -1):
        stones_line(put, (s * hx, hy, 0), (s * hx, -hy * 0.2, 0), 0.05, 3, 0.3, rng)
    # posts and beams
    for s in (1, -1):
        for y in (-hy, hy):
            timber(put, (s * hx, y, 0.05), (s * hx, y, Hp), 0.22)
        timber(put, (s * hx, -hy - 0.25, Hp), (s * hx, hy + 0.25, Hp), 0.2)
        timber(put, (s * hx, -hy, Hp - 0.6), (s * hx, -hy + 0.6, Hp), 0.12)
        timber(put, (s * hx, hy, Hp - 0.6), (s * hx, hy - 0.6, Hp), 0.12)
        # gable truss
        timber(put, (s * hx, 0, Hp), (s * hx, 0, Hp + rise - 0.1), 0.16)
        timber(put, (s * hx, -hy * 0.55, Hp + 0.05), (s * hx, 0, Hp + rise * 0.6), 0.1)
        timber(put, (s * hx, hy * 0.55, Hp + 0.05), (s * hx, 0, Hp + rise * 0.6), 0.1)
    for y in (-hy, hy):
        timber(put, (-hx - 0.25, y, Hp), (hx + 0.25, y, Hp), 0.2)
    timber(put, (-hx, -hy, Hp - 0.55), (-hx + 0.55, -hy, Hp), 0.12)
    timber(put, (hx, -hy, Hp - 0.55), (hx - 0.55, -hy, Hp), 0.12)
    timber(put, (0, hy, 0.9), (0, hy, Hp), 0.18)
    # back wall above the stones: plaster panels and a tool board
    put(box(W - 0.5, 0.1, Hp - 0.95, 0.02), C(PLASTER, rough=0.95), loc=(0, hy + 0.02, 0.95 + (Hp - 0.95) / 2))
    put(box(1.5, 0.06, 0.8, 0.02), C(WOODS[2]), loc=(-1.0, hy - 0.08, 1.6))
    iron = C('#8d949c', rough=0.4, )
    put(box(0.05, 0.05, 0.5), C(WOODS[1]), loc=(-1.5, hy - 0.13, 1.6))
    put(box(0.22, 0.07, 0.12, 0.02), iron, loc=(-1.5, hy - 0.13, 1.86))
    put(torus(0.13, 0.03, 12, 5), iron, loc=(-1.05, hy - 0.13, 1.68), rot=(PI / 2, 0, 0))
    put(box(0.07, 0.05, 0.55), iron, loc=(-0.62, hy - 0.13, 1.6), rot=(0, 0.2, 0))
    window(P.put(Matrix.Translation((1.05, hy - 0.04, 1.6))), 0.6, 0.55, True)
    # roof: ridge along X
    tiles_gable(P.put(Rz(PI / 2)), D, W, Hp + 0.08, rise, 0.42, rng, TILES_BLUE)
    # chimney pipe
    put(cyl(0.11, 0.11, 0.9, 10), C('#4d535a', rough=0.5), loc=(1.3, 0.9, Hp + 0.75))
    put(cyl(0.2, 0.05, 0.14, 10), C('#4d535a', rough=0.5), loc=(1.3, 0.9, Hp + 1.68))
    # workbench along the back
    bz = 0.85
    put(box(2.0, 0.7, 0.09, 0.02), C(WOODS[0]), loc=(-0.9, hy - 0.62, bz))
    for sx in (-1.8, 0.0):
        for sy in (hy - 0.9, hy - 0.36):
            timber(put, (sx, sy, 0.08), (sx, sy, bz), 0.1, WOODS[1])
    put(box(1.9, 0.5, 0.05, 0.01), C(WOODS[1]), loc=(-0.9, hy - 0.62, 0.3))
    put(box(0.2, 0.16, 0.16, 0.02), iron, loc=(-0.2, hy - 0.86, bz + 0.12))
    put(cyl(0.02, 0.02, 0.3, 6), iron, loc=(-0.2, hy - 1.05, bz + 0.12), rot=(-PI / 2, 0, 0))
    put(cyl(0.02, 0.02, 0.36, 6), C(WOODS[2]), loc=(-1.5, hy - 0.72, bz + 0.07), rot=(0, PI / 2, 0.4))
    put(box(0.09, 0.2, 0.09, 0.015), iron, mtx=TRS((-1.19, hy - 0.59, bz + 0.07), (0, 0, 0.4)))
    for k, (gx, gr) in enumerate(((-0.95, 0.13), (-0.72, 0.09))):
        put(cyl(gr, gr, 0.04, 12), C('#c9a24a', rough=0.4), loc=(gx, hy - 0.55 - 0.1 * k, bz + 0.045))
        for t in range(8):
            an = 2 * PI * t / 8
            put(box(gr * 0.4, gr * 0.3, 0.04), C('#c9a24a', rough=0.4),
                mtx=TRS((gx + gr * math.cos(an), hy - 0.55 - 0.1 * k + gr * math.sin(an), bz + 0.065), (0, 0, an)))
    # anvil on a stump, crate, barrel
    put(lathe([(0, 0), (0.3, 0), (0.27, 0.45), (0, 0.45)], 12), C(WOODS[1]), loc=(1.2, -0.5, 0.06))
    put(box(0.5, 0.2, 0.14, 0.03), C('#4d535a', rough=0.4), loc=(1.2, -0.5, 0.62))
    put(box(0.26, 0.16, 0.12, 0.02), C('#4d535a', rough=0.4), loc=(1.2, -0.5, 0.53))
    put(cyl(0.09, 0.02, 0.24, 8), C('#4d535a', rough=0.4), loc=(1.44, -0.5, 0.62), rot=(0, PI / 2, 0))
    crate(put, (1.45, 0.95, 0.06), 0.6, 0.2)
    crate(put, (1.4, 0.9, 0.66), 0.42, -0.3)
    barrel(put, (0.55, 1.05, 0.06), 0.85)
    # gear sign and hanging lantern on the front beam
    put(cyl(0.3, 0.3, 0.07, 14), C('#c9a24a', rough=0.4), loc=(0, -hy - 0.14, Hp - 0.5), rot=(PI / 2, 0, 0))
    for t in range(10):
        an = 2 * PI * t / 10
        put(box(0.11, 0.07, 0.1, 0.01), C('#c9a24a', rough=0.4),
            mtx=TRS((0.32 * math.cos(an), -hy - 0.175, Hp - 0.5 + 0.32 * math.sin(an)), (0, -an + PI / 2, 0)))
    put(cyl(0.1, 0.1, 0.09, 10), C(TIMBER), loc=(0, -hy - 0.15, Hp - 0.5), rot=(PI / 2, 0, 0))
    put(cyl(0.012, 0.012, 0.3, 5), C('#4d535a'), loc=(-1.2, -hy, Hp - 0.4))
    lantern_body(put, (-1.2, -hy, Hp - 0.4), 1.2)
    a.anchor('Light', (-1.2, -hy, Hp - 0.7))
    dressing(P.put(Matrix.Diagonal((1.25, 1.05, 1, 1))), rng, 2.05, 9, 5, ('#f7f1e3', '#f2c94c', '#9ab8e6'))
    return a


def burrow():
    rng = random.Random(31)
    a = Asset('burrow', "Memo's den: a turf mound 5.2 m across and 2.2 m tall with a stone front, round door and chimney.")
    stones_part(a)
    snow_part(a)
    P = a.part('Burrow')
    put = P.put()
    R, H = 2.55, 2.0
    m = dome(R, H, 40, 12)
    displace(m, 0.26, 0.55, 2.0)
    displace(m, 0.07, 2.4, 5.0)
    put(m, C('#6fa84c', rough=0.95))
    Tf = a.raw('Turf')
    turf_cards(Tf, rng, R * 1.02, H * 1.03, 420, lambda p: p.y < -1.5 and abs(p.x) < 1.7 and p.z < 2.0)
    # stone front
    fy = -2.6
    put(cyl(1.28, 1.28, 1.6, 24), C('#8f887b'), loc=(0, fy + 1.55, 0.92), rot=(PI / 2, 0, 0))
    put(cyl(1.5, 1.5, 1.2, 24), C('#7db356', rough=0.95), loc=(0, fy + 1.6, 0.9), rot=(PI / 2, 0, 0))
    F = P.put(Matrix.Translation((0, fy, 0)))
    for i in range(15):
        an = -0.25 + (PI + 0.5) * i / 14
        stone(F, (1.2 * math.cos(an), -0.02, 0.92 + 1.2 * math.sin(an)), 0, (0.42, 0.5, 0.42), rng)
    for i in range(9):
        an = -0.15 + (PI + 0.3) * i / 8
        stone(F, (0.86 * math.cos(an), -0.06, 0.92 + 0.86 * math.sin(an)), 0, (0.36, 0.4, 0.36), rng, ['#cbc5b7', '#d6d0c2'])
    # round door
    F(cyl(0.7, 0.7, 0.12, 24), C(TIMBER), loc=(0, -0.1, 0.82), rot=(PI / 2, 0, 0))
    for i in range(6):
        x = -0.62 + 1.24 * (i + 0.5) / 6
        hh = 2 * math.sqrt(max(0.01, 0.64 ** 2 - x * x))
        F(box(1.24 / 6 * 0.93, 0.1, hh, 0.015), C(shade('#6f9aa0', 1.0 - 0.06 * (i % 2))), loc=(x, -0.22, 0.82))
        grain(F, x, 0.82, 0.16, hh * 0.8, -0.272, rng, '#6f9aa0', True, 2)
    F(torus(0.66, 0.045, 24, 6), C('#4d535a', rough=0.5), loc=(0, -0.24, 0.82), rot=(PI / 2, 0, 0))
    F(sphere(0.07, 8, 6), C('#c9a24a', rough=0.35), loc=(0, -0.3, 0.82))
    F(box(1.5, 0.6, 0.12, 0.04), C(STONES[0]), loc=(0, -0.42, 0.06))
    # eyebrow roof over the door
    tiles_gable(P.put(Matrix.Translation((0, fy - 0.12, 0))), 2.3, 0.75, 1.95, 0.62, 0.22, rng, TILES_SAGE)
    for s in (1, -1):
        timber(put, (s * 1.25, fy - 0.42, 0.0), (s * 1.25, fy - 0.42, 1.95), 0.15)
        timber(put, (s * 1.25, fy - 0.42, 1.5), (s * 0.8, fy - 0.42, 1.95), 0.1)
    timber(put, (-1.4, fy - 0.42, 1.98), (1.4, fy - 0.42, 1.98), 0.14)
    # round windows either side
    for s in (1, -1):
        az = s * 0.95
        Wn = P.put(Rz(az) @ Matrix.Translation((0, -2.38, 0.95)) @ TRS(rot=(-0.3, 0, 0)))
        Wn(cyl(0.36, 0.36, 0.5, 16), C('#8f887b'), loc=(0, 0.35, 0), rot=(PI / 2, 0, 0))
        Wn(cyl(0.26, 0.26, 0.06, 16), glow(), loc=(0, -0.13, 0), rot=(PI / 2, 0, 0))
        Wn(box(0.05, 0.08, 0.52), C(TIMBER), loc=(0, -0.2, 0))
        Wn(box(0.52, 0.08, 0.05), C(TIMBER), loc=(0, -0.2, 0))
        for i in range(10):
            an = 2 * PI * i / 10
            stone(Wn, (0.34 * math.cos(an), -0.14, 0.34 * math.sin(an)), 0, (0.22, 0.26, 0.22), rng)
    # chimney
    Cx, Cy = 0.9, 0.7
    put(cyl(0.3, 0.26, 1.0, 12), C('#8f887b'), loc=(Cx, Cy, 1.55))
    stones_ring(P.put(Matrix.Translation((Cx, Cy, 0))), 0.31, 1.75, 3, 0.26, rng, sw=0.3, depth=0.24)
    put(cyl(0.4, 0.4, 0.08, 12), C(STONES[2]), loc=(Cx, Cy, 2.52))
    put(cyl(0.14, 0.11, 0.3, 10), C(TILES_RED[0]), loc=(Cx, Cy, 2.6))
    # lantern post, stepping stones, greenery
    timber(put, (2.0, -3.3, 0), (2.0, -3.3, 1.5), 0.12)
    timber(put, (2.0, -3.3, 1.42), (1.65, -3.3, 1.42), 0.07)
    lantern_body(put, (1.68, -3.3, 1.38), 1.2)
    a.anchor('Light', (1.68, -3.3, 1.1))
    for i in range(4):
        stone(put, (rng.uniform(-0.15, 0.15), -3.7 - 0.55 * i, 0.03), rng.uniform(0, 3), (0.6, 0.5, 0.1), rng)
    for i in range(14):
        az, el = rng.uniform(0, 2 * PI), rng.uniform(0.2, 1.2)
        p = Vector((R * math.cos(el) * math.cos(az), R * math.cos(el) * math.sin(az), H * math.sin(el)))
        if p.y < -1.3 and abs(p.x) < 1.6:
            continue
        (flower if i % 2 else grass)(put, p * 0.99, *((rng.choice(('#f7f1e3', '#f2a0a8', '#f2c94c')), 0.3, rng) if i % 2 else (8, 0.32, rng)))
    mushroom(put, (-2.0, -2.9, 0), 1.6, rng=rng)
    mushroom(put, (-2.25, -2.7, 0), 1.1, '#d9903f', False, rng)
    dressing(put, rng, 2.7, 12, 8)
    return a


def notice_board():
    rng = random.Random(41)
    a = Asset('notice_board', 'Timber notice board with a tiled roof, 2.9 m wide and 2.5 m tall, with pinned notes.')
    stones_part(a)
    snow_part(a)
    P = a.part('Board')
    put = P.put()
    for s in (1, -1):
        timber(put, (s * 1.05, 0, 0), (s * 1.05, 0, 2.0), 0.18)
        timber(put, (s * 1.05, 0, 1.55), (s * 0.65, 0, 1.95), 0.09)
        for i in range(5):
            an = 2 * PI * i / 5
            stone(put, (s * 1.05 + 0.2 * math.cos(an), 0.2 * math.sin(an), 0.1), an, (0.3, 0.26, 0.24), rng)
    timber(put, (-1.25, 0, 1.98), (1.25, 0, 1.98), 0.14)
    for i in range(5):
        put(box(1.9, 0.07, 0.215, 0.012), C(WOODS[i % 3]), loc=(0, 0, 0.7 + 0.225 * i), tint=rng.uniform(0.9, 1.08))
        grain(put, 0, 0.7 + 0.225 * i, 1.8, 0.16, -0.037, rng, WOODS[i % 3], False, 4)
    put(box(2.0, 0.1, 0.08, 0.02), C(TIMBER), loc=(0, 0, 0.56))
    put(box(2.0, 0.1, 0.08, 0.02), C(TIMBER), loc=(0, 0, 1.82))
    tiles_gable(P.put(Rz(PI / 2)), 0.9, 2.5, 2.05, 0.4, 0.2, rng, TILES_RED)
    notes = [(-0.62, 1.45, '#f6efdc', 0.06), (-0.15, 1.5, '#f6e3a6', -0.05), (0.38, 1.42, '#f6efdc', 0.03),
             (0.72, 1.05, '#d6e8d0', -0.08), (-0.45, 0.98, '#f3d4d0', 0.04), (0.1, 1.0, '#f6efdc', -0.02)]
    pins = ['#d0463b', '#5b8fd6', '#f2c94c', '#4c7a4a']
    N = a.part('Notes')
    for i, (x, z, colr, rot) in enumerate(notes):
        w, h = rng.uniform(0.3, 0.4), rng.uniform(0.32, 0.42)
        N.add(box(w, 0.012, h), C(colr), mtx=TRS((x, -0.045, z), (0.04, rot, 0)))
        for k in range(3):
            N.add(box(w * 0.7, 0.014, 0.012), C('#8a8578'), mtx=TRS((x, -0.05, z + h * 0.2 - 0.07 * k), (0.04, rot, 0)))
        N.add(sphere(0.022, 6, 4), C(pins[i % 4], rough=0.4), loc=(x, -0.06, z + h * 0.42))
    put(cyl(0.012, 0.012, 0.28, 5), C('#4d535a'), loc=(1.2, -0.02, 1.62))
    lantern_body(put, (1.2, -0.02, 1.62), 1.0)
    a.anchor('Light', (1.2, -0.05, 1.4))
    dressing(P.put(Matrix.Diagonal((1.0, 0.35, 1, 1))), rng, 1.25, 8, 7)
    return a


def pond():
    rng = random.Random(53)
    a = Asset('pond', 'Pond with a 4.6 m water radius, stone bank, lily pads, reeds and a small jetty. Water is its own node.')
    stones_part(a)
    R = 4.6
    Wt = a.part('Water')
    w = disc(R * 0.99, 40, 0.08, 3.0)
    Wt.add(w, C('#6fb7cf', rough=0.08), loc=(0, 0, 0.04), recalc=False)
    P = a.part('Pond')
    put = P.put()

    def rim(an):
        from mathutils import noise
        return R * (1 + 0.08 * noise.noise(Vector((math.cos(an) * 1.3, math.sin(an) * 1.3, 3.0))))
    bed = lathe([(R * 1.02, 0.0), (R * 0.8, -0.3), (R * 0.4, -0.55), (0, -0.6)], 40)
    put(bed, C('#5c8f8a'))
    n = 54
    for i in range(n):
        an = 2 * PI * i / n + rng.uniform(-0.03, 0.03)
        r = rim(an) + rng.uniform(-0.05, 0.12)
        s = rng.uniform(0.45, 0.8)
        stone(put, (r * math.cos(an), r * math.sin(an), 0.08), an + PI / 2, (s, s * 0.75, s * 0.5), rng)
        if i % 3 == 0:
            r2 = r + rng.uniform(0.35, 0.5)
            stone(put, (r2 * math.cos(an + 0.05), r2 * math.sin(an + 0.05), 0.05), an, (0.4, 0.34, 0.24), rng)
    # lily pads, lotus, frog
    pads = []
    for i in range(11):
        an, r = rng.uniform(0, 2 * PI), rng.uniform(0.8, R * 0.78)
        p = Vector((r * math.cos(an), r * math.sin(an), 0.06))
        if any((p - q).length < 0.9 for q in pads):
            continue
        pads.append(p)
        s = rng.uniform(0.32, 0.5)
        put(disc(s, 12, 0.0, 0.0, 0.5), C(rng.choice(['#5c9c48', '#6fae52', '#4d8a44']), rough=0.5, double=True),
            mtx=TRS(p, (0, 0, rng.uniform(0, 6.28))), recalc=False)
        if len(pads) % 3 == 1:
            for ringk, (pr, tilt, colr) in enumerate(((0.13, 0.5, '#f6c1cf'), (0.09, 1.0, '#fbe3ea'))):
                for k in range(6):
                    ak = 2 * PI * k / 6 + ringk * 0.5
                    put(leaf(pr * 1.6, pr * 0.9, 0.3, 0.3, 4, 2), C(colr, double=True),
                        mtx=TRS(p + Vector((0.02, 0.02, 0.02)), (0, 0, ak)) @ TRS(rot=(tilt, 0, 0)), recalc=False)
            put(sphere(0.035, 6, 4), C('#f2c94c'), loc=p + Vector((0.02, 0.02, 0.07)))
    fp = pads[1] if len(pads) > 1 else Vector((1, 1, 0.06))
    put(sphere(1.0, 10, 6), C('#7fb24f'), loc=fp + Vector((0, 0, 0.07)), scale=(0.11, 0.13, 0.08))
    for s in (1, -1):
        put(sphere(0.035, 6, 4), C('#7fb24f'), loc=fp + Vector((s * 0.055, -0.07, 0.14)))
        put(sphere(0.018, 5, 3), C('#17171c', rough=0.2), loc=fp + Vector((s * 0.06, -0.095, 0.15)))
    # reeds
    for c in range(5):
        an = 0.5 + c * 1.25 + rng.uniform(-0.2, 0.2)
        base = Vector((rim(an) * 0.9 * math.cos(an), rim(an) * 0.9 * math.sin(an), 0.02))
        for k in range(6):
            o = base + Vector((rng.uniform(-0.3, 0.3), rng.uniform(-0.3, 0.3), 0))
            h = rng.uniform(0.9, 1.5)
            lean = Vector((rng.uniform(-0.12, 0.12), rng.uniform(-0.12, 0.12), 0))
            put(tube([o, o + Vector((0, 0, h / 2)) + lean * 0.4, o + Vector((0, 0, h)) + lean], 0.014, 4), C('#6fa544'))
            if k % 2 == 0:
                put(lathe([(0, 0), (0.035, 0.03), (0.035, 0.2), (0, 0.23)], 6), C('#7c5a2e'), loc=o + Vector((0, 0, h - 0.12)) + lean)
            put(leaf(h * 0.8, 0.07, 0.15, 0.3, 4, 2), C('#86bf5e', double=True),
                mtx=TRS(o, (0, 0, rng.uniform(0, 6.28))) @ TRS(rot=(1.35, 0, 0)), recalc=False)
    # jetty at the front
    J = P.put(Matrix.Translation((0, -R * 0.98, 0)))
    for i in range(7):
        J(box(1.1, 0.26, 0.07, 0.015), C(WOODS[i % 3]), loc=(rng.uniform(-0.03, 0.03), -0.6 + 0.29 * i, 0.3), rot=(0, 0, rng.uniform(-0.03, 0.03)))
    for sx in (1, -1):
        for y in (-0.5, 0.45, 1.25):
            timber(J, (sx * 0.5, y, -0.4), (sx * 0.5, y, 0.5 if y > 1 else 0.28), 0.12)
        timber(J, (sx * 0.5, -0.65, 0.2), (sx * 0.5, 1.3, 0.2), 0.08)
    lantern_post = P.put(Matrix.Translation((0.5, -R * 0.98 + 1.25, 0.5)))
    timber(lantern_post, (0, 0, 0), (0, 0, 0.6), 0.08)
    timber(lantern_post, (0, 0, 0.56), (0.25, 0, 0.56), 0.05)
    lantern_body(lantern_post, (0.22, 0, 0.53), 0.9)
    a.anchor('Light', (0.72, -R * 0.98 + 1.25, 0.8))
    dressing(put, rng, R + 0.75, 26, 16, ('#f7f1e3', '#f2a0a8', '#c7a7e8', '#f2c94c'))
    return a


def garden_plot():
    rng = random.Random(61)
    a = Asset('garden_plot', 'Raised garden bed, 2.8 x 2.2 m, with a stone border and three crop rows.')
    stones_part(a)
    P = a.part('Plot')
    put = P.put()
    hx, hy = 1.3, 1.0
    for y in (-hy, hy):
        stones_line(put, (-hx, y, 0), (hx, y, 0), 0.0, 1, 0.3, rng, sw=0.4, depth=0.32)
    for x in (-hx, hx):
        stones_line(put, (x, -hy, 0), (x, hy, 0), 0.0, 1, 0.3, rng, sw=0.4, depth=0.32)
    soil = box(2 * hx, 2 * hy, 0.3, 0.05)
    displace(soil, 0.02, 4, 1)
    put(soil, C(SOIL, rough=1.0), loc=(0, 0, 0.1))
    for k, y in enumerate((-0.6, 0.0, 0.6)):
        put(cyl(0.2, 0.2, 2 * hx - 0.3, 8), C(shade(SOIL, 0.9), rough=1.0), loc=(-hx + 0.15, y, 0.16), rot=(0, PI / 2, 0), scale=(0.6, 1, 1))
        for i in range(5):
            x = -hx + 0.35 + (2 * hx - 0.7) * i / 4
            if k == 0:   # cabbages
                put(blob(0.16, 2, 0.1, 2, i), C('#9cc77a'), loc=(x, y, 0.38))
                for j in range(5):
                    an = 2 * PI * j / 5 + i
                    put(leaf(0.3, 0.26, -0.3, 0.3, 4, 2), C(rng.choice(['#86bf5e', '#6fae52']), double=True),
                        mtx=TRS((x, y, 0.3), (0, 0, an)) @ TRS(rot=(0.75, 0, 0)), recalc=False)
            elif k == 1:  # carrots
                put(cyl(0.05, 0.06, 0.06, 6), C('#e08a3c'), loc=(x, y, 0.27))
                for j in range(5):
                    an = 2 * PI * j / 5 + i
                    put(leaf(0.3, 0.09, 0.2, 0.2, 4, 2), C('#6fae52', double=True),
                        mtx=TRS((x, y, 0.32), (0, 0, an)) @ TRS(rot=(1.15, 0, 0)), recalc=False)
            else:        # pumpkins and sprouts
                if i % 2 == 0:
                    pm = sphere(1.0, 12, 6)
                    for v in pm.verts:
                        an = math.atan2(v.co.y, v.co.x)
                        f = 1 + 0.08 * math.cos(6 * an)
                        v.co.x *= f
                        v.co.y *= f
                    put(pm, C('#e59a4a', rough=0.6), loc=(x, y, 0.4), scale=(0.2, 0.2, 0.15))
                    put(cyl(0.025, 0.015, 0.08, 5), C('#5c9c48'), loc=(x, y, 0.53))
                else:
                    for j in range(3):
                        put(leaf(0.22, 0.14, 0.2, 0.3, 4, 2), C('#86bf5e', double=True),
                            mtx=TRS((x, y, 0.28), (0, 0, 2.1 * j + i)) @ TRS(rot=(1.0, 0, 0)), recalc=False)
    # sunflower in the back corner, name stake at the front
    sx, sy = hx - 0.2, hy - 0.2
    put(tube([(sx, sy, 0.2), (sx + 0.03, sy, 0.9), (sx, sy - 0.04, 1.5)], 0.025, 6), C('#5c9c48'))
    Sf = P.put(TRS((sx, sy - 0.06, 1.52), (0.35, 0, 0)))
    Sf(cyl(0.12, 0.12, 0.05, 12), C('#6b4630'), rot=(PI / 2, 0, 0))
    for j in range(12):
        an = 2 * PI * j / 12
        Sf(leaf(0.17, 0.08, 0.0, 0.2, 4, 2), C('#f2c94c', double=True),
           mtx=TRS((0.1 * math.cos(an), -0.03, 0.1 * math.sin(an)), (PI / 2, 0, 0)) @ TRS(rot=(0, 0, an - PI / 2)), recalc=False)
    for j in range(2):
        put(leaf(0.3, 0.2, -0.2, 0.2, 4, 2), C('#6fae52', double=True),
            mtx=TRS((sx, sy, 0.7 + 0.3 * j), (0, 0, 2 + 3 * j)) @ TRS(rot=(0.8, 0, 0)), recalc=False)
    timber(put, (-hx + 0.1, -hy - 0.2, 0), (-hx + 0.1, -hy - 0.2, 0.5), 0.05, WOODS[1])
    put(box(0.32, 0.03, 0.2, 0.01), C(WOODS[2]), loc=(-hx + 0.1, -hy - 0.23, 0.5))
    # watering can
    Wc = P.put(TRS((hx + 0.35, -hy + 0.1, 0), (0, 0, 0.6)))
    Wc(lathe([(0, 0), (0.13, 0), (0.14, 0.24), (0.1, 0.27), (0, 0.27)], 12), C('#7fa0a8', rough=0.45))
    Wc(tube([(0.1, 0, 0.08), (0.24, 0, 0.2), (0.32, 0, 0.3)], [0.03, 0.025, 0.022], 6), C('#7fa0a8', rough=0.45))
    Wc(cyl(0.02, 0.05, 0.04, 8), C('#7fa0a8', rough=0.45), mtx=Matrix.Translation((0.32, 0, 0.3)) @ align_z((0.14, 0, 0.1)))
    Wc(tube(arc((-0.12, 0, 0.14), 0.11, PI / 2, 3 * PI / 2, 6, 'xz'), 0.014, 5, False), C('#7fa0a8', rough=0.45))
    dressing(P.put(Matrix.Diagonal((1.0, 0.82, 1, 1))), rng, 1.75, 8, 4)
    return a


def computer():
    rng = random.Random(71)
    a = Asset('computer', "Memo's computer desk, 1.5 x 0.8 m. The Screen node glows and can be swapped or animated.")
    stones_part(a)
    P = a.part('Desk')
    put = P.put()
    put(box(1.5, 0.8, 0.07, 0.02), C(WOODS[0]), loc=(0, 0, 0.72))
    for sx in (-0.66, 0.66):
        for sy in (-0.3, 0.3):
            timber(put, (sx, sy, 0), (sx, sy, 0.7), 0.09, WOODS[1])
    put(box(1.3, 0.05, 0.14, 0.01), C(WOODS[1]), loc=(0, 0.3, 0.6))
    put(box(0.4, 0.6, 0.16, 0.015), C(WOODS[2]), loc=(0.45, 0, 0.6))
    put(sphere(0.025, 6, 4), C('#c9a24a', rough=0.35), loc=(0.45, -0.31, 0.6))
    cream = C('#e6dcc6', rough=0.6)
    put(box(0.56, 0.46, 0.44, 0.05, 2), cream, loc=(-0.1, 0.1, 1.06))
    put(box(0.36, 0.3, 0.06, 0.02), cream, loc=(-0.1, 0.1, 0.79))
    put(box(0.5, 0.04, 0.36, 0.03), C('#bfb59e', rough=0.6), loc=(-0.1, -0.13, 1.07))
    S = a.part('Screen', (-0.1, -0.155, 1.08))
    S.add(box(0.4, 0.02, 0.28, 0.02), C('#a8e6c9', rough=0.3, emit=1.0), loc=(-0.1, -0.155, 1.08))
    put(sphere(0.012, 5, 3), C('#7bd88f', emit=1.0), loc=(0.1, -0.155, 0.9))
    put(box(0.46, 0.17, 0.03, 0.01), cream, loc=(-0.1, -0.24, 0.775), rot=(0.08, 0, 0))
    for r in range(3):
        for c in range(9):
            put(box(0.036, 0.036, 0.016, 0.004), C('#f6efdc'), loc=(-0.29 + 0.0475 * c, -0.29 + 0.048 * r, 0.795 + 0.004 * r))
    put(sphere(1.0, 8, 5), cream, loc=(0.27, -0.24, 0.775), scale=(0.035, 0.05, 0.022))
    # mug, books, candle lantern
    put(lathe([(0, 0), (0.045, 0), (0.05, 0.1), (0.04, 0.1), (0.035, 0.02), (0, 0.02)], 10), C('#e98d78', rough=0.4), loc=(0.55, -0.2, 0.755))
    put(torus(0.03, 0.008, 8, 4), C('#e98d78', rough=0.4), loc=(0.605, -0.2, 0.805), rot=(PI / 2, 0, 0))
    for k, colr in enumerate(('#3d5f8f', '#4c7a4a', '#8f3d2f')):
        book(put, (-0.58, 0.18, 0.785 + 0.055 * k), 0.15 * k, (0.2, 0.28, 0.05), colr)
    put(cyl(0.04, 0.04, 0.02, 8), C('#4d535a'), loc=(0.6, 0.22, 0.755))
    put(cyl(0.02, 0.02, 0.1, 6), C('#f6efdc'), loc=(0.6, 0.22, 0.77))
    put(sphere(1.0, 6, 4), glow(), loc=(0.6, 0.22, 0.9), scale=(0.015, 0.015, 0.03))
    a.anchor('Light', (0.6, 0.22, 0.95))
    # stool
    put(cyl(0.2, 0.2, 0.06, 14), C(WOODS[2]), loc=(-0.05, -0.75, 0.42))
    for k in range(3):
        an = 2 * PI * k / 3
        timber(put, (-0.05 + 0.13 * math.cos(an), -0.75 + 0.13 * math.sin(an), 0.42), (-0.05 + 0.2 * math.cos(an), -0.75 + 0.2 * math.sin(an), 0), 0.05, WOODS[1])
    put(sphere(1.0, 12, 6), C('#c8674b'), loc=(-0.05, -0.75, 0.49), scale=(0.19, 0.19, 0.05))
    return a


# ------------------------------------------------------------------ props

def lantern():
    rng = random.Random(81)
    a = Asset('lantern', 'Lantern post, 2.3 m tall. The Light empty marks where a point light goes.')
    stones_part(a)
    put = a.part('Lantern').put()
    timber(put, (0, 0, 0), (0, 0, 2.2), 0.14)
    for i in range(5):
        an = 2 * PI * i / 5
        stone(put, (0.17 * math.cos(an), 0.17 * math.sin(an), 0.09), an, (0.26, 0.22, 0.22), rng)
    put(tube(arc((0.0, 0, 1.95), 0.38, PI / 2, 0, 8, 'xz'), 0.022, 6, True), C('#4d535a', rough=0.5))
    put(tube([(0, 0, 2.2), (0, 0, 2.34)], [0.05, 0.0], 6), C(TIMBER))
    lantern_body(put, (0.38, 0, 1.93), 1.5)
    a.anchor('Light', (0.38, 0, 1.6))
    grass(put, (0.15, -0.2, 0), 7, 0.3, rng)
    flower(put, (-0.2, -0.12, 0), '#f7f1e3', 0.26, rng)
    return a


def bench():
    rng = random.Random(82)
    a = Asset('bench', 'Timber bench on stone feet, 1.5 m wide.')
    stones_part(a)
    put = a.part('Bench').put()
    for s in (1, -1):
        stone(put, (s * 0.6, 0, 0.14), 0, (0.26, 0.5, 0.3), rng)
        timber(put, (s * 0.6, 0.2, 0.25), (s * 0.6, 0.3, 0.92), 0.08)
        timber(put, (s * 0.6, -0.22, 0.3), (s * 0.6, -0.22, 0.6), 0.07)
        timber(put, (s * 0.6, -0.26, 0.6), (s * 0.6, 0.26, 0.6), 0.06)
    for i in range(3):
        put(box(1.5, 0.15, 0.055, 0.015), C(WOODS[i % 3]), loc=(0, -0.17 + 0.165 * i, 0.44))
    for i in range(2):
        put(box(1.5, 0.05, 0.16, 0.015), C(WOODS[(i + 1) % 3]), loc=(0, 0.25 + 0.03 * i, 0.62 + 0.2 * i), rot=(-0.15, 0, 0))
    return a


def stump():
    rng = random.Random(83)
    a = Asset('stump', 'Tree stump seat with roots and a mushroom.')
    stones_part(a)
    put = a.part('Stump').put()
    t = lathe([(0, 0), (0.46, 0), (0.36, 0.12), (0.32, 0.42), (0.33, 0.5), (0, 0.5)], 16)
    displace(t, 0.025, 5, 2)
    put(t, C(WOODS[1], rough=0.95))
    put(cyl(0.28, 0.28, 0.02, 16), C('#d9b98a'), loc=(0, 0, 0.495))
    put(torus(0.16, 0.008, 16, 4), C('#b98f5f'), loc=(0, 0, 0.515))
    put(torus(0.08, 0.008, 12, 4), C('#b98f5f'), loc=(0, 0, 0.515))
    for k in range(4):
        an = 2 * PI * k / 4 + 0.4
        put(tube([(0.25 * math.cos(an), 0.25 * math.sin(an), 0.22), (0.45 * math.cos(an), 0.45 * math.sin(an), 0.08),
                  (0.62 * math.cos(an), 0.62 * math.sin(an), -0.02)], [0.1, 0.08, 0.04], 6), C(WOODS[1], rough=0.95))
    mushroom(put, (0.38, -0.22, 0.0), 1.2, rng=rng)
    moss(put, (-0.12, 0.1, 0.5), 0.3, 0.24, rng)
    grass(put, (-0.4, -0.3, 0), 6, 0.26, rng)
    return a


def signpost():
    rng = random.Random(84)
    a = Asset('signpost', 'Signpost with two arrow boards on a stone base, 1.9 m tall.')
    stones_part(a)
    put = a.part('Signpost').put()
    timber(put, (0, 0, 0), (0.02, 0, 1.85), 0.13)
    for i in range(6):
        an = 2 * PI * i / 6
        stone(put, (0.18 * math.cos(an), 0.18 * math.sin(an), 0.1), an, (0.28, 0.24, 0.24), rng)
    for z, rot, colr in ((1.55, 0.25, WOODS[2]), (1.22, PI - 0.35, WOODS[0])):
        M = TRS((0, -0.07, z), (0, 0, rot))
        put(box(0.75, 0.05, 0.2, 0.015), C(colr), mtx=M @ Matrix.Translation((0.25, 0, 0)))
        put(box(0.16, 0.05, 0.16, 0.012), C(colr), mtx=M @ TRS((0.63, 0, 0), (0, PI / 4, 0)))
    grass(put, (0.2, 0.15, 0), 7, 0.3, rng)
    return a












def well():
    rng = random.Random(89)
    a = Asset('well', 'Stone well with a tiled roof and bucket, 2.6 m tall.')
    stones_part(a)
    snow_part(a)
    put = a.part('Well').put()
    put(lathe([(0.5, 0), (0.78, 0), (0.78, 0.78), (0.5, 0.78)], 18), C('#8f887b'))
    stones_ring(put, 0.74, 0.0, 3, 0.27, rng, sw=0.36, depth=0.3)
    put(disc(0.52, 16), C('#3f6f86', rough=0.1), loc=(0, 0, 0.5), recalc=False)
    for s in (1, -1):
        timber(put, (s * 0.72, 0, 0.3), (s * 0.72, 0, 2.0), 0.13)
        timber(put, (s * 0.72, 0, 1.6), (s * 0.4, 0, 2.0), 0.08)
    put(cyl(0.05, 0.05, 1.5, 8), C(WOODS[1]), loc=(-0.75, 0, 1.45), rot=(0, PI / 2, 0))
    put(cyl(0.012, 0.012, 0.55, 5), C('#cbb98f'), loc=(0.1, 0, 0.9))
    put(lathe([(0, 0), (0.12, 0), (0.15, 0.22), (0.13, 0.22), (0.11, 0.02), (0, 0.02)], 10), C(WOODS[2]), loc=(0.1, 0, 0.7))
    tiles_gable(next(p for p in a.parts if p.name == 'Well').put(Rz(PI / 2)), 1.0, 1.5, 2.0, 0.55, 0.25, rng, TILES_RED)
    dressing(put, rng, 0.95, 6, 4)
    return a


def stone_wall():
    rng = random.Random(90)
    a = Asset('stone_wall', 'Curving low stone wall: an 80 degree arc of radius 3 m centred on the origin, 0.75 m tall. Repeat to ring a yard.')
    stones_part(a)
    put = a.part('Wall').put()
    stones_ring(put, 3.0, 0.0, 2, 0.3, rng, sw=0.44, depth=0.4, a0=-0.7, a1=0.7)
    n = 8
    for i in range(n):
        az = -0.68 + 1.36 * (i + 0.5) / n
        stone(put, (3.0 * math.sin(az), -3.0 * math.cos(az), 0.66), az, (0.56, 0.5, 0.18), rng, ['#cbc5b7', '#d6d0c2'])
    for i in range(4):
        az = rng.uniform(-0.6, 0.6)
        moss(put, (3.0 * math.sin(az), -3.0 * math.cos(az), 0.72), 0.4, 0.3, rng)
    for i in range(6):
        az = rng.uniform(-0.65, 0.65)
        r = 3.0 + rng.choice((-0.32, 0.32))
        (grass if i % 2 else flower)(put, (r * math.sin(az), -r * math.cos(az), 0), *((7, 0.3, rng) if i % 2 else (rng.choice(('#f7f1e3', '#f2a0a8')), 0.3, rng)))
    return a


def path_stones():
    rng = random.Random(91)
    a = Asset('path_stones', 'Cobbled path piece, about 2.6 x 1.3 m, running front to back. Tile along a route.')
    stones_part(a)
    put = a.part('Path').put()
    placed = []
    tries = 0
    while len(placed) < 20 and tries < 400:
        tries += 1
        p = Vector((rng.uniform(-0.55, 0.55), rng.uniform(-1.25, 1.25), 0))
        s = rng.uniform(0.3, 0.5)
        if any((p - q).length < (s + t) * 0.52 for q, t in placed):
            continue
        placed.append((p, s))
        stone(put, (p.x, p.y, 0.02), rng.uniform(0, 3), (s, s * rng.uniform(0.75, 1.0), 0.1), rng, ['#cbc5b7', '#bdb6a7', '#d6d0c2', '#b4ae9f'])
    for i in range(4):
        grass(put, (rng.choice((-0.72, 0.72)), rng.uniform(-1.2, 1.2), 0), 5, 0.2, rng)
    return a


def fence():
    rng = random.Random(92)
    a = Asset('fence', 'Rustic timber fence segment, 2.4 m long, 0.9 m tall.')
    stones_part(a)
    put = a.part('Fence').put()
    for x in (-1.2, 0, 1.2):
        timber(put, (x, 0, 0), (x + rng.uniform(-0.02, 0.02), 0, 0.9 + rng.uniform(-0.04, 0.04)), 0.11)
        put(tube([(x, 0, 0.9), (x, 0, 0.98)], [0.05, 0.0], 6), C(TIMBER))
    for z in (0.35, 0.68):
        for s in (-1, 1):
            put(tube([(s * 1.2, -0.06, z + rng.uniform(-0.03, 0.03)), (s * 0.6, -0.07, z + rng.uniform(-0.02, 0.02)), (0, -0.06, z + rng.uniform(-0.03, 0.03))], 0.04, 6), C(WOODS[rng.randrange(3)]))
    grass(put, (-0.6, 0.1, 0), 7, 0.3, rng)
    flower(put, (0.5, -0.15, 0), '#f2a0a8', 0.32, rng)
    flower(put, (0.7, -0.2, 0), '#f7f1e3', 0.26, rng)
    return a


def grass_tuft():
    rng = random.Random(93)
    a = Asset('grass_tuft', 'Tufty grass clump, 0.45 m tall. Scatter many.')
    stones_part(a)
    put = a.part('Grass').put()
    grass(put, (0, 0, 0), 12, 0.42, rng, 0.12)
    grass(put, (0.14, 0.08, 0), 6, 0.28, rng, 0.08)
    return a


def flower_cluster(name, cols):
    rng = random.Random(hash(name) & 0xfff)
    a = Asset(name, 'Cluster of wildflowers with grass, about 0.8 m across.')
    put = a.part('Flowers').put()
    for i in range(9):
        an, r = rng.uniform(0, 2 * PI), rng.uniform(0.05, 0.38)
        flower(put, (r * math.cos(an), r * math.sin(an), 0), rng.choice(cols), rng.uniform(0.24, 0.42), rng)
    for i in range(3):
        an = 2 * PI * i / 3
        grass(put, (0.2 * math.cos(an), 0.2 * math.sin(an), 0), 6, 0.3, rng)
    return a


def mushrooms():
    rng = random.Random(94)
    a = Asset('mushrooms', 'Three red-capped mushrooms.')
    stones_part(a)
    put = a.part('Mushrooms').put()
    mushroom(put, (0, 0, 0), 2.0, rng=rng)
    mushroom(put, (0.25, -0.12, 0), 1.3, rng=rng)
    mushroom(put, (-0.2, -0.18, 0), 1.0, '#d9903f', False, rng)
    grass(put, (0.1, 0.2, 0), 6, 0.24, rng)
    return a


def crate_asset():
    a = Asset('crate', 'Wooden crate, 0.6 m.')
    stones_part(a)
    crate(a.part('Crate').put(), (0, 0, 0), 0.6)
    return a


def barrel_asset():
    a = Asset('barrel', 'Barrel, 0.8 m tall.')
    stones_part(a)
    barrel(a.part('Barrel').put(), (0, 0, 0))
    return a


def lookout():
    rng = random.Random(95)
    a = Asset('lookout', 'Lookout set for the hilltop: telescope on a tripod, pennant pole and a ring of stones. Pennant is its own node.')
    stones_part(a)
    put = a.part('Lookout').put()
    stones_ring(put, 1.9, 0.0, 1, 0.3, rng, sw=0.5, depth=0.42, a0=0.5, a1=2 * PI - 0.5)
    top = Vector((0, -0.4, 1.15))
    for k in range(3):
        an = 2 * PI * k / 3 + 0.5
        timber(put, top, (0.45 * math.cos(an), -0.4 + 0.45 * math.sin(an), 0), 0.06, WOODS[1])
    brass = C('#c9a24a', rough=0.35)
    T = next(p for p in a.parts if p.name == 'Lookout').put(TRS(top + Vector((0, 0, 0.08)), (0.25, 0, 0.3)))
    T(cyl(0.07, 0.055, 0.6, 10), brass, loc=(0, 0.3, 0), rot=(PI / 2, 0, 0))
    T(cyl(0.085, 0.085, 0.08, 10), C('#8a6f2f', rough=0.4), loc=(0, -0.28, 0), rot=(PI / 2, 0, 0))
    T(cyl(0.045, 0.04, 0.25, 10), brass, loc=(0, 0.52, 0), rot=(PI / 2, 0, 0))
    timber(put, (1.1, 0.6, 0), (1.1, 0.6, 3.0), 0.1)
    Pn = a.part('Pennant', (1.1, 0.6, 2.75))
    Pn.add(leaf(0.9, 0.5, 0.0, 0.0, 6, 2), C('#d6604d', double=True), mtx=TRS((1.1, 0.6, 2.75), (0, 0, -PI / 2)) @ TRS(rot=(0, PI / 2, 0)), recalc=False)
    dressing(put, rng, 2.2, 8, 6)
    return a


def tile_tint(rng):
    k = rng.uniform(0.84, 1.08)
    return (k * 0.8, k * 0.96, k * 0.74) if rng.random() < 0.05 else k   # the odd mossy tile


def stone(put, loc, rotz, size, rng, mats=STONES):
    """One hand-cut stone: an irregular chamfered block, never a ball."""
    put(block(rng, size[0], size[1], size[2], 0.18, 0.2, 1), C(rng.choice(mats), rough=0.95),
        mtx=TRS(loc, (rng.uniform(-0.08, 0.08), rng.uniform(-0.08, 0.08), rotz + rng.uniform(-0.07, 0.07))),
        tint=rng.uniform(0.86, 1.08))


def timber(put, a, b, th=0.16, col=TIMBER, pegs=True):
    """Hand-hewn beam: chamfered, slightly wavy along its length, pegged near the ends."""
    a, b = Vector(a), Vector(b)
    d = b - a
    ln = d.length
    bm = box(th, th, ln, th * 0.14)
    for z in (-ln / 6, ln / 6):
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, 0, z), plane_no=(0, 0, 1))
    s = a.x * 7.3 + a.y * 3.1 + a.z * 5.7 + b.x * 2.9 + b.z
    for v in bm.verts:
        v.co.x += th * 0.07 * math.sin(v.co.z * 2.1 + s)
        v.co.y += th * 0.07 * math.cos(v.co.z * 1.7 + s * 1.7)
    M = Matrix.Translation((a + b) / 2) @ align_z(d)
    put(bm, C(col, rough=0.9), mtx=M, tint=0.88 + 0.18 * (abs(math.sin(s * 12.9898)) % 1))
    if pegs and th >= 0.1 and ln > th * 5:
        for e in (-1, 1):
            put(cyl(th * 0.1, th * 0.1, th * 1.14, 6), C(shade(col, 0.55)),
                mtx=M @ TRS((-th * 0.57, 0, e * (ln / 2 - th * 0.9)), (0, PI / 2, 0)))


def grain(put, cx, cz, w, h, y, rng, col, vertical=True, n=3):
    """A few fine dark grain lines on a plank face at depth y."""
    for _ in range(n):
        ln = (h if vertical else w) * rng.uniform(0.25, 0.6)
        ox = rng.uniform(-0.38, 0.38) * w
        oz = rng.uniform(-0.3, 0.3) * h
        dims = (0.009, 0.006, ln) if vertical else (ln, 0.006, 0.009)
        put(box(*dims), C(shade(col, 0.72)), loc=(cx + ox, y, cz + oz))


def tiles_cone(put, R, z0, H, rows, rng, mats, flare=1.25, tw=0.44):
    """Conical roof of separate overlapping beaver-tail tiles."""
    rr = lambda t: R * (1 - t) ** flare
    prof = [(0, z0), (R * 0.97, z0)] + [(rr(k / 12) * 0.97, z0 + H * k / 12) for k in range(1, 12)] + [(0, z0 + H)]
    put(lathe(prof, 24), C(shade(mats[1], 0.7)))
    for k in range(rows):
        t = k / rows * 0.96
        t2 = min(t + 1 / rows, 0.999)
        r = rr(t) + 0.03
        z = z0 + H * t
        a = math.atan2(H / rows, max(1e-3, rr(t) - rr(t2)))
        ls = math.hypot(H / rows, rr(t) - rr(t2)) * 1.45
        n = max(5, int(2 * PI * r / tw))
        w = 2 * PI * r / n * 1.06
        for i in range(n):
            az = 2 * PI * (i + 0.5 * (k % 2)) / n
            put(tile_shape(w, ls, 0.075), C(rng.choice(mats), rough=0.8),
                mtx=Rz(az) @ Matrix.Translation((0, -r, z)) @ TRS(rot=(a - 0.12 + rng.uniform(-0.05, 0.05), 0, 0))
                @ Matrix.Translation((0, ls * 0.42, 0.04)) @ Rz(rng.uniform(-0.06, 0.06)), tint=tile_tint(rng))


def tiles_gable(put, W, D, z, rise, ov, rng, mats, tw=0.4, slab=TIMBER):
    """Gable roof (ridge along local Y) of separate beaver-tail tiles with half-round ridge caps."""
    half = W / 2
    th = math.atan2(rise, half)
    Lx = (half + ov) / math.cos(th)
    rows = max(2, round(Lx / 0.36))
    cols = max(2, round((D + 2 * ov) / tw))
    w = (D + 2 * ov) / cols
    tl = Lx / rows * 1.45
    for sgn in (1, -1):
        mid = Vector((sgn * (half + ov) / 2, 0, z + rise - (half + ov) / 2 * math.tan(th)))
        M = TRS(mid, (0, sgn * th, 0))
        put(box(Lx, D + 2 * ov - 0.06, 0.1, 0.02), C(slab, rough=0.9), mtx=M)
        for r in range(rows):
            for c in range(cols + (r % 2)):
                v = -(D + 2 * ov) / 2 + w * (c + 0.5 - 0.5 * (r % 2))
                ww = w
                if r % 2 and c in (0, cols):
                    v += w * 0.25 * (1 if c == 0 else -1)
                    ww = w * 0.5
                u = Lx / 2 - r * Lx / rows - tl * 0.42
                put(tile_shape(ww * 1.03, tl, 0.07), C(rng.choice(mats), rough=0.8),
                    mtx=M @ TRS((sgn * u, v, 0.1), (0, -sgn * (0.11 + rng.uniform(-0.03, 0.03)), 0))
                    @ Rz(sgn * PI / 2 + rng.uniform(-0.05, 0.05)), tint=tile_tint(rng))
    n = max(2, round((D + 2 * ov) / 0.4))
    seg = (D + 2 * ov) / n
    for i in range(n):
        v = -(D + 2 * ov) / 2 + seg * i
        put(cyl(0.17, 0.15, seg * 1.1, 8), C(rng.choice(mats), rough=0.8),
            mtx=TRS((0, v, z + rise + 0.05), (-PI / 2, 0, 0)), tint=tile_tint(rng))


def moss(put, loc, w, d, rng):
    put(boulder(rng, w, d, 0.1, 9, 0.2, 1), C(rng.choice(GRASS), rough=1.0), loc=loc, tint=rng.uniform(0.9, 1.1))


def _rock(name, note, seed, pieces, mossy=True):
    rng = random.Random(seed)
    a = Asset(name, note)
    stones_part(a)
    put = a.part('Rock').put()
    for i, (x, y, w, d, h) in enumerate(pieces):
        rock_piece(put, boulder(rng, w, d, h, 18, 0.07, 2), TRS((x, y, -0.03), (0, 0, rng.uniform(0, 6))), rng)
    x, y, w, d, h = pieces[0]
    if mossy:
        moss(put, (x - w * 0.08, y + d * 0.05, h * 0.86), w * 0.5, d * 0.5, rng)
    grass(put, (x + w * 0.45, y - d * 0.5, 0), 7, 0.28, rng)
    grass(put, (x - w * 0.5, y + d * 0.3, 0), 6, 0.24, rng)
    flower(put, (x - w * 0.4, y - d * 0.55, 0), '#f2c94c', 0.26, rng)
    return a


def rock():
    return _rock('rock', 'Faceted mossy boulder with two smaller stones, about 1.6 m across.', 87,
                 [(0, 0, 1.3, 1.05, 0.9), (0.75, -0.3, 0.6, 0.5, 0.42), (-0.6, -0.45, 0.42, 0.36, 0.3)])


def rock_tall():
    return _rock('rock_tall', 'Standing stone with companions, about 1.7 m tall.', 187,
                 [(0, 0, 0.85, 0.7, 1.7), (0.55, 0.2, 0.6, 0.5, 0.7), (-0.5, -0.3, 0.5, 0.42, 0.34)], mossy=False)


def rock_flat():
    return _rock('rock_flat', 'Low slab outcrop, about 2 m across.', 287,
                 [(0, 0, 1.7, 1.2, 0.5), (0.9, 0.5, 0.9, 0.7, 0.34), (-0.8, -0.5, 0.7, 0.55, 0.3), (0.3, -0.75, 0.5, 0.4, 0.22)])


def turf_cards(rp, rng, R, H, n, skip=None, scale=1.0):
    """Tufty grass cards standing on a mound of radius R and height H."""
    dark, light = Vector(lin('#4f8f3a')), Vector(lin('#b4dc6c'))
    done = 0
    while done < n:
        az, el = rng.uniform(0, 2 * PI), math.asin(rng.uniform(0.05, 0.98))
        p = Vector((R * math.cos(el) * math.cos(az), R * math.cos(el) * math.sin(az), H * math.sin(el)))
        if skip and skip(p):
            continue
        done += 1
        nrm = Vector((p.x / (R * R), p.y / (R * R), p.z / (H * H))).normalized()
        up = (nrm * 0.55 + Vector((0, 0, 0.6))).normalized() * rng.uniform(0.2, 0.34) * scale
        t = up.cross(Vector((rng.gauss(0, 1), rng.gauss(0, 1), 0.01))).normalized() * rng.uniform(0.22, 0.34) * scale
        k = rng.uniform(0.85, 1.12)
        rp.card(p * 1.0 + up * 0.9, t, up, 3, [dark * k, dark * k, light * k, light * k], [nrm + Vector((0, 0, 0.4))] * 4,
                flip=rng.random() < 0.5)

_STONES = None


def stones_part(a):
    """Give this asset a textured 'Stones' node; stone() and rock_piece() then build real rounded stones into it."""
    global _STONES
    from memo_lib import stone_mat
    _STONES = a.raw('Stones')
    _STONES.material = stone_mat()
    _STONES.occlude = True
    return _STONES


_stone_blocky = stone


def stone(put, loc, rotz, size, rng, mats=STONES):
    """One hand-laid stone: rounded, chipped, tinted and textured (same rule as the wall generator)."""
    if _STONES is None:
        return _stone_blocky(put, loc, rotz, size, rng, mats)
    import memo_walls as MWL
    flat = min(size) < 0.16
    bm = MWL.rounded_stone(rng, size[0], size[1], size[2], 2 if flat else 3, rad=rng.uniform(0.18, 0.28), lump=0.05)
    tint = Vector(lin(rng.choice(MWL.TINTS))) * rng.uniform(0.84, 1.05)
    if mats is not STONES:
        tint = tint * 1.06
    M = put.base @ TRS(loc, (rng.uniform(-0.07, 0.07), rng.uniform(-0.07, 0.07), rotz + rng.uniform(-0.07, 0.07)))
    _STONES.mesh(bm, M, lambda wp, n: tint, uv_scale=1.1, uv_off=(rng.random(), rng.random()))


def rock_piece(put, bm, mtx, rng, tint=None):
    """A sculpted boulder with the stone texture and a little moss on its upward faces."""
    if _STONES is None:
        return put(bm, C(rng.choice(STONES), rough=0.95), mtx=mtx, tint=rng.uniform(0.88, 1.06))
    import memo_walls as MWL
    t = (Vector(lin(tint)) if tint else Vector(lin(rng.choice(MWL.TINTS)))) * rng.uniform(0.8, 1.0)
    mo = Vector((rng.uniform(0, 30), rng.uniform(0, 30), 0))
    mossy = rng.random() < 0.6

    def col(wp, n):
        c = t
        if mossy and n.z > 0.45:
            from mathutils import noise as _n
            c = c.lerp(MWL.MOSS, max(0.0, min(0.8, (n.z - 0.45) * 1.6 * (0.5 + 0.7 * _n.noise(wp * 3 + mo)))))
        return c
    _STONES.mesh(bm, put.base @ mtx, col, uv_scale=0.9, uv_off=(rng.random(), rng.random()))

_SNOW = None
SNOW_COL = '#f4f8fb'


def snow_part(a):
    """Optional 'Snow' node (exported hidden): soft caps laid over this asset's roofs."""
    global _SNOW
    _SNOW = a.part('Snow')
    _SNOW.hidden = True
    return _SNOW


_tiles_cone0, _tiles_gable0 = tiles_cone, tiles_gable


def tiles_cone(put, R, z0, H, rows, rng, mats, flare=1.25, tw=0.44):
    _tiles_cone0(put, R, z0, H, rows, rng, mats, flare, tw)
    if _SNOW is not None:
        rr = lambda t: R * (1 - t) ** flare
        prof = [(rr(0.1) + 0.02, z0 + H * 0.1)] + [(rr(t) + 0.13, z0 + H * t + 0.12) for t in [0.1 + 0.9 * k / 9 for k in range(9)]] + [(0, z0 + H + 0.16)]
        cap = lathe(prof, 22)
        for v in cap.verts:
            if v.co.z < z0 + H * 0.2:
                v.co.z -= 0.1 * abs(math.sin(3.5 * math.atan2(v.co.y, v.co.x)))
        displace(cap, 0.03, 2.0, 3)
        _SNOW.put(put.base)(cap, C(SNOW_COL, rough=0.9))


def tiles_gable(put, W, D, z, rise, ov, rng, mats, tw=0.4, slab=TIMBER):
    _tiles_gable0(put, W, D, z, rise, ov, rng, mats, tw, slab)
    if _SNOW is not None:
        sp = _SNOW.put(put.base)
        half = W / 2
        th = math.atan2(rise, half)
        Lx = (half + ov) / math.cos(th)
        for sgn in (1, -1):
            mid = Vector((sgn * (half + ov) / 2, 0, z + rise - (half + ov) / 2 * math.tan(th)))
            sl = box(Lx * 0.93, D + 2 * ov - 0.08, 0.15, 0.06, 2)
            displace(sl, 0.02, 2.5, sgn)
            sp(sl, C(SNOW_COL, rough=0.9), mtx=TRS(mid, (0, sgn * th, 0)) @ Matrix.Translation((-sgn * Lx * 0.03, 0, 0.22)))
        sp(cyl(0.2, 0.2, D + 2 * ov - 0.06, 10), C(SNOW_COL, rough=0.9), mtx=TRS((0, -(D + 2 * ov - 0.06) / 2, z + rise + 0.1), (-PI / 2, 0, 0)))


def build_all():
    yield library_tower()
    yield workshop_hut()
    yield burrow()
    yield notice_board()
    yield pond()
    yield garden_plot()
    yield computer()
    for f in (lantern, bench, stump, signpost, rock, rock_tall, rock_flat, well, path_stones, fence,
              grass_tuft, mushrooms, crate_asset, barrel_asset, lookout):
        yield f()
    yield flower_cluster('flower_cluster', ('#f2a0a8', '#f7f1e3', '#f6c1cf'))
    yield flower_cluster('flower_cluster_gold', ('#f2c94c', '#f7f1e3', '#eaa24c'))
    yield flower_cluster('flower_cluster_blue', ('#9ab8e6', '#c7a7e8', '#f7f1e3'))
