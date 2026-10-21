"""Optical-flow frame interpolation for smooth slow-motion (Farneback, CPU)."""

from collections import OrderedDict

import cv2
import numpy as np

_flow_cache = OrderedDict()   # (key, shape) -> (flow fwd, flow bwd) at full res
_MAX_H = 360                  # flow is estimated at <=360 px height (ponytail: raise for quality)


def _flows(f0, f1, key):
    ck = (key, f0.shape)
    hit = _flow_cache.get(ck) if key is not None else None
    if hit is not None:
        _flow_cache.move_to_end(ck)
        return hit
    h, w = f0.shape[:2]
    k = min(1.0, _MAX_H / h)
    sz = (max(8, int(w * k)), max(8, int(h * k)))
    g0 = cv2.cvtColor(cv2.resize(f0, sz, interpolation=cv2.INTER_AREA), cv2.COLOR_RGB2GRAY)
    g1 = cv2.cvtColor(cv2.resize(f1, sz, interpolation=cv2.INTER_AREA), cv2.COLOR_RGB2GRAY)
    args = (None, 0.5, 3, 15, 3, 5, 1.2, 0)
    ff = cv2.calcOpticalFlowFarneback(g0, g1, *args)
    fb = cv2.calcOpticalFlowFarneback(g1, g0, *args)
    up = lambda fl: cv2.resize(fl, (w, h)) / k
    out = (up(ff), up(fb))
    if key is not None:
        _flow_cache[ck] = out
        if len(_flow_cache) > 6:
            _flow_cache.popitem(last=False)
    return out


def _warp(img, flow, scale):
    """Backward-warp img by `scale * flow` (flow maps destination pixel -> source offset)."""
    h, w = img.shape[:2]
    gx, gy = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    mx = gx + flow[..., 0] * scale
    my = gy + flow[..., 1] * scale
    return cv2.remap(img, mx.astype(np.float32), my.astype(np.float32), cv2.INTER_LINEAR,
                     borderMode=cv2.BORDER_REPLICATE)


def interpolate(f0, f1, alpha: float, key=None):
    """Frame at fractional position alpha in (0,1) between RGB frames f0 and f1.
    Falls back to a plain blend if flow fails."""
    try:
        ff, fb = _flows(f0, f1, key)
        # flow ff: f0 -> f1. Pixel p at time alpha came from p - alpha*ff in f0 (approx),
        # and from p - (1-alpha)*fb in f1.
        a = _warp(f0, ff, -alpha)
        b = _warp(f1, fb, -(1 - alpha))
        return cv2.addWeighted(a, 1 - alpha, b, alpha, 0)
    except cv2.error:
        return cv2.addWeighted(f0, 1 - alpha, f1, alpha, 0)
