"""Draw the topography map (and a tilted preview) from the generator's output.

Run:  python3 tools/topography/render.py [dir]
"""
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LightSource, ListedColormap, to_rgb
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from scipy import ndimage as ndi

out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "..", "world", "topography")
w = np.load(os.path.join(out, "_work.npz"))
data = json.load(open(os.path.join(out, "island-topography.json")))
h, d, biome = w["h"], w["d"], w["biome"]
N = h.shape[0]
HALF = data["grid"]["world_m"] / 2
ext = [-HALF, HALF, HALF, -HALF]
xs = np.linspace(-HALF, HALF, N)

INK = "#4a3b2e"
COL = {0: "#7fb6c2", 1: "#a5d3d2", 2: "#f1e2b8", 3: "#d6cdb9", 4: "#c9dc8f", 5: "#a9cf7c", 6: "#7fb06a", 7: "#b9ae9f", 8: "#6bbccb", 9: "#6bbccb"}
SURF = {"cobble": ("#8a6f55", "-", 2.6), "dirt": ("#9c7a4f", "-", 1.7), "trail": ("#6e5a3c", (0, (4, 2)), 1.6),
        "sand": ("#b8935a", (0, (1, 1.6)), 1.9), "steps": ("#7a4b3a", (0, (2, 1)), 2.2), "stones": ("#55626b", (0, (0.6, 1.6)), 2.6)}
halo = [pe.withStroke(linewidth=3, foreground="#fffaf0", alpha=0.9)]


def base_rgb():
    rgb = np.zeros((N, N, 3))
    for k, c in COL.items():
        rgb[biome == k] = to_rgb(c)
    rgb = ndi.gaussian_filter(rgb, (1.2, 1.2, 0))
    land = d > 0
    # higher ground slightly warmer and paler, like an old hand-tinted survey sheet
    t = np.clip((h - 4) / 20, 0, 1)[..., None] * land[..., None] * (np.isin(biome, (4, 5, 6)))[..., None]
    rgb = rgb * (1 - 0.35 * t) + np.array(to_rgb("#efe2b4")) * 0.35 * t
    ls = LightSource(azdeg=315, altdeg=42)
    shade = ls.hillshade(np.where(land, h, 0), vert_exag=2.2, dx=0.5, dy=0.5)
    shade = 0.62 + 0.5 * shade
    rgb = np.clip(rgb * np.where(land, shade, 1)[..., None], 0, 1)
    # depth bands in the sea
    sea = d <= 0
    t = np.clip(-ndi.gaussian_filter(h, 3) / 7, 0, 1)[..., None]
    t = np.round(t * 5) / 5 * 0.6 + t * 0.4  # soft depth bands
    rgb = np.where(sea[..., None], np.array(to_rgb("#b4dcd8")) * (1 - t) + np.array(to_rgb("#6fa3b3")) * t, rgb)
    return rgb


def draw_map(path, size=15, dpi=150):
    fig = plt.figure(figsize=(size, size), facecolor="#f6efe0")
    ax = fig.add_axes([0.035, 0.035, 0.93, 0.93])
    ax.imshow(base_rgb(), extent=ext, interpolation="bilinear")
    hs = ndi.gaussian_filter(h, 1.0)
    land_h = np.where(d > -1, hs, np.nan)
    ax.contour(xs, xs, land_h, levels=np.arange(1, 30, 1), colors=INK, linewidths=0.35, alpha=0.38)
    cs = ax.contour(xs, xs, land_h, levels=np.arange(5, 30, 5), colors=INK, linewidths=0.95, alpha=0.6)
    ax.clabel(cs, fmt="%d m", fontsize=7, colors=INK)
    ax.contour(xs, xs, d, levels=[0], colors="#5b6f73", linewidths=1.3)
    ax.contour(xs, xs, w["lake"].astype(float), levels=[0.5], colors="#3f8796", linewidths=1.0)

    for s in data["water"]["streams"]:
        p = np.array(s["points"])
        ax.plot(p[:, 0], p[:, 2], color="#3f8796", lw=3.0, solid_capstyle="round", zorder=3)
        ax.plot(p[:, 0], p[:, 2], color="#7fd0dc", lw=1.7, solid_capstyle="round", zorder=3)

    for t in data["trees"]:
        pine = t["kind"] == "pine"
        ax.plot(t["x"], t["z"], marker="^" if pine else "o", ms=(5.0 if pine else 5.6) * t["scale"], color="#3f7650" if pine else "#5c9a55",
                mec="#2f5a3d", mew=0.3, alpha=0.75, zorder=4)

    for r in data["paths"]["routes"]:
        p = np.array(r["points"])
        c, ls_, lw = SURF[r["surface"]]
        ax.plot(p[:, 0], p[:, 2], color="#fff7e6", lw=lw + 1.6, alpha=0.85, solid_capstyle="round", zorder=5)
        ax.plot(p[:, 0], p[:, 2], color=c, lw=lw, ls=ls_, zorder=6)

    for c in data["water"]["crossings"]:
        ax.plot(c["x"], c["z"], marker="s" if "bridge" in c["kind"] else "o", ms=7, color="#fff7e6", mec=INK, mew=1.2, zorder=8)
    for j in data["junctions"]:
        ax.plot(j["x"], j["z"], "o", ms=4.5, color="#fff7e6", mec=INK, mew=1.0, zorder=8)
    wf = data["water"]["waterfall"]
    ax.plot([wf["lip"][0], wf["foot"][0]], [wf["lip"][2], wf["foot"][2]], color="white", lw=4, zorder=7, solid_capstyle="round")

    OFF = {"board": (0, 5.5), "nook": (-1, 6), "well": (5, 4), "garden": (6, 7), "workshop": (9, 4.5), "library": (-10, -5), "jetty": (2, -4.5),
           "meadow": (0, 7), "shore": (0, 7), "beach_hut": (9, 4), "observatory": (10, -5), "lookout": (9, -5), "waterfall": (-12, -5),
           "campfire": (10, 6), "bridge": (9, -3.5)}
    for e in data["entities"]:
        if e["id"] != "shore":
            ax.plot(e["x"], e["z"], marker="D" if e["kind"] == "place" else "s", ms=8.5, color="#c8553d", mec="#fff7e6", mew=1.4, zorder=9)
        ox, oz = OFF.get(e["id"], (0, 5))
        ax.text(e["x"] + ox, e["z"] + oz, f"{e['name']}\n", ha="center", va="center", fontsize=10.5, weight="bold", color=INK, path_effects=halo, zorder=10, linespacing=0.9)
        ax.text(e["x"] + ox, e["z"] + oz + 1.6, f"{e['y']:.1f} m", ha="center", va="center", fontsize=7.5, color=INK, path_effects=halo, zorder=10)
    for reg in data["regions"]:
        ax.text(reg["x"], reg["z"], reg["name"].upper(), ha="center", va="center", fontsize=8.5, style="italic", color="#5d6b4f" if reg["name"] not in ("Cove", "Sandy Bay", "North Cliffs", "Lake") else "#3b6f7a",
                alpha=0.95, path_effects=[pe.withStroke(linewidth=2.5, foreground="#fffaf0", alpha=0.7)], zorder=7)
    for j in data["junctions"]:
        ax.text(j["x"], j["z"] - 2.6, j["name"], ha="center", fontsize=6.5, color=INK, path_effects=halo, zorder=9)
    s = data["water"]["spring"]
    ax.plot(s["x"], s["z"], marker="*", ms=11, color="#7fd0dc", mec="#3f8796", zorder=9)
    ax.text(s["x"] - 6, s["z"] + 3.6, "Spring", fontsize=7.5, color="#3f8796", path_effects=halo, zorder=9)

    # furniture
    ax.set_xlim(-108, 108)
    ax.set_ylim(104, -108)
    ax.set_xticks(range(-100, 101, 20))
    ax.set_yticks(range(-100, 101, 20))
    ax.tick_params(labelsize=7, colors=INK, length=3)
    ax.grid(color=INK, alpha=0.10, lw=0.5)
    for sp in ax.spines.values():
        sp.set_color(INK)
    ax.plot([-100, -60], [98, 98], color=INK, lw=3, solid_capstyle="butt")
    ax.plot([-90, -80], [98, 98], color="#f6efe0", lw=1.6, solid_capstyle="butt")
    ax.plot([-70, -60], [98, 98], color="#f6efe0", lw=1.6, solid_capstyle="butt")
    ax.text(-80, 95.5, "40 metres", ha="center", fontsize=8, color=INK)
    ax.annotate("N", xy=(98, -100), xytext=(98, -86), ha="center", fontsize=13, weight="bold", color=INK, arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.6))
    ax.text(-104, -101, "Ash's Island", fontsize=24, weight="bold", color=INK, family="serif", path_effects=halo)
    ax.text(-104, -95.5, "Topography, places and paths.  Contours every 1 m, bold every 5 m.  x east, z south, metres from the Notice Board.", fontsize=8.5, color=INK, path_effects=halo)
    hd = [Line2D([], [], color=SURF[k][0], ls=SURF[k][1], lw=SURF[k][2], label=lab) for k, lab in
          (("cobble", "Cobbled lane"), ("dirt", "Footpath"), ("trail", "Woodland trail"), ("sand", "Sand track"), ("steps", "Rock steps"), ("stones", "Stepping stones"))]
    hd += [Line2D([], [], marker="D", ls="", ms=8, color="#c8553d", mec="#fff7e6", label="Place"), Line2D([], [], marker="o", ls="", ms=5, color="#fff7e6", mec=INK, label="Junction or crossing")]
    hd += [Patch(fc=COL[k], ec=INK, lw=0.4, label=lab) for k, lab in ((4, "Flower meadow"), (5, "Grass"), (6, "Woodland"), (2, "Sand"), (3, "Shingle"), (7, "Rock and cliff"))]
    leg = ax.legend(handles=hd, loc="lower right", fontsize=8, ncol=2, frameon=True, facecolor="#fbf6ea", edgecolor=INK, framealpha=0.95)
    for t in leg.get_texts():
        t.set_color(INK)
    fig.savefig(path, dpi=dpi, facecolor=fig.get_facecolor())
    plt.close(fig)


def draw_3d(path):
    fig = plt.figure(figsize=(14, 9), facecolor="#b4dcd8")
    ax = fig.add_axes([0, 0, 1, 1], projection="3d", facecolor="#b4dcd8")
    st = 2
    hh = np.maximum(h, 0)[::st, ::st]
    rgb = base_rgb()[::st, ::st]
    xx, zz = np.meshgrid(xs[::st], xs[::st])
    ax.plot_surface(xx, -zz, hh, facecolors=rgb, rstride=1, cstride=1, linewidth=0, antialiased=False, shade=False)
    for r in data["paths"]["routes"]:
        p = np.array(r["points"])
        ax.plot(p[:, 0], -p[:, 2], p[:, 1] + 0.25, color="#7a5c3c", lw=1.1, zorder=10)
    ax.set_box_aspect((1, 1, 0.2), zoom=2.05)
    ax.set_zlim(0, 34)
    ax.view_init(elev=40, azim=-105)
    ax.set_axis_off()
    fig.savefig(path, dpi=130, facecolor=fig.get_facecolor())
    plt.close(fig)


draw_map(os.path.join(out, "island-topography-map.png"))
draw_3d(os.path.join(out, "island-topography-tilted.png"))
print("drawn")
