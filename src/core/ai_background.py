"""
AI Background Removal — rembg with OpenCV GrabCut/threshold fallback
"""
import numpy as np
import cv2

REMBG_AVAILABLE = False
try:
    from rembg import remove as rembg_remove
    REMBG_AVAILABLE = True
except ImportError:
    pass


class AIBackground:
    """Background removal: AI (rembg) or OpenCV fallback."""

    @staticmethod
    def remove_background(frame: np.ndarray, method: str = "ai") -> np.ndarray:
        """
        Remove background from BGR frame.
        Returns BGRA (alpha = foreground mask).
        method: 'ai' | 'grabcut' | 'threshold'
        """
        if method == "ai" and REMBG_AVAILABLE:
            return AIBackground._rembg_remove(frame)
        elif method == "grabcut":
            return AIBackground._grabcut_remove(frame)
        else:
            return AIBackground._threshold_remove(frame)

    @staticmethod
    def _rembg_remove(frame: np.ndarray) -> np.ndarray:
        try:
            from PIL import Image
            import io
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb)
            result = rembg_remove(pil_img)
            result_np = np.array(result)  # RGBA
            return cv2.cvtColor(result_np, cv2.COLOR_RGBA2BGRA)
        except Exception:
            return AIBackground._grabcut_remove(frame)

    @staticmethod
    def _grabcut_remove(frame: np.ndarray, iterations: int = 5) -> np.ndarray:
        h, w = frame.shape[:2]
        mask = np.zeros((h, w), np.uint8)
        mx, my = max(1, w // 10), max(1, h // 10)
        rect = (mx, my, w - 2 * mx, h - 2 * my)
        bgd = np.zeros((1, 65), np.float64)
        fgd = np.zeros((1, 65), np.float64)
        try:
            cv2.grabCut(frame, mask, rect, bgd, fgd, iterations, cv2.GC_INIT_WITH_RECT)
            fg = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
        except Exception:
            fg = np.ones((h, w), np.uint8) * 255
        fg = cv2.GaussianBlur(fg, (5, 5), 0)
        bgra = cv2.cvtColor(frame, cv2.COLOR_BGR2BGRA)
        bgra[:, :, 3] = fg
        return bgra

    @staticmethod
    def _threshold_remove(frame: np.ndarray,
                           lower=(35, 50, 50), upper=(85, 255, 255)) -> np.ndarray:
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, np.array(lower, np.uint8), np.array(upper, np.uint8))
        fg = cv2.bitwise_not(mask)
        fg = cv2.GaussianBlur(fg, (5, 5), 0)
        bgra = cv2.cvtColor(frame, cv2.COLOR_BGR2BGRA)
        bgra[:, :, 3] = fg
        return bgra

    @staticmethod
    def composite_on_background(fg_bgra: np.ndarray,
                                  bg: np.ndarray | None) -> np.ndarray:
        h, w = fg_bgra.shape[:2]
        if bg is None:
            canvas = np.zeros((h, w, 3), np.uint8)
        else:
            canvas = cv2.resize(bg, (w, h))
            if canvas.ndim == 2:
                canvas = cv2.cvtColor(canvas, cv2.COLOR_GRAY2BGR)
        alpha = fg_bgra[:, :, 3:4].astype(np.float32) / 255.0
        fg = fg_bgra[:, :, :3].astype(np.float32)
        out = fg * alpha + canvas.astype(np.float32) * (1.0 - alpha)
        return np.clip(out, 0, 255).astype(np.uint8)

    @staticmethod
    def is_ai_available() -> bool:
        return REMBG_AVAILABLE
