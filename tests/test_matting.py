"""Background matting checks. Run: python tests/test_matting.py"""
import os, sys, tempfile, subprocess, time, copy, glob
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cv2
import numpy as np
from src.ai import assets, matting, models
from src.ai.media import Cancelled
from src.core.exporter import ffmpeg_exe
from src.core.project import Project, Clip, ClipType
from src.core import renderer

tmp = tempfile.mkdtemp()
FF = ffmpeg_exe()
W, H = 64, 48

# synthetic source: bright disc on a dark background, 25 fps, 2 s
vid = os.path.join(tmp, 'disc.mp4')
fr = np.full((H, W, 3), 20, np.uint8)
cv2.circle(fr, (32, 24), 14, (230, 230, 230), -1)
p = subprocess.Popen([FF, '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', '25', '-i', '-',
                      '-c:v', 'libx264', '-crf', '8', '-pix_fmt', 'yuv420p', vid], stdin=subprocess.PIPE)
for _ in range(50):
    p.stdin.write(fr.tobytes())
p.stdin.close(); p.wait()

lum = lambda rgb: np.repeat(((rgb.mean(2) > 120) * 255).astype(np.uint8)[..., None], 3, 2)   # no model: threshold matte
inside, outside = (24, 32), (3, 3)                                                           # (y, x)


def mk():
    pr = Project()
    c = Clip(clip_type=ClipType.VIDEO, source_path=vid, timeline_end=2000, source_end=2000)
    pr.add_clip(c)
    pr.settings.width, pr.settings.height = W, H
    return pr, c


def render(pr, t=500):
    rd = {}
    f = renderer.compose_frame(pr, t, lambda c, ms: renderer.fetch_clip_frame(rd, c, ms), size=(W, H))
    for r in rd.values():
        r and hasattr(r, 'close') and r.close()
    return f


pr, c = mk()
d = assets.asset_dir(pr)
assert matting.matte_status(c) == 'none'
c.ai['matte'] = matting.bake_matte(c, d, frame_fn=lum)
c.ai['matte_style'] = dict(matting.DEFAULT_STYLE)
m = c.ai['matte']
assert matting.matte_status(c) == 'ok' and m['frames'] == 50 and abs(m['fps'] - 25) < .01, m
print('OK bake', m['frames'], 'frames')

# transparent: disc kept, outside shows the track below (black canvas here) -> compare against opaque render
base = render(mk()[0])
f = render(pr)
assert abs(int(f[inside].mean()) - int(base[inside].mean())) < 12 and f[outside].max() < 12, (f[inside], f[outside], base[inside])

# colour mode
c.ai['matte_style'] = {**matting.DEFAULT_STYLE, 'mode': 'color', 'color': '#ff0000'}
f = render(pr)
assert tuple(f[outside]) == (255, 0, 0) and f[inside].mean() > 150 and f[inside][0] > 150 and f[inside][1] > 150, (f[outside], f[inside])

# media mode: image background, then looped video background
bgimg = os.path.join(tmp, 'bg.png')
cv2.imwrite(bgimg, np.full((20, 20, 3), (0, 0, 255), np.uint8))          # BGR red
c.ai['matte_style'] = {**matting.DEFAULT_STYLE, 'mode': 'media', 'path': bgimg}
f = render(pr)
assert f[outside][0] > 240 and f[outside][1] < 15, f[outside]
bgvid = os.path.join(tmp, 'bg.mp4')
subprocess.run([FF, '-y', '-loglevel', 'error', '-f', 'lavfi', '-i', 'color=c=0x00ff00:s=32x32:r=25:d=0.5', '-pix_fmt', 'yuv420p', bgvid], check=True)
c.ai['matte_style']['path'] = bgvid
f = render(pr, 1500)                                                      # past bg length: must loop, not go black
assert f[outside][1] > 150 and f[outside][0] < 80, f[outside]
print('OK modes')

# feather softens the edge
c.ai['matte_style'] = {**matting.DEFAULT_STYLE, 'mode': 'color', 'color': '#000000', 'feather': 0}
hard = render(pr)[24].astype(np.float32).mean(1)
c.ai['matte_style']['feather'] = 8
soft = render(pr)[24].astype(np.float32).mean(1)
assert np.abs(np.diff(soft)).max() < np.abs(np.diff(hard)).max() - 20, (np.abs(np.diff(soft)).max(), np.abs(np.diff(hard)).max())
print('OK feather')

# trimmed clip (source_start>0) stays aligned: moving disc, matte follows
mv = os.path.join(tmp, 'move.mp4')
p = subprocess.Popen([FF, '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', '25', '-i', '-',
                      '-c:v', 'libx264', '-crf', '8', '-pix_fmt', 'yuv420p', mv], stdin=subprocess.PIPE)
for i in range(50):
    g = np.full((H, W, 3), 20, np.uint8); cv2.circle(g, (8 + i, 24), 6, (230, 230, 230), -1); p.stdin.write(g.tobytes())
p.stdin.close(); p.wait()
pr2 = Project(); pr2.settings.width, pr2.settings.height = W, H
c2 = Clip(clip_type=ClipType.VIDEO, source_path=mv, timeline_end=1200, source_start=400, source_end=1600)
pr2.add_clip(c2)
c2.ai['matte'] = matting.bake_matte(c2, assets.asset_dir(pr2), frame_fn=lum)
c2.ai['matte_style'] = {**matting.DEFAULT_STYLE, 'mode': 'color', 'color': '#ff0000'}
for t in (0, 600, 1100):
    f = render(pr2, t)
    cx = 8 + int((400 + t) / 40)
    assert f[24, cx].mean() > 150 and tuple(f[24, cx][1:]) != (0, 0) or f[24, cx][1] > 150, (t, f[24, cx])
    assert tuple(f[24, (cx + 20) % W]) == (255, 0, 0), (t, f[24, (cx + 20) % W])
c3 = copy.deepcopy(c2); c3.id = 'x'                                       # split/duplicate keeps the bake
assert matting.matte_status(c3) == 'ok'
print('OK trim align')

# stale / missing -> render equals no matte, no crash
os.utime(vid, (time.time() + 5, time.time() + 5))
assert matting.matte_status(c) == 'stale'
assert (render(pr) == render(mk()[0])).all()
os.utime(vid, (time.time() - 5, time.time() - 5))
c.ai['matte']['path'] = os.path.join(tmp, 'gone.mkv')
assert matting.matte_status(c) == 'stale'
render(pr)
print('OK stale')

# refine: flat binary mask untouched, soft edge gets graded
rgb = np.full((40, 40, 3), 30, np.uint8); rgb[:, 20:] = 220
a = np.zeros((40, 40), np.float32); a[:, 20:] = 1
r = matting.refine(a, rgb)
assert (np.abs(r - a) < .05).mean() > .99
print('OK refine')

# cancel mid-bake -> no .part, nothing left running
n = [0]
def slow(rgb):
    n[0] += 1
    return lum(rgb)
try:
    matting.bake_matte(c, d, frame_fn=slow, cancelled=lambda: n[0] > 5)
    raise SystemExit('cancel ignored')
except Cancelled:
    pass
assert not glob.glob(os.path.join(str(d), '*.part'))
print('OK cancel')

# relocate / prune keep the matte
pr3, c4 = mk()
c4.ai['matte'] = matting.bake_matte(c4, assets.asset_dir(pr3), frame_fn=lum)
c4.ai['matte_style'] = dict(matting.DEFAULT_STYLE)
assets.prune(pr3)
assert os.path.isfile(c4.ai['matte']['path'])
newp = os.path.join(tmp, 'moved', 'proj.vcp'); os.makedirs(os.path.dirname(newp))
assets.relocate(pr3, newp)
assert c4.ai['matte']['path'].startswith(os.path.join(tmp, 'moved')) and os.path.isfile(c4.ai['matte']['path'])
print('OK relocate')

# image clip: single PNG matte
img = os.path.join(tmp, 'img.png'); cv2.imwrite(img, cv2.cvtColor(fr, cv2.COLOR_RGB2BGR))
pi = Project(); pi.settings.width, pi.settings.height = W, H
ci = Clip(clip_type=ClipType.IMAGE, source_path=img, timeline_end=1000)
pi.add_clip(ci)
ci.ai['matte'] = matting.bake_matte(ci, assets.asset_dir(pi), frame_fn=lum)
ci.ai['matte_style'] = {**matting.DEFAULT_STYLE, 'mode': 'color', 'color': '#ff0000'}
assert ci.ai['matte']['path'].endswith('.png') and matting.matte_status(ci) == 'ok'
f = render(pi, 100)
assert tuple(f[outside]) == (255, 0, 0) and f[inside].mean() > 150
print('OK image')

# real model (skipped without it)
if models.available('u2netp'):
    from src.ai.runtime import ort_session
    t0 = time.time()
    out = matting.matte_frame(fr, ort_session('u2netp'), 'u2netp')
    assert out.shape == (H, W) and out.dtype == np.float32 and 0 <= out.min() and out.max() <= 1
    assert out[inside] > out[outside], (out[inside], out[outside])
    print('OK u2netp real', round(time.time() - t0, 2), 's')
else:
    print('SKIP u2netp real (model not installed)')

# GUI
from PyQt6.QtWidgets import QApplication, QMessageBox, QDialog
app = QApplication([])
sys.excepthook = lambda *a: (_ for _ in ()).throw(a[1])
QMessageBox.information = staticmethod(lambda *a, **k: None)
from src.ui.background_panel import BackgroundPanel
from src.ui.main_window import MainWindow
os.environ['VIDEOCUT_MODELS_DIR'] = os.path.join(tmp, 'nomodels')
bp = BackgroundPanel()
if not os.path.isdir(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'models')):
    assert not bp.apply_btn.isEnabled()
got = []
bp.bg_removal_requested.connect(got.append)
bp.mode.setCurrentIndex(1); bp.feather.setValue(5)
t0 = time.time()
while not got and time.time() - t0 < 2: app.processEvents()
assert got and got[0]['action'] == 'style' and got[0]['mode'] == 'color' and got[0]['feather'] == 5, got

del os.environ['VIDEOCUT_MODELS_DIR']
win = MainWindow()
wc = Clip(clip_type=ClipType.VIDEO, source_path=vid, timeline_end=2000, source_end=2000)
win.project.add_clip(wc)
win.timeline_panel.selected_clip_id = wc.id
win._open_bg_removal()
win._on_bg_removal({'action': 'apply', 'quality': 'fast', 'mode': 'color', 'color': '#00ff00', 'feather': 0, 'bg_path': ''})
if models.available('u2netp'):
    t0 = time.time()
    while win._bg_worker and time.time() - t0 < 120: app.processEvents()
    assert matting.matte_status(wc) == 'ok' and wc.ai['matte_style']['mode'] == 'color', wc.ai
    win._on_bg_removal({'action': 'style', 'quality': 'fast', 'mode': 'color', 'color': '#0000ff', 'feather': 3, 'bg_path': ''})
    assert wc.ai['matte_style']['color'] == '#0000ff'
    win._on_bg_removal({'action': 'preview', 'quality': 'fast', 'mode': 'color', 'color': '#0000ff', 'feather': 3, 'bg_path': ''})
    assert win._bg_dlg.preview.pixmap() is not None and not win._bg_dlg.preview.pixmap().isNull()
    win._on_bg_removal({'action': 'remove', 'quality': 'fast', 'mode': 'color', 'color': '#0000ff', 'feather': 3, 'bg_path': ''})
    assert 'matte' not in wc.ai and not os.path.isfile(wc.ai.get('x', 'nofile'))
    print('OK gui real model')
else:
    assert not win._bg_worker
    print('SKIP gui apply (model not installed)')
win._stop_mix()
src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src', 'core', 'renderer.py')).read()
import re; assert 'bg_remover' not in src and not re.search(r'\b_matte\(', src)
print('ALL OK')
