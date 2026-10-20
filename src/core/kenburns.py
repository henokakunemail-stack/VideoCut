"""
Ken Burns / Motion Blur / 3D Zoom effect engine.
All methods work on individual np.ndarray frames (BGR).
"""

import math
import numpy as np
import cv2
from typing import Tuple, Optional


class KenBurnsEngine:
    """Smooth pan + zoom effect (Ken Burns) applied frame by frame."""

    @staticmethod
    def apply(
        frame: np.ndarray,
        t: float,           # normalized time 0..1
        start_rect: Tuple[float, float, float, float] = (0.0, 0.0, 1.0, 1.0),
        end_rect:   Tuple[float, float, float, float] = (0.1, 0.1, 0.8, 0.8),
        easing: str = "ease_in_out",
    ) -> np.ndarray:
        """
        Crop and zoom frame according to Ken Burns path.
        start_rect / end_rect: (x, y, w, h) in 0..1 normalized coords.
        """
        e = KenBurnsEngine._ease(t, easing)
        x  = start_rect[0] + (end_rect[0] - start_rect[0]) * e
        y  = start_rect[1] + (end_rect[1] - start_rect[1]) * e
        w  = start_rect[2] + (end_rect[2] - start_rect[2]) * e
        h  = start_rect[3] + (end_rect[3] - start_rect[3]) * e

        fh, fw = frame.shape[:2]
        x0 = max(0, int(x * fw))
        y0 = max(0, int(y * fh))
        x1 = min(fw, int((x + w) * fw))
        y1 = min(fh, int((y + h) * fh))

        if x1 <= x0 or y1 <= y0:
            return frame

        cropped = frame[y0:y1, x0:x1]
        return cv2.resize(cropped, (fw, fh), interpolation=cv2.INTER_LINEAR)

    @staticmethod
    def _ease(t: float, mode: str) -> float:
        t = max(0.0, min(1.0, t))
        if mode == "linear":
            return t
        elif mode == "ease_in":
            return t * t
        elif mode == "ease_out":
            return 1.0 - (1.0 - t) ** 2
        else:  # ease_in_out
            return t * t * (3.0 - 2.0 * t)


class MotionBlurEngine:
    """Directional and zoom motion blur effects."""

    @staticmethod
    def directional(frame: np.ndarray, angle_deg: float = 0.0, strength: int = 15) -> np.ndarray:
        """Apply directional motion blur at given angle."""
        if strength < 1:
            return frame
        k = max(3, strength | 1)  # must be odd
        kernel = np.zeros((k, k), np.float32)
        center = k // 2
        rad = math.radians(angle_deg)
        dx = math.cos(rad)
        dy = math.sin(rad)
        for i in range(k):
            x = int(center + (i - center) * dx)
            y = int(center + (i - center) * dy)
            if 0 <= x < k and 0 <= y < k:
                kernel[y, x] = 1.0
        s = kernel.sum()
        if s > 0:
            kernel /= s
        return cv2.filter2D(frame, -1, kernel)

    @staticmethod
    def zoom(frame: np.ndarray, strength: float = 0.05) -> np.ndarray:
        """Radial zoom blur — simulates fast zoom."""
        if strength <= 0:
            return frame
        h, w = frame.shape[:2]
        acc = frame.astype(np.float32)
        steps = max(3, int(strength * 30))
        for i in range(1, steps + 1):
            s = 1.0 + (strength * i / steps)
            scaled = cv2.resize(frame, None, fx=s, fy=s)
            # Center crop back to original size
            sh, sw = scaled.shape[:2]
            cx, cy = sw // 2, sh // 2
            x0 = max(0, cx - w // 2)
            y0 = max(0, cy - h // 2)
            cropped = scaled[y0:y0 + h, x0:x0 + w]
            if cropped.shape[:2] != (h, w):
                cropped = cv2.resize(cropped, (w, h))
            acc += cropped.astype(np.float32)
        return (acc / (steps + 1)).clip(0, 255).astype(np.uint8)

    @staticmethod
    def horizontal(frame: np.ndarray, strength: int = 15) -> np.ndarray:
        return MotionBlurEngine.directional(frame, 0.0, strength)

    @staticmethod
    def vertical(frame: np.ndarray, strength: int = 15) -> np.ndarray:
        return MotionBlurEngine.directional(frame, 90.0, strength)

    @staticmethod
    def diagonal(frame: np.ndarray, strength: int = 15, angle: float = 45.0) -> np.ndarray:
        return MotionBlurEngine.directional(frame, angle, strength)


class ThreeDZoomEngine:
    """Fake 3D perspective zoom (barrel / pincushion distortion + zoom)."""

    @staticmethod
    def apply(
        frame: np.ndarray,
        zoom_factor: float = 1.05,
        rotation_x: float = 0.0,
        rotation_y: float = 0.0,
    ) -> np.ndarray:
        """
        Simple 3D-looking zoom with slight perspective warp.
        zoom_factor: 1.0 = no zoom, 1.1 = 10% zoom
        rotation_x / rotation_y: degrees, small values (< 15) look best
        """
        h, w = frame.shape[:2]
        if zoom_factor <= 1.0 and rotation_x == 0.0 and rotation_y == 0.0:
            return frame

        # Build perspective transform via cv2
        src_pts = np.float32([[0, 0], [w, 0], [w, h], [0, h]])

        rx = math.radians(rotation_x)
        ry = math.radians(rotation_y)
        ox = w / 2
        oy = h / 2
        d  = w  # focal depth

        dst_pts = []
        for px, py in [(0, 0), (w, 0), (w, h), (0, h)]:
            # Translate to center
            x = px - ox
            y = py - oy
            # Apply rotation offsets
            x_rot = x * math.cos(ry) + d * math.sin(ry)
            y_rot = y * math.cos(rx) + d * math.sin(rx)
            # Perspective divide
            z = d
            xp = ox + (x_rot / z) * d
            yp = oy + (y_rot / z) * d
            dst_pts.append([xp, yp])

        dst_pts = np.float32(dst_pts)
        M = cv2.getPerspectiveTransform(src_pts, dst_pts)

        warped = cv2.warpPerspective(frame, M, (w, h))

        # Apply zoom
        if zoom_factor != 1.0:
            new_w = int(w / zoom_factor)
            new_h = int(h / zoom_factor)
            x0 = (w - new_w) // 2
            y0 = (h - new_h) // 2
            cropped = warped[y0:y0 + new_h, x0:x0 + new_w]
            if cropped.size > 0:
                warped = cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LINEAR)

        return warped
