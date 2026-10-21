"""
ffmpeg-based exporter: renders every frame through core.renderer (same as preview),
burns text overlays, mixes all audio, writes the final file with the chosen codec.
"""

import os
import re
import shutil
import subprocess
import tempfile

import cv2
import numpy as np

from src.core.project import ClipType
from src.core.renderer import compose_frame, fetch_clip_frame, text_infos_at

# format key -> (container ext, video args, audio codec args)
CODECS = {
    'h264': ('.mp4', ['-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-preset', 'medium', '-movflags', '+faststart'], ['-c:a', 'aac', '-b:a', '192k']),
    'h265': ('.mp4', ['-c:v', 'libx265', '-pix_fmt', 'yuv420p', '-tag:v', 'hvc1', '-movflags', '+faststart'], ['-c:a', 'aac', '-b:a', '192k']),
    'prores': ('.mov', ['-c:v', 'prores_ks', '-profile:v', '3', '-pix_fmt', 'yuv422p10le'], ['-c:a', 'pcm_s16le']),
    'vp9': ('.webm', ['-c:v', 'libvpx-vp9', '-pix_fmt', 'yuv420p', '-b:v', '0'], ['-c:a', 'libopus']),
    'mpeg4': ('.avi', ['-c:v', 'mpeg4', '-pix_fmt', 'yuv420p'], ['-c:a', 'mp3']),
}
CRF = {0: 30, 1: 25, 2: 20, 3: 15}  # Low, Medium, High, Ultra


def ffmpeg_exe() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        exe = shutil.which('ffmpeg')
        if exe:
            return exe
    raise RuntimeError("ffmpeg not found. Run: pip install imageio-ffmpeg")


def has_audio(path: str) -> bool:
    """True if media has an audio stream (ffmpeg -i prints stream info to stderr)."""
    try:
        r = subprocess.run([ffmpeg_exe(), '-hide_banner', '-i', path], capture_output=True, text=True, timeout=30)
        return bool(re.search(r'Stream #.*Audio:', r.stderr))
    except Exception:
        return False


def _audio_sources(project):
    """Yield dicts: path, segs [(src_lo_ms, src_hi_ms, reversed, speed)], tl_start/tl_dur (ms),
    volume, fade_in/out (s). Speed curves arrive as several constant-speed segments."""
    from src.core import timemap
    for c in project.clips:
        if c.clip_type in (ClipType.VIDEO, ClipType.AUDIO) and c.source_path and not c.muted                 and c.volume > 0 and not c.freeze:
            segs = timemap.audio_segments(c)
            if segs and has_audio(c.source_path):
                yield dict(path=c.source_path, segs=segs, tl_start=c.timeline_start, tl_dur=c.duration,
                           volume=c.volume, fade_in=c.audio_fade_in, fade_out=c.audio_fade_out)
    for t in project.audio_tracks:
        if t.source_path and not t.muted and t.volume > 0:
            yield dict(path=t.source_path, segs=[(t.source_start, t.source_end, False, 1.0)],
                       tl_start=t.timeline_start, tl_dur=t.duration,
                       volume=t.volume, fade_in=t.fade_in, fade_out=t.fade_out)


def _atempo(speed: float) -> str:
    parts = []
    while speed > 2.0:
        parts.append('atempo=2.0'); speed /= 2.0
    while speed < 0.5:
        parts.append('atempo=0.5'); speed /= 0.5
    parts.append(f'atempo={speed:.4f}')
    return ','.join(parts)


def build_audio_cmd(sources, duration_s):
    """Returns (input_args, filter_complex, map_label) or None when there is no audio.
    Audio inputs are numbered from 1 (input 0 is the silent video)."""
    if not sources:
        return None
    ins, chains, labels = [], [], []
    for i, s in enumerate(sources):
        ins += ['-i', s['path']]
        segs, n = s['segs'], len(s['segs'])
        if n > 1:
            chains.append(f"[{i + 1}:a]asplit={n}" + ''.join(f'[i{i}_{k}]' for k in range(n)))
        for k, (lo, hi, rev, spd) in enumerate(segs):
            f = [f"atrim=start={lo/1000:.3f}:end={hi/1000:.3f}", 'asetpts=PTS-STARTPTS']
            if rev:
                f.append('areverse')
            if abs(spd - 1.0) > 1e-3:
                f.append(_atempo(spd))
            src = f"[i{i}_{k}]" if n > 1 else f"[{i + 1}:a]"
            chains.append(f"{src}{','.join(f)}[s{i}_{k}]")
        dur = s['tl_dur'] / 1000
        tail = [f"apad=whole_dur={dur:.3f}", f"atrim=0:{dur:.3f}"]
        if s['fade_in'] > 0:
            tail.append(f"afade=t=in:st=0:d={s['fade_in']:.3f}")
        if s['fade_out'] > 0:
            tail.append(f"afade=t=out:st={max(0, dur - s['fade_out']):.3f}:d={s['fade_out']:.3f}")
        tail.append(f"volume={s['volume']:.3f}")
        tail.append(f"adelay={int(s['tl_start'])}|{int(s['tl_start'])}")
        joined = ''.join(f'[s{i}_{k}]' for k in range(n))
        head = f"{joined}concat=n={n}:v=0:a=1," if n > 1 else f"{joined}"
        chains.append(f"{head}{','.join(tail)}[a{i}]")
        labels.append(f'[a{i}]')
    chains.append(f"{''.join(labels)}amix=inputs={len(sources)}:normalize=0:duration=longest,"
                  f"atrim=0:{duration_s:.3f}[aout]")
    return ins, ';'.join(chains), '[aout]'


def _burn_text(frame: np.ndarray, infos) -> np.ndarray:
    if not infos:
        return frame
    from PyQt6.QtGui import QImage, QPainter
    from src.ui.preview_panel import VideoCanvas
    h, w = frame.shape[:2]
    frame = np.ascontiguousarray(frame)
    img = QImage(frame.data, w, h, w * 3, QImage.Format.Format_RGB888)
    p = QPainter(img)
    for info in infos:
        VideoCanvas._draw_text_overlay(p, info, 0, 0, w, h)
    p.end()
    return frame  # QImage shares the buffer, so painting wrote into `frame`


def export_project(project, s: dict, progress=lambda pct: None, cancelled=lambda: False):
    """s: output_path, width, height, fps, quality(0-3), codec(CODECS key). Returns (ok, msg)."""
    dur_ms = project.settings.duration
    if dur_ms <= 0:
        return False, "No content to export (empty timeline)."

    w, h, fps = s['width'] - s['width'] % 2, s['height'] - s['height'] % 2, s['fps']
    codec = s.get('codec', 'h264')
    _, vargs, aargs = CODECS[codec]
    out = s['output_path']
    exe = ffmpeg_exe()
    total = max(1, int(dur_ms / 1000 * fps))

    tmpdir = tempfile.mkdtemp(prefix='videocut_')
    silent = os.path.join(tmpdir, 'video' + os.path.splitext(out)[1])
    qargs = ['-crf', str(CRF.get(s.get('quality', 2), 20))] if codec in ('h264', 'h265', 'vp9') else \
            (['-q:v', '3'] if codec == 'mpeg4' else [])
    cmd = [exe, '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{w}x{h}', '-r', str(fps), '-i', '-',
           *vargs, *qargs, '-an', silent]

    readers = {}

    def get_frame(clip, t_ms):
        return fetch_clip_frame(readers, clip, t_ms)

    trans_cache = {}
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        black = np.zeros((h, w, 3), np.uint8)
        for i in range(total):
            if cancelled():
                proc.kill()
                return False, "Export cancelled."
            t_ms = int(i / fps * 1000)
            frame = compose_frame(project, t_ms, get_frame, size=(w, h), cache=trans_cache)
            frame = _burn_text(black.copy() if frame is None else frame, text_infos_at(project, t_ms))
            try:
                proc.stdin.write(frame.tobytes())
            except (BrokenPipeError, OSError):
                break
            progress(int((i + 1) / total * 90))
        proc.stdin.close()
        err = proc.stderr.read().decode(errors='replace')
        if proc.wait() != 0:
            return False, f"ffmpeg video encode failed:\n{err[-600:]}"

        audio = build_audio_cmd(list(_audio_sources(project)), dur_ms / 1000)
        if audio:
            ins, fc, label = audio
            mux = [exe, '-y', '-i', silent, *ins, '-filter_complex', fc, '-map', '0:v', '-map', label,
                   '-c:v', 'copy', *aargs, '-shortest', out]
        else:
            mux = [exe, '-y', '-i', silent, '-c', 'copy', out]
        r = subprocess.run(mux, capture_output=True, text=True)
        if r.returncode != 0:
            return False, f"ffmpeg audio mux failed:\n{r.stderr[-600:]}"
        progress(100)
        return True, f"Exported to: {out}"
    finally:
        if proc.poll() is None:
            proc.kill()
        for r_ in readers.values():
            if r_ and hasattr(r_, 'close'):
                r_.close()
        shutil.rmtree(tmpdir, ignore_errors=True)
