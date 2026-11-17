import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import memo_lib as L, memo_trees as MT
out = sys.argv[sys.argv.index('--') + 1]
os.makedirs(out, exist_ok=True)
L.foliage_mat(out)
fn, name, kw = MT.TREES[0]
e = L.export_asset(fn(name, **kw), out)
print('BUILT', name, e['triangles'], e['bytes'] // 1024, 'KB', e['size'], e['optional_nodes'])
