"""Voice FX chain + preview mix checks. Run: python tests/test_audio.py"""
import os, sys, tempfile, subprocess, wave, time
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from src.core.exporter import ffmpeg_exe, _audio_sources, build_audio_cmd
from src.core.project import Project, Clip, ClipType
from src.core import audio_chain, audio_mix

tmp = tempfile.mkdtemp()
FF = ffmpeg_exe()


def sine(path, hz=440, secs=2.0):
    subprocess.run([FF, '-y', '-loglevel', 'error', '-f', 'lavfi', '-i', f'sine=frequency={hz}:duration={secs}',
                    '-ar', '48000', '-ac', '1', path], check=True)
    return path


def read(path):
    with wave.open(path) as w:
        n, ch = w.getnframes(), w.getnchannels()
        x = np.frombuffer(w.readframes(n), np.int16).astype(np.float32) / 32768
        return x.reshape(-1, ch).mean(1), w.getframerate()


def peak_hz(x, sr):
    sp = np.abs(np.fft.rfft(x * np.hanning(len(x))))
    return np.fft.rfftfreq(len(x), 1 / sr)[sp.argmax()]


src = sine(os.path.join(tmp, 's.wav'))

# empty chain -> '' ; unknown names skipped
assert audio_chain.chain_filters([]) == '' and audio_chain.chain_filters([{'name': 'nope'}]) == ''

# every preset runs in real ffmpeg, keeps duration
for name, chain in audio_chain.PRESETS.items():
    out = os.path.join(tmp, f'{name}.wav')
    fx = audio_chain.chain_filters([{'name': n, 'params': p} for n, p in chain])
    subprocess.run([FF, '-y', '-loglevel', 'error', '-i', src, '-af', fx, out], check=True)
    x, sr = read(out)
    assert 1.9 < len(x) / sr < 3.0, (name, len(x) / sr)   # echo/rubberband tails extend; the mix graph trims (checked in render_mix)
print('OK presets', len(audio_chain.PRESETS))

# pitch +12 -> 880 Hz, same duration
out = os.path.join(tmp, 'p12.wav')
subprocess.run([FF, '-y', '-loglevel', 'error', '-i', src, '-af',
                audio_chain.chain_filters([{'name': 'pitch', 'params': {'semitones': 12}}]), out], check=True)
x, sr = read(out)
assert abs(peak_hz(x[sr // 4: -sr // 4], sr) - 880) < 25, peak_hz(x, sr)
assert abs(len(x) / sr - 2.0) < 0.1
print('OK pitch +12 ->', round(peak_hz(x[sr // 4: -sr // 4], sr)))

# robot alters the spectrum
out = os.path.join(tmp, 'rb.wav')
voice = os.path.join(tmp, 'noise.wav')
subprocess.run([FF, '-y', '-loglevel', 'error', '-f', 'lavfi', '-i', 'anoisesrc=d=1:c=pink:r=48000', '-ac', '1', voice], check=True)
subprocess.run([FF, '-y', '-loglevel', 'error', '-i', voice, '-af',
                audio_chain.chain_filters([{'name': 'robot', 'params': {'freq_hz': 100}}]), out], check=True)
a, _ = read(voice); b, _ = read(out); n = min(len(a), len(b))
assert abs(np.corrcoef(a[:n], b[:n])[0, 1]) < 0.99
print('OK robot')

# export graph uses chain + audio_source; empty chain leaves graph unchanged
vid = os.path.join(tmp, 'v.mp4')
subprocess.run([FF, '-y', '-loglevel', 'error', '-f', 'lavfi', '-i', 'testsrc=size=64x48:rate=25:duration=2',
                '-i', src, '-shortest', '-pix_fmt', 'yuv420p', vid], check=True)
p = Project()
c = Clip(clip_type=ClipType.VIDEO, source_path=vid, timeline_end=2000, source_end=2000)
p.add_clip(c)
base = build_audio_cmd(list(_audio_sources(p)), 2.0)[1]
assert 'rubberband' not in base
c.audio_fx = [{'name': 'pitch', 'params': {'semitones': 5}}]
fc = build_audio_cmd(list(_audio_sources(p)), 2.0)[1]
assert 'rubberband' in fc and fc.replace('rubberband=pitch=1.33484:formant=preserved,', '') == base, fc
c.audio_fx = []
c.audio_source = src
srcs = list(_audio_sources(p))
assert srcs and srcs[0]['path'] == src
c.audio_source = ''
print('OK export graph')

# mix_key: audio fields change it, visual fields don't
k0 = audio_mix.mix_key(p)
c.brightness = 0.3; c.position_x = 0.2
assert audio_mix.mix_key(p) == k0
c.volume = 0.5
k1 = audio_mix.mix_key(p); assert k1 != k0
c.audio_fx = [{'name': 'echo', 'params': {}}]
assert audio_mix.mix_key(p) != k1
c.audio_fx = []; c.volume = 0.8
c.muted = True; assert audio_mix.mix_key(p) != k0
c.muted = False
print('OK mix_key')

# render_mix: duration, cache, silence
p.settings.duration = 2000
wav = audio_mix.render_mix(p)
x, sr = read(wav)
assert sr == 48000 and abs(len(x) / sr - 2.0) < 0.05, len(x) / sr
assert audio_mix.render_mix(p) == wav
c.muted = True
assert audio_mix.render_mix(p) is None
c.muted = False
c.audio_fx = [{'name': 'pitch', 'params': {'semitones': 12}}]
wav2 = audio_mix.render_mix(p)
x, sr = read(wav2)
assert abs(peak_hz(x[sr // 4: -sr // 4], sr) - 880) < 25 and wav2 != wav and not os.path.exists(wav)
print('OK render_mix')

# master clock
assert audio_mix.pick_time(1000, 960, 33) == 1000
assert audio_mix.pick_time(None, 960, 33) == 993
assert audio_mix.pick_time(100, 960, 33) == 993       # audio jumped back (loop/seek race): free-run
print('OK pick_time')

# audition
out = audio_mix.render_audition(c, [{'name': 'echo', 'params': {}}], secs=1)
assert os.path.getsize(out) > 1000
print('OK audition')

# GUI: panel round-trip, window mix flow
from PyQt6.QtWidgets import QApplication, QMessageBox, QDialog
app = QApplication([])
sys.excepthook = lambda *a: (_ for _ in ()).throw(a[1])
from src.ui.audio_fx_panel import AudioFxPanel
pn = AudioFxPanel()
chain = [{'name': 'pitch', 'params': {'semitones': 4.0}}, {'name': 'echo', 'params': {'delay_ms': 200.0, 'decay': 0.3}},
         {'name': 'highpass', 'params': {'hz': 500}}]
pn.set_chain(chain)
got = pn.get_chain()
assert [g[0] for g in got] == ['pitch', 'echo', 'highpass'], got
assert got[0][1]['semitones'] == 4 and abs(got[1][1]['decay'] - 0.3) < 0.01 and got[2][1]['hz'] == 500
emitted = []
pn.fx_chain_changed.connect(emitted.append)
for i in range(5):
    pn._sliders[('echo', 'delay_ms')][0].setValue(300 + i)
t0 = time.time()
while not emitted and time.time() - t0 < 2: app.processEvents()
assert len(emitted) == 1                              # debounced: 5 moves -> 1 emit
pn.preset_combo.setCurrentIndex(pn.preset_combo.findText('Robot')); pn._on_preset(pn.preset_combo.currentIndex())
assert [g[0] for g in pn.get_chain()] == ['robot']
print('OK panel')

QMessageBox.information = staticmethod(lambda *a, **k: None)
QDialog.exec = lambda self: 0
from src.ui.main_window import MainWindow
win = MainWindow()
win.project.add_clip(Clip(clip_type=ClipType.VIDEO, source_path=vid, timeline_end=2000, source_end=2000))
win.project.settings.duration = 2000
win._start_mix()
t0 = time.time()
while win.audio.source is None and time.time() - t0 < 15: app.processEvents()
assert win.audio.source and os.path.isfile(win.audio.source)
win._toggle_play(True); win._toggle_play(False)       # headless player must not raise
win.preview_panel.volume_slider.setValue(30)
win._open_voice_fx()
win._stop_mix()
print('OK gui mix')
print('ALL OK')
