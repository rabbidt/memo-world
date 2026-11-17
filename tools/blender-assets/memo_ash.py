"""Ash the wolf: blockout measured from Rob's character sheet (ATLAS/wolf/sheet.webp, read only).

Dimensions are pixel measurements from the sheet's front and side views, in units of the character's
height (ear tips to soles = 1.0), then checked by overlaying orthographic renders on the sheet
(ash_shots.py + ash_compare.py). Simple shapes first; refinement comes in later passes.

Nodes: Body (children EyeL, EyeR, ArmL, ArmR, Tail; Notebook under ArmR), FootL, FootR.
"""
import math

from mathutils import Vector, Matrix

from memo_lib import PI, Asset, sphere, box, cyl, lathe, tube, torus, leaf, align_z, TRS
from memo_char import C

FUR = '#8fa5ae'
EAR_IN = '#5f7f8a'
HOODIE = '#6b7f8c'
HOOD_DARK = '#58697a'
EYE = '#e9eeef'
INK = '#101114'

STAGES = {'pup': 0.65, 'young': 0.73, 'growing_up': 0.82, 'grown': 0.90}

# --- sheet measurements (front view centre x=508 px, soles y=470 px, 375 px tall; side view centre x=845) ---
HEAD_C = Vector((0, 0.03, 0.595))
HEAD_R = Vector((0.345, 0.3, 0.215))
EYE_R = 0.113
EYE_X = 0.128
EYE_Z = 0.60
PUPIL = (0.098, 0.035, 0.075)        # centre |x|, half width, half height
NOSE_Z = 0.55
NOSE_Y = -0.345                      # nose tip in the side view
CHEEK = ((0.64, 0.39, 0.2), (0.53, 0.4, 0.21), (0.43, 0.35, 0.2))     # ruff tips: height, |x|, tuft width
TORSO = dict(z0=0.133, z1=0.385, rx=0.143, ry=0.105)
LEG = dict(x=0.06, r=0.04, h=0.14)
ARM = dict(x=0.15, z=0.345, len=0.15, r=0.038)


def ell(put, m, centre, radii, seg=24, rings=14, **kw):
    put(sphere(1.0, seg, rings), m, loc=centre, scale=tuple(radii), **kw)


def wedge(length, width, thick, round_tip=0.3):
    """Soft fur tuft or ear: a rounded triangle growing along +Z from the origin."""
    w = width / 2
    bm = lathe([(0, -length * 0.1), (w, 0), (w * 0.8, length * 0.35), (w * round_tip * 1.4, length * 0.75),
                (w * round_tip * 0.6, length * 0.95), (0, length)], 14)
    for v in bm.verts:
        v.co.y *= thick / width
    return bm


def pear(z):
    """The head is widest at cheek level and narrower at the crown."""
    t = (z - HEAD_C.z) / HEAD_R.z
    return 1 + 0.14 * max(0.0, -t) - 0.06 * max(0.0, t)


def head_y(x, z):
    """Front surface of the head at (x, z)."""
    k = 1 - (x / (HEAD_R.x * pear(z))) ** 2 - ((z - HEAD_C.z) / HEAD_R.z) ** 2
    return HEAD_C.y - HEAD_R.y * math.sqrt(max(0.0, k))


def decal(put, m, cx, cz, rx, rz, lift=0.006, seg=28, rings=5):
    """An oval patch laid onto the front of the head, following its curve (for eyes, pupils)."""
    import bmesh
    bm = bmesh.new()
    c = bm.verts.new((cx, head_y(cx, cz) - lift, cz))
    prev = [c] * seg
    for j in range(1, rings + 1):
        t = j / rings
        ring = []
        for i in range(seg):
            a = 2 * PI * i / seg
            x, z = cx + rx * t * math.cos(a), cz + rz * t * math.sin(a)
            ring.append(bm.verts.new((x, head_y(x, z) - lift * (1 - 0.6 * t * t), z)))
        for i in range(seg):
            k = (i + 1) % seg
            if j == 1:
                bm.faces.new((c, ring[i], ring[k]))
            else:
                bm.faces.new((prev[i], ring[i], ring[k], prev[k]))
        prev = ring
    put(bm, m, recalc=False)


def build_ash(name, stage='pup'):
    height = STAGES[stage]
    a = Asset(name, f'Ash the wolf, {stage} stage, {height:.2f} m to the ear tips. Blockout measured from the character sheet.')
    fur, ink = C(FUR, rough=0.9), C(INK, rough=0.7)
    hood, hood2 = C(HOODIE, rough=0.9), C(HOOD_DARK, rough=0.9)
    S = height
    M = Matrix.Scale(S, 4)
    Body = a.part('Body')
    put = Body.put(M)

    # head (pear-shaped), short snout, nose, mouth
    head = sphere(1.0, 40, 24)
    for v in head.verts:
        z = HEAD_C.z + v.co.z * HEAD_R.z
        v.co = Vector((v.co.x * HEAD_R.x * pear(z), v.co.y * HEAD_R.y, v.co.z * HEAD_R.z))
    put(head, fur, loc=HEAD_C)
    ell(put, fur, (0, -0.225, 0.545), (0.075, 0.105, 0.05), 20, 12)
    ell(put, ink, (0, NOSE_Y + 0.02, NOSE_Z), (0.038, 0.022, 0.024), 14, 10)
    put(tube([(-0.016, -0.318, 0.503), (0, -0.325, 0.498), (0.016, -0.318, 0.503)], 0.004, 5), ink)
    # ears: broad rounded cones set back on the head, darker inside, leaning out a little
    for s in (1, -1):
        base = Vector((s * 0.205, 0.11, 0.735))
        d = Vector((s * 0.02, 0.0, 0.252))
        put(wedge(d.length, 0.2, 0.15, 0.42), fur, mtx=Matrix.Translation(base) @ align_z(d))
        put(wedge(d.length * 0.56, 0.115, 0.03, 0.42), C(EAR_IN, rough=0.9),
            mtx=Matrix.Translation(base + Vector((-s * 0.004, -0.056, 0.035))) @ align_z(d))
    # cheek ruff: three broad flat tufts each side, a rear row, and the back of the head
    for s in (1, -1):
        for z, x, w in CHEEK:
            for yy, k in ((0.0, 1.0),):
                b = Vector((s * 0.22, HEAD_C.y + yy, z + 0.05))
                t = Vector((s * x * k, HEAD_C.y + yy, z - 0.035))
                put(wedge((t - b).length, w, 0.17), fur, mtx=Matrix.Translation(b) @ align_z(t - b))
    for zz, yy in ((0.63, 0.385), (0.52, 0.39), (0.42, 0.34)):
        put(wedge(0.2, 0.3, 0.2), fur, mtx=Matrix.Translation((0, 0.2, zz + 0.05)) @ align_z((0, yy - 0.2, -0.085)) @ Matrix.Rotation(PI / 2, 4, 'Z'))
    for x in (-0.12, 0, 0.12):      # jaw line
        put(wedge(0.06, 0.2, 0.22), fur, mtx=Matrix.Translation((x, -0.02, 0.415)) @ align_z((x * 0.6, 0, -1)))
    for dx, tilt, ln in ((0.02, 0.9, 0.1), (-0.02, 0.35, 0.085), (-0.05, -0.2, 0.06)):     # forward-swept crown tuft
        put(wedge(ln, 0.075, 0.07), fur, mtx=Matrix.Translation((dx, -0.08, 0.79)) @ align_z((math.sin(tilt) * 0.8, -0.45, math.cos(tilt))))

    # eyes
    for s, nm in ((1, 'EyeL'), (-1, 'EyeR')):
        cx = s * EYE_X
        E = a.part(nm, Vector((cx, head_y(cx, EYE_Z), EYE_Z)) * S, parent=Body)
        ep = E.put(M)
        decal(ep, C(EYE, rough=0.8), cx, EYE_Z, EYE_R, EYE_R * 1.04, 0.008)
        decal(ep, ink, s * PUPIL[0], EYE_Z, PUPIL[1], PUPIL[2], 0.022, 18, 3)

    # hoodie
    t = TORSO
    tb = lathe([(0, t['z0']), (t['rx'], t['z0']), (t['rx'] * 1.03, t['z0'] + 0.03), (t['rx'] * 0.97, t['z0'] + 0.15),
                (t['rx'] * 0.82, t['z1'] - 0.03), (t['rx'] * 0.6, t['z1']), (0, t['z1'])], 24)
    for v in tb.verts:
        v.co.y *= t['ry'] / t['rx']
    put(tb, hood)
    ell(put, hood2, (0, 0.1, 0.355), (0.115, 0.075, 0.05), 16, 10)                       # hood
    put(box(0.13, 0.02, 0.06, 0.01, 2), hood2, loc=(0, -t['ry'] - 0.002, 0.2))           # pocket
    put(torus(t['rx'] * 1.0, 0.014, 24, 6), hood2, loc=(0, 0, t['z0'] + 0.02), scale=(1, t['ry'] / t['rx'], 1))

    # arms with mitten paws; the right arm is held out to the side and carries the notebook clear of the body
    for s, nm in ((1, 'ArmL'), (-1, 'ArmR')):
        sh = Vector((s * ARM['x'], 0, ARM['z']))
        A = a.part(nm, sh * S, parent=Body)
        frame = TRS(sh, (0, -s * (0.3 if s > 0 else 0.9), 0))
        P = A.put(M @ frame)
        r, ln = ARM['r'], ARM['len']
        P(lathe([(0, 0.02), (r, 0.0), (r * 1.1, -ln * 0.6), (r * 1.1, -ln), (0, -ln)], 14), hood)
        P(torus(r * 1.05, 0.011, 14, 6), hood2, loc=(0, 0, -ln + 0.008))
        P(sphere(1.0, 16, 10), fur, loc=(0, -0.004, -ln - 0.03), scale=(0.04, 0.042, 0.04))          # paw
        P(sphere(1.0, 10, 8), fur, loc=(-s * 0.03, -0.012, -ln - 0.02), scale=(0.016, 0.018, 0.02))  # thumb
        if s < 0:
            grip = frame @ Vector((0, 0, -ln - 0.03))
            N = a.part('Notebook', grip * S, parent=A)
            Q = N.put(M @ TRS(grip + Vector((-0.02, -0.03, -0.055)), (0.0, 0, 0.12)))
            Q(box(0.105, 0.02, 0.135, 0.005), C('#b5533c', rough=0.7))
            Q(box(0.095, 0.014, 0.125, 0.002), C('#f6efdc'), loc=(0.007, 0, 0))
            Q(leaf(0.045, 0.026, 0, 0, 5, 2), C('#f2d58a', double=True), loc=(0, -0.0115, -0.02), rot=(PI / 2, 0, 0), recalc=False)

    # legs and feet
    for s, nm in ((1, 'FootL'), (-1, 'FootR')):
        hip = Vector((s * LEG['x'], 0, LEG['h']))
        F = a.part(nm, hip * S)
        P = F.put(M @ Matrix.Translation(hip))
        r, h = LEG['r'], LEG['h']
        P(lathe([(0, 0.02), (r, 0.0), (r, -h * 0.75), (r * 1.1, -h * 0.95), (r * 0.9, -h), (0, -h)], 14), fur)
        P(sphere(1.0, 14, 8), fur, loc=(0, -0.022, -h + 0.022), scale=(0.043, 0.06, 0.024))

    # tail: big and low, sweeping out to his left and back, three soft points turned up
    tb_ = Vector((0.03, 0.09, 0.14))
    T = a.part('Tail', tb_ * S, parent=Body)
    P = T.put(M)
    pts = [tb_, tb_ + Vector((0.08, 0.06, -0.04)), tb_ + Vector((0.17, 0.11, -0.04)), tb_ + Vector((0.25, 0.15, 0.0))]
    P(tube(pts, [0.035, 0.06, 0.075, 0.06], 12), fur)
    for d, ln in (((0.9, 0.35, 0.45), 0.12), ((0.45, 0.3, 0.95), 0.12), ((0.1, 0.2, 1.0), 0.09)):
        P(wedge(ln, 0.1, 0.09), fur, mtx=Matrix.Translation(pts[-1] - Vector((0.03 + 0.04 * (d[0] < 0.2), 0.02, 0.0))) @ align_z(d))
    return a
