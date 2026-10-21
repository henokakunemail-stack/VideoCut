"""
Transitions: fn(a, b, p) -> frame. a = outgoing, b = incoming (same HxWx3 uint8), p in 0..1.
Use transition_frame() — it clamps p, eases it and guarantees p<=0 -> a, p>=1 -> b.
"""

import cv2
import numpy as np


def _mix(a, b, p):
    return cv2.addWeighted(a, 1.0 - p, b, p, 0)


def _zoom(img, s):
    """Centre zoom-in by factor s >= 1, same output size."""
    h, w = img.shape[:2]
    ch, cw = max(1, int(h / s)), max(1, int(w / s))
    y, x = (h - ch) // 2, (w - cw) // 2
    return cv2.resize(img[y:y + ch, x:x + cw], (w, h), interpolation=cv2.INTER_LINEAR)


def _cols(a, b, mask_cols):
    out = a.copy()
    out[:, mask_cols] = b[:, mask_cols]
    return out


def _rows(a, b, mask_rows):
    out = a.copy()
    out[mask_rows] = b[mask_rows]
    return out


def _wipe_left(a, b, p):
    w = a.shape[1]
    return _cols(a, b, np.arange(w) >= int(w * (1 - p)))


def _wipe_right(a, b, p):
    w = a.shape[1]
    return _cols(a, b, np.arange(w) < int(w * p))


def _wipe_up(a, b, p):
    h = a.shape[0]
    return _rows(a, b, np.arange(h) >= int(h * (1 - p)))


def _wipe_down(a, b, p):
    h = a.shape[0]
    return _rows(a, b, np.arange(h) < int(h * p))


def _slide_left(a, b, p):
    w = a.shape[1]
    off = int(w * p)
    return np.concatenate([a, b], axis=1)[:, off:off + w]


def _slide_right(a, b, p):
    w = a.shape[1]
    off = int(w * p)
    return np.concatenate([b, a], axis=1)[:, w - off:2 * w - off]


def _zoom_in(a, b, p):
    return _mix(_zoom(a, 1 + p), b, p)


def _zoom_out(a, b, p):
    return _mix(a, _zoom(b, 2 - p), p)


def _rotate(a, b, p):
    h, w = a.shape[:2]
    M = cv2.getRotationMatrix2D((w / 2, h / 2), 90 * p, max(0.01, 1 - p))
    wa = cv2.warpAffine(a, M, (w, h), borderMode=cv2.BORDER_CONSTANT)
    cover = cv2.warpAffine(np.ones((h, w), np.float32), M, (w, h))[..., None]
    return (wa * cover + b * (1 - cover)).astype(np.uint8)


_NOISE = {}


def _dissolve(a, b, p):
    h, w = a.shape[:2]
    if (h, w) not in _NOISE:
        _NOISE[(h, w)] = np.random.default_rng(7).random((h, w), dtype=np.float32)
    m = (_NOISE[(h, w)] < p)[..., None]
    return np.where(m, b, a)


def _flash(a, b, p):
    white = np.full_like(a, 255)
    return _mix(a, white, p * 2) if p < 0.5 else _mix(white, b, p * 2 - 1)


def _blur(a, b, p):
    mixed = _mix(a, b, p)
    sigma = 30 * np.sin(np.pi * p)
    return cv2.GaussianBlur(mixed, (0, 0), sigma) if sigma > 0.5 else mixed


def _glitch(a, b, p):
    h, w = a.shape[:2]
    rng = np.random.default_rng(int(p * 24))
    out = a.copy()
    band = max(2, h // 24)
    amp = int(w * 0.08 * np.sin(np.pi * p))
    for y in range(0, h, band):
        src = b if rng.random() < p else a
        dx = int(rng.integers(-amp, amp + 1)) if amp else 0
        out[y:y + band] = np.roll(src[y:y + band], dx, axis=1)
    if amp:  # RGB split
        out[..., 0] = np.roll(out[..., 0], amp // 2, axis=1)
        out[..., 2] = np.roll(out[..., 2], -amp // 2, axis=1)
    return out


def _split_h(a, b, p):
    w = a.shape[1]
    return _cols(a, b, np.abs(np.arange(w) - w / 2) < p * w / 2)


def _split_v(a, b, p):
    h = a.shape[0]
    return _rows(a, b, np.abs(np.arange(h) - h / 2) < p * h / 2)


def _page_turn(a, b, p):
    h, w = a.shape[:2]
    x0 = w * (1 - p)
    xs = np.arange(w, dtype=np.float32)
    out = a.copy()
    out[:, xs >= x0] = b[:, xs >= x0]
    back = (xs < x0) & (xs >= x0 - (w - x0))  # peeled page showing its back
    src = np.clip((2 * x0 - xs[back]).astype(int), 0, w - 1)
    out[:, back] = (a[:, src] * 0.75).astype(np.uint8)
    return out


def _swirl_img(img, k):
    h, w = img.shape[:2]
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    cx, cy = w / 2, h / 2
    dx, dy = xs - cx, ys - cy
    r = np.sqrt(dx * dx + dy * dy)
    ang = k * np.clip(1 - r / (min(w, h) / 2 + 1e-6), 0, 1)
    c, s = np.cos(ang), np.sin(ang)
    return cv2.remap(img, (cx + dx * c - dy * s).astype(np.float32),
                     (cy + dx * s + dy * c).astype(np.float32), cv2.INTER_LINEAR,
                     borderMode=cv2.BORDER_REPLICATE)


def _swirl(a, b, p):
    k = 6 * np.sin(np.pi * p)
    return _mix(_swirl_img(a, k * p), _swirl_img(b, -k * (1 - p)), p)


def _cube(a, b, p):
    h, w = a.shape[:2]
    wa, wb = max(1, int(w * (1 - p))), max(1, int(w * p))
    left = (cv2.resize(a, (wa, h)) * (1 - 0.4 * p)).astype(np.uint8)
    right = (cv2.resize(b, (wb, h)) * (0.6 + 0.4 * p)).astype(np.uint8)
    return np.concatenate([left, right], axis=1)[:, :w] if wa + wb >= w else \
        np.concatenate([left, right, np.zeros((h, w - wa - wb, 3), np.uint8)], axis=1)


def _flip(a, b, p):
    h, w = a.shape[:2]
    src, k = (a, np.cos(np.pi * p)) if p < 0.5 else (b, -np.cos(np.pi * p))
    nw = max(1, int(w * abs(k)))
    out = np.zeros_like(a)
    x = (w - nw) // 2
    out[:, x:x + nw] = cv2.resize(src, (nw, h))
    return out


def _fade(a, b, p):
    return _mix(a, b, p)


TRANSITIONS = {
    'fade': _fade, 'wipe_left': _wipe_left, 'wipe_right': _wipe_right, 'wipe_up': _wipe_up,
    'wipe_down': _wipe_down, 'slide_left': _slide_left, 'slide_right': _slide_right,
    'zoom_in': _zoom_in, 'zoom_out': _zoom_out, 'rotate': _rotate, 'dissolve': _dissolve,
    'flash': _flash, 'blur': _blur, 'glitch': _glitch, 'split_h': _split_h, 'split_v': _split_v,
    'page_turn': _page_turn, 'swirl': _swirl, 'cube': _cube, 'flip': _flip,
}


def transition_frame(tid, a, b, p):
    """Blend outgoing a into incoming b. Unknown id -> hard cut at p>=1."""
    p = float(min(1.0, max(0.0, p)))
    if p <= 0.0 or tid not in TRANSITIONS:
        return a if p < 1.0 else b
    if p >= 1.0:
        return b
    if a.shape != b.shape:
        a = cv2.resize(a, (b.shape[1], b.shape[0]))
    p = p * p * (3 - 2 * p)  # smoothstep
    return np.ascontiguousarray(TRANSITIONS[tid](a, b, p))
