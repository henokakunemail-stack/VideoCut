"""Grading unit checks. Run: python tests/test_grading.py"""
import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from src.core import grading as G
from src.core.project import Clip, ClipType
from src.core.renderer import render_clip_frame

rng = np.random.default_rng(3)
img = rng.integers(0, 255, (60, 80, 3), dtype=np.uint8)


def cube(path, fn, n=5):
    lines = [f'TITLE "t"', f'LUT_3D_SIZE {n}']
    for b in range(n):
        for g in range(n):
            for r in range(n):
                o = fn(np.array([r, g, b]) / (n - 1))
                lines.append('%f %f %f' % tuple(o))
    open(path, 'w').write('\n'.join(lines))


d = tempfile.mkdtemp()
p_id, p_inv, p_bad = (os.path.join(d, x) for x in ('id.cube', 'inv.cube', 'bad.cube'))
cube(p_id, lambda v: v)
cube(p_inv, lambda v: 1 - v)
open(p_bad, 'w').write('LUT_3D_SIZE 3\n0 0 0\n')

# 1. .cube identity ~ original, invert -> 255-x (R-fastest ordering matters: asymmetric fn)
assert np.abs(G.apply_lut3d(img, G.load_cube(p_id)).astype(int) - img).max() <= 1
assert np.abs(G.apply_lut3d(img, G.load_cube(p_inv)).astype(int) - (255 - img)).max() <= 1
p_swap = os.path.join(d, 'swap.cube')
cube(p_swap, lambda v: v[::-1])  # out = (b,g,r)
sw = G.apply_lut3d(img, G.load_cube(p_swap)).astype(int)
assert np.abs(sw - img[..., ::-1]).max() <= 1
try:
    G.load_cube(p_bad)
    raise SystemExit('bad cube accepted')
except ValueError:
    pass
assert np.array_equal(G.apply_named_lut(img, 'cube:' + p_bad), img)  # bad file -> no-op, no crash

# 2. procedural looks run, change pixels, keep dtype/shape; legacy id still works
for k in G.LOOKS:
    o = G.apply_named_lut(img, k)
    assert o.shape == img.shape and o.dtype == np.uint8 and not np.array_equal(o, img), k
assert G.apply_named_lut(img, 'teal_orange').shape == img.shape

# 3. wheels
luma = lambda a: a.astype(float).mean()
assert G.color_wheels(img, {}) is img
assert luma(G.color_wheels(img, {'gain': [0, 0, 0, .3]})) > luma(img)
dark = np.full((10, 10, 3), 20, np.uint8)
lifted = G.color_wheels(dark, {'lift': [.2, 0, 0, 0]})
assert lifted[0, 0, 0] > lifted[0, 0, 1] == 20

# 4. hsl: shift red saturation down; blue untouched
px = np.zeros((4, 4, 3), np.uint8)
px[:2] = (220, 30, 30)
px[2:] = (30, 30, 220)
o = G.hsl_adjust(px, {'red': [0, -80, 0]})
assert abs(int(o[0, 0, 1]) - 30) > 20 and np.array_equal(o[3], px[3])
assert G.hsl_adjust(px, {}) is px

# 5. curves: identity untouched, S-curve raises contrast, per-channel works
assert G.apply_curves(img, {'master': [[0, 0], [1, 1]]}) is img
s = G.apply_curves(img, {'master': [[0, 0], [.25, .15], [.75, .85], [1, 1]]})
assert s.std() > img.std()
r = G.apply_curves(img, {'r': [[0, 0], [.5, .8], [1, 1]]})
assert r[..., 0].mean() > img[..., 0].mean() and np.array_equal(r[..., 1], img[..., 1])

# 6. scopes
for f, shp in ((G.histogram, (128, 256, 3)), (G.waveform, (128, 256, 3)), (G.vectorscope, (160, 160, 3))):
    o = f(img)
    assert o.shape == shp and o.dtype == np.uint8 and o.max() > 0

# 7. Clip round-trip + old projects (no new keys) still load
c = Clip(clip_type=ClipType.IMAGE)
c.color_wheels = {'gain': [.1, 0, 0, 0]}
c.hsl = {'red': [0, 10, 0]}
c.curves = {'master': [[0, 0], [1, 1]]}
c2 = Clip.from_dict(c.to_dict())
assert c2.color_wheels == c.color_wheels and c2.hsl == c.hsl and c2.curves == c.curves
old = c.to_dict()
for k in ('color_wheels', 'hsl', 'curves'):
    del old[k]
assert Clip.from_dict(old).hsl == {}

# 8. renderer applies grading
c = Clip(clip_type=ClipType.IMAGE, timeline_start=0, timeline_end=1000)
c.color_wheels = {'gain': [0, 0, 0, .4]}
base = Clip(clip_type=ClipType.IMAGE, timeline_start=0, timeline_end=1000)
assert luma(render_clip_frame(c, img, 0)) > luma(render_clip_frame(base, img, 0))
c.color_wheels = {}
c.lut_id = 'cube:' + p_inv
inv = render_clip_frame(c, img, 0)
assert np.abs(inv.astype(int) - (255 - img)).max() <= 1

print('OK')
