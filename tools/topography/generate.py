"""Generate Ash's island topography: heightmap, biome map, entity positions and path network.

Run:  python3 tools/topography/generate.py [out_dir]
Needs numpy, scipy, scikit-image, pillow (matplotlib only for render.py).

Conventions (same as world/island-layout.xlsx): x is east (+), z is south (+), metres from the
Notice Board at (0, 0). Heights are metres above sea level (sea = 0).
The grid is N x N samples covering WORLD metres; row 0 is the north edge, column 0 the west edge.
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from skimage.graph import MCP_Geometric

N = 513
WORLD = 256.0
HALF = WORLD / 2
CELL = WORLD / (N - 1)
SEED = 20261119
H_MIN, H_MAX = -8.0, 32.0  # range encoded by the 16-bit PNG

xs = np.linspace(-HALF, HALF, N)
X, Z = np.meshgrid(xs, xs)


def g(x, z):
    """World metres -> (row, col) float grid coordinates."""
    return (z + HALF) / CELL, (x + HALF) / CELL


def sample(a, x, z):
    r, c = g(np.asarray(x, float), np.asarray(z, float))
    return ndi.map_coordinates(a, [np.atleast_1d(r), np.atleast_1d(c)], order=1, mode="nearest")


def sstep(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)


def fbm(seed, lo, hi, beta=2.4):
    """Band-limited fractal noise, wavelengths between lo and hi metres, unit variance."""
    rng = np.random.default_rng(SEED + seed)
    n = N - 1
    f = np.fft.fft2(rng.standard_normal((n, n)))
    k = np.hypot(*np.meshgrid(np.fft.fftfreq(n, CELL), np.fft.fftfreq(n, CELL)))
    k[0, 0] = 1
    amp = k ** (-beta / 2) * (k >= 1 / hi) * (k <= 1 / lo)
    out = np.real(np.fft.ifft2(f * amp))
    out = np.pad(out, ((0, 1), (0, 1)), mode="wrap")
    return out / out.std()


def catmull(pts, per=24, closed=False):
    p = np.asarray(pts, float)
    if closed:
        p = np.vstack([p[-1], p, p[0], p[1]])
    else:
        p = np.vstack([2 * p[0] - p[1], p, 2 * p[-1] - p[-2]])
    out = []
    t = np.linspace(0, 1, per, endpoint=False)[:, None]
    for i in range(1, len(p) - 2):
        a, b, c, d = p[i - 1], p[i], p[i + 1], p[i + 2]
        out.append(0.5 * ((2 * b) + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t ** 2 + (-a + 3 * b - 3 * c + d) * t ** 3))
    out = np.vstack(out)
    return out if closed else np.vstack([out, p[-2]])


def blob(cx, cz, rx, rz=None, rot=0.0, xw=X, zw=Z):
    rz = rz or rx
    a = math.radians(rot)
    u = (xw - cx) * math.cos(a) + (zw - cz) * math.sin(a)
    v = -(xw - cx) * math.sin(a) + (zw - cz) * math.cos(a)
    return np.exp(-((u / rx) ** 2 + (v / rz) ** 2))


def signed_dist(mask):
    sd = np.where(mask, ndi.distance_transform_edt(mask) - 0.5, 0.5 - ndi.distance_transform_edt(~mask)) * CELL
    return ndi.gaussian_filter(sd, 1.3)


# ---------------------------------------------------------------- coastline
COAST = [  # hand-drawn, clockwise from the north; nothing here is a circle
    (2, -78), (16, -86), (32, -90), (50, -84), (70, -76), (86, -62), (92, -42), (86, -24), (76, -10),
    (72, 2), (80, 14), (82, 30), (72, 44), (62, 54), (56, 68), (40, 76), (24, 78), (10, 88), (-6, 84),
    (-16, 72), (-28, 62), (-40, 54), (-54, 50), (-66, 54), (-72, 66), (-84, 64), (-92, 48), (-90, 30),
    (-82, 14), (-88, -4), (-90, -24), (-80, -40), (-68, -50), (-62, -66), (-46, -78), (-28, -80), (-14, -72),
]


def build_coast():
    poly = catmull(COAST, closed=True)
    img = Image.new("1", (N, N), 0)
    ImageDraw.Draw(img).polygon([(float(c), float(r)) for r, c in (g(x, z) for x, z in poly)], fill=1)
    d0 = signed_dist(np.array(img, bool))
    d1 = d0 + 6.0 * fbm(1, 30, 90) + 2.2 * fbm(2, 8, 28)
    mask = d1 > 0
    lab, n = ndi.label(mask)
    mask = lab == (1 + np.argmax(ndi.sum(mask, lab, range(1, n + 1))))
    mask = ndi.binary_fill_holes(mask)
    return signed_dist(mask)


# ---------------------------------------------------------------- land form
def build_land(d):
    wx, wz = X + 7 * fbm(3, 25, 80), Z + 7 * fbm(4, 25, 80)
    b = lambda *a, **k: blob(*a, xw=wx, zw=wz, **k)

    # character of the coast: 1 = sea cliff, or 1 = sandy beach; everything else is a grassy seaside bank
    cliff = np.clip(b(40, -88, 30, 16) + b(78, -70, 22) + b(94, -44, 18, 22) + 0.8 * b(-88, -22, 12, 20) + 0.7 * b(8, 90, 14, 10), 0, 1)
    beach = np.clip(b(-52, 52, 22, 16) + 0.9 * b(74, 2, 11, 10) + 0.8 * b(-48, -80, 14, 9) + 0.6 * b(30, 80, 12, 8), 0, 1) * (1 - cliff)

    hills = (
        20.0 * blob(56, -52, 29, 22, 25, X + 0.35 * (wx - X), Z + 0.35 * (wz - Z))  # Lookout Hill, the summit
        + 2.5 * b(34, -72, 18, 11, -15)      # north shoulder running out to the lookout headland
        + 5.0 * b(72, -30, 14, 18, 10)       # east spur falling toward the campfire banks
        + 4.5 * b(-12, -54, 26, 13, 8)       # wooded ridge behind the library
        + 2.0 * b(-6, -38, 9)                # library rise
        + 6.0 * b(-74, -24, 13, 20, -8)      # west headland above the lake
        + 3.0 * b(-70, 22, 12, 16)           # dune-backed rise west of the stream mouth
        + 5.0 * b(6, 74, 17, 13, 15)         # south head
        + 2.6 * b(40, 44, 20, 14, -30)       # meadow swell, south-east
        + 2.2 * b(-8, 40, 16, 12, 20)        # meadow swell, south
        + 1.6 * b(-24, 8, 9, 7, 30)          # the den's grassy mound country
        - 1.4 * b(-44, -10, 24, 18, 15)      # lake basin
        - 1.2 * b(58, 10, 10, 8)             # sheltered hollow for the campfire
    )
    south = sstep((Z + 10) / 50)
    rolls = (0.55 + 0.75 * south) * fbm(5, 14, 45) + 0.25 * fbm(6, 5, 14)
    base = 5.3 + 0.9 * fbm(7, 50, 140) + rolls + hills * (1 + 0.10 * fbm(8, 10, 40))
    base = np.maximum(base, 3.0)

    width = 9 + 22 * beach - 4.5 * cliff          # how far inland the coastal slope runs
    strip = 3.0 * (1 - beach) * (1 - cliff) + 0.5 * (1 - cliff)  # flat foreshore before the bank rises
    ramp = sstep((d - strip) / width)
    foreshore = np.minimum((0.09 + 0.22 * (1 - beach) + 0.6 * cliff) * np.maximum(d, 0), 1.0)
    dunes = 0.7 * beach * sstep((d - 12) / 6) * sstep((30 - d) / 8) * np.abs(fbm(9, 6, 16))
    land = foreshore + (base - 1.0) * ramp + dunes
    sea = -np.minimum(0.16 * np.maximum(-d, 0) * (1 + 0.8 * cliff), 7.0) + 0.25 * fbm(10, 10, 40) * sstep(-d / 12)
    h = np.where(d > 0, land, np.minimum(sea, -0.02))

    # a rock step on the hill's south-west flank, for the waterfall to drop over
    m = np.clip(1.6 * blob(38, -41, 12, 9, 35), 0, 1)
    hc = float(sample(ndi.gaussian_filter(h, 4), 38, -41)[0])
    lo, hi = hc - 4.0, hc + 4.0
    t = np.clip((h - lo) / (hi - lo), 0, 1)
    steep = lo + (hi - lo) * sstep(sstep(sstep(sstep(t))))
    h = h + m * (np.where((h > lo) & (h < hi), steep, h) - h)
    return h, cliff, beach


def erode(h, d, drops=70000, steps=80):
    """Light droplet erosion so slopes get drainage creases rather than staying mathematically smooth."""
    rng = np.random.default_rng(SEED + 50)
    hc = (h / CELL).copy()
    land = np.argwhere((d > 6) & (h > 3.0))
    p = land[rng.integers(0, len(land), drops)].astype(float) + rng.random((drops, 2))
    dr = np.zeros_like(p)
    vel = np.ones(drops)
    water = np.ones(drops)
    sed = np.zeros(drops)
    alive = np.ones(drops, bool)
    for _ in range(steps):
        i = np.clip(p[:, 0].astype(int), 0, N - 2)
        j = np.clip(p[:, 1].astype(int), 0, N - 2)
        fi, fj = p[:, 0] - i, p[:, 1] - j
        h00, h01, h10, h11 = hc[i, j], hc[i, j + 1], hc[i + 1, j], hc[i + 1, j + 1]
        gi = (h10 - h00) * (1 - fj) + (h11 - h01) * fj
        gj = (h01 - h00) * (1 - fi) + (h11 - h10) * fi
        hold = h00 * (1 - fi) * (1 - fj) + h01 * (1 - fi) * fj + h10 * fi * (1 - fj) + h11 * fi * fj
        dr = dr * 0.35 - np.stack([gi, gj], 1) * 0.65
        ln = np.hypot(dr[:, 0], dr[:, 1])
        alive &= ln > 1e-6
        dr /= np.maximum(ln, 1e-6)[:, None]
        q = p + dr
        alive &= (q[:, 0] > 1) & (q[:, 0] < N - 2) & (q[:, 1] > 1) & (q[:, 1] < N - 2) & (hold > 0.5 / CELL)
        hnew = ndi.map_coordinates(hc, [q[:, 0], q[:, 1]], order=1, mode="nearest")
        dh = hnew - hold
        cap = np.maximum(-dh, 0.01) * vel * water * 5.0
        dep = np.where(dh > 0, np.minimum(dh, sed), np.where(sed > cap, (sed - cap) * 0.3, 0.0))
        ero = np.where((dh <= 0) & (sed <= cap), np.minimum((cap - sed) * 0.25, -dh), 0.0)
        delta = (dep - ero) * alive
        for (a, b_), w in (((i, j), (1 - fi) * (1 - fj)), ((i, j + 1), (1 - fi) * fj), ((i + 1, j), fi * (1 - fj)), ((i + 1, j + 1), fi * fj)):
            np.add.at(hc, (a, b_), delta * w)
        sed += -delta
        vel = np.sqrt(np.maximum(vel ** 2 - dh * 3.0, 0.01))
        water *= 0.985
        p = np.where(alive[:, None], q, p)
    diff = ndi.gaussian_filter(hc * CELL - h, 1.6)
    return h + np.clip(diff, -1.4, 0.8) * sstep((d - 4) / 8)


# ---------------------------------------------------------------- water
LAKE_LEVEL = 3.0
SPRING = (50.5, -47.0)
STREAM_UPPER = [SPRING, (48, -43.5), (44, -44), (41, -42), (38, -41), (34.5, -38), (31.5, -33.5), (26, -32), (21.5, -27.5), (15, -27),
                (10, -23), (4, -22.5), (-1.5, -19.5), (-8, -21.5), (-13, -18), (-19, -18.5), (-24, -15.5), (-29, -16), (-34, -13.5)]
STREAM_LOWER = [(-55, -3), (-57, 3), (-55.5, 10), (-58, 17), (-61.5, 24), (-60, 31), (-62, 38), (-61, 45), (-62, 51), (-62, 58)]


def build_lake():
    wx, wz = X + 3 * fbm(20, 12, 40), Z + 3 * fbm(21, 12, 40)
    f = blob(-46, -12, 13, 8.5, 18, wx, wz) + 0.9 * blob(-37, -8, 7, 6, 0, wx, wz) + 0.9 * blob(-54, -7, 7.5, 6, -30, wx, wz) + 0.5 * blob(-50, -19, 6, 4, 0, wx, wz)
    return signed_dist(f > 0.42)  # positive inside the lake


def densify(pts, step=0.4):
    c = catmull(pts, per=40)
    seg = np.hypot(*np.diff(c, axis=0).T)
    s = np.concatenate([[0], np.cumsum(seg)])
    t = np.arange(0, s[-1], step)
    return np.stack([np.interp(t, s, c[:, 0]), np.interp(t, s, c[:, 1])], 1), t


def carve_stream(h, pts, start, end, depth, half0, half1, make_fall=False):
    line, s = densify(pts)
    ground = sample(h, line[:, 0], line[:, 1])
    bed = np.minimum.accumulate(np.minimum(ground - depth, start))
    bed = np.maximum(bed, end)
    fall = None
    if make_fall:
        win = int(7 / 0.4)
        drop = bed[:-win] - bed[win:]
        a = int(np.argmax(drop))
        lip = a + int(win * 0.8)
        bed[a:lip] = np.maximum(bed[a:lip], bed[a] - 0.25 * np.linspace(0, 1, lip - a))
        foot = lip + 3
        bed[foot:] = np.minimum(bed[foot:], bed[a + win] - 0.2)
        bed[lip:foot] = np.linspace(bed[lip - 1], bed[foot], foot - lip)
        bed = np.minimum.accumulate(bed)
        fall = dict(lip=line[lip - 1], foot=line[foot + 4], top=float(bed[lip - 1]), bottom=float(bed[foot]), i=foot + 4)
    half = np.linspace(half0, half1, len(line))
    if fall:  # plunge pool
        k = np.arange(len(line)) - fall["i"]
        half = half + 2.6 * np.exp(-(k * 0.4 / 3.0) ** 2) * (k > -6)
        bed = bed - 0.5 * np.exp(-(k * 0.4 / 3.0) ** 2) * (k > -6)
    dist, idx = cKDTree(line).query(np.stack([X.ravel(), Z.ravel()], 1))
    dist, idx = dist.reshape(N, N), idx.reshape(N, N)
    b, w = bed[idx], half[idx]
    side = b + np.maximum(dist - w, 0) * 0.55
    near = dist < w + 9
    h2 = np.where(near, np.minimum(h, side), h)
    water = (dist < w) & (h2 <= b + 1e-6)
    return h2, water, dict(line=line, bed=bed, half=half, s=s, fall=fall)


# ---------------------------------------------------------------- places
# id, name, x, z, pad radius (ground levelled for the model), kind, note
ENTITIES = [
    ("board", "Notice Board", 0, 0, 5.5, "place", "The village green: every lane starts here."),
    ("nook", "Den", -23, 21, 6.0, "place", "Dug into the lee of a grassy mound, door facing the morning sun."),
    ("well", "Well", 11, 9, 3.0, "place", "On the lane between the green and the garden."),
    ("garden", "Garden", 27, 23, 7.5, "place", "A gentle south-facing slope, sheltered from the sea wind by the meadow swell."),
    ("workshop", "Workshop", 35, -13, 6.5, "place", "At the forest edge, close to timber and to the stream."),
    ("library", "Little Library", -7, -38, 6.0, "place", "On a rise at the foot of the wooded ridge; library tower and Ash's computer."),
    ("jetty", "Lake Jetty", -31.5, -6.5, 0, "place", "Reaches out from the lake's east shore."),
    ("meadow", "Meadow", 8, 48, 9.0, "place", "The heart of the rolling southern meadows."),
    ("shore", "Shore", -52, 44, 0, "place", "The sandy bay. The stream reaches the sea at its west end."),
    ("beach_hut", "Beach Hut", -43, 39, 3.5, "place", "At the top of the sand, just above the dunes."),
    ("observatory", "Observatory", 56, -52, 5.0, "place", "The summit of Lookout Hill. The spring rises just below it."),
    ("lookout", "Lookout", 31, -78, 4.0, "place", "Cliff-top point on the north headland: telescope, pennant, the whole sea."),
    ("waterfall", "Waterfall", 0, 0, 0, "place", "The stream drops off the rock step into a plunge pool."),  # positioned from the carve
    ("campfire", "Campfire Circle", 58, 11, 4.5, "place", "A sheltered hollow on the east banks, looking over the cove."),
    ("bridge", "Stone Bridge", 0, 0, 0, "crossing", "Arched bridge carrying the north lane over the stream."),  # positioned from routing
]

# Named areas of the island, for labels and for Ash's descriptions
REGIONS = [
    ("Lookout Hill", 62, -44), ("Whisper Wood", 6, -50), ("Pine Slope", 44, -30), ("Lake", -47, -11),
    ("Rolling Meadows", 22, 60), ("Sandy Bay", -56, 56), ("East Banks", 70, 28), ("North Cliffs", 60, -84),
    ("West Banks", -78, 2), ("South Head", 6, 76), ("Village Green", 8, -6), ("Cove", 78, 3),
]


def level_pads(h, ents):
    for (_, _, x, z, r, _, _) in ents:
        if r <= 0:
            continue
        dist = np.hypot(X - x, Z - z)
        target = h[dist < r].mean()
        h = h + (target - h) * sstep((1.7 * r - dist) / (0.7 * r))
    return h


# ---------------------------------------------------------------- paths
# Extra junctions (not places): id, name, x, z
JUNCTIONS = [
    ("falls_foot", "Falls Foot", 0, 0),          # set from the carve
    ("lake_north", "North Shore", -44, -27),
    ("lake_west", "West Shore", -65, -11),
    ("outlet", "Outlet Stones", 0, 0),           # set from the carve
    ("saddle", "Hill Saddle", 45, -62),
    ("wood_gate", "Wood Gate", 14, -37),
    ("south_stile", "South Stile", -20, 52),
    ("east_stile", "East Stile", 56, 38),
    ("west_cove", "West Cove", -52, -68),
]

# id, name, from, to, via points, surface, tags, what it is like
ROUTES = [
    ("green_den", "Den Lane", "board", "nook", [], "cobble", ["main", "easy"], "The short cobbled lane home."),
    ("green_well", "Well Lane", "board", "well", [], "cobble", ["main", "easy"], "Cobbles down to the well."),
    ("well_garden", "Garden Lane", "well", "garden", [], "cobble", ["main", "easy"], "On from the well to the garden gate."),
    ("green_bridge", "North Lane", "board", "bridge", [], "cobble", ["main", "easy"], "From the green up to the stone bridge."),
    ("bridge_library", "Library Lane", "bridge", "library", [], "cobble", ["main", "easy"], "Over the bridge and up the rise to the library."),
    ("green_workshop", "Workshop Lane", "board", "workshop", [(18, -5)], "cobble", ["main", "easy"], "East along the stream meadows to the workshop."),
    ("green_jetty", "Lake Lane", "board", "jetty", [(-16, -6)], "cobble", ["main", "easy", "water"], "West to the lake and out along the jetty."),
    ("green_meadow", "Meadow Way", "board", "meadow", [(2, 24)], "dirt", ["main", "easy", "open"], "South through long grass into the meadows."),
    ("den_jetty", "Reed Path", "nook", "jetty", [(-33, 6)], "dirt", ["quiet", "water"], "A back way from the den to the lake through the reeds."),
    ("den_hut", "Sandy Track", "nook", "beach_hut", [(-34, 31)], "sand", ["easy", "sea"], "Down through the dunes to the beach hut."),
    ("den_stile", "Home Field Path", "nook", "south_stile", [], "dirt", ["quiet", "open"], "Across the home field to the south stile."),
    ("hut_stile", "Bay Path", "beach_hut", "south_stile", [(-30, 48)], "sand", ["sea"], "Along the back of the bay."),
    ("stile_meadow", "Clover Path", "south_stile", "meadow", [], "dirt", ["open", "easy"], "Over the swell into the middle of the meadow."),
    ("stile_head", "South Head Path", "south_stile", "meadow", [(-8, 68), (8, 74), (20, 64)], "dirt", ["sea", "view", "long"], "The long way: out round South Head above the sea."),
    ("hut_outlet", "Brookside", "beach_hut", "outlet", [(-53, 30), (-51, 14)], "dirt", ["water", "quiet"], "Follows the brook up from the bay to the lake's outlet."),
    ("outlet_jetty", "South Shore Path", "outlet", "jetty", [(-44, 1)], "dirt", ["water", "easy"], "Round the lake's south shore."),
    ("outlet_west", "Stepping Stones", "outlet", "lake_west", [], "stones", ["water", "careful"], "Across the outlet on stepping stones to the far shore."),
    ("west_north", "Far Shore Path", "lake_west", "lake_north", [(-60, -24)], "dirt", ["water", "quiet", "wood"], "The wild side of the lake under the west headland."),
    ("north_jetty", "Inflow Path", "lake_north", "jetty", [(-26, -21)], "dirt", ["water", "wood"], "Back to the jetty over the plank bridge where the stream runs in."),
    ("north_library", "Woodland Trail West", "lake_north", "library", [(-26, -36)], "trail", ["wood", "quiet"], "Under the trees between the lake and the library."),
    ("library_gate", "Woodland Trail East", "library", "wood_gate", [], "trail", ["wood"], "Through Whisper Wood on the stream's north bank."),
    ("gate_falls", "Falls Trail", "wood_gate", "falls_foot", [(25, -38)], "trail", ["wood", "water"], "Follows the sound of water to the plunge pool."),
    ("workshop_falls", "Mill Path", "workshop", "falls_foot", [(34, -27)], "dirt", ["water", "easy"], "Up the stream's south bank from the workshop to the stones below the falls."),
    ("falls_obs", "Falls Climb", "falls_foot", "observatory", [(40, -34), (47, -38.5), (54, -45)], "steps", ["steep", "view", "short"], "Steep and short: rock steps beside the falls, past the spring, to the summit."),
    ("workshop_obs", "Hill Road", "workshop", "observatory", [(50, -18), (66, -28), (60, -40), (66, -48)], "dirt", ["view", "steady"], "The steady way up, winding round the east spur."),
    ("obs_saddle", "Ridge Path", "observatory", "saddle", [], "dirt", ["view", "exposed"], "Down the north ridge to the saddle."),
    ("saddle_lookout", "Headland Path", "saddle", "lookout", [(38, -72)], "dirt", ["view", "exposed", "sea"], "Out along the headland to the lookout."),
    ("saddle_gate", "Pine Descent", "saddle", "wood_gate", [(28, -52)], "trail", ["wood", "steep"], "Drops off the saddle through the pines into the wood."),
    ("lookout_library", "Cliff Path", "lookout", "library", [(14, -70), (-4, -58)], "dirt", ["sea", "view", "exposed"], "Along the top of the north cliffs, then over the wooded ridge."),
    ("library_cove", "Ridge Trail", "library", "west_cove", [(-30, -56)], "trail", ["wood", "quiet"], "Along the wooded ridge to the little north-west cove."),
    ("cove_north", "Cove Path", "west_cove", "lake_north", [(-56, -46)], "dirt", ["sea", "quiet"], "From the cove back over to the lake."),
    ("west_banks", "West Banks Path", "lake_west", "hut_ford", [(-78, 2), (-74, 30)], "dirt", ["sea", "view", "long"], "High on the west banks, then down the dunes to the ford."),
    ("ford_hut", "The Ford", "hut_ford", "beach_hut", [], "sand", ["sea", "water", "careful"], "Paddle across the brook's mouth on the sand."),
    ("workshop_fire", "Cove Road", "workshop", "campfire", [(48, -2)], "dirt", ["easy"], "Down to the campfire hollow."),
    ("fire_obs", "East Spur Path", "campfire", "observatory", [(72, -10), (74, -32)], "dirt", ["sea", "view", "steep"], "Up the east spur with the sea below on the right."),
    ("fire_garden", "Banks Path", "campfire", "garden", [(46, 20)], "dirt", ["easy", "open"], "Inland from the banks to the garden."),
    ("fire_stile", "Sea Banks Walk", "campfire", "east_stile", [(68, 26)], "dirt", ["sea", "view"], "Along the top of the seaside banks."),
    ("garden_stile", "Hedge Path", "garden", "east_stile", [(42, 32)], "dirt", ["easy", "open"], "From the garden out to the east stile."),
    ("stile_meadow_e", "Skylark Path", "east_stile", "meadow", [(34, 50)], "dirt", ["open", "easy"], "Over the south-east swell into the meadow."),
    ("garden_meadow", "Bee Path", "garden", "meadow", [(18, 36)], "dirt", ["open", "easy", "short"], "The straight way between garden and meadow."),
    ("well_den", "Back Lane", "well", "nook", [(-6, 16)], "dirt", ["quiet", "easy"], "Skips the green: well to den behind the hedges."),
]
JUNCTIONS.append(("hut_ford", "Ford", 0, 0))  # set from the carve


def rdp(p, eps):
    if len(p) < 3:
        return p
    a, b = p[0], p[-1]
    ab = b - a
    n = np.hypot(*ab) or 1
    dist = np.abs(ab[0] * (p[:, 1] - a[1]) - ab[1] * (p[:, 0] - a[0])) / n
    i = int(np.argmax(dist))
    if dist[i] > eps:
        return np.vstack([rdp(p[: i + 1], eps)[:-1], rdp(p[i:], eps)])
    return np.vstack([a, b])


def resample(p, step):
    seg = np.hypot(*np.diff(p, axis=0).T)
    s = np.concatenate([[0], np.cumsum(seg)])
    t = np.linspace(0, s[-1], max(2, int(round(s[-1] / step)) + 1))
    return np.stack([np.interp(t, s, p[:, 0]), np.interp(t, s, p[:, 1])], 1)


def main(out):
    os.makedirs(out, exist_ok=True)
    d = build_coast()
    h, cliff, beach = build_land(d)
    h = erode(h, d)
    h = np.where(d > 0, np.maximum(h, 0.03), h)

    ents = [list(e) for e in ENTITIES]
    h = level_pads(h, [e for e in ents if e[0] not in ("observatory",)])
    # the summit pad is levelled last so the observatory really is the top
    h = level_pads(h, [e for e in ents if e[0] == "observatory"])

    # lake
    ls = build_lake()
    rim = LAKE_LEVEL + 0.15
    shore = np.minimum(np.maximum(h, rim + 0.35 * sstep(-ls / 5)), rim + 0.5 * -ls)
    h = np.where(ls <= 0, h + (shore - h) * (1 - sstep((-ls - 6) / 10)), h)
    h = np.where(ls > 0, LAKE_LEVEL - np.minimum(0.3 + 0.32 * ls, 2.4), h)
    lake = ls > 0

    # streams
    h, w1, up = carve_stream(h, STREAM_UPPER, 99, LAKE_LEVEL + 0.02, 0.35, 0.55, 1.2, make_fall=True)
    lo_line, _ = densify(STREAM_LOWER)
    h, w2, low = carve_stream(h, STREAM_LOWER, LAKE_LEVEL - 0.05, -0.3, 0.3, 1.2, 2.2)
    # the lower brook has to reach the sea: grade its bed from lake level to the tide line
    stream = (w1 | w2) & ~lake & (d > 0)
    h = np.where(lake, np.minimum(h, LAKE_LEVEL - 0.3), h)

    fall = up["fall"]
    for e in ents:
        if e[0] == "waterfall":
            e[2], e[3] = float(fall["foot"][0]), float(fall["foot"][1])
    juncs = {j[0]: [j[1], j[2], j[3]] for j in JUNCTIONS}
    # falls foot: stepping stones a little downstream of the pool
    k = fall["i"] + int(9 / 0.4)
    juncs["falls_foot"][1:] = [float(up["line"][k][0]), float(up["line"][k][1])]
    k = int(8 / 0.4)
    juncs["outlet"][1:] = [float(low["line"][k][0]), float(low["line"][k][1])]
    ford_i = int(np.argmin(np.abs(low["line"][:, 1] - 47.5)))
    juncs["hut_ford"][1:] = [float(low["line"][ford_i][0]), float(low["line"][ford_i][1])]

    # ---- routing
    gz, gx = np.gradient(ndi.gaussian_filter(h, 1.5), CELL)
    slope = np.hypot(gx, gz)
    cost = 1 + 6 * sstep((1.2 - h) / 0.8) * (1 - beach)
    cost = cost * (1 - 0.25 * np.clip(beach, 0, 1) * 0)  # sand is neither preferred nor avoided
    wet = lake | (ndi.binary_dilation(stream, iterations=2)) | (h < 0.25)
    crossings = {}

    def open_crossing(key, name, kind, x, z, r=3.2):
        crossings[key] = dict(id=key, name=name, kind=kind, x=round(x, 2), z=round(z, 2))
        wet[np.hypot(X - x, Z - z) < r] = False

    # stone bridge: where the north lane (x ~ -1) meets the stream
    bi = int(np.argmin(np.hypot(up["line"][:, 0] + 1.5, up["line"][:, 1] + 19.5)))
    bx, bz = up["line"][bi]
    tang = up["line"][bi + 3] - up["line"][bi - 3]
    for e in ents:
        if e[0] == "bridge":
            e[2], e[3] = float(bx), float(bz)
    open_crossing("bridge", "Stone Bridge", "bridge", bx, bz)
    open_crossing("falls_foot", "Falls Stones", "stepping_stones", *juncs["falls_foot"][1:])
    open_crossing("outlet", "Outlet Stones", "stepping_stones", *juncs["outlet"][1:])
    open_crossing("hut_ford", "The Ford", "ford", *juncs["hut_ford"][1:], r=4.0)
    pi_ = int(np.argmin(np.hypot(up["line"][:, 0] + 24, up["line"][:, 1] + 15.5)))
    open_crossing("plank", "Plank Bridge", "footbridge", *up["line"][pi_])
    # jetty: let the lake lane reach out over the water
    jx, jz = next((e[2], e[3]) for e in ents if e[0] == "jetty")
    wet[np.hypot(X - jx, Z - jz) < 2.5] = False
    cost = np.where(wet, 1e6, cost)
    slope2 = np.where(wet, 0, slope ** 2)
    for e in ents:  # do not route straight through somebody else's building
        if e[4] > 0:
            cost += 4 * blob(e[2], e[3], e[4] * 0.6)

    nodes = {e[0]: (e[2], e[3]) for e in ents}
    nodes.update({k_: (v[1], v[2]) for k_, v in juncs.items()})
    subs = {k_: (cost + k_ * slope2)[::2, ::2] for k_ in (30, 90)}

    def rc(x, z):
        return int(round((z + HALF) / (2 * CELL))), int(round((x + HALF) / (2 * CELL)))

    routes = []
    for rid, name, a, b_, via, surface, tags, about in ROUTES:
        stops = [nodes[a]] + via + [nodes[b_]]
        cells = []
        for p0, p1 in zip(stops[:-1], stops[1:]):
            mcp = MCP_Geometric(subs[30 if surface == 'cobble' else 90])
            mcp.find_costs([rc(*p0)], [rc(*p1)])
            tb = mcp.traceback(rc(*p1))
            cells += tb if not cells else tb[1:]
        pts = np.array([(c * 2 * CELL - HALF, r * 2 * CELL - HALF) for r, c in cells], float)
        pts[0], pts[-1] = nodes[a], nodes[b_]
        pts = rdp(pts, 1.3)
        while len(pts) > 3:  # drop hairpin spikes left where a via point sat off the natural line
            v0, v1 = pts[1:-1] - pts[:-2], pts[2:] - pts[1:-1]
            cosang = (v0 * v1).sum(1) / (np.hypot(*v0.T) * np.hypot(*v1.T) + 1e-9)
            if cosang.min() > -0.5:
                break
            pts = np.delete(pts, 1 + int(np.argmin(cosang)), axis=0)
        for _ in range(2):  # Chaikin corner cutting, endpoints kept
            q = np.empty((2 * len(pts) - 2, 2))
            q[0::2], q[1::2] = 0.75 * pts[:-1] + 0.25 * pts[1:], 0.25 * pts[:-1] + 0.75 * pts[1:]
            pts = np.vstack([pts[0], q, pts[-1]])
        pts = resample(pts, 2.0)
        routes.append(dict(id=rid, name=name, **{"from": a, "to": b_}, surface=surface, tags=tags, about=about, pts=pts))

    # bench the paths into the slope a little so they read as trodden ground
    allp = np.vstack([resample(r["pts"], 0.5) for r in routes])
    yp = ndi.gaussian_filter(h, 2.0)
    dist, idx = cKDTree(allp).query(np.stack([X.ravel(), Z.ravel()], 1), distance_upper_bound=4.0)
    dist = dist.reshape(N, N)
    target = np.append(sample(yp, allp[:, 0], allp[:, 1]), 0)[idx].reshape(N, N)
    wgt = sstep((3.2 - dist) / 2.2) * (~lake) * (~stream) * (h > 0.3)
    h = h + (np.where(np.isfinite(dist), target, h) - h) * wgt * 0.8
    path_dist = dist

    for r in routes:
        p = r["pts"]
        y = sample(h, p[:, 0], p[:, 1])
        dy = np.diff(y)
        seg = np.hypot(*np.diff(p, axis=0).T)
        r.update(length=float(seg.sum()), ascent=float(dy[dy > 0].sum()), descent=float(-dy[dy < 0].sum()),
                 steepest=float(np.max(np.abs(dy) / np.maximum(seg, 1e-6))), y=y,
                 wet=int(np.sum(sample((lake | stream).astype(float), p[:, 0], p[:, 1]) > 0.5)))

    # ---- biomes
    gz, gx = np.gradient(h, CELL)
    slope = np.hypot(gx, gz)
    wx, wz = X + 6 * fbm(30, 15, 50), Z + 6 * fbm(31, 15, 50)
    fb = lambda *a: blob(*a, xw=wx, zw=wz)
    forest_f = (fb(6, -50, 30, 15, 6) + fb(-28, -40, 20, 14, -20) + fb(30, -36, 16, 9, 20) + 0.9 * fb(44, -22, 12, 12, 0)
                + 0.9 * fb(40, -62, 14, 9, -20) + 0.8 * fb(-64, -22, 9, 16, 0) + 0.7 * fb(46, 6, 9, 7, 0) + 0.7 * fb(-36, 14, 7, 9, 0)
                + 0.6 * fb(22, 6, 6, 5, 0) + 0.25 * fbm(32, 6, 20))
    clear = np.ones_like(h, bool)
    for e in ents:
        if e[4] > 0:
            clear &= np.hypot(X - e[2], Z - e[3]) > e[4] * 1.25
    forest = (forest_f > 0.36) & (d > 6) & (slope < 0.9) & clear & ~lake & (ndi.distance_transform_edt(~(lake | stream)) * CELL > 2.5) & (h > 2.0)
    meadow = (sstep((Z - 14) / 16) * (1 - beach) + fb(40, 44, 22, 16, -30) > 0.55) & (d > 10)
    sand = (d > 0) & (beach > 0.3) & (h < 2.1) & (d < 34)
    shingle = (d > 0) & (h < 1.0) & ~sand
    rock = (d > 0) & (slope > 1.0) & (h > 1.0)
    biome = np.full((N, N), 5, np.uint8)                  # 5 grass
    biome[meadow] = 4                                     # 4 flower meadow
    biome[forest] = 6                                     # 6 woodland
    biome[shingle] = 3
    biome[sand] = 2
    biome[rock] = 7
    biome[d <= 0] = 1                                     # 1 shallows
    biome[(d <= 0) & (h < -2.5)] = 0                      # 0 deep sea
    biome[lake] = 8
    biome[stream] = 9
    BIOMES = ["deep_sea", "shallows", "sand", "shingle", "meadow", "grass", "woodland", "rock", "lake", "stream"]

    # ---- trees
    rng = np.random.default_rng(SEED + 70)
    trees = []
    taken = np.zeros((0, 2))
    cand = np.argwhere(forest & (path_dist > 2.2))
    rng.shuffle(cand)
    pts_t = []
    grid = {}
    for r, c in cand[:60000]:
        x, z = xs[c] + rng.uniform(-0.25, 0.25), xs[r] + rng.uniform(-0.25, 0.25)
        key = (int(x // 3.0), int(z // 3.0))
        if any(math.hypot(x - px, z - pz) < 3.0 for dx in (-1, 0, 1) for dz in (-1, 0, 1) for px, pz in grid.get((key[0] + dx, key[1] + dz), [])):
            continue
        grid.setdefault(key, []).append((x, z))
        y = float(h[r, c])
        pine = y > 8.5 + rng.normal(0, 1.5) or (cliff[r, c] > 0.5 and rng.random() < 0.6)
        trees.append(dict(x=round(x, 2), z=round(z, 2), y=round(y, 2), kind="pine" if pine else "tree", scale=round(float(rng.uniform(0.8, 1.25)), 2)))
    # a few lone trees in the open country
    opens = np.argwhere(np.isin(biome, (4, 5)) & (path_dist > 3) & clear & (d > 12) & (slope < 0.4))
    for r, c in opens[rng.choice(len(opens), 400, replace=False)]:
        x, z = float(xs[c]), float(xs[r])
        key = (int(x // 9), int(z // 9))
        if key in grid or len([t for t in trees if t.get("lone")]) >= 38:
            continue
        grid[key] = [(x, z)]
        trees.append(dict(x=x, z=z, y=round(float(h[r, c]), 2), kind="tree", scale=round(float(rng.uniform(0.9, 1.3)), 2), lone=True))

    # ---- write
    h = np.clip(h, H_MIN, H_MAX)
    Image.fromarray(np.round((h - H_MIN) / (H_MAX - H_MIN) * 65535).astype(np.uint16)).save(os.path.join(out, "island-heightmap.png"))
    h.astype("<f4").tofile(os.path.join(out, "island-heightmap.f32"))
    Image.fromarray(biome).save(os.path.join(out, "island-biomes.png"))
    np.savez_compressed(os.path.join(out, "_work.npz"), h=h, d=d, biome=biome, lake=lake, stream=stream, slope=slope, beach=beach, cliff=cliff)

    def yat(x, z):
        return round(float(sample(h, x, z)[0]), 2)

    def poly(line, y=None, n=1):
        return [[round(float(p[0]), 2), round(float(y[i]) if y is not None else yat(p[0], p[1]), 2), round(float(p[1]), 2)] for i, p in enumerate(line)][::n]

    lake_contour = None
    try:
        from skimage import measure
        c = max(measure.find_contours(ls, 0.0), key=len)[::6]
        lake_contour = [[round(float(cc * CELL - HALF), 2), round(float(rr * CELL - HALF), 2)] for rr, cc in c]
    except Exception:
        pass
    coast_c = max(measure.find_contours(d, 0.0), key=len)[::4]

    data = dict(
        version=1,
        about="Ash's island topography. x east, z south, metres from the Notice Board; y is metres above sea level.",
        seed=SEED,
        grid=dict(samples=N, world_m=WORLD, cell_m=CELL, origin="row 0 = north edge (z=-128), column 0 = west edge (x=-128)",
                  heightmap_png="island-heightmap.png", png_encoding=dict(bits=16, min_m=H_MIN, max_m=H_MAX),
                  heightmap_f32="island-heightmap.f32", f32_encoding="little-endian float32 metres, row-major, 513 x 513",
                  biome_png="island-biomes.png", biome_ids=BIOMES),
        sea_level=0.0,
        summit=dict(x=float(X.ravel()[h.argmax()]), z=float(Z.ravel()[h.argmax()]), y=round(float(h.max()), 2)),
        entities=[dict(id=e[0], name=e[1], x=round(e[2], 2), z=round(e[3], 2), y=yat(e[2], e[3]), pad_radius=e[4], kind=e[5], note=e[6]) for e in ents],
        junctions=[dict(id=k_, name=v[0], x=round(v[1], 2), z=round(v[2], 2), y=yat(v[1], v[2])) for k_, v in juncs.items()],
        regions=[dict(name=n_, x=x, z=z) for n_, x, z in REGIONS],
        water=dict(
            lake=dict(level=LAKE_LEVEL, max_depth=2.4, outline=lake_contour),
            spring=dict(x=SPRING[0], z=SPRING[1], y=yat(*SPRING)),
            streams=[
                dict(id="upper", name="Hill Stream", **{"from": "spring", "to": "lake"}, points=poly(up["line"], up["bed"] + 0.12, 5), half_width=[round(float(v), 2) for v in up["half"][::5]]),
                dict(id="lower", name="The Brook", **{"from": "lake", "to": "sea"}, points=poly(low["line"], low["bed"] + 0.12, 5), half_width=[round(float(v), 2) for v in low["half"][::5]]),
            ],
            waterfall=dict(lip=[round(float(fall["lip"][0]), 2), round(fall["top"] + 0.12, 2), round(float(fall["lip"][1]), 2)],
                           foot=[round(float(fall["foot"][0]), 2), round(fall["bottom"] + 0.12, 2), round(float(fall["foot"][1]), 2)],
                           drop_m=round(fall["top"] - fall["bottom"], 2)),
            crossings=[dict(c, y=yat(c["x"], c["z"])) for c in crossings.values()] + [],
            bridge_heading_deg=round(math.degrees(math.atan2(tang[0], -tang[1])) % 180, 1),
        ),
        paths=dict(
            note="Each route joins two nodes (an entity id or a junction id). Routes can be walked either way; ascent and descent are given from 'from' to 'to'.",
            routes=[dict(id=r["id"], name=r["name"], **{"from": r["from"], "to": r["to"]}, surface=r["surface"], tags=r["tags"], about=r["about"],
                         length_m=round(r["length"], 1), ascent_m=round(r["ascent"], 1), descent_m=round(r["descent"], 1), steepest_grade=round(r["steepest"], 2),
                         points=poly(r["pts"], r["y"])) for r in routes],
        ),
        coastline=[[round(float(cc * CELL - HALF), 2), round(float(rr * CELL - HALF), 2)] for rr, cc in coast_c],
        trees=[{k_: v for k_, v in t.items() if k_ != "lone"} for t in trees],
    )
    with open(os.path.join(out, "island-topography.json"), "w") as f:
        json.dump(data, f, separators=(",", ":"))

    # ---- report
    land = d > 0
    print(f"land area {land.sum() * CELL * CELL / 1e4:.2f} ha, extent x {X[land].min():.0f}..{X[land].max():.0f}, z {Z[land].min():.0f}..{Z[land].max():.0f}")
    print(f"summit {data['summit']}, waterfall drop {data['water']['waterfall']['drop_m']} m at {data['water']['waterfall']['foot']}")
    print("biome share of land:", {b: round(float((biome[land] == i).mean()), 3) for i, b in enumerate(BIOMES) if i >= 2})
    for e in data["entities"]:
        print(f"  {e['id']:12s} x {e['x']:7.1f} z {e['z']:7.1f} y {e['y']:6.2f}")
    for r in data["paths"]["routes"]:
        w = next(q["wet"] for q in routes if q["id"] == r["id"])
        print(f"  {r['id']:16s} {r['length_m']:6.1f} m  +{r['ascent_m']:5.1f} -{r['descent_m']:5.1f}  steepest {r['steepest_grade']:.2f}  wet pts {w}")
    print("trees", len(trees), "| bed upper", up["bed"][0].round(2), "->", up["bed"][-1].round(2), "| lower", low["bed"][0].round(2), "->", low["bed"][-1].round(2))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "..", "world", "topography"))
