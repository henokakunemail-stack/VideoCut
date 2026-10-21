"""
Timeline <-> source time mapping (constant speed, speed curves, reverse, freeze).

Model: u in [0,1] is playback progress through the clip's source span (reverse flips the
source direction, not u). speed(u) is clip.speed, or a PCHIP curve through clip.speed_curve
[[u, speed], ...]. Timeline time maps to u by normalising the integral of 1/speed to the
clip's actual timeline duration, so the speed *profile* is honoured even if the stored
duration differs by a few ms (split rounding) from duration_ms().
"""

import numpy as np

from src.core.grading import _pchip

MIN_SPEED, MAX_SPEED = 0.1, 10.0
_N = 256
_cache = {}   # (L, speed, curve tuple) -> (u grid, normalised cumulative time 0..1, total ms)


def _curve_pts(curve):
    pts = sorted((min(1.0, max(0.0, float(a))), min(MAX_SPEED, max(MIN_SPEED, float(b)))) for a, b in curve or [])
    xs, ys = [], []
    for x, y in pts:
        if xs and x <= xs[-1] + 1e-6:
            continue
        xs.append(x); ys.append(y)
    return (np.array(xs), np.array(ys)) if len(xs) >= 2 else None


def speed_at(clip, u):
    """Speed multiplier at playback progress u (scalar or array)."""
    pts = _curve_pts(clip.speed_curve)
    if pts is None:
        return np.full_like(np.asarray(u, float), clip.speed or 1.0)
    return np.clip(_pchip(pts[0], pts[1], np.asarray(u, float)), MIN_SPEED, MAX_SPEED)


def _table(clip):
    L = max(0, clip.source_end - clip.source_start)
    key = (L, clip.speed, tuple(map(tuple, clip.speed_curve or ())))
    hit = _cache.get(key)
    if hit:
        return hit
    u = np.linspace(0.0, 1.0, _N + 1)
    inv = 1.0 / speed_at(clip, u)
    cum = np.concatenate([[0.0], np.cumsum((inv[1:] + inv[:-1]) / 2 * np.diff(u))])
    total = float(cum[-1] * L)
    out = (u, cum / cum[-1], total)
    if len(_cache) > 64:
        _cache.clear()
    _cache[key] = out
    return out


def is_timed(clip) -> bool:
    from src.core.project import ClipType
    return clip.clip_type in (ClipType.VIDEO, ClipType.AUDIO)


def duration_ms(clip) -> int:
    """Timeline duration implied by the source span and speed settings."""
    if not is_timed(clip) or clip.freeze:
        return clip.duration
    return max(1, int(round(_table(clip)[2])))


def progress_at(clip, time_ms: float) -> float:
    """Timeline time -> playback progress u in [0,1]."""
    f = min(1.0, max(0.0, (time_ms - clip.timeline_start) / max(1, clip.duration)))
    if not clip.speed_curve:
        return f
    u, c, _ = _table(clip)
    return float(np.interp(f, c, u))


def source_ms(clip, time_ms: float) -> float:
    """Timeline time -> source media time (ms, fractional)."""
    if clip.freeze:
        return float(clip.source_start)
    L = clip.source_end - clip.source_start
    u = progress_at(clip, time_ms)
    return clip.source_end - u * L if clip.reverse else clip.source_start + u * L


def crop_curve(curve, u0, u1):
    """Speed curve restricted to progress [u0,u1], re-based to [0,1]."""
    class _C:  # minimal clip-like for speed_at
        speed, speed_curve = 1.0, curve
    if not curve or u1 - u0 < 1e-6:
        return []
    inner = [p for p in curve if u0 + 1e-3 < p[0] < u1 - 1e-3]
    ends = speed_at(_C, np.array([u0, u1]))
    return ([[0.0, float(ends[0])]] + [[(p[0] - u0) / (u1 - u0), p[1]] for p in inner]
            + [[1.0, float(ends[1])]])


def audio_segments(clip, max_segments=16):
    """Constant-speed pieces in playback order: (src_lo_ms, src_hi_ms, reversed, speed).
    Each piece occupies an equal share of the clip's timeline duration."""
    L = clip.source_end - clip.source_start
    dur = max(1, clip.duration)
    if L <= 0 or clip.freeze:
        return []
    n = 1 if not clip.speed_curve else max_segments
    segs = []
    for k in range(n):
        u0 = progress_at_frac(clip, k / n)
        u1 = progress_at_frac(clip, (k + 1) / n)
        a, b = u0 * L, u1 * L
        lo, hi = ((clip.source_end - b, clip.source_end - a) if clip.reverse
                  else (clip.source_start + a, clip.source_start + b))
        if hi - lo < 1:
            continue
        segs.append((lo, hi, clip.reverse, (hi - lo) / (dur / n)))
    return segs


def progress_at_frac(clip, f):
    return progress_at(clip, clip.timeline_start + f * max(1, clip.duration))
