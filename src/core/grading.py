"""
Pro color grading: .cube 3D LUTs, procedural looks, lift/gamma/gain wheels,
8-band HSL, RGB/luma curves, scopes. All functions take/return RGB uint8.
"""

import os
import cv2
import numpy as np

BANDS = ['red', 'orange', 'yellow', 'green', 'cyan', 'blue', 'purple', 'magenta']
_BAND_HUE = [0, 15, 30, 60, 90, 120, 142, 165]   # OpenCV hue (0-180)
WHEELS = ['lift', 'gamma', 'gain']                # each [r, g, b, master], 0 = identity
CURVE_KEYS = ['master', 'r', 'g', 'b']

# ── .cube 3D LUT ──────────────────────────────────────────────────────────────

_cube_cache = {}


def load_cube(path: str):
    """Parse a .cube file -> float32 table (N,N,N,3) indexed [b,g,r]. Raises ValueError."""
    key = (path, os.path.getmtime(path))
    if key in _cube_cache:
        return _cube_cache[key]
    size, rows, dmin, dmax = None, [], np.zeros(3), np.ones(3)
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.split('#')[0].strip()
            if not line:
                continue
            p = line.split()
            k = p[0].upper()
            if k == 'LUT_3D_SIZE':
                size = int(p[1])
            elif k == 'LUT_1D_SIZE':
                raise ValueError('1D LUT not supported')
            elif k == 'DOMAIN_MIN':
                dmin = np.array(p[1:4], dtype=np.float64)
            elif k == 'DOMAIN_MAX':
                dmax = np.array(p[1:4], dtype=np.float64)
            elif k == 'TITLE':
                pass
            else:
                try:
                    rows.append([float(v) for v in p[:3]])
                except ValueError:
                    raise ValueError(f'bad line: {line[:40]}')
    if size is None or not 2 <= size <= 65:
        raise ValueError('missing or invalid LUT_3D_SIZE')
    if len(rows) != size ** 3 or any(len(r) != 3 for r in rows):
        raise ValueError('data row count does not match LUT_3D_SIZE')
    t = (np.array(rows, dtype=np.float64) - dmin) / np.maximum(dmax - dmin, 1e-9)
    t = np.clip(t, 0, 1).astype(np.float32).reshape(size, size, size, 3)  # [b,g,r] (R fastest)
    _cube_cache[key] = t
    return t


def apply_lut3d(frame: np.ndarray, table: np.ndarray) -> np.ndarray:
    """Trilinear interpolation. ponytail: pure NumPy (~150ms @1080p); upgrade = GPU/cv2 path."""
    n = table.shape[0]
    x = frame.astype(np.float32) * ((n - 1) / 255.0)
    i0 = np.minimum(x.astype(np.int32), n - 2)
    f = x - i0
    r0, g0, b0 = i0[..., 0], i0[..., 1], i0[..., 2]
    fr, fg, fb = f[..., 0:1], f[..., 1:2], f[..., 2:3]
    flat = table.reshape(-1, 3)
    base = (b0 * n + g0) * n + r0

    def c(db, dg, dr):
        return flat[base + (db * n + dg) * n + dr]

    c00 = c(0, 0, 0) * (1 - fr) + c(0, 0, 1) * fr
    c01 = c(0, 1, 0) * (1 - fr) + c(0, 1, 1) * fr
    c10 = c(1, 0, 0) * (1 - fr) + c(1, 0, 1) * fr
    c11 = c(1, 1, 0) * (1 - fr) + c(1, 1, 1) * fr
    c0 = c00 * (1 - fg) + c01 * fg
    c1 = c10 * (1 - fg) + c11 * fg
    out = c0 * (1 - fb) + c1 * fb
    return np.clip(out * 255.0 + 0.5, 0, 255).astype(np.uint8)


# Procedural looks (original formulas, built as 17^3 tables). fn: float (...,3) RGB 0-1 -> same.

def _luma(x):
    return (x[..., 0] * .299 + x[..., 1] * .587 + x[..., 2] * .114)[..., None]


def _sat(x, k):
    l = _luma(x)
    return l + (x - l) * k


def _scurve(x, k=0.5):
    x = np.clip(x, 0, 1)
    return x + k * (x * x * (3 - 2 * x) - x)


LOOKS = {
    'cinematic_cool': lambda x: np.clip(_sat(_scurve(x * np.array([.96, 1.0, 1.06]), .6), .9), 0, 1),
    'warm_film': lambda x: np.clip(_sat(_scurve(x * np.array([1.06, 1.0, .92]) + .02, .4), 1.1), 0, 1),
    'faded': lambda x: np.clip(_sat(x * .85 + .1, .8), 0, 1),
    'cyberpunk': lambda x: np.clip(_sat(x * np.array([1.1, .9, 1.15]) + np.array([.0, -.02, .04]) * (1 - _luma(x)), 1.35), 0, 1),
    'mono_noir': lambda x: np.clip(np.repeat(_scurve(_luma(x), .8), 3, axis=-1), 0, 1),
    'vivid': lambda x: np.clip(_sat(_scurve(x, .3), 1.4), 0, 1),
}


def _build_look(fn, n=17):
    g = np.linspace(0, 1, n, dtype=np.float32)
    b, gg, r = np.meshgrid(g, g, g, indexing='ij')
    return np.clip(fn(np.stack([r, gg, b], -1)), 0, 1).astype(np.float32)


_look_cache = {}


def apply_named_lut(frame: np.ndarray, lut_id: str) -> np.ndarray:
    """lut_id: 'cube:<path>', '*.cube', a LOOKS key, or a legacy FrameProcessor id."""
    if not lut_id:
        return frame
    if lut_id.startswith('cube:') or lut_id.lower().endswith('.cube'):
        path = lut_id[5:] if lut_id.startswith('cube:') else lut_id
        try:
            return apply_lut3d(frame, load_cube(path))
        except (OSError, ValueError):
            return frame
    if lut_id in LOOKS:
        if lut_id not in _look_cache:
            _look_cache[lut_id] = _build_look(LOOKS[lut_id])
        return apply_lut3d(frame, _look_cache[lut_id])
    from src.core.video_player import FrameProcessor
    return FrameProcessor.apply_lut(frame, lut_id)


# ── Lift / Gamma / Gain ───────────────────────────────────────────────────────

def _wheel_vals(w):
    w = list(w or [])
    return (w + [0.0] * 4)[:4]


def wheels_identity(wheels) -> bool:
    return not wheels or all(abs(v) < 1e-4 for k in WHEELS for v in _wheel_vals(wheels.get(k)))


def color_wheels(frame: np.ndarray, wheels: dict) -> np.ndarray:
    """out = ((x + lift*(1-x)) * gain) ** (1/gamma); per channel, values in [-1,1]."""
    if wheels_identity(wheels):
        return frame
    x = np.arange(256, dtype=np.float32) / 255.0
    luts = []
    for ch in range(3):
        lift = _wheel_vals(wheels.get('lift'))
        gamma = _wheel_vals(wheels.get('gamma'))
        gain = _wheel_vals(wheels.get('gain'))
        l = lift[ch] + lift[3]
        gm = float(np.clip(2.0 ** (gamma[ch] + gamma[3]), 0.2, 5.0))
        gn = max(0.0, 1.0 + gain[ch] + gain[3])
        y = np.clip((x + l * (1 - x)) * gn, 0, 1) ** (1.0 / gm)
        luts.append(np.clip(y * 255 + 0.5, 0, 255).astype(np.uint8))
    out = np.empty_like(frame)
    for ch in range(3):
        out[..., ch] = cv2.LUT(frame[..., ch], luts[ch])
    return out


# ── HSL (8 bands) ─────────────────────────────────────────────────────────────

def hsl_identity(hsl) -> bool:
    return not hsl or all(abs(v) < 1e-4 for b in BANDS for v in (hsl.get(b) or []))


def hsl_adjust(frame: np.ndarray, hsl: dict) -> np.ndarray:
    """hsl[band] = [hue, sat, lum] each -100..100. Smooth cosine falloff between bands."""
    if hsl_identity(hsl):
        return frame
    hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV).astype(np.float32)
    h = hsv[..., 0]
    dh = np.zeros_like(h)
    ds = np.zeros_like(h)
    dl = np.zeros_like(h)
    width = 22.0
    for band, centre in zip(BANDS, _BAND_HUE):
        v = (list(hsl.get(band) or []) + [0, 0, 0])[:3]
        if not any(v):
            continue
        d = np.abs(h - centre)
        d = np.minimum(d, 180 - d)
        w = np.where(d < width, np.cos(d / width * (np.pi / 2)) ** 2, 0).astype(np.float32)
        dh += w * v[0]
        ds += w * v[1]
        dl += w * v[2]
    hsv[..., 0] = (h + dh * 0.15) % 180
    hsv[..., 1] = np.clip(hsv[..., 1] * (1 + ds / 100), 0, 255)
    hsv[..., 2] = np.clip(hsv[..., 2] * (1 + dl / 200), 0, 255)
    return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB)


# ── Curves ────────────────────────────────────────────────────────────────────

def _pchip(xs, ys, x):
    """Monotone cubic (Fritsch-Carlson); flat outside [xs[0], xs[-1]]."""
    h = np.diff(xs)
    d = np.diff(ys) / h
    m = np.zeros(len(xs))
    if len(xs) == 2:
        m[:] = d[0]
    else:
        m[1:-1] = np.where(d[:-1] * d[1:] > 0, 2 * d[:-1] * d[1:] / (d[:-1] + d[1:] + 1e-12), 0)
        m[0] = d[0] if d[0] * m[1] >= 0 else 0
        m[-1] = d[-1] if d[-1] * m[-2] >= 0 else 0
    xc = np.clip(x, xs[0], xs[-1])
    i = np.clip(np.searchsorted(xs, xc, side='right') - 1, 0, len(xs) - 2)
    t = (xc - xs[i]) / h[i]
    t2, t3 = t * t, t * t * t
    return ((2 * t3 - 3 * t2 + 1) * ys[i] + (t3 - 2 * t2 + t) * h[i] * m[i]
            + (-2 * t3 + 3 * t2) * ys[i + 1] + (t3 - t2) * h[i] * m[i + 1])


def _curve_lut(points):
    pts = sorted({(round(float(p[0]), 4), float(p[1])) for p in points})
    xs, ys = [], []
    for x, y in pts:
        if xs and x <= xs[-1]:
            continue
        xs.append(min(1.0, max(0.0, x)))
        ys.append(min(1.0, max(0.0, y)))
    if len(xs) < 2:
        return None
    y = _pchip(np.array(xs), np.array(ys), np.linspace(0, 1, 256))
    return np.clip(y * 255 + 0.5, 0, 255).astype(np.uint8)


def _is_identity_pts(points):
    return not points or all(abs(p[0] - p[1]) < 1e-4 for p in points)


def curves_identity(curves) -> bool:
    return not curves or all(_is_identity_pts(curves.get(k)) for k in CURVE_KEYS)


def apply_curves(frame: np.ndarray, curves: dict) -> np.ndarray:
    """curves[key] = [[x,y],...] in 0..1, key in master/r/g/b. Monotone (PCHIP) interpolation."""
    if curves_identity(curves):
        return frame
    ident = np.arange(256, dtype=np.uint8)
    master = _curve_lut(curves.get('master') or []) if not _is_identity_pts(curves.get('master')) else None
    out = np.empty_like(frame)
    for i, k in enumerate(['r', 'g', 'b']):
        lut = ident
        if not _is_identity_pts(curves.get(k)):
            c = _curve_lut(curves[k])
            if c is not None:
                lut = c
        if master is not None:
            lut = master[lut]
        out[..., i] = cv2.LUT(frame[..., i], lut)
    return out


# ── Entry point used by renderer ─────────────────────────────────────────────

def apply_grading(frame: np.ndarray, clip) -> np.ndarray:
    """Wheels -> HSL -> curves (skipping identity steps)."""
    frame = color_wheels(frame, getattr(clip, 'color_wheels', None))
    frame = hsl_adjust(frame, getattr(clip, 'hsl', None))
    return apply_curves(frame, getattr(clip, 'curves', None))


# ── Scopes ────────────────────────────────────────────────────────────────────

def histogram(frame: np.ndarray, w=256, h=128) -> np.ndarray:
    img = np.zeros((h, w, 3), np.uint8)
    for ch in range(3):
        hist = cv2.calcHist([frame], [ch], None, [w], [0, 256]).ravel()
        hist = hist / max(hist.max(), 1) * (h - 1)
        for x, v in enumerate(hist.astype(int)):
            if v > 0:
                img[h - v:, x, ch] = 255
    return img


def waveform(frame: np.ndarray, w=256, h=128) -> np.ndarray:
    small = cv2.resize(frame, (w, min(frame.shape[0], 90)), interpolation=cv2.INTER_AREA)
    luma = (small.astype(np.float32) @ np.array([.299, .587, .114], np.float32))
    acc = np.zeros((h, w), np.float32)
    ys = np.clip((255 - luma) / 255 * (h - 1), 0, h - 1).astype(int)
    for x in range(w):
        np.add.at(acc[:, x], ys[:, x], 1)
    acc = np.clip(acc / max(acc.max(), 1) * 4, 0, 1)
    g = (acc * 255).astype(np.uint8)
    return np.stack([g // 3, g, g // 3], -1)


def vectorscope(frame: np.ndarray, size=160) -> np.ndarray:
    small = cv2.resize(frame, (96, 54), interpolation=cv2.INTER_AREA)
    ycc = cv2.cvtColor(small, cv2.COLOR_RGB2YCrCb).reshape(-1, 3).astype(np.float32)
    cr, cb = ycc[:, 1] - 128, ycc[:, 2] - 128
    img = np.zeros((size, size, 3), np.uint8)
    c = size // 2
    cv2.circle(img, (c, c), c - 2, (50, 50, 50), 1)
    xs = np.clip(c + cb / 128 * (c - 2), 0, size - 1).astype(int)
    ys = np.clip(c - cr / 128 * (c - 2), 0, size - 1).astype(int)
    img[ys, xs] = (0, 255, 120)
    return img
