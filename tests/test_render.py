"""Renderer unit checks (no GUI/ffmpeg). Run: python tests/test_render.py"""
import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cv2
import numpy as np
from src.core.project import Project, Clip, ClipType
from src.core.renderer import compose_frame, render_clip_frame
from src.core.transitions import TRANSITIONS, transition_frame
from src.core.video_player import FrameProcessor as FP, ImageReader

rng = np.random.default_rng(1)
A = rng.integers(0, 255, (72, 128, 3), dtype=np.uint8)
B = rng.integers(0, 255, (72, 128, 3), dtype=np.uint8)

# 1. every transition: p=0 -> A, p=1 -> B, shape/dtype kept, mid-point differs from both
assert len(TRANSITIONS) == 20
for tid in TRANSITIONS:
    assert np.array_equal(transition_frame(tid, A, B, 0), A), tid
    assert np.array_equal(transition_frame(tid, A, B, 1), B), tid
    mid = transition_frame(tid, A, B, 0.5)
    assert mid.shape == A.shape and mid.dtype == np.uint8, tid
    assert not np.array_equal(mid, A) and not np.array_equal(mid, B), tid

# 2. mask_inverted flips alpha
m = FP.mask_alpha(60, 80, 'circle', 0.0)
assert np.allclose(FP.mask_alpha(60, 80, 'circle', 0.0, True), 1 - m)

# 3. whitening raises luma, dehaze changes pixels
g = np.full((40, 40, 3), 100, np.uint8)
c = Clip(); c.whitening = 0.8
assert FP.apply_color_correction(g, c).mean() > g.mean()
c = Clip(); c.dehaze = 0.8
hazy = (np.linspace(150, 200, 40 * 40).reshape(40, 40, 1) * np.ones((1, 1, 3))).astype(np.uint8)
assert not np.array_equal(FP.apply_color_correction(hazy, c), hazy)

# 4. keyframe scale changes pixels (clip shrinks -> black border appears)
p = Project()
v = Clip(clip_type=ClipType.VIDEO, source_path='x', timeline_start=0, timeline_end=2000, source_end=2000)
v.keyframes = [{'time': 0.0, 'props': {'scale': 1.0}, 'easing': 'linear'},
               {'time': 2.0, 'props': {'scale': 0.5}, 'easing': 'linear'}]
p.add_clip(v)
get = lambda clip, t: A.copy()
f0 = compose_frame(p, 0, get, size=(128, 72))
f1 = compose_frame(p, 1900, get, size=(128, 72))
assert np.array_equal(f0, A) and f1[:5].sum() == 0 and f1.sum() < f0.sum()

# 5. RGBA sticker composited with correct alpha on track 1
png = os.path.join(tempfile.mkdtemp(), 's.png')
st = np.zeros((32, 32, 4), np.uint8); st[:, :16] = (0, 0, 255, 255)   # left half opaque red (BGRA)
cv2.imwrite(png, st)
img = ImageReader(png).read_frame()
assert img.shape[2] == 4
p2 = Project()
p2.add_clip(Clip(clip_type=ClipType.IMAGE, source_path='bg', timeline_end=1000, source_end=1000))
p2.add_clip(Clip(clip_type=ClipType.STICKER, source_path=png, track=1, timeline_end=1000, source_end=1000))
bg = np.full((72, 128, 3), 50, np.uint8)
out = compose_frame(p2, 0, lambda clip, t: bg.copy() if clip.track == 0 else img.copy(), size=(128, 72))
# sticker is placed at 50% of canvas, centred: 36x36 square at x 46..82; opaque half is the left
assert tuple(out[36, 50]) == (255, 0, 0), out[36, 50]      # red (RGB)
assert tuple(out[36, 78]) == (50, 50, 50), out[36, 78]     # transparent half shows bg
assert tuple(out[2, 2]) == (50, 50, 50)

# 6. transition integrated in compose_frame: B at t_start+dur/2 is a mix, not pure B
p3 = Project()
a = Clip(clip_type=ClipType.IMAGE, source_path='a', timeline_start=0, timeline_end=1000, source_end=1000)
b = Clip(clip_type=ClipType.IMAGE, source_path='b', timeline_start=1000, timeline_end=2000, source_end=1000,
         transition_in='fade', transition_in_duration=500)
p3.add_clip(a); p3.add_clip(b)
src = lambda clip, t: (A if clip.source_path == 'a' else B).copy()
cache = {}
assert np.array_equal(compose_frame(p3, 1000, src, (128, 72), cache), A)
mid = compose_frame(p3, 1250, src, (128, 72), cache)
assert not np.array_equal(mid, A) and not np.array_equal(mid, B)
assert np.array_equal(compose_frame(p3, 1600, src, (128, 72), cache), B)
print('OK')
