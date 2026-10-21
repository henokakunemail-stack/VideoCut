"""End-to-end check: filter+LUT+effect+text -> ffmpeg export -> video+audio streams exist. Run: python tests/test_export.py"""
import os, subprocess, sys, tempfile
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from PyQt6.QtWidgets import QApplication
from src.core.exporter import ffmpeg_exe, export_project, has_audio
from src.core.project import Project, Clip, ClipType
from src.core.renderer import render_clip_frame, set_effect

app = QApplication([])
tmp = tempfile.mkdtemp()
src = os.path.join(tmp, 'src.mp4')
subprocess.run([ffmpeg_exe(), '-y', '-f', 'lavfi', '-i', 'testsrc=size=320x180:rate=30:duration=2',
                '-f', 'lavfi', '-i', 'sine=frequency=440:duration=2', '-shortest', '-pix_fmt', 'yuv420p', src],
               check=True, capture_output=True)
assert has_audio(src)

p = Project()
v = Clip(clip_type=ClipType.VIDEO, source_path=src, timeline_start=0, timeline_end=2000, source_start=0, source_end=2000)
v.filter_id, v.lut_id, v.lut_strength = 'noir', 'teal_orange', 0.7
set_effect(v, 'chromatic_aberration', {'amount': .5})
t = Clip(clip_type=ClipType.TEXT, track=1, timeline_start=0, timeline_end=2000, text_content='HI', position_x=.5, position_y=.5)
v2 = Clip(clip_type=ClipType.VIDEO, source_path=src, timeline_start=2000, timeline_end=3000, source_start=0, source_end=1000,
          transition_in='wipe_left', transition_in_duration=500)
import cv2
png = os.path.join(tmp, 'st.png')
cv2.imwrite(png, np.dstack([np.zeros((64, 64, 3), np.uint8), np.full((64, 64), 255, np.uint8)]) + np.array([0, 0, 255, 0], np.uint8))
stk = Clip(clip_type=ClipType.STICKER, source_path=png, track=1, timeline_start=0, timeline_end=3000, source_end=3000)
p.add_clip(v); p.add_clip(v2); p.add_clip(stk); p.add_clip(t)

# renderer actually changes pixels
raw = np.full((90, 160, 3), 128, np.uint8); raw[:, :80, 0] = 255
assert not np.array_equal(render_clip_frame(v, raw, 0), raw), "pipeline is a no-op"

out = os.path.join(tmp, 'out.mp4')
ok, msg = export_project(p, dict(output_path=out, width=320, height=180, fps=30, quality=1, codec='h264'))
assert ok, msg
info = subprocess.run([ffmpeg_exe(), '-hide_banner', '-i', out], capture_output=True, text=True).stderr
assert 'Video: h264' in info and 'Audio: aac' in info, info
assert 'Duration: 00:00:03' in info, info
# frame mid-transition (t=2.25s) must differ from the same frame without the transition
f = lambda ss, o: subprocess.run([ffmpeg_exe(), '-y', '-ss', ss, '-i', out, '-frames:v', '1', o], capture_output=True)
f1, f2 = os.path.join(tmp, 'a.png'), os.path.join(tmp, 'b.png')
f('2.25', f1); f('2.9', f2)
a_, b_ = cv2.imread(f1), cv2.imread(f2)
assert a_ is not None and b_ is not None and not np.array_equal(a_, b_)
sticker_px = b_[90, 160]   # centre of canvas: red sticker (BGR)
assert sticker_px[2] > 150 and sticker_px[0] < 100, sticker_px
print('OK', msg)
