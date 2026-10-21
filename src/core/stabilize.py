"""Video stabilisation: track camera motion (LK optical flow + RANSAC similarity), smooth the
trajectory, store per-frame corrections in clip.stabilize. Applied by renderer._layer on the raw
source frame, indexed by source time, so it is independent of speed/reverse.

ponytail: transforms live inline in the project JSON (~24 bytes/frame); move to a sidecar .npy for
hour-long clips. Rolling-shutter and 3D parallax are not modelled (needs a mesh warp)."""

import math

import cv2
import numpy as np

LEVELS = {"low": 5, "medium": 15, "high": 30}     # moving-average radius, frames
_MAX_H = 480


def analyze(path, start_ms, end_ms, level="medium", progress=None, cancelled=None):
    """Return a clip.stabilize dict, or None when cancelled/unreadable."""
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        return None
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    cap.set(cv2.CAP_PROP_POS_MSEC, start_ms)
    n_total = max(1, int((end_ms - start_ms) / 1000.0 * fps))
    motion, prev, scale = [], None, 1.0
    for i in range(n_total):
        if cancelled and cancelled():
            cap.release()
            return None
        ok, bgr = cap.read()
        if not ok:
            break
        g = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        if i == 0:
            scale = min(1.0, _MAX_H / g.shape[0])
            w0, h0 = bgr.shape[1], bgr.shape[0]
        if scale < 1.0:
            g = cv2.resize(g, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        d = (0.0, 0.0, 0.0)
        if prev is not None:
            pts = cv2.goodFeaturesToTrack(prev, 300, 0.01, 12)
            if pts is not None and len(pts) >= 6:
                nxt, st, _ = cv2.calcOpticalFlowPyrLK(prev, g, pts, None)
                st = st.ravel() == 1
                if st.sum() >= 6:
                    M, _ = cv2.estimateAffinePartial2D(pts[st], nxt[st], method=cv2.RANSAC)
                    if M is not None:
                        d = (M[0, 2] / scale, M[1, 2] / scale, math.atan2(M[1, 0], M[0, 0]))
        motion.append(d)
        prev = g
        if progress and i % 8 == 0:
            progress(int(100 * i / n_total))
    cap.release()
    if len(motion) < 2:
        return None
    raw = np.cumsum(np.array(motion, float), axis=0)
    r = LEVELS.get(level, 15)
    pad = np.pad(raw, ((r, r), (0, 0)), mode="edge")
    k = np.ones(2 * r + 1) / (2 * r + 1)
    smooth = np.stack([np.convolve(pad[:, c], k, mode="valid") for c in range(3)], axis=1)
    corr = smooth - raw
    zoom = 1.0 + 2 * max(np.abs(corr[:, 0]).max() / w0, np.abs(corr[:, 1]).max() / h0) \
        + 2 * np.abs(corr[:, 2]).max()
    zoom = float(min(1.3, zoom + 0.01))
    if progress:
        progress(100)
    return {"level": level, "fps": float(fps), "start_ms": int(start_ms), "path": path, "zoom": zoom,
            "transforms": [[round(a / w0, 6), round(b / w0, 6), round(c, 6)] for a, b, c in corr]}


def apply(frame, st, src_ms):
    """Warp a raw source frame with the stored correction for source time src_ms."""
    tr = st.get("transforms")
    if not tr:
        return frame
    i = int(round((src_ms - st["start_ms"]) / 1000.0 * st["fps"]))
    dx, dy, da = tr[max(0, min(len(tr) - 1, i))]
    h, w = frame.shape[:2]
    c, s = math.cos(da), math.sin(da)
    z = st.get("zoom", 1.0)
    M = np.array([[c * z, -s * z, 0], [s * z, c * z, 0]], np.float64)
    M[:, 2] = np.array([w / 2, h / 2]) - M[:, :2] @ np.array([w / 2, h / 2]) + (dx * w, dy * w)
    return cv2.warpAffine(frame, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
