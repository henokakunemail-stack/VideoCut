"""AI foundation checks. Run: python tests/test_ai.py"""
import os, sys, tempfile, subprocess, time
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from src.ai import models, assets, runtime
from src.ai.bake import run_bake
from src.ai.media import Cancelled, extract_audio
from src.core.exporter import ffmpeg_exe
from src.core.project import Project, Clip, ClipType

tmp = tempfile.mkdtemp()

# registry: permissive only, clear errors
try:
    models.register(models.Model('bad', 'bad.onnx', 'x', 'GPL-3.0', 'https://x'))
    raise SystemExit('GPL model accepted')
except ValueError:
    pass
models.register(models.Model('t', 't.onnx', '0' * 64, 'MIT', 'https://example.org/t.onnx'))
os.environ['VIDEOCUT_MODELS_DIR'] = tmp
try:
    models.resolve('t'); raise SystemExit('missing model resolved')
except models.ModelMissing as e:
    assert 'example.org' in str(e)
open(os.path.join(tmp, 't.onnx'), 'wb').write(b'abc')
assert models.available('t')
try:
    models.resolve('t', verify=True); raise SystemExit('bad hash accepted')
except models.ModelMissing as e:
    assert 'sha256' in str(e)
print('OK registry')

# runtime: CPU fallback always listed
try:
    assert 'CPUExecutionProvider' in runtime.providers()
    print('OK runtime providers', runtime.providers())
except ImportError:
    print('SKIP runtime (onnxruntime missing)')

# Clip.from_dict ignores unknown keys; new fields round-trip
d = Clip(clip_type=ClipType.VIDEO, source_path='a.mp4', ai={'bake': {'path': 'p'}}, text_words=[{'w': 'hi', 's': 0, 'e': 5}]).to_dict()
d['field_from_the_future'] = 1
c = Clip.from_dict(d)
assert c.ai['bake']['path'] == 'p' and c.text_words[0]['w'] == 'hi'
print('OK from_dict')

# synthetic video
vid = os.path.join(tmp, 'v.mp4')
subprocess.run([ffmpeg_exe(), '-y', '-loglevel', 'error', '-f', 'lavfi', '-i', 'testsrc=size=160x120:rate=25:duration=2',
                '-f', 'lavfi', '-i', 'sine=frequency=440:duration=2', '-shortest', '-pix_fmt', 'yuv420p', vid], check=True)

# bake: 1:1 frames, identity-ish, atomic
out = os.path.join(tmp, 'b.mkv')
info = run_bake(vid, 0, 2000, out, lambda f: 255 - f)
assert os.path.isfile(out) and not os.path.exists(out + '.part')
assert info['frames'] == 50 and info['w'] == 160 and info['h'] == 120, info
import cv2
cap = cv2.VideoCapture(out); assert int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) in (49, 50, 51); cap.release()
print('OK bake', info['frames'])

# bake cancel leaves nothing
out2 = os.path.join(tmp, 'c.mkv'); n = [0]
def cancel():
    n[0] += 1
    return n[0] > 10
try:
    run_bake(vid, 0, 2000, out2, lambda f: f, cancelled=cancel); raise SystemExit('not cancelled')
except Cancelled:
    pass
assert not os.path.exists(out2) and not os.path.exists(out2 + '.part')
print('OK bake cancel')

# extract_audio
wav = extract_audio(vid, os.path.join(tmp, 'a.wav'))
assert os.path.getsize(wav) > 10000
print('OK extract_audio')

# assets: relocate on Save As repoints paths
p = Project(); p.save(os.path.join(tmp, 'one.ccproj'))
clip = Clip(clip_type=ClipType.VIDEO, source_path=vid, timeline_end=1000)
p.add_clip(clip)
f = assets.asset_dir(p) / 'x.mkv'; f.write_bytes(b'1')
clip.ai = {'bake': {'path': str(f)}}
p.save(os.path.join(tmp, 'two.ccproj'))
new = clip.ai['bake']['path']
assert new.endswith('x.mkv') and 'two.assets' in new and os.path.isfile(new), new
assets.prune(p); assert os.path.isfile(new)
clip.ai = {}; assets.prune(p); assert not os.path.isfile(new)
print('OK assets')

# beat snap
from src.core.beat_sync import snap_cuts, BeatSyncEngine
cl = [Clip(clip_type=ClipType.VIDEO, source_path=vid, timeline_start=i * 3000, timeline_end=i * 3000 + 3000, source_start=0, source_end=3000) for i in range(3)]
assert snap_cuts(cl, [1000, 2500, 5400]) == 2
assert cl[0].timeline_end == 2500 and cl[1].timeline_start == 2500 and cl[1].timeline_end == 5400
assert abs(BeatSyncEngine.get_bpm([0, .5, 1.0, 1.5]) - 120) < 1e-6
print('OK beat snap')

# GUI: handlers don't raise (empty + filled project), Worker runs and cancels
from PyQt6.QtWidgets import QApplication, QMessageBox, QDialog
app = QApplication([])
sys.excepthook = lambda *a: (_ for _ in ()).throw(a[1])
from src.ui.main_window import MainWindow
from src.ui.workers import Worker, start_worker
QMessageBox.information = staticmethod(lambda *a, **k: None)
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.No)
QDialog.exec = lambda self: 0
win = MainWindow()
for proj in (None, 'filled'):
    if proj:
        win.project.add_clip(Clip(clip_type=ClipType.VIDEO, source_path=vid, timeline_end=2000, source_end=2000))
        win.timeline_panel.selected_clip_id = win.project.clips[0].id
    win._open_auto_captions(); win._open_bg_removal(); win._open_voice_fx()
    win._on_bg_removal({'action': 'style', 'mode': 'color', 'color': '#000000', 'feather': 0, 'bg_path': ''})
    win._on_captions_ready(type('T', (), {'subtitles': [type('S', (), {'start': 0.5, 'end': 1.0, 'text': 'hello'})()]})(), win.project.clips[0] if proj else None)
assert any(c.clip_type == ClipType.TEXT and c.text_content == 'hello' for c in win.project.clips)

got = []
w = Worker(lambda x, progress, cancelled: (progress(50), x * 2)[1], 21)
w.finished.connect(got.append)
th = start_worker(w, win)
t0 = time.time()
while not got and time.time() - t0 < 5: app.processEvents()
assert got == [42], got

def slow(progress, cancelled):
    while not cancelled(): time.sleep(.01)
    raise Cancelled()
got.clear(); w = Worker(slow); w.finished.connect(got.append); th = start_worker(w, win)
w.cancel(); t0 = time.time()
while not got and time.time() - t0 < 5: app.processEvents()
assert got == [None]
th.wait(2000)
print('OK gui + worker')
print('ALL OK')
