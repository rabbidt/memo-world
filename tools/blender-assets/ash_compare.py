"""Lay Ash's orthographic renders over the character sheet views (plain Python + Pillow).

python ash_compare.py out_dir
Each row: sheet view | render at the same scale | render outline drawn over the sheet.
"""
import os
import sys

from PIL import Image, ImageChops, ImageFilter

out = sys.argv[1]
sheet = Image.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ash_ref', 'sheet.png')).convert('RGB')
K = 2                      # enlarge the sheet crops
CHAR_PX = 375 * K          # the character's height on the enlarged sheet
REN = int(1000 * CHAR_PX / (1000 / 1.15))   # the 1000 px render covers 1.15 heights
# view: sheet crop box, x of the body centre line, y of the soles
VIEWS = {'front': ((352, 80, 690, 490), 508, 470), 'side': ((690, 80, 1012, 490), 845, 470)}
rows = []
for name, (crop, cx, soles) in VIEWS.items():
    ref = sheet.crop(crop).resize(((crop[2] - crop[0]) * K, (crop[3] - crop[1]) * K), Image.LANCZOS)
    ren = Image.open(os.path.join(out, f'ortho_{name}.png')).convert('RGBA').resize((REN, REN), Image.LANCZOS)
    ox = (cx - crop[0]) * K - REN // 2
    oy = (soles - crop[1]) * K - (REN // 2 + CHAR_PX // 2)
    lit = Image.new('RGBA', ref.size, 'white')
    lit.alpha_composite(ren, (ox, oy)) if ox >= 0 and oy >= 0 else lit.paste(ren, (ox, oy), ren)
    alpha = Image.new('L', ref.size, 0)
    alpha.paste(ren.getchannel('A'), (ox, oy))
    edge = ImageChops.difference(alpha.filter(ImageFilter.MaxFilter(7)), alpha.filter(ImageFilter.MinFilter(7)))
    over = ref.convert('RGBA')
    over.paste(Image.new('RGBA', ref.size, (230, 40, 90, 255)), (0, 0), edge)
    rows.append([ref.convert('RGB'), lit.convert('RGB'), over.convert('RGB')])
    # how well the silhouettes agree
    g = ref.convert('L').point(lambda v: 255 if v < 243 else 0)
    a = alpha.point(lambda v: 255 if v > 128 else 0)
    inter = ImageChops.multiply(g, a).histogram()[255]
    union = ImageChops.lighter(g, a).histogram()[255]
    print(f'{name}: silhouette overlap {inter / union:.2f}')
tq = Image.open(os.path.join(out, 'three_quarter.png')).convert('RGBA')
bgw = Image.new('RGBA', tq.size, 'white')
bgw.alpha_composite(tq)
W = sum(i.size[0] for i in rows[0]) + 20
Hh = sum(r[0].size[1] for r in rows) + 10
sheet_img = Image.new('RGB', (W + 830, Hh), 'white')
y = 0
for r in rows:
    x = 0
    for im in r:
        sheet_img.paste(im, (x, y))
        x += im.size[0] + 10
    y += r[0].size[1] + 10
sheet_img.paste(bgw.convert('RGB').resize((820, 820)), (W, (Hh - 820) // 2))
sheet_img.save(os.path.join(out, 'ash_blockout_vs_sheet.png'))
print(sheet_img.size)
