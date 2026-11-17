import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import memo_lib as L, memo_walls as MWL
out = sys.argv[sys.argv.index('--') + 1]
os.makedirs(out, exist_ok=True)
L.foliage_mat(out)
for a in MWL.build_walls():
    e = L.export_asset(a, out)
    print('BUILT', a.name, e['triangles'], e['bytes'] // 1024, 'KB', e['size'])
