"""Build GLB assets.

blender -b --factory-startup --python build.py -- <what> <out_dir>
  what: concepts | memo:<design> | world | all:<design>
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import memo_lib as L  # noqa: E402
import memo_char as MC  # noqa: E402

argv = sys.argv[sys.argv.index('--') + 1:]
what, out = argv[0], argv[1]
os.makedirs(out, exist_ok=True)
entries = []


def emit(asset):
    e = L.export_asset(asset, out)
    e = {'name': asset.name, **e}
    entries.append(e)
    print(f"BUILT {asset.name}: {e['triangles']} tris, {e['bytes'] / 1024:.0f} KB, size {e['size']}")


if what == 'concepts':
    for key in MC.DESIGNS:
        emit(MC.build_memo('concept_' + key, key, 'childlike'))
else:
    kind, _, design = what.partition(':')
    if kind in ('memo', 'all'):
        for stage in MC.STAGES:
            emit(MC.build_memo('memo_' + stage, design or 'mossball', stage))
    if kind in ('world', 'all'):
        import memo_world as MW
        for asset in MW.build_all():
            emit(asset)

if what != 'concepts':
    path = os.path.join(out, 'manifest.json')
    old = []
    if os.path.exists(path):
        old = [m for m in json.load(open(path))['models'] if m['name'] not in {e['name'] for e in entries}]
    json.dump({'units': 'metres', 'up': '+Y', 'front': '+Z', 'origin': 'ground centre',
               'models': old + entries}, open(path, 'w'), indent=1)
