"""Motion/stylise effects: camera shake, 3D zoom, zoom/spin, flash, mirror, wave, pixelate, ...
All pure functions of (frame RGB uint8, params, progress). params['_t'] = timeline seconds (set by
the renderer) so results are deterministic: preview == export."""

import math

import cv2
import numpy as np


def _warp(f, M):
    h, w = f.shape[:2]
    return cv2.warpAffine(f, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def camera_shake(f, p, progress):
    """Sum of three seeded sines for x, y, roll. amount/speed 0..1; pulse=True decays like an impact."""
    t = p.get('_t', 0.0)
    amt = max(0.0, min(1.0, p.get('amount', .4)))
    if amt <= 0:
        return f
    base = 1.5 + 10 * max(0.0, min(1.0, p.get('speed', .4)))
    rs = np.random.RandomState(int(p.get('seed', 7)))
    ph = rs.uniform(0, 2 * math.pi, (3, 3))
    fr = base * np.array([1.0, 1.7, 2.9])
    w3 = np.array([1.0, .5, .25])
    wave_ = lambda k: float((w3 * np.sin(2 * math.pi * fr * t + ph[k])).sum() / w3.sum())
    if p.get('pulse'):
        amt *= math.exp(-4.0 * ((t * base / 6) % 1.0))
    h, w = f.shape[:2]
    dx, dy = wave_(0) * amt * 0.03 * w, wave_(1) * amt * 0.03 * h
    rot = wave_(2) * amt * 2.0
    zoom = 1.0 + amt * 0.07           # crop in so reflected edges rarely show
    M = cv2.getRotationMatrix2D((w / 2, h / 2), rot, zoom)
    M[:, 2] += (dx, dy)
    return _warp(f, M)


def zoom_3d(f, p, progress):
    from src.core.kenburns import ThreeDZoomEngine
    k = progress if p.get('animate', True) else 1.0
    return ThreeDZoomEngine.apply(f, 1.0 + (p.get('zoom', 1.2) - 1.0) * k,
                                  p.get('rotation_x', 0.0) * k, p.get('rotation_y', 0.0) * k)


def zoom_in(f, p, progress):
    h, w = f.shape[:2]
    z = 1.0 + p.get('amount', .3) * progress
    return _warp(f, cv2.getRotationMatrix2D((w / 2, h / 2), 0, z))


def zoom_out(f, p, progress):
    h, w = f.shape[:2]
    z = 1.0 + p.get('amount', .3) * (1 - progress)
    return _warp(f, cv2.getRotationMatrix2D((w / 2, h / 2), 0, z))


def spin(f, p, progress):
    h, w = f.shape[:2]
    a = math.radians(p.get('turns', 1.0) * 360 * progress)
    z = abs(math.cos(a)) + abs(math.sin(a)) * max(w / h, h / w)   # cover the canvas while rotated
    return _warp(f, cv2.getRotationMatrix2D((w / 2, h / 2), -math.degrees(a), z))


def flash(f, p, progress):
    t = p.get('_t', 0.0)
    k = max(0.0, 1 - ((t * p.get('rate', 2.0)) % 1.0) * 4) * p.get('amount', .6)
    return f if k <= 0 else cv2.addWeighted(f, 1 - k, np.full_like(f, 255), k, 0)


def blur(f, p, progress):
    s = p.get('amount', 6.0)
    return f if s <= 0.1 else cv2.GaussianBlur(f, (0, 0), s)


def glow(f, p, progress):
    s = p.get('amount', .6)
    hi = cv2.GaussianBlur(np.clip(f.astype(np.float32) - 160, 0, 255), (0, 0), 12)
    return np.clip(f.astype(np.float32) + hi * s * 2.2, 0, 255).astype(np.uint8)


def mirror(f, p, progress):
    h, w = f.shape[:2]
    out = f.copy()
    if p.get('axis', 'h') == 'h':
        out[:, w - w // 2:] = f[:, :w // 2][:, ::-1]
    else:
        out[h - h // 2:] = f[:h // 2][::-1]
    return out


def wave(f, p, progress):
    h, w = f.shape[:2]
    amp = p.get('amount', .5) * 0.02 * w
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    mx = xx + amp * np.sin(yy / max(1, h) * 2 * math.pi * 4 + p.get('_t', 0.0) * 4)
    return cv2.remap(f, mx, yy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def pixelate(f, p, progress):
    h, w = f.shape[:2]
    n = max(2, int(p.get('size', 16)))
    small = cv2.resize(f, (max(1, w // n), max(1, h // n)), interpolation=cv2.INTER_AREA)
    return cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)


def scanlines(f, p, progress):
    out = f.astype(np.float32)
    out[::3] *= 1 - p.get('amount', .35)
    return out.astype(np.uint8)


def tv_noise(f, p, progress):
    rs = np.random.RandomState(int(p.get('_t', 0.0) * 30) + 1)    # per-frame, deterministic
    n = rs.normal(0, 255 * p.get('amount', .12), f.shape[:2]).astype(np.float32)[..., None]
    return np.clip(f.astype(np.float32) + n, 0, 255).astype(np.uint8)


# effect id -> (function, default params)
FX = {
    'camera_shake': (camera_shake, {'amount': .4, 'speed': .4, 'seed': 7}),
    'zoom_3d': (zoom_3d, {'zoom': 1.2, 'rotation_x': 6.0, 'rotation_y': 6.0}),
    'zoom_in': (zoom_in, {'amount': .3}),
    'zoom_out': (zoom_out, {'amount': .3}),
    'spin': (spin, {'turns': 1.0}),
    'flash': (flash, {'rate': 2.0, 'amount': .6}),
    'blur': (blur, {'amount': 6.0}),
    'glow': (glow, {'amount': .6}),
    'mirror': (mirror, {'axis': 'h'}),
    'wave': (wave, {'amount': .5}),
    'pixelate': (pixelate, {'size': 16}),
    'mosaic': (pixelate, {'size': 32}),
    'scanlines': (scanlines, {'amount': .35}),
    'tv_noise': (tv_noise, {'amount': .12}),
}

SHAKE_PRESETS = {
    'Handheld': {'amount': .25, 'speed': .3},
    'Earthquake': {'amount': .9, 'speed': .9},
    'Impact pulse': {'amount': .8, 'speed': .7, 'pulse': True},
}
