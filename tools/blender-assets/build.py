"""Build every model.

blender -b --factory-startup --python build.py -- <what> <out_dir>
  what: all | trees | walls | world | extra | ash   (comma separated)
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import memo_lib as L  # noqa: E402

argv = sys.argv[sys.argv.index('--') + 1:]
what, out = set(argv[0].split(',')), os.path.abspath(argv[1])   # absolute, so shared textures resolve
os.makedirs(out, exist_ok=True)
L.foliage_mat(out)
entries = []


def emit(asset):
    e = {'name': asset.name, **L.export_asset(asset, out)}
    entries.append(e)
    print(f"BUILT {asset.name}: {e['triangles']} tris, {e['bytes'] / 1024:.0f} KB, size {e['size']}")


def want(k):
    return 'all' in what or k in what


if want('ash'):
    import memo_ash as MA
    ao = L.AO_STRENGTH
    L.AO_STRENGTH = 0.3
    for stage in MA.STAGES:
        emit(MA.build_ash('memo_' + stage, stage))
    L.AO_STRENGTH = ao
if want('trees'):
    import memo_trees as MT
    for asset in MT.build_trees():
        emit(asset)
if want('walls'):
    import memo_walls as MWL
    for asset in MWL.build_walls():
        emit(asset)
if want('world'):
    import memo_world as MW
    for asset in MW.build_all():
        emit(asset)
if want('extra'):
    import memo_extra as MX
    for asset in MX.build_extra():
        emit(asset)

path = os.path.join(out, 'manifest.json')
old = []
if os.path.exists(path):
    old = [m for m in json.load(open(path))['models'] if m['name'] not in {e['name'] for e in entries}]
json.dump({'units': 'metres', 'up': '+Y', 'front': '+Z', 'origin': 'ground centre',
           'textures': 'shared, in _tex/ (referenced by the .gltf models)',
           'models': old + entries}, open(path, 'w'), indent=1)
