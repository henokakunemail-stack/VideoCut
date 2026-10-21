"""Frame-by-frame video bake: decode -> frame_fn(rgb) -> x264 (crf 12, video only).
The bake keeps source fps and frame count 1:1 for [start_ms, end_ms), so timemap/stabilize/reframe
stay indexed by original source time (clip_video_path returns start_ms as the offset)."""

import os
import subprocess

import cv2
import numpy as np

from src.ai.media import Cancelled, ffmpeg_exe


def run_bake(src, start_ms, end_ms, out_path, frame_fn, progress=None, cancelled=None, out_size=None):
    """Returns {path,start_ms,end_ms,w,h,fps,frames}. out_size=(w,h) when frame_fn changes the size."""
    cap = cv2.VideoCapture(src)
    if not cap.isOpened():
        raise RuntimeError(f"cannot open {src}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    cap.set(cv2.CAP_PROP_POS_MSEC, start_ms)
    total = max(1, int((end_ms - start_ms) / 1000.0 * fps))
    part = out_path + ".part"
    proc = None
    n = 0
    w = h = 0
    try:
        while n < total:
            if cancelled and cancelled():
                raise Cancelled()
            ok, bgr = cap.read()
            if not ok:
                break
            rgb = np.ascontiguousarray(frame_fn(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)))
            if proc is None:
                h, w = rgb.shape[:2]
                w, h = out_size or (w, h)
                w -= w % 2
                h -= h % 2
                proc = subprocess.Popen(
                    [ffmpeg_exe(), "-y", "-hide_banner", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                     "-s", f"{w}x{h}", "-r", f"{fps}", "-i", "-", "-an", "-c:v", "libx264", "-crf", "12",
                     "-preset", "veryfast", "-pix_fmt", "yuv420p", "-f", "matroska", part],
                    stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
            if rgb.shape[1] != w or rgb.shape[0] != h:
                rgb = cv2.resize(rgb, (w, h), interpolation=cv2.INTER_AREA)
            proc.stdin.write(rgb.tobytes())
            n += 1
            if progress and n % 4 == 0:
                progress(min(99, int(100 * n / total)))
        if proc is None:
            raise RuntimeError("no frames decoded")
        proc.stdin.close()
        proc.wait()
        if proc.returncode:
            raise RuntimeError("ffmpeg encode failed")
        os.replace(part, out_path)
        if progress:
            progress(100)
        return {"path": out_path, "start_ms": int(start_ms), "end_ms": int(end_ms), "w": w, "h": h,
                "fps": float(fps), "frames": n}
    except BaseException:
        if proc is not None and proc.poll() is None:
            proc.kill()
            proc.wait()
        if os.path.exists(part):
            try:
                os.remove(part)
            except OSError:
                pass
        raise
    finally:
        cap.release()
