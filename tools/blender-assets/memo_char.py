"""Memo the island critter: parametric character builder with several concept designs.

Nodes (animated by the game): Body, Sprout, EyeL, EyeR, ArmL, ArmR, Notebook (child of ArmR),
Tail, FootL, FootR.
"""
import math
import random

from mathutils import Vector, Matrix

from memo_lib import (PI, Asset, mat, sphere, ico, box, cyl, lathe, dome, torus, tube, arc, leaf,
                      disc, displace, blob, align_z, TRS)

STAGES = {
    'childlike': dict(top=0.65, tall=0.95, eye=1.00, grow=0),
    'young': dict(top=0.73, tall=1.00, eye=0.93, grow=1),
    'growing_up': dict(top=0.82, tall=1.05, eye=0.86, grow=2),
    'grown': dict(top=0.90, tall=1.10, eye=0.80, grow=3),
}

SHAPES = {
    'round': lambda t: 1.0 + 0.08 * (1 - t),
    'pear': lambda t: 0.80 + 0.34 * (1 - t) ** 1.3,
    'teardrop': lambda t: 1.08 - 0.40 * t ** 1.8,
    'pebble': lambda t: 1.20 + 0.06 * (1 - t),
    'bean': lambda t: 0.80 + 0.12 * (1 - t),
}

DESIGNS = {
    'mossball': dict(
        title='Mossball', shape='round', body='#76a846', belly='#efe6cc', feet='#e08a3c', cheek='#f2a0a8',
        tuft=('#4f7f35', '#a3cc6a'), tufts=16, top='sprout', leafc='#5fae4a', ears=None, tail='moss',
        eyes='bead', book='#8f3d2f'),
    'acorn': dict(
        title='Acorn sprite', shape='pear', body='#e4b780', belly='#f8ead0', feet='#a8683a', cheek='#f0907a',
        tufts=0, top='acorn', capc='#7a5234', leafc='#6fae52', ears='round', tail='stub',
        eyes='oval', book='#4c7a4a'),
    'fernfox': dict(
        title='Fern bun', shape='teardrop', body='#a9c8a4', belly='#f5f1e2', feet='#d9a679', cheek='#f4b0b4',
        tufts=0, top='fern', leafc='#5d9c66', ears='leaf', tail='fluffy', eyes='sleepy', fuzz=True,
        book='#b5533c', eye_az=0.46),
    'mushroom': dict(
        title='Mushroom cap', shape='bean', body='#f3ead8', belly='#fff8ea', feet='#d8b890', cheek='#f4a9a0',
        tufts=0, top='cap', capc='#e58a7b', leafc='#6fae52', ears=None, tail='stub', eyes='dot',
        book='#3f7f7a', top_scale=0.74, eye_az=0.5),
    'pebble': dict(
        title='Pebble', shape='pebble', body='#9fb0bd', belly='#e1e8ec', feet='#6f8090', cheek='#f0a6b0',
        tuft=('#6fa544', '#9cc765'), tufts=0, top='flowers', leafc='#6fae52', ears='nub', tail='grass',
        eyes='bead', book='#c9a24a', top_scale=0.86, tall_scale=0.84),
}


def C(hexcol, rough=0.85, emit=0.0, double=False):
    return mat(f'{hexcol}_{rough}_{emit}_{int(double)}', rough=rough, emit=emit, double=double, color=hexcol)


def shade(hexcol, f):
    h = hexcol.lstrip('#')
    return '#' + ''.join(f'{max(0, min(255, int(int(h[i:i + 2], 16) * f))):02x}' for i in (0, 2, 4))


def build_memo(name, design, stage='childlike'):
    d = DESIGNS[design] if isinstance(design, str) else design
    st = STAGES[stage]
    rng = random.Random(hash((d['title'], stage)) & 0xffff)
    grow = st['grow']
    lift = 0.045
    tall = st['tall'] * d.get('tall_scale', 1.0)
    top_h = st['top'] * d.get('top_scale', 1.0)
    R = (top_h - lift) / (2 * tall)
    c = Vector((0, 0, lift + R * tall))
    rad = SHAPES[d['shape']]
    es = st['eye']

    def surf(az, el, k=1.0):
        r = rad((math.sin(el) + 1) / 2)
        return c + Vector((R * r * math.cos(el) * math.sin(az), -R * 0.96 * r * math.cos(el) * math.cos(az),
                           R * tall * math.sin(el))) * k

    def nrm(az, el):
        p = surf(az, el) - c
        return Vector((p.x / (R * R), p.y / (R * R * 0.92), p.z / (R * R * tall * tall))).normalized()

    a = Asset(name, note=f"Memo, {d['title']} design, {stage} stage. Body top {top_h:.2f} m.")
    body_m = C(d['body'])
    belly_m = C(d['belly'])
    black = C('#17171c', rough=0.12)
    white = C('#ffffff', rough=0.3, emit=0.4)
    leaf_m = C(d['leafc'], rough=0.7, double=True)
    stem_m = C(shade(d['leafc'], 0.8))

    Body = a.part('Body')
    bm = sphere(1.0, 32, 20)
    for v in bm.verts:
        r = rad((v.co.z + 1) / 2)
        v.co = Vector((v.co.x * R * r, v.co.y * R * 0.96 * r, v.co.z * R * tall))
    if d.get('fuzz'):
        displace(bm, 0.008, 55, 3.0)
    displace(bm, 0.008, 6, 1.0)
    Body.add(bm, body_m, loc=c)

    # belly patch: a flattened ellipsoid poking through the front
    dv = Vector((0, -0.82, -0.57)).normalized()
    rb = rad(0.25)
    bc = c + Vector((0, dv.y * 0.96 * R * rb * 0.72, dv.z * R * tall * 0.72))
    Body.add(sphere(1.0, 20, 12), belly_m,
             mtx=Matrix.Translation(bc) @ align_z(dv) @ Matrix.Diagonal((0.60 * R * rb, 0.60 * R * rb, 0.40 * R, 1)))

    # face
    az_e = d.get('eye_az', 0.42)
    el_e = 0.16
    for sgn, nm in ((1, 'EyeL'), (-1, 'EyeR')):
        az = sgn * az_e
        ec = surf(az, el_e, 0.95)
        E = a.part(nm, ec)
        put = E.put(TRS(ec, (0, 0, az)))
        kind = d['eyes']
        er = R * es * {'bead': 0.15, 'oval': 0.15, 'sleepy': 0.15, 'dot': 0.085}[kind]
        zs = 1.35 if kind == 'oval' else 1.08
        put(sphere(1.0, 16, 10), black, scale=(er, er * 0.72, er * zs))
        put(sphere(1.0, 8, 6), white, loc=(-0.30 * er, -0.60 * er, 0.38 * er * zs), scale=er * (0.34 if kind != 'dot' else 0.28))
        if kind in ('bead', 'oval'):
            put(sphere(1.0, 8, 6), white, loc=(0.28 * er, -0.66 * er, -0.30 * er * zs), scale=er * 0.14)
        if kind == 'sleepy':
            put(sphere(1.0, 16, 10), C(shade(d['body'], 0.86)), loc=(0, -0.02 * er, 0.62 * er),
                scale=(er * 1.12, er * 0.80, er * 0.95))
        # cheek
        cp = surf(sgn * (az_e + 0.30), -0.06, 0.99)
        Body.add(sphere(1.0, 10, 6), C(d['cheek']), mtx=TRS(cp, (0, 0, sgn * (az_e + 0.30))) @ Matrix.Diagonal((0.12 * R, 0.035 * R, 0.075 * R, 1)))
    Body.add(sphere(1.0, 10, 6), C(shade(d['feet'], 0.85)), loc=surf(0, 0.03, 1.0), scale=(0.05 * R, 0.04 * R, 0.035 * R))
    mouth = [surf(0.085 * math.cos(t), -0.035 + 0.085 * math.sin(t), 1.004)
             for t in [math.radians(205 + 130 * i / 8) for i in range(9)]]
    Body.add(tube(mouth, 0.011 * R / 0.3, 5), C('#5a3626'))

    # moss tufts
    if d.get('tufts'):
        n = d['tufts'] + grow * 4
        placed = 0
        while placed < n:
            az = rng.uniform(-PI, PI)
            el = rng.uniform(0.15, 1.45)
            if el < 0.8 and abs(az) < 1.1:
                continue
            if el < 0.5 and abs(az) < 2.0:
                continue
            r = R * rng.uniform(0.15, 0.24)
            b = sphere(1.0, 10, 6)
            displace(b, 0.18, 2.2, placed)
            Body.add(b, C(d['tuft'][placed % 2]),
                     mtx=Matrix.Translation(surf(az, el, 0.98)) @ align_z(nrm(az, el)) @ Matrix.Diagonal((r, r, r * 0.6, 1)))
            placed += 1

    # ears
    ears = d.get('ears')
    for sgn in (1, -1):
        if ears == 'round':
            p = surf(sgn * 0.75, 1.02, 1.0)
            put = Body.put(TRS(p, (0, sgn * 0.35, sgn * 0.3)))
            put(sphere(1.0, 12, 8), body_m, scale=(0.17 * R, 0.07 * R, 0.17 * R), loc=(0, 0, 0.08 * R))
            put(sphere(1.0, 10, 6), C(d['cheek']), scale=(0.10 * R, 0.04 * R, 0.10 * R), loc=(0, -0.05 * R, 0.08 * R))
        elif ears == 'nub':
            p = surf(sgn * 0.9, 0.95, 1.0)
            Body.add(sphere(1.0, 10, 6), body_m, loc=p, scale=(0.11 * R, 0.08 * R, 0.10 * R))
        elif ears == 'leaf':
            p = surf(sgn * 1.2, 0.95, 0.96)
            L = R * (0.95 + 0.08 * grow)
            Body.add(leaf(L, L * 0.48, bend=-0.55, fold=0.25, nu=10, nv=4), leaf_m,
                     mtx=TRS(p, (0, 0, -sgn * (PI / 2 - 0.35))) @ TRS(rot=(0.75, 0, 0)), recalc=False)

    # top / sprout
    top = c + Vector((0, 0, R * tall))
    S = a.part('Sprout', top - Vector((0, 0, 0.01)))
    kind = d['top']
    nleaf = 2 + grow

    def sprout_leaves(base, n, L, W, pitch=0.7, start=0.4):
        for i in range(n):
            ang = start + 2 * PI * i / n
            S.add(leaf(L * (1 - 0.12 * (i % 2)), W, bend=-0.28, fold=0.3), leaf_m,
                  mtx=TRS(base, (0, 0, ang)) @ TRS(rot=(pitch, 0, 0)), recalc=False)

    if kind == 'sprout':
        h = 0.10 + 0.01 * grow
        pts = [top + Vector((0.012 * math.sin(i * 0.9), 0, -0.01 + (h + 0.01) * i / 4)) for i in range(5)]
        S.add(tube(pts, [0.014, 0.012, 0.011, 0.010, 0.009], 6), stem_m)
        sprout_leaves(pts[-1], nleaf, 0.17 + 0.012 * grow, 0.085 + 0.005 * grow)
        if grow == 3:
            for i in range(5):
                an = 2 * PI * i / 5
                S.add(sphere(1.0, 8, 5), C('#f6c1cf'), loc=pts[-1] + Vector((0.022 * math.cos(an), 0.022 * math.sin(an), 0.035)),
                      scale=(0.02, 0.02, 0.012))
            S.add(sphere(1.0, 8, 5), C('#f2c94c'), loc=pts[-1] + Vector((0, 0, 0.04)), scale=0.014)
    elif kind == 'acorn':
        el0 = 0.52
        prof = [(R * rad((math.sin(el0) + 1) / 2) * math.cos(el0) * 0.9, c.z + R * tall * math.sin(el0) - 0.004)]
        for i in range(9):
            el = el0 + (PI / 2 - el0) * i / 9
            prof.append((R * rad((math.sin(el) + 1) / 2) * math.cos(el) * 1.09 + 0.012, c.z + R * tall * math.sin(el) * 1.0 + 0.012))
        prof.append((0, top.z + 0.016))
        cap = lathe(prof, 28)
        displace(cap, 0.006, 42, 2.0)
        Body.add(cap, C(d['capc'], rough=0.9), scale=(1, 0.96, 1))
        Body.add(torus(prof[1][0], 0.016, 28, 6), C(shade(d['capc'], 0.8)), loc=(0, 0, prof[1][1]), scale=(1, 0.96, 1))
        pts = [top + Vector((0.01 * i, 0, 0.005 + 0.03 * i)) for i in range(4)]
        S.add(tube(pts, [0.016, 0.014, 0.012, 0.011], 6), C(shade(d['capc'], 0.75)))
        sprout_leaves(pts[-1], 1 + grow, 0.16, 0.085, pitch=0.5, start=-PI / 2)
    elif kind == 'cap':
        zb = top.z - 0.30 * R
        Rc = 1.42 * R
        prof = [(0, zb + 0.02), (Rc * 0.92, zb)] + \
               [(Rc * math.cos(t) ** 0.8, zb + 0.02 + 0.95 * R * math.sin(t)) for t in [PI / 2 * i / 8 for i in range(8)]] + \
               [(0, zb + 0.02 + 0.95 * R)]
        cap = lathe(prof, 32)
        displace(cap, 0.006, 8, 4.0)
        Body.add(cap, C(d['capc'], rough=0.6))
        Body.add(lathe([(0, zb + 0.03), (Rc * 0.9, zb - 0.004), (Rc * 0.5, zb - 0.02), (0.6 * R, zb - 0.01)], 32), C('#f7e3cf'))
        for i in range(7 + grow * 2):
            az = rng.uniform(-PI, PI)
            t = rng.uniform(0.35, 1.25)
            p = Vector((Rc * math.cos(t) ** 0.8 * math.sin(az), -Rc * math.cos(t) ** 0.8 * math.cos(az), zb + 0.02 + 0.95 * R * math.sin(t)))
            n = Vector((p.x, p.y, (p.z - zb) * 1.6)).normalized()
            r = R * rng.uniform(0.09, 0.17)
            Body.add(sphere(1.0, 10, 6), C('#fff6ea', rough=0.6), mtx=Matrix.Translation(p) @ align_z(n) @ Matrix.Diagonal((r, r, r * 0.25, 1)))
        ct = Vector((0, 0, zb + 0.02 + 0.95 * R))
        S.pivot = ct.copy()
        pts = [ct + Vector((0, 0, -0.01 + 0.03 * i)) for i in range(3)]
        S.add(tube(pts, 0.009, 6), stem_m)
        for i in range(3 + grow):
            an = 2 * PI * i / (3 + grow)
            S.add(sphere(1.0, 10, 6), leaf_m, loc=pts[-1] + Vector((0.034 * math.cos(an), 0.034 * math.sin(an), 0.004)),
                  rot=(0, 0, an), scale=(0.036, 0.03, 0.006))
    elif kind == 'flowers':
        el0 = 0.95
        prof = [(R * rad((math.sin(el0) + 1) / 2) * math.cos(el0) * 0.95, c.z + R * tall * math.sin(el0) - 0.004)]
        for i in range(6):
            el = el0 + (PI / 2 - el0) * i / 6
            prof.append((R * rad((math.sin(el) + 1) / 2) * math.cos(el) * 1.06 + 0.012, c.z + R * tall * math.sin(el) + 0.014))
        prof.append((0, top.z + 0.02))
        mp = lathe(prof, 24)
        displace(mp, 0.012, 22, 5.0)
        Body.add(mp, C(d['tuft'][0]), scale=(1, 0.96, 1))
        for i in range(5):
            an = 2 * PI * i / 5 + 0.3
            r = R * 0.12
            b = sphere(1.0, 10, 6)
            displace(b, 0.2, 2.0, i)
            Body.add(b, C(d['tuft'][i % 2]), loc=top + Vector((0.32 * R * math.cos(an), 0.3 * R * math.sin(an), -0.03)), scale=(r, r, r * 0.6))
        for i in range(3 + grow):
            an = 2 * PI * i / (3 + grow) + 0.5
            base = top + Vector((0.07 * math.cos(an), 0.07 * math.sin(an), 0.0))
            h = 0.09 + 0.04 * (i % 2) + 0.01 * grow
            tip = base + Vector((0.025 * math.cos(an), 0.025 * math.sin(an), h))
            S.add(tube([base, (base + tip) / 2 + Vector((0, 0, 0.01)), tip], 0.006, 5), stem_m)
            for k in range(7):
                pa = 2 * PI * k / 7
                S.add(sphere(1.0, 6, 4), C('#fffaf0'), loc=tip + Vector((0.022 * math.cos(pa), 0.022 * math.sin(pa), 0.002)),
                      rot=(0, 0, pa), scale=(0.016, 0.009, 0.004))
            S.add(sphere(1.0, 8, 5), C('#f2c94c'), loc=tip + Vector((0, 0, 0.004)), scale=(0.012, 0.012, 0.008))
    elif kind == 'fern':
        h1 = 0.10 + 0.015 * grow
        rr = 0.05 + 0.006 * grow
        pts = [top + Vector((0, 0, -0.01)), top + Vector((0, 0.004, h1 * 0.5))]
        cc = top + Vector((0, -rr, h1))
        nseg = 16
        rads = [0.015, 0.014]
        for i in range(nseg + 1):
            ang = 1.75 * PI * i / nseg
            r = rr * (1 - 0.62 * i / nseg)
            pts.append(cc + Vector((0, r * math.cos(ang), r * math.sin(ang))))
            rads.append(0.013 - 0.007 * i / nseg)
        S.add(tube(pts, rads, 7), C(d['leafc']))
        for i in range(2 + grow):
            z = h1 * (0.25 + 0.5 * i / (1 + grow))
            for sgn in (1, -1):
                S.add(leaf(0.075, 0.035, bend=-0.2, fold=0.2, nu=5, nv=2), leaf_m,
                      mtx=TRS(top + Vector((0, 0.003, z)), (0, 0, -sgn * PI / 2)) @ TRS(rot=(0.5, 0, 0)), recalc=False)

    # arms
    for sgn, nm in ((1, 'ArmL'), (-1, 'ArmR')):
        sp = surf(sgn * 1.2, -0.12, 0.93)
        A = a.part(nm, sp)
        swing = -1.0 if sgn < 0 else -0.1
        put = A.put(TRS(sp, (swing, 0, 0)) @ TRS(rot=(0, sgn * 0.35, 0)))
        put(sphere(1.0, 12, 8), C(d.get('arm', d['body'])), loc=(sgn * 0.02 * R, 0, -0.16 * R), scale=(0.11 * R, 0.12 * R, 0.21 * R))
        if sgn < 0:
            hand = TRS(sp, (swing, 0, 0)) @ TRS(rot=(0, sgn * 0.35, 0)) @ Vector((sgn * 0.02 * R, 0, -0.34 * R))
            nb_c = hand + Vector((0.12 * R, -0.12 * R, 0.16 * R))
            N = a.part('Notebook', nb_c, parent=A)
            put = N.put(TRS(nb_c, (-0.25, 0.0, 0.35)))
            w, t, h = 0.46 * R, 0.1 * R, 0.6 * R
            put(box(w, t, h, 0.012), C(d['book'], rough=0.7))
            put(box(w * 0.9, t * 0.72, h * 0.92, 0.004), C('#f6efdc'), loc=(0.03 * R, 0, 0))
            put(box(0.03 * R, t * 0.2, h * 0.5), C('#d0463b'), loc=(0.06 * R, 0, -h * 0.42))
            put(leaf(0.16 * R, 0.09 * R, 0.0, 0.0, 5, 2), C('#f2d58a', double=True), loc=(0.0, -t * 0.55, -0.07 * R),
                rot=(PI / 2, 0, 0), recalc=False)
            if grow >= 2:  # a pencil for the older, more studious Memo
                put(cyl(0.012 * R / 0.3, 0.012 * R / 0.3, 0.42 * R, 6), C('#f2c94c'), loc=(-0.24 * R, 0, -0.2 * R), rot=(0, 0.25, 0))
                put(cyl(0.012 * R / 0.3, 0.001, 0.05 * R, 6), C('#3a2a20'), loc=(-0.24 * R + 0.42 * R * math.sin(0.25), 0, -0.2 * R + 0.42 * R * math.cos(0.25)), rot=(0, 0.25, 0))

    # feet
    for sgn, nm in ((1, 'FootL'), (-1, 'FootR')):
        fp = Vector((sgn * 0.42 * R, -0.12 * R, 0.085 * R))
        F = a.part(nm, fp)
        F.add(sphere(1.0, 12, 8), C(d['feet']), loc=fp + Vector((0, -0.16 * R, 0)), rot=(0, 0, -sgn * 0.25),
              scale=(0.17 * R, 0.25 * R, 0.085 * R))

    # tail
    tp = surf(PI, -0.5, 0.97)
    T = a.part('Tail', tp)
    back = Vector((0, 1, 0))
    tail = d.get('tail')
    if tail == 'moss':
        T.add(blob(0.16 * R, 2, 0.22, 2.0, 7), C(d['tuft'][0]), loc=tp + back * 0.08 * R)
        T.add(blob(0.09 * R, 1, 0.22, 2.0, 9), C(d['tuft'][1]), loc=tp + back * 0.2 * R + Vector((0, 0, 0.06 * R)))
    elif tail == 'stub':
        T.add(sphere(1.0, 10, 6), C(d.get('capc', d['body'])) if d['top'] == 'acorn' else body_m, loc=tp + back * 0.06 * R, scale=0.11 * R)
    elif tail == 'fluffy':
        for i, (r, off, zz) in enumerate(((0.2, 0.1, 0.0), (0.24, 0.3, 0.14), (0.2, 0.42, 0.36))):
            b = blob(r * R, 2, 0.14, 2.4, i)
            T.add(b, body_m if i < 2 else belly_m, loc=tp + back * off * R + Vector((0, 0, zz * R)))
    elif tail == 'grass':
        for i in range(4):
            T.add(leaf(0.3 * R * (1 - 0.1 * i), 0.07 * R, bend=0.6, fold=0.3, nu=5, nv=2), C('#6fa544', double=True),
                  mtx=TRS(tp, (0, 0, (i - 1.5) * 0.45)) @ TRS(rot=(0.5, 0, 0)), recalc=False)
    return a
