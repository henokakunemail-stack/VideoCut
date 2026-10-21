"""Motion/time-model checks. Run: python tests/test_motion.py"""
import os, subprocess, sys, tempfile, re
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from src.core import timemap
from src.core.exporter import ffmpeg_exe, export_project, build_audio_cmd, _audio_sources
from src.core.project import Project, Clip, ClipType


def vclip(**kw):
    d = dict(clip_type=ClipType.VIDEO, source_path='x.mp4', timeline_start=0, timeline_end=4000, source_start=0, source_end=4000)
    d.update(kw)
    return Clip(**d)


# constant speed: source offset regression (source_start>0, speed 2)
c = vclip(source_start=1000, source_end=5000, speed=2.0)
assert timemap.duration_ms(c) == 2000
c.timeline_end = 2000
assert timemap.source_ms(c, 0) == 1000 and abs(timemap.source_ms(c, 1000) - 3000) < 1
assert abs(timemap.source_ms(c, 2000 - 1e-6) - 5000) < 1

# slow-mo 0.5x doubles duration
c = vclip(speed=0.5); assert timemap.duration_ms(c) == 8000

# reverse
c = vclip(reverse=True); assert timemap.source_ms(c, 0) == 4000 and abs(timemap.source_ms(c, 2000) - 2000) < 1

# freeze
c = vclip(freeze=True, source_start=1234, source_end=1234, timeline_end=2000)
assert timemap.source_ms(c, 1500) == 1234 and timemap.duration_ms(c) == 2000

# curve 0.5 -> 2.0: analytic duration = L * ln(4)/1.5 for linear speed ramp (PCHIP of 2 pts is linear)
c = vclip(speed_curve=[[0, 0.5], [1, 2.0]])
want = 4000 * np.log(4.0) / 1.5
assert abs(timemap.duration_ms(c) - want) < want * 0.01, (timemap.duration_ms(c), want)
c.timeline_end = timemap.duration_ms(c)
ts = np.linspace(0, c.timeline_end, 200)
ss = np.array([timemap.source_ms(c, t) for t in ts])
assert np.all(np.diff(ss) >= -1e-6) and abs(ss[-1] - 4000) < 1 and abs(ss[0]) < 1e-6
assert np.max(np.diff(ss)) / np.min(np.diff(ss)) > 3          # actually ramps (0.5x -> 2x = 4x)

# project: retime + ripple, other tracks untouched, split continuity
p = Project()
a = vclip(); b = vclip(timeline_start=4000, timeline_end=8000); o = vclip(track=1, timeline_start=5000, timeline_end=6000)
for x in (a, b, o): p.add_clip(x)
a.speed = 2.0
assert p.retime_clip(a.id) == -2000
assert a.timeline_end == 2000 and b.timeline_start == 2000 and b.timeline_end == 6000 and o.timeline_start == 5000
assert p.settings.duration == 6000

a.speed = 1.0; p.retime_clip(a.id)
a.speed_curve = [[0, 0.5], [1, 2.0]]; p.retime_clip(a.id)
mid = a.timeline_start + a.duration // 3
expect = timemap.source_ms(a, mid)
L0 = a.speed_curve[:]
right = p.split_clip(a.id, mid)
assert right and abs(a.source_end - expect) <= 1 and right.source_start == a.source_end
assert a.timeline_end == right.timeline_start
# speed continuous across the cut
sl = timemap.speed_at(a, 1.0); sr = timemap.speed_at(right, 0.0)
assert abs(float(sl) - float(sr)) < 0.05, (sl, sr)
# playback positions continuous: just before / after cut
assert abs(timemap.source_ms(a, mid - 1) - timemap.source_ms(right, mid + 1)) < 30

# reverse split: left half plays high source range first
r = vclip(reverse=True); p2 = Project(); p2.add_clip(r)
rr = p2.split_clip(r.id, 1000)
assert r.source_start == rr.source_end == 3000 and r.source_end == 4000 and rr.source_start == 0
assert abs(timemap.source_ms(r, 999) - 3001) < 2 and abs(timemap.source_ms(rr, 1000) - 3000) < 2

# freeze frame insertion
p3 = Project(); f = vclip(); g = vclip(timeline_start=4000, timeline_end=8000); p3.add_clip(f); p3.add_clip(g)
fz = p3.freeze_frame(f.id, 1000, 2000)
assert fz and fz.freeze and fz.timeline_start == 1000 and fz.timeline_end == 3000 and fz.source_start == 1000
assert g.timeline_start == 6000 and p3.settings.duration == 10000

# old project dicts load; new fields roundtrip
d = vclip(speed=2.0).to_dict()
for k in ('speed_curve', 'freeze', 'frame_mode', 'stabilize'): d.pop(k)
p4 = Project.from_dict({'clips': [d]})
assert p4.clips[0].timeline_end == 2000 and p4.clips[0].frame_mode == 'none'
assert Clip.from_dict(vclip(speed_curve=[[0, 1], [1, 2]]).to_dict()).speed_curve == [[0, 1], [1, 2]]

# audio graph shape
c = vclip(speed_curve=[[0, 0.5], [1, 2.0]]); c.timeline_end = timemap.duration_ms(c)
segs = timemap.audio_segments(c)
assert len(segs) == 16 and abs(sum((h - l) for l, h, *_ in segs) - 4000) < 20
src = dict(path='x', segs=segs, tl_start=0, tl_dur=c.duration, volume=1, fade_in=0, fade_out=0)
ins, fc, lab = build_audio_cmd([src], c.duration / 1000)
assert 'concat=n=16' in fc and 'atempo' in fc and 'asplit=16' in fc

# end to end export: ramp clip duration == duration_ms, audio present
tmp = tempfile.mkdtemp()
mp4 = os.path.join(tmp, 's.mp4')
subprocess.run([ffmpeg_exe(), '-y', '-f', 'lavfi', '-i', 'testsrc=size=160x90:rate=30:duration=3',
                '-f', 'lavfi', '-i', 'sine=frequency=440:duration=3', '-shortest', '-pix_fmt', 'yuv420p', mp4],
               check=True, capture_output=True)
from PyQt6.QtWidgets import QApplication
app = QApplication([])
p5 = Project()
v = Clip(clip_type=ClipType.VIDEO, source_path=mp4, timeline_start=0, timeline_end=3000, source_start=0, source_end=3000,
         speed_curve=[[0, 0.5], [1, 2.0]], frame_mode='blend')
p5.add_clip(v); p5.retime_clip(v.id)
out = os.path.join(tmp, 'o.mp4')
ok, msg = export_project(p5, dict(output_path=out, width=160, height=90, fps=30, quality=0, codec='h264'))
assert ok, msg
info = subprocess.run([ffmpeg_exe(), '-hide_banner', '-i', out], capture_output=True, text=True).stderr
m = re.search(r'Duration: (\d+):(\d+):([\d.]+)', info)
got = int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3])
assert abs(got - v.duration / 1000) < 0.1 and 'Audio:' in info, (got, v.duration, info)
print('OK motion core')

# ---- GUI (offscreen): speed tab -> retime -> timeline; freeze; reverse; no exceptions ----
sys.excepthook = lambda *a: (_ for _ in ()).throw(a[1])
from src.ui.main_window import MainWindow
win = MainWindow()
win.project = Project(); 
vc = Clip(clip_type=ClipType.VIDEO, source_path=mp4, timeline_start=0, timeline_end=3000, source_start=0, source_end=3000)
nxt = Clip(clip_type=ClipType.VIDEO, source_path=mp4, timeline_start=3000, timeline_end=6000, source_start=0, source_end=3000)
win.project.add_clip(vc); win.project.add_clip(nxt)
win._refresh_timeline()
pp = win.properties_panel
pp.set_clip(vc)
pp._set_speed(2.0)
assert vc.timeline_end == 1500 and nxt.timeline_start == 1500, (vc.timeline_end, nxt.timeline_start)
pp.speed_curve._combo.setCurrentIndex(2); pp.speed_curve._on_preset(2)   # Montage
assert vc.speed_curve and vc.timeline_end == vc.timeline_start + timemap.duration_ms(vc)
assert nxt.timeline_start == vc.timeline_end
win.current_time_ms = 300
win._toggle_reverse(vc.id); assert vc.reverse
win._freeze_frame(vc.id)
assert any(c.freeze for c in win.project.clips)
pm = win.grab(); 
print('OK motion gui')

# ---- optical flow beats blend on a moving pattern ----
import cv2
from src.core.interp import interpolate
rng = np.random.RandomState(0)
tex = cv2.GaussianBlur(rng.randint(0, 255, (180, 320, 3)).astype(np.uint8), (0, 0), 3)
shift = lambda d: np.roll(tex, d, axis=1)
f0, f1, gt = shift(0), shift(8), shift(4)
of = interpolate(f0, f1, 0.5).astype(float)
bl = cv2.addWeighted(f0, .5, f1, .5, 0).astype(float)
mse = lambda a: ((a - gt.astype(float))[:, 20:-20] ** 2).mean()   # skip np.roll wrap edges
assert mse(of) < mse(bl) * 0.6, (mse(of), mse(bl))
print('OK interp', round(mse(of), 1), round(mse(bl), 1))

# ---- 3d: shake, bezier, card mapping ----
from src.core import fx_motion
from src.core.keyframe_engine import _ease
from src.core.renderer import CARD_EFFECTS, EFFECTS
img = cv2.GaussianBlur(np.random.RandomState(1).randint(0, 255, (180, 320, 3)).astype(np.uint8), (0, 0), 2)
P = {'amount': .6, 'speed': .5, 'seed': 7}
a = fx_motion.camera_shake(img, {**P, '_t': 1.0}, 0)
assert np.array_equal(a, fx_motion.camera_shake(img, {**P, '_t': 1.0}, 0))
assert not np.array_equal(a, fx_motion.camera_shake(img, {**P, '_t': 1.13}, 0))
assert a.mean() > 0.5 * img.mean() and a[:3].mean() > 10      # edges not black
assert np.array_equal(fx_motion.camera_shake(img, {**P, 'amount': 0, '_t': 1.0}, 0), img)
assert abs(_ease(.37, 'bezier:0,0,1,1') - .37) < 1e-3
assert _ease(0, 'bezier:0.34,1.56,0.64,1') == 0 and abs(_ease(1, 'bezier:0.34,1.56,0.64,1') - 1) < 1e-6
assert max(_ease(i / 50, 'bezier:0.34,1.56,0.64,1') for i in range(51)) > 1.05   # overshoot
assert all(fx_motion.FX[k][0](img, {**fx_motion.FX[k][1], '_t': .3}, .5).shape == img.shape for k in fx_motion.FX)
assert all(eid in EFFECTS for eid, _ in CARD_EFFECTS.values())
print('OK 3d')

# GUI wiring: effect card toggle + panel buttons
win._get_selected_clip = lambda: vc
win._on_effect_card('Shake', 'shake'); assert any(e.effect_id == 'camera_shake' for e in vc.effects)
win._on_effect_card('Shake', 'shake'); assert not any(e.effect_id == 'camera_shake' for e in vc.effects)
ep = win.properties_panel.effects_panel
ep._emit_shake(); ep._emit_zoom_3d()
assert {e.effect_id for e in vc.effects} >= {'camera_shake', 'zoom_3d'}
from src.core.renderer import compose_frame
assert compose_frame(win.project, 500, lambda c, t: np.full((72, 128, 3), 90, np.uint8), size=(128, 72)) is not None
print('OK 3d gui')

# ---- 3e: stabilisation reduces jitter >= 50% ----
from src.core import stabilize
rs = np.random.RandomState(3)
big = cv2.GaussianBlur(rs.randint(0, 255, (600, 900, 3)).astype(np.uint8), (0, 0), 4)
N = 60
jit = rs.randint(-8, 9, (N, 2))
sp = os.path.join(tempfile.mkdtemp(), 'jit.avi')
vw = cv2.VideoWriter(sp, cv2.VideoWriter_fourcc(*'MJPG'), 30, (320, 240))
for i in range(N):
    x, y = 200 + i * 2 + jit[i, 0], 150 + jit[i, 1]
    vw.write(big[y:y + 240, x:x + 320])
vw.release()
res = stabilize.analyze(sp, 0, int(N / 30 * 1000), 'high')
assert res and len(res['transforms']) >= N - 3
cap = cv2.VideoCapture(sp)
raw, fixed = [], []
for i in range(len(res['transforms'])):
    ok, bgr = cap.read()
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    raw.append(cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32))
    fixed.append(cv2.cvtColor(stabilize.apply(rgb, res, i / 30 * 1000), cv2.COLOR_RGB2GRAY).astype(np.float32))
def jitter(fr):
    sh = np.array([cv2.phaseCorrelate(fr[i], fr[i + 1])[0] for i in range(len(fr) - 1)])
    return sh.std(axis=0).mean()
j0, j1 = jitter(raw), jitter(fixed)
assert j1 < j0 * 0.5, (j0, j1)
print('OK stabilize', round(j0, 2), round(j1, 2))

# worker + panel (offscreen), cancel path
from PyQt6.QtCore import QEventLoop, QTimer
c = Clip(clip_type=ClipType.VIDEO, source_path=sp, timeline_start=0, timeline_end=2000, source_start=0, source_end=2000)
win.project.add_clip(c); win._refresh_timeline()
pp.set_clip(c); pp._stab_start()
loop = QEventLoop(); pp._stab_worker.finished.connect(lambda *_: QTimer.singleShot(0, loop.quit)); loop.exec()
assert c.stabilize.get('transforms'), 'worker produced nothing'
pp._stab_clear(); assert not c.stabilize
print('OK stabilize gui')
