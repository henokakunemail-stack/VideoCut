"""Background matting: U2-Net / IS-Net (ONNX, Apache-2.0) -> guided-filter refine -> baked gray matte.
The matte is baked 1:1 with the source frames (src/ai/bake.py) and read back by the renderer as an alpha
channel, so flip/crop/stabilize treat it exactly like the picture."""

import os

import cv2
import numpy as np

from src.ai import assets, models

_BASE = "https://github.com/danielgatis/rembg/releases/download/v0.0.0/"
models.register(models.Model(
    "u2netp", "u2netp.onnx", "309c8469258dda742793dce0ebea8e6dd393174f89934733ecc8b14c76f4ddd8",
    "Apache-2.0", _BASE + "u2netp.onnx", 4.4))                       # xuebinqin/U-2-Net
models.register(models.Model(
    "isnet", "isnet-general-use.onnx", "60920e99c45464f2ba57bee2ad08c919a52bbf852739e96947fbb4358c0d964a",
    "Apache-2.0", _BASE + "isnet-general-use.onnx", 170.4, optional=True))   # xuebinqin/DIS

QUALITY = {"fast": "u2netp", "high": "isnet"}
_SIZE = {"u2netp": 320, "isnet": 1024}
_MEAN = {"u2netp": (.485, .456, .406), "isnet": (.5, .5, .5)}
_STD = {"u2netp": (.229, .224, .225), "isnet": (1., 1., 1.)}
DEFAULT_STYLE = {"mode": "transparent", "color": "#00ff00", "path": "", "feather": 0}


def matte_frame(rgb, session, model_id="u2netp"):
    """float32 HxW 0..1 foreground probability."""
    h, w = rgb.shape[:2]
    s = _SIZE[model_id]
    x = cv2.resize(rgb, (s, s), interpolation=cv2.INTER_AREA).astype(np.float32)
    x = x / (x.max() if model_id == "u2netp" and x.max() > 0 else 255.0)
    x = ((x - _MEAN[model_id]) / _STD[model_id]).transpose(2, 0, 1)[None].astype(np.float32)
    d = session.run(None, {session.get_inputs()[0].name: x})[0][0, 0]
    d = (d - d.min()) / max(1e-6, float(d.max() - d.min()))
    return cv2.resize(d, (w, h), interpolation=cv2.INTER_LINEAR)


def refine(alpha, rgb, r=15, eps=1e-3):
    """Guided filter (He et al.): snaps the matte edge to image edges. ponytail: plain box filters, no ximgproc."""
    I = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0
    p = alpha.astype(np.float32)
    k = (2 * r + 1, 2 * r + 1)
    box = lambda x: cv2.boxFilter(x, -1, k)
    mI, mp = box(I), box(p)
    a = (box(I * p) - mI * mp) / (box(I * I) - mI * mI + eps)
    b = mp - a * mI
    return np.clip(box(a) * I + box(b), 0, 1)


def make_frame_fn(quality="fast", ema=0.6):
    """rgb -> 3-channel gray matte (uint8). Session is created on the calling (worker) thread."""
    from src.ai.runtime import ort_session
    mid = QUALITY[quality]
    sess = ort_session(mid)
    prev = [None]

    def fn(rgb):
        a = refine(matte_frame(rgb, sess, mid), rgb)
        if prev[0] is not None and prev[0].shape == a.shape:
            a = ema * a + (1 - ema) * prev[0]
        prev[0] = a
        return np.repeat((a * 255 + .5).astype(np.uint8)[..., None], 3, 2)
    return fn


def _probe(path):
    cap = cv2.VideoCapture(path)
    w, h, fps, n = (int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                    cap.get(cv2.CAP_PROP_FPS), int(cap.get(cv2.CAP_PROP_FRAME_COUNT)))
    cap.release()
    return w, h, fps, n


def bake_matte(clip, out_dir, quality="fast", *, frame_fn=None, progress=None, cancelled=None):
    """Bake the matte for clip's trimmed range into out_dir. Returns the clip.ai['matte'] dict; does not touch clip."""
    from src.ai.bake import run_bake
    from src.core.project import ClipType
    mid = QUALITY[quality]
    src, s, e = clip.source_path, int(clip.source_start), int(clip.source_end)
    is_img = clip.clip_type != ClipType.VIDEO
    key = assets.cache_key(src, s, e, mid, quality)
    out = os.path.join(str(out_dir), f"matte_{key}{'.png' if is_img else '.mkv'}")
    meta = {"path": out, "start_ms": s, "end_ms": e, "key": key, "model": mid, "quality": quality}
    if frame_fn is None:
        if os.path.isfile(out):                       # same source+range+model: reuse
            w, h, fps, n = _probe(out) if not is_img else (0, 0, 0.0, 1)
            return {**meta, "w": w, "h": h, "fps": fps, "frames": n}
        frame_fn = make_frame_fn(quality)
    if is_img:
        img = cv2.cvtColor(cv2.imread(src, cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)
        m = frame_fn(img)
        cv2.imwrite(out, m[..., 0])
        return {**meta, "w": m.shape[1], "h": m.shape[0], "fps": 0.0, "frames": 1}
    r = run_bake(src, s, e, out, frame_fn, progress, cancelled)
    return {**meta, "w": r["w"], "h": r["h"], "fps": r["fps"], "frames": r["frames"]}


def matte_status(clip) -> str:
    """'none' (no bake), 'ok', or 'stale' (file gone / source changed / trim outside the baked range)."""
    m = (clip.ai or {}).get("matte")
    if not m:
        return "none"
    try:
        if not os.path.isfile(m["path"]) or m["key"] != assets.cache_key(
                clip.source_path, m["start_ms"], m["end_ms"], m["model"], m["quality"]):
            return "stale"
        from src.core.project import ClipType
        if clip.clip_type == ClipType.VIDEO and (clip.source_start < m["start_ms"] or clip.source_end > m["end_ms"]):
            return "stale"
    except KeyError:
        return "stale"
    return "ok"


def matte_style(clip):
    """Style dict when the clip has a usable matte, else None."""
    if matte_status(clip) != "ok":
        return None
    return {**DEFAULT_STYLE, **(clip.ai.get("matte_style") or {})}


def read_matte(readers, clip, src_ms, shape):
    """float32 HxW 0..1 matte for source time src_ms resized to `shape`, or None."""
    from src.core.project import ClipType
    from src.core.video_player import ImageReader, VideoReader
    m = clip.ai["matte"]
    p = m["path"]
    if p not in readers:
        r = ImageReader(p) if clip.clip_type != ClipType.VIDEO else VideoReader(p)
        readers[p] = r if r.is_valid() else None
    r = readers[p]
    if r is None:
        return None
    if clip.clip_type == ClipType.VIDEO:               # same index rule as the source reader
        f = r.read_index(int(src_ms / 1000.0 * r.fps + 1e-6) - int(m["start_ms"] / 1000.0 * r.fps + 1e-6))
    else:
        f = r.read_frame()
    if f is None:
        return None
    a = f[..., 0].astype(np.float32) / 255.0
    return a if a.shape == shape[:2] else cv2.resize(a, (shape[1], shape[0]), interpolation=cv2.INTER_LINEAR)
