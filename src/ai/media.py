"""ffmpeg helpers with progress + cancel. Output goes to <out>.part, then atomically renamed."""

import os
import subprocess
import threading


class Cancelled(Exception):
    pass


def ffmpeg_exe() -> str:
    from src.core.exporter import ffmpeg_exe as f
    return f()


def run_ffmpeg(args, out_path, duration_ms=0, progress=None, cancelled=None):
    """Run ffmpeg with `args` (no exe, no output path); writes out_path atomically.
    Muxer is inferred from out_path's extension. Raises Cancelled / RuntimeError."""
    part = out_path + ".part"
    ext = os.path.splitext(out_path)[1].lstrip(".").lower()
    fmt = {"mkv": "matroska", "wav": "wav", "mp4": "mp4", "m4a": "ipod"}.get(ext, ext)
    cmd = [ffmpeg_exe(), "-y", "-hide_banner", "-loglevel", "error", "-nostats", "-progress", "pipe:1",
           *args, "-f", fmt, part]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    err = []
    t = threading.Thread(target=lambda: err.append(p.stderr.read()), daemon=True)
    t.start()
    try:
        for line in p.stdout:
            if cancelled and cancelled():
                raise Cancelled()
            if progress and duration_ms and line.startswith("out_time_us="):
                try:
                    progress(min(99, int(int(line.split("=")[1]) / 1000 * 100 / duration_ms)))
                except ValueError:
                    pass
        p.wait()
        t.join(2)
        if cancelled and cancelled():
            raise Cancelled()
        if p.returncode:
            raise RuntimeError("ffmpeg failed: " + "".join(err).strip()[-400:])
        os.replace(part, out_path)
        if progress:
            progress(100)
    except BaseException:
        if p.poll() is None:
            p.kill()
            p.wait()
        if os.path.exists(part):
            try:
                os.remove(part)
            except OSError:
                pass
        raise
    return out_path


def extract_audio(src, out_wav, sr=16000, channels=1, start_ms=None, end_ms=None, progress=None, cancelled=None):
    a = []
    if start_ms:
        a += ["-ss", f"{start_ms / 1000:.3f}"]
    if end_ms:
        a += ["-to", f"{end_ms / 1000:.3f}"]
    a += ["-i", src, "-vn", "-acodec", "pcm_s16le", "-ar", str(sr), "-ac", str(channels)]
    dur = (end_ms or 0) - (start_ms or 0)
    return run_ffmpeg(a, out_wav, dur if dur > 0 else 0, progress, cancelled)
